"""
扫描核心模块
实现URL扫描的核心功能
"""
import csv
import queue
import re
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import chardet
import requests
from bs4 import BeautifulSoup

from .config import ScannerConfig
from .output_handler import OutputHandler
from .sensitive_detector import SensitiveDetector
from .url_matcher import URLMatcher, domain_matches
from .utils import DebugMixin, Fore, Style, output_lock, BloomFilter


class UltimateURLScanner(DebugMixin):
    """终极URL扫描器 - 核心扫描类"""

    # 全局共享的已访问URL布隆过滤器和锁
    visited_urls_global = BloomFilter(expected_elements=1000000, false_positive_rate=0.001)
    visited_urls_lock = threading.Lock()

    def __init__(self, config):
        self.config = config
        self.debug_mode = config.debug_mode

        # 请求链接计数器
        self.request_count = 0
        self.request_count_lock = threading.Lock()
        self.max_requests = config.max_urls

        # 初始化连接池
        self._init_connection_pool()

        # 初始化队列和状态
        self._init_queues_and_state()

        # 初始化组件
        self._init_components()

        if self.config.debug_mode:
            self._debug_print("扫描器初始化完成")

    def _init_connection_pool(self):
        """初始化连接池配置"""
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        # 创建会话并配置连接池
        self.session = requests.Session()

        # 配置连接池大小 - 根据线程数调整
        pool_size = max(50, self.config.max_workers * 2)
        max_pool_size = max(100, self.config.max_workers * 3)

        # 创建HTTP适配器
        adapter = HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=max_pool_size,
            max_retries=Retry(
                total=3,
                backoff_factor=0.1,
                status_forcelist=[500, 502, 503, 504]
            )
        )

        # 为HTTP和HTTPS都配置适配器
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        # 设置会话头
        self.session.headers = self.config.headers

        # 设置连接超时和读取超时
        self.session.timeout = (self.config.timeout, self.config.timeout)

        if self.config.debug_mode:
            self._debug_print(f"连接池配置: pool_connections={pool_size}, pool_maxsize={max_pool_size}")
            self._debug_print(f"最大请求数配置: max_requests={self.max_requests}")

    def _init_queues_and_state(self):
        """初始化队列和状态变量"""
        self.url_queue = queue.Queue()
        self.results = []
        self.lock = threading.Lock()
        self.running = True
        self.duplicate_urls = set()
        self.url_request_count = {}
        self.out_of_domain_urls = []
        self.external_urls = set()
        self.external_urls_lock = threading.Lock()
        self.external_url_queue = queue.Queue()
        self.external_results = []
        self.external_running = True

    def _init_components(self):
        """初始化扫描组件"""
        self.url_matcher = URLMatcher(self.config, scanner=self)
        self.sensitive_detector = SensitiveDetector(self.config.sensitive_patterns, self.config.debug_mode)
        self.output_handler = OutputHandler(self.config)

    def _check_request_limits(self):
        """检查请求限制，返回是否应该继续处理"""
        # 检查URL数量限制
        if self.output_handler.url_count >= self.config.max_urls:
            self._debug_print(f"达到最大URL数量限制: {self.output_handler.url_count}/{self.config.max_urls}")
            return False

        # 检查请求数量限制
        with self.request_count_lock:
            if self.request_count >= self.max_requests:
                self._debug_print(f"达到最大请求数限制: {self.request_count}/{self.max_requests}")
                return False

        return True

    def _periodic_cleanup(self, processed_count, last_cleanup_time):
        """定期清理连接池"""
        current_time = time.time()
        if processed_count % 1000 == 0 and processed_count > 0 and (current_time - last_cleanup_time) > 60:
            try:
                self._cleanup_connections()
                self._debug_print(f"定期清理连接池 - 线程: {threading.current_thread().name}")
                return current_time
            except Exception as e:
                self._debug_print(f"清理连接池失败: {type(e).__name__}: {e} - 线程: {threading.current_thread().name}")

        return last_cleanup_time

    def _safe_queue_get(self, queue_obj, timeout=10):
        """安全地从队列获取项目"""
        try:
            return queue_obj.get(timeout=timeout)
        except queue.Empty:
            return None
        except Exception as e:
            self._debug_print(f"队列获取异常: {type(e).__name__}: {e}")
            return None

    def _safe_queue_task_done(self, queue_obj):
        """安全地标记队列任务完成"""
        try:
            queue_obj.task_done()
        except Exception as e:
            self._debug_print(f"task_done异常: {e}")

    def _process_url_result(self, url, depth, result, result_list, lock=None):
        """统一处理URL扫描结果"""
        if result:
            if lock:
                with lock:
                    result_list.append(result)
            else:
                result_list.append(result)
            self._debug_print(f"成功处理URL: {url}")
            return True
        else:
            self._debug_print(f"URL处理返回None: {url}")
            return False

    def _http_request(self, url):
        """统一的HTTP请求和异常处理，返回response或异常信息"""
        max_retries = 3
        response = None
        last_exception = None

        # 域名过滤逻辑：白名单优先（可覆盖黑名单），然后黑名单
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc

        # 优先检查白名单（白名单可以覆盖黑名单）
        in_whitelist = False
        if self.config.whitelist_domains:
            for white_domain in self.config.whitelist_domains:
                if domain_matches(white_domain, domain):
                    in_whitelist = True
                    self._debug_print(f"[_http_request] 域名在白名单中 (覆盖黑名单): {url} (匹配: {white_domain})")
                    break
            else:
                # scope模式3：不在白名单中则拒绝
                if self.config.url_scope_mode == 3:
                    self._debug_print(f"[_http_request] 域名不在白名单中 (scope模式3)，跳过请求: {url}")
                    return None, Exception(f"域名不在白名单中: {url}")

        # 检查黑名单（使用精确域名匹配），但跳过白名单中的域名
        if not in_whitelist:
            for black_domain in self.config.blacklist_domains:
                if domain_matches(black_domain, domain):
                    self._debug_print(f"[_http_request] 域名在黑名单中，跳过请求: {url} (匹配: {black_domain})")
                    return None, Exception(f"域名在黑名单中: {url}")

        # 检查请求数量限制
        with self.request_count_lock:
            if self.request_count >= self.max_requests:
                self._debug_print(f"[_http_request] 达到最大请求数限制: {self.request_count}/{self.max_requests}")
                return None, Exception("达到最大请求数限制")
            self.request_count += 1
            current_request_count = self.request_count

        # 输出当前线程情况
        try:
            self._debug_print(f"[_http_request] 开始请求: {url} (请求计数: {current_request_count}/{self.max_requests})\n"
                            f"[_http_request] 配置: proxy={self.config.proxy}, timeout={self.config.timeout}\n"
                            f"[_http_request] 目前线程和队列情况: {threading.active_count()}, 主队列: {self.url_queue.qsize()}, 外部队列: {self.external_url_queue.qsize()}")
        except Exception as e:
            self._debug_print(f"[_http_request] 输出请求信息失败: {type(e).__name__}: {e}")

        for attempt in range(max_retries):
            try:
                self._debug_print(f"[_http_request] 第{attempt+1}次尝试请求: {url}")

                # 使用会话的超时设置
                response = self.session.get(
                    url,
                    timeout=self.config.timeout,
                    proxies=self.config.proxy,
                    verify=False,
                    allow_redirects=True
                )

                self._debug_print(f"[_http_request] 请求成功: url={url}, status_code={response.status_code}, elapsed={response.elapsed}")

                return response, None

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                   requests.exceptions.SSLError, requests.exceptions.RequestException) as e:
                last_exception = e
                self._debug_print(f"[_http_request] 网络异常 (第{attempt+1}次): {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)

            except requests.exceptions.TooManyRedirects as e:
                last_exception = e
                self._debug_print(f"[_http_request] 重定向过多: {e}")
                break

            except Exception as e:
                last_exception = e
                self._debug_print(f"[_http_request] 未知异常 (第{attempt+1}次): {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)

        self._debug_print(f"[_http_request] 所有重试失败: {type(last_exception).__name__}: {last_exception}")

        return None, last_exception

    def _cleanup_connections(self):
        """清理连接池中的连接"""
        try:
            if hasattr(self.session, 'poolmanager'):
                self.session.poolmanager.clear()
                self._debug_print("连接池已清理")
        except Exception as e:
            self._debug_print(f"清理连接池时出错: {type(e).__name__}: {e}")

    def get_request_stats(self):
        """获取请求统计信息"""
        with self.request_count_lock:
            return {
                'current_requests': self.request_count,
                'max_requests': self.max_requests,
                'remaining_requests': max(0, self.max_requests - self.request_count),
                'url_count': self.output_handler.url_count,
                'max_urls': self.config.max_urls
            }

    def _build_result(self, url, response=None, error=None, depth=0):
        """统一构建扫描结果字典"""
        self._debug_print(f"[_build_result] 开始构建结果: url={url}, depth={depth}, response={response is not None}, error={error}")

        # 初始化结果字段
        elapsed = 0
        redirect_chain = []
        final_url = url
        sensitive_info = []
        status = 'Err'
        title = ''
        content = ''
        content_type = ''
        headers_info = {}

        if response is not None:
            # 处理成功的响应
            elapsed = self._extract_response_time(response)
            redirect_chain = self._extract_redirect_chain(response)
            final_url = self._extract_final_url(response, url)
            content = self._extract_response_content(response)
            headers_info, content_type = self._extract_headers_info(response)
            sensitive_info = self._detect_sensitive_info(content)
            status = self._extract_status_code(response)
            title = self._extract_title(response)
        elif error is not None:
            # 处理错误情况
            status = self._format_error_status(error)
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 处理错误: {type(error).__name__}: {error}")
        else:
            # 处理异常情况
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 警告: response和error都为None")
            status = "Error: No response and no error"

        # 构建结果字典
        result = {
            'url': final_url,
            'status': status,
            'title': title,
            'length': len(content),
            'redirects': ' → '.join([str(x) for x in redirect_chain]),
            'depth': depth,
            'time': elapsed,
            'sensitive': sensitive_info,
            'sensitive_raw': sensitive_info,
            'is_duplicate': False,
            'content_type': content_type,
            'headers_count': len(headers_info),
            'error_type': type(error).__name__ if error else None,
            'original_url': url,
        }

        if self.config.debug_mode:
            self._debug_print(f"[_build_result] 结果构建完成: status={status}, length={len(content)}, sensitive_count={len(sensitive_info)}")

        return result

    def _extract_response_time(self, response):
        """提取响应时间"""
        try:
            elapsed = getattr(response, 'elapsed', None)
            if elapsed:
                elapsed = elapsed.total_seconds()
            else:
                elapsed = 0
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 响应时间: {elapsed}秒")
            return elapsed
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 获取响应时间失败: {e}")
            return 0

    def _extract_redirect_chain(self, response):
        """提取重定向链"""
        try:
            redirect_chain = [r.url for r in response.history] if response.history else []
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 重定向链: {len(redirect_chain)} 个重定向")
            return redirect_chain
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 获取重定向链失败: {e}")
            return []

    def _extract_final_url(self, response, original_url):
        """提取最终URL"""
        try:
            final_url = response.url
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 最终URL: {final_url}")
            return final_url
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 获取最终URL失败: {e}, 使用原始URL: {original_url}")
            return original_url

    def _extract_response_content(self, response):
        """提取响应内容"""
        try:
            # 默认先用 requests 推断的编码
            content_bytes = response.content
            encoding = None

            # 优先用 response.encoding（但有些网站会错误地标成 ISO-8859-1）
            if response.encoding and response.encoding.lower() != 'iso-8859-1':
                encoding = response.encoding
            else:
                # 用 chardet 检测编码
                detected = chardet.detect(content_bytes)
                encoding = detected.get('encoding', 'utf-8')

            try:
                content = content_bytes.decode(encoding, errors='replace')
            except Exception:
                # 兜底用 utf-8
                content = content_bytes.decode('utf-8', errors='replace')

            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 响应内容长度: {len(content)} 字节, 编码: {encoding}")
            return content
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 获取响应内容失败: {e}")
            return ''

    def _extract_headers_info(self, response):
        """提取响应头信息"""
        try:
            headers_info = dict(response.headers) if hasattr(response, 'headers') else {}
            content_type = headers_info.get('Content-Type', '')
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] Content-Type: {content_type}")
            return headers_info, content_type
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 获取响应头失败: {e}")
            return {}, ''

    def _detect_sensitive_info(self, content):
        """检测敏感信息"""
        try:
            sensitive_info = self.sensitive_detector.detect(content)
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 敏感信息检测结果: {len(sensitive_info)} 项")
            return sensitive_info
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 敏感信息检测失败: {e}")
            return []

    def _extract_status_code(self, response):
        """提取状态码"""
        try:
            status = getattr(response, 'status_code', 'Err')
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 状态码: {status}")
            return status
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 获取状态码失败: {e}")
            return 'Err'

    def _extract_title(self, response):
        """提取页面标题"""
        try:
            if response.status_code != 200:
                return f"请求失败，状态码: {response.status_code}"

            # 检测响应内容的编码
            raw_content = response.content

            detected_encoding = chardet.detect(raw_content)['encoding']
            self._debug_print(f"chardet检测到的编码: {detected_encoding}")

            # 尝试使用不同编码解码
            encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'utf-16']
            if detected_encoding and detected_encoding not in encodings_to_try:
                encodings_to_try.append(detected_encoding)

            best_title = None

            for encoding in encodings_to_try:
                try:
                    content = raw_content.decode(encoding)
                    soup = BeautifulSoup(content, 'html.parser')
                    title = soup.title.string.strip() if soup.title else ''

                    if best_title is None or len(title) > len(best_title):
                        best_title = title
                except UnicodeDecodeError:
                    continue

            best_title = str(best_title).strip().replace('\n', '').replace('\r', '')
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 提取到标题: {best_title[:50]}...")

            return best_title if best_title else ''

        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"[_build_result] 标题提取失败: {e}")
            return ''

    def _format_error_status(self, error):
        """格式化错误状态"""
        error_type = type(error).__name__
        error_msg = str(error)

        if isinstance(error, requests.exceptions.ConnectionError):
            return f"ConnectionError: {error_msg}"
        elif isinstance(error, requests.exceptions.Timeout):
            return f"TimeoutError: {error_msg}"
        elif isinstance(error, requests.exceptions.SSLError):
            return f"SSLError: {error_msg}"
        elif isinstance(error, requests.exceptions.TooManyRedirects):
            return f"TooManyRedirects: {error_msg}"
        elif isinstance(error, requests.exceptions.RequestException):
            return f"RequestError: {error_msg}"
        else:
            return f"Error({error_type}): {error_msg}"

    def _extract_and_process_urls(self, content, base_url, depth):
        """提取和处理URL的统一方法"""
        if not content:
            self._debug_print(f"无法获取内容，跳过URL提取: {base_url}")
            return

        try:
            new_urls = self.url_matcher.extract_urls(content, base_url)
            self._debug_print(f"从内容中提取到 {len(new_urls)} 个新URL")
        except Exception as e:
            self._debug_print(f"内容URL提取异常: {type(e).__name__}: {e}, url={base_url}, depth={depth}")
            new_urls = []

        # 处理新URL
        added_count = 0
        skipped_count = 0
        error_count = 0

        for new_url in new_urls:
            try:
                with UltimateURLScanner.visited_urls_lock:
                    if new_url not in UltimateURLScanner.visited_urls_global and not self.url_matcher.should_skip_url(new_url):
                        self.url_queue.put((new_url, depth + 1))
                        UltimateURLScanner.visited_urls_global.add(new_url)
                        added_count += 1
                    else:
                        skipped_count += 1
            except Exception as e:
                error_count += 1
                self._debug_print(f"新URL入队异常: {type(e).__name__}: {e}, url={base_url}, depth={depth}, new_url={new_url}")

        self._debug_print(f"URL处理统计: 添加={added_count}, 跳过={skipped_count}, 错误={error_count}")

    def scan_url(self, url, depth=0):
        """扫描单个URL"""
        if self.config.debug_mode:
            self._debug_print(f"[scan_url] 开始扫描: url={url}, depth={depth}")

        # 预检查URL是否应该扫描
        check_result = self._pre_check_url(url, depth)
        if check_result is not None:
            return check_result

        if self.config.debug_mode:
            self._debug_print(f"[scan_url] 开始扫描URL: {url} (深度: {depth})")

        # 延迟处理
        time.sleep(self.config.delay)

        # HTTP请求
        response, error = self._http_request(url)

        # 输出请求统计信息（仅在debug模式下）
        self._log_request_stats()

        # 构建结果
        result = self._build_result(url, response, error, depth)

        # 实时输出
        self._realtime_output_result(result)

        # === 内联提取内容/TOC ===
        if response and response.status_code == 200:
            self._inline_extract_content(result, response)
        # === END 内联提取 ===

        # 递归内容提取
        self._recursive_extract_urls(response, result, depth)

        if self.config.debug_mode:
            self._debug_print(f"[scan_url] 扫描完成: url={url}, status={result.get('status', 'Unknown')}")

        return result

    def _is_dangerous_url(self, url):
        """检查URL是否为危险接口"""
        if not self.config.danger_filter_enabled:
            return False

        # 排除JS文件
        if url.endswith(".js"):
            return False

        for danger_api in self.config.danger_api_list:
            if danger_api.lower() in url.lower():
                return danger_api
        return False

    def _is_allowed_by_api_list(self, url):
        """检查URL是否匹配allowed_api_list中的模式"""
        if not self.config.allowed_api_list:
            return True

        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()
        full_url = url.lower()

        for pattern in self.config.allowed_api_list:
            pattern_lower = pattern.lower()
            if pattern_lower in path or pattern_lower in full_url:
                return True

        return False

    def _pre_check_url(self, url, depth):
        """预检查URL是否应该扫描

        过滤规则（按优先级）：
        1. 白名单域名（可覆盖黑名单）
        2. 黑名单域名（跳过不在白名单中的）
        3. 扩展名黑名单
        4. 排除规则（exclude_fuzzy）
        5. 危险接口列表（danger_api_list）
        6. 允许的API列表（allowed_api_list）- 必须匹配才扫描
        """
        # 检查扫描状态
        if not self.running or depth > self.config.max_depth:
            if self.config.debug_mode:
                self._debug_print(f"[scan_url] 跳过URL扫描: {url} (深度: {depth}, 最大深度: {self.config.max_depth}, running: {self.running})")
            return None

        # 域名过滤逻辑：白名单优先（可覆盖黑名单），然后黑名单
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc

        # 优先检查白名单（白名单可以覆盖黑名单）
        in_whitelist = False
        if self.config.whitelist_domains:
            for white_domain in self.config.whitelist_domains:
                if domain_matches(white_domain, domain):
                    in_whitelist = True
                    self._debug_print(f"[scan_url] 域名在白名单中 (覆盖黑名单): {url} (匹配: {white_domain})")
                    break
            else:
                # scope模式3：不在白名单中则拒绝
                if self.config.url_scope_mode == 3:
                    self._debug_print(f"[scan_url] 域名不在白名单中 (scope模式3)，跳过扫描: {url}")
                    return None

        # 检查黑名单（使用精确域名匹配），但跳过白名单中的域名
        if not in_whitelist:
            for black_domain in self.config.blacklist_domains:
                if domain_matches(black_domain, domain):
                    self._debug_print(f"[scan_url] 域名在黑名单中，跳过扫描: {url} (匹配: {black_domain})")
                    return None

        # 检查扩展名黑名单
        if self.url_matcher.should_skip_url(url):
            if self.config.debug_mode:
                self._debug_print(f"[scan_url] URL因扩展名黑名单跳过: {url}")
            return None

        # 检查排除规则（exclude_fuzzy）
        if self.url_matcher.should_exclude_fuzzy(url):
            if self.config.debug_mode:
                self._debug_print(f"[scan_url] URL因排除规则跳过: {url}")
            return None

        # 检查危险接口列表（danger_api_list）
        if self.config.danger_filter_enabled:
            danger_api = self._is_dangerous_url(url)
            if danger_api:
                self._debug_print(f"[scan_url] URL因危险接口跳过: {url} (匹配: {danger_api})")
                return None

        # 检查允许的API列表（allowed_api_list）- 必须匹配才扫描
        if not self._is_allowed_by_api_list(url):
            if self.config.debug_mode:
                self._debug_print(f"[scan_url] URL不匹配allowed_api_list模式，跳过扫描: {url}")
            return None

        # url_scope_mode 0: 只允许主域/子域
        if self.config.url_scope_mode == 0:
            if not self.url_matcher.is_valid_domain(url):
                if self.config.debug_mode:
                    self._debug_print(f"[scan_url] 外部URL跳过: {url}")
                return None

        # url_scope_mode 1: 外部链接访问一次，不递归
        elif self.config.url_scope_mode == 1:
            return self._handle_external_url_once(url, depth)

        return None

    def _handle_external_url_once(self, url, depth):
        """处理只访问一次的外部URL"""
        if not self.url_matcher.is_valid_domain(url):
            with UltimateURLScanner.visited_urls_lock:
                if url in UltimateURLScanner.visited_urls_global:
                    if self.config.debug_mode:
                        self._debug_print(f"[scan_url] 外部URL已访问过: {url}")
                    return None
                UltimateURLScanner.visited_urls_global.add(url)
            if self.config.debug_mode:
                self._debug_print(f"[scan_url] 外部URL只访问一次: {url}")
            response, error = self._http_request(url)
            result = self._build_result(url, response, error, depth)
            try:
                self.output_handler.realtime_output(result)
            except Exception as e:
                if self.config.debug_mode:
                    self._debug_print(f"[scan_url] 外部URL输出失败: {e}")
            return result
        return None

    def _log_request_stats(self):
        """记录请求统计信息"""
        if self.config.debug_mode:
            stats = self.get_request_stats()
            self._debug_print(f"[scan_url] 请求统计: {stats['current_requests']}/{stats['max_requests']} 请求, {stats['url_count']}/{stats['max_urls']} URL")

    def _inline_extract_content(self, result, response):
        """
        在扫描过程中实时提取内容和TOC，避免重复HTTP请求

        仅在 mode=1/2/3 且 enable_inline_extraction=1 时执行

        Args:
            result: 扫描结果字典
            response: HTTP响应对象
        """
        # 检查是否启用内联提取
        if not self.config.enable_inline_extraction:
            return

        # 检查模式
        if self.config.mode not in [1, 2, 3]:
            return

        # 检查响应状态
        if not response or response.status_code != 200:
            return

        try:
            from .content_extractor import ContentExtractor

            # 延迟初始化提取器（第一次调用时创建）
            if not hasattr(self, '_content_extractor'):
                self._content_extractor = ContentExtractor(self.config)

            # 执行内联提取
            self._content_extractor.extract_inline(result, response, mode=self.config.mode)

        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"内联提取失败: {e}")

    def _realtime_output_result(self, result):
        """实时输出结果"""
        try:
            self.output_handler.realtime_output(result)
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"[scan_url] 实时输出失败: {e}")

    def _recursive_extract_urls(self, response, result, depth):
        """递归提取URL"""
        if response is not None and depth < self.config.max_depth:
            try:
                content = getattr(response, 'content', b'')
                content_type = response.headers.get('Content-Type', '') if hasattr(response, 'headers') else ''

                if self.config.debug_mode:
                    self._debug_print(f"[scan_url] 开始从内容提取URL: {result['url']} (内容类型: {content_type}, 内容长度: {len(content)})")

                self._extract_and_process_urls(content, result['url'], depth)

            except Exception as e:
                if self.config.debug_mode:
                    self._debug_print(f"[scan_url] 递归处理异常: {type(e).__name__}: {e}, url={result.get('url', 'Unknown')}, depth={depth}")
        else:
            if self.config.debug_mode:
                if response is None:
                    self._debug_print(f"[scan_url] 响应为空，跳过递归")
                elif depth >= self.config.max_depth:
                    self._debug_print(f"[scan_url] 达到最大深度，跳过递归: depth={depth}, max_depth={self.config.max_depth}")

    def _worker_loop(self, queue_obj, result_list, lock=None, is_external=False):
        """统一的工作线程循环"""
        thread_name = threading.current_thread().name
        if self.config.debug_mode:
            self._debug_print(f"[worker_loop] {'外部URL' if is_external else '工作'}线程启动: {thread_name}")

        processed_count = 0
        error_count = 0
        last_cleanup_time = time.time()

        while (self.external_running if is_external else self.running) or not queue_obj.empty():
            try:
                item = self._get_and_process_queue_item(
                    queue_obj, result_list, lock, is_external, thread_name,
                    processed_count, last_cleanup_time)

                if item is False:
                    break

                if item is True:
                    processed_count += 1
                    last_cleanup_time = self._update_cleanup_time(processed_count, last_cleanup_time)

            except Exception as e:
                error_count += 1
                if self.config.debug_mode:
                    self._debug_print(f"[worker_loop] {'外部URL' if is_external else '工作'}线程主循环异常: {type(e).__name__}: {e}, 线程: {thread_name}")
                self._safe_queue_task_done(queue_obj)

        if self.config.debug_mode:
            self._debug_print(f"[worker_loop] {'外部URL' if is_external else '工作'}线程结束: {thread_name}, 处理={processed_count}, 错误={error_count}")

    def _get_and_process_queue_item(self, queue_obj, result_list, lock, is_external, thread_name, processed_count, last_cleanup_time):
        """获取并处理队列中的项目"""
        item = self._safe_queue_get(queue_obj, timeout=2 if is_external else 10)
        if not item:
            if not (self.external_running if is_external else self.running):
                if self.config.debug_mode:
                    self._debug_print(f"[worker_loop] {'外部URL' if is_external else '工作'}线程队列为空，退出: {thread_name}")
                return False
            return None

        url, depth = item if isinstance(item, tuple) else (item, 0)

        if not self._check_request_limits():
            if self.config.debug_mode:
                self._debug_print(f"[worker_loop] 达到限制，跳过扫描URL: {url} (深度: {depth}) - 线程: {thread_name}")
            self._safe_queue_task_done(queue_obj)
            return None

        last_cleanup_time = self._periodic_cleanup(processed_count, last_cleanup_time)

        if self.config.debug_mode:
            self._debug_print(f"[worker_loop] 处理URL: {url} (深度: {depth}) - 线程: {thread_name}")

        try:
            result = self.scan_url(url, depth)
            self._handle_scan_result(result, url, depth, result_list, lock, is_external)
            self._debug_print(f"成功处理URL: {url}")
            self._safe_queue_task_done(queue_obj)
            return True
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"[worker_loop] URL扫描异常: {type(e).__name__}: {e}, url={url}, depth={depth}, 线程={thread_name}")
            self._safe_queue_task_done(queue_obj)
            return None

    def _handle_scan_result(self, result, url, depth, result_list, lock, is_external):
        """处理扫描结果"""
        if is_external:
            if result is None:
                result = {
                    'url': url,
                    'status': '外部',
                    'title': '外部',
                    'length': 0,
                    'redirects': '',
                    'depth': depth,
                    'time': 0,
                    'sensitive': '',
                    'sensitive_raw': [],
                    'is_duplicate_signature': False,
                    'content_type': '',
                    'headers_count': 0,
                    'error_type': None,
                    'original_url': url,
                }
            if lock:
                with lock:
                    result_list.append(result)
            else:
                result_list.append(result)
        else:
            self._process_url_result(url, depth, result, result_list, lock)

    def _update_cleanup_time(self, processed_count, last_cleanup_time):
        """更新清理时间"""
        current_time = time.time()
        if processed_count % 1000 == 0 and processed_count > 0 and (current_time - last_cleanup_time) > 60:
            try:
                self._cleanup_connections()
                self._debug_print(f"定期清理连接池 - 线程: {threading.current_thread().name}")
                return current_time
            except Exception as e:
                self._debug_print(f"清理连接池失败: {type(e).__name__}: {e} - 线程: {threading.current_thread().name}")

        return last_cleanup_time

    def worker(self):
        """工作线程"""
        self._worker_loop(self.url_queue, self.results, self.lock, is_external=False)

    def external_worker(self):
        """外部URL工作线程"""
        self._worker_loop(self.external_url_queue, self.external_results, self.lock, is_external=True)

    def start_scan(self):
        """开始扫描过程"""
        if self.config.debug_mode:
            self._debug_print(f"[start_scan] 开始扫描过程: start_url={self.config.start_url}")
            stats = self.get_request_stats()
            self._debug_print(f"[start_scan] 初始配置: 最大请求数={stats['max_requests']}, 最大URL数={stats['max_urls']}")

        try:
            # 添加起始URL到队列
            self.url_queue.put((self.config.start_url, 0))
            if self.config.debug_mode:
                self._debug_print(f"[start_scan] 起始URL已加入队列: {self.config.start_url}")

            # 创建线程池
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                if self.config.debug_mode:
                    self._debug_print(f"[start_scan] 创建线程池，工作线程数: {self.config.max_workers}")

                # 启动工作线程
                workers = []
                try:
                    workers = [executor.submit(self.worker) for _ in range(min(self.config.max_workers, 100))]
                    if self.config.debug_mode:
                        self._debug_print(f"[start_scan] 已启动 {len(workers)} 个工作线程")
                except Exception as e:
                    if self.config.debug_mode:
                        self._debug_print(f"[start_scan] 启动工作线程失败: {type(e).__name__}: {e}")
                    raise

                # 等待所有任务完成
                try:
                    if self.config.debug_mode:
                        self._debug_print(f"[start_scan] 等待队列任务完成...")
                    self.url_queue.join()
                    if self.config.debug_mode:
                        self._debug_print(f"[start_scan] 队列任务已完成")
                except Exception as e:
                    if self.config.debug_mode:
                        self._debug_print(f"[start_scan] 等待队列完成时异常: {type(e).__name__}: {e}")

                # 停止扫描
                self.running = False
                if self.config.debug_mode:
                    self._debug_print(f"[start_scan] 扫描已停止，取消工作线程")

                # 取消工作线程
                for i, worker in enumerate(workers):
                    try:
                        worker.cancel()
                        if self.config.debug_mode:
                            self._debug_print(f"[start_scan] 已取消工作线程 {i+1}")
                    except Exception as e:
                        if self.config.debug_mode:
                            self._debug_print(f"[start_scan] 取消工作线程 {i+1} 失败: {e}")

                if self.config.debug_mode:
                    self._debug_print(f"[start_scan] 所有工作线程已处理")

                # 扫描结束时清理连接池
                try:
                    self._cleanup_connections()
                    if self.config.debug_mode:
                        self._debug_print(f"[start_scan] 扫描结束，连接池已清理")
                except Exception as e:
                    if self.config.debug_mode:
                        self._debug_print(f"[start_scan] 清理连接池失败: {type(e).__name__}: {e}")

        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"[start_scan] 扫描过程异常: {type(e).__name__}: {e}")
            self.running = False
            try:
                self._cleanup_connections()
                if self.config.debug_mode:
                    self._debug_print(f"[start_scan] 异常退出，连接池已清理")
            except Exception as cleanup_e:
                if self.config.debug_mode:
                    self._debug_print(f"[start_scan] 异常退出时清理连接池失败: {type(cleanup_e).__name__}: {cleanup_e}")
            raise

    def generate_report(self, report_file="full_report.csv"):
        """生成最终报告"""
        if self.config.debug_mode:
            self._debug_print(f"生成最终报告: {report_file}")
        self.output_handler.generate_report(self.results, report_file)

        if hasattr(self, 'external_urls'):
            with UltimateURLScanner.visited_urls_lock:
                unvisited = [u for u in self.external_urls if u not in UltimateURLScanner.visited_urls_global]
            if unvisited:
                print(f"{Fore.MAGENTA}=============================================={Style.RESET_ALL}")
                print(f"{Fore.MAGENTA}未访问的外部URL如下:\n{Style.RESET_ALL}")
                self.output_handler.output_external_unvisited(unvisited, report_file)
                print(f"\n{Fore.MAGENTA}外部URL已经追加到报告文件: {report_file}{Style.RESET_ALL}")

    def _generate_report_filename(self):
        """生成报告文件名"""
        parsed_url = urllib.parse.urlparse(self.config.start_url)
        domain = parsed_url.netloc or self.config.start_url
        domain = domain.split(':')[0]
        domain = re.sub(r'[^a-zA-Z0-9.]', '', domain)
        dt_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"results/{domain}_{dt_str}.csv"

    def _handle_scan_completion(self, start_time, external_thread):
        """处理扫描完成后的清理工作"""
        try:
            report_filename = self._generate_report_filename()

            if self.config.debug_mode:
                print(f"{Fore.CYAN}[start_scanning] 生成报告: {report_filename}{Style.RESET_ALL}")

            self.generate_report(report_filename)
            total_time = time.time() - start_time

            if total_time > 0:
                avg_speed = self.output_handler.url_count / total_time
            else:
                avg_speed = 0

            # 输出所有发现的危险链接
            if URLMatcher.danger_api_filtered:
                with output_lock:
                    print(f"\n{Fore.MAGENTA}=== 扫描过程中发现的危险链接汇总 ==={Style.RESET_ALL}")
                    print(f"{Fore.MAGENTA}共发现 {len(URLMatcher.danger_api_filtered)} 个危险链接:{Style.RESET_ALL}")
                    for i, danger_url in enumerate(sorted(URLMatcher.danger_api_filtered), 1):
                        print(f"{Fore.MAGENTA}[{i:3d}] {danger_url}{Style.RESET_ALL}")

                # 将危险链接写入CSV文件
                try:
                    with open(report_filename, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)

                        for i, danger_url in enumerate(sorted(URLMatcher.danger_api_filtered), 1):
                            danger_types = []
                            for danger_api in self.config.danger_api_list:
                                if danger_api in danger_url and not danger_url.endswith(".js"):
                                    danger_types.append(danger_api)

                            danger_type_str = ", ".join(danger_types) if danger_types else "未知"

                            writer.writerow([
                                danger_url,
                                '危险',
                                '危险接口',
                                0,
                                '危险',
                                '',
                                0,
                                danger_type_str,
                                '1',
                                f'危险接口: {danger_type_str}',
                                '否'
                            ])
                    print(f"{Fore.MAGENTA}\n危险链接已经追加到报告文件: {report_filename} \n {Style.RESET_ALL}")
                    if self.config.debug_mode:
                        self._debug_print(f"危险链接已经追加到报告文件: {report_filename}")

                except Exception as e:
                    if self.config.debug_mode:
                        self._debug_print(f"写入危险链接汇总到CSV文件时出错: {type(e).__name__}: {e}")
                    with output_lock:
                        print(f"{Fore.RED}写入危险链接汇总到CSV文件失败: {type(e).__name__}: {e}{Style.RESET_ALL}")
            else:
                with output_lock:
                    print(f"{Fore.YELLOW}=============================================={Style.RESET_ALL}")
                    print(f"{Fore.GREEN}未发现危险链接{Style.RESET_ALL}")

            print(f"{Fore.YELLOW}=============================================={Style.RESET_ALL}")
            print(f"{Fore.YELLOW}总耗时: {total_time:.2f}秒 | 平均速度: {avg_speed:.1f} URL/秒{Style.RESET_ALL}")
            print(f"{Fore.GREEN}扫描结束!{Style.RESET_ALL}")

            # 优雅关闭外部线程
            try:
                self.external_running = False
                external_thread.join(timeout=10)
                if self.config.debug_mode:
                    print(f"{Fore.CYAN}[start_scanning] 外部URL线程已关闭{Style.RESET_ALL}")
            except Exception as e:
                if self.config.debug_mode:
                    print(f"{Fore.RED}[start_scanning] 关闭外部URL线程失败: {e}{Style.RESET_ALL}")

            # 生成外部URL访问报告
            try:
                if hasattr(self, 'external_results') and self.external_results:
                    self.output_handler.append_results(self.external_results, report_filename)
                    print(f"{Fore.GREEN}外部URL访问结束，结果已追加写入: {report_filename}{Style.RESET_ALL}")
            except Exception as e:
                if self.config.debug_mode:
                    print(f"{Fore.RED}[start_scanning] 处理外部URL结果失败: {e}{Style.RESET_ALL}")

            # 最终清理连接池
            try:
                self._cleanup_connections()
                if self.config.debug_mode:
                    print(f"{Fore.CYAN}[start_scanning] 最终清理连接池完成{Style.RESET_ALL}")
            except Exception as e:
                if self.config.debug_mode:
                    print(f"{Fore.RED}[start_scanning] 最终清理连接池失败: {e}{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}生成报告时出错: {str(e)}{Style.RESET_ALL}")
            if self.config.debug_mode:
                print(f"{Fore.RED}[start_scanning] 报告生成异常详情: {type(e).__name__}: {e}{Style.RESET_ALL}")
                import traceback
                traceback.print_exc()

            try:
                self._cleanup_connections()
                if self.config.debug_mode:
                    print(f"{Fore.CYAN}[start_scanning] 异常退出时清理连接池完成{Style.RESET_ALL}")
            except Exception as cleanup_e:
                if self.config.debug_mode:
                    print(f"{Fore.RED}[start_scanning] 异常退出时清理连接池失败: {cleanup_e}{Style.RESET_ALL}")

    def start_scanning(self):
        """启动扫描器"""
        if self.config.debug_mode:
            print(f"{Fore.CYAN}[start_scanning] 开始初始化扫描器...{Style.RESET_ALL}")

        try:
            if self.config.debug_mode:
                print(f"{Fore.CYAN}[start_scanning] 扫描器创建成功{Style.RESET_ALL}")

            print(f"{Fore.GREEN}扫描器已就绪，开始扫描目标: {self.config.start_url}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}配置: 最大深度={self.config.max_depth}, 最大URL数={self.config.max_urls}, 线程数={self.config.max_workers}{Style.RESET_ALL}")
            start_time = time.time()

            # 启动外部URL线程
            try:
                external_thread = threading.Thread(target=self.external_worker, name="ExternalURLThread", daemon=True)
                external_thread.start()
                if self.config.debug_mode:
                    print(f"{Fore.CYAN}[start_scanning] 外部URL线程已启动{Style.RESET_ALL}")
            except Exception as e:
                if self.config.debug_mode:
                    print(f"{Fore.RED}[start_scanning] 启动外部URL线程失败: {e}{Style.RESET_ALL}")

            try:
                self.start_scan()
            except KeyboardInterrupt:
                print(f"\n{Fore.RED}扫描被用户中断!{Style.RESET_ALL}")
                if self.config.debug_mode:
                    print(f"{Fore.YELLOW}[start_scanning] 用户中断扫描{Style.RESET_ALL}")
            except Exception as e:
                print(f"\n{Fore.RED}扫描出错: {str(e)}{Style.RESET_ALL}")
                if self.config.debug_mode:
                    print(f"{Fore.RED}[start_scanning] 扫描异常详情: {type(e).__name__}: {e}{Style.RESET_ALL}")
                    import traceback
                    traceback.print_exc()
            finally:
                self._handle_scan_completion(start_time, external_thread)

        except Exception as e:
            print(f"{Fore.RED}扫描器初始化失败: {str(e)}{Style.RESET_ALL}")
            if self.config.debug_mode:
                print(f"{Fore.RED}[start_scanning] 初始化异常详情: {type(e).__name__}: {e}{Style.RESET_ALL}")
                import traceback
                traceback.print_exc()
