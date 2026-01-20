"""
输出处理模块
负责日志记录和结果输出
"""
import csv
import os
import re
import sys
import time
import urllib.parse
from .utils import DebugMixin, Fore, Style, output_lock
from .url_matcher import domain_matches


class OutputLogger:
    """输出日志记录器 - 同时输出到终端和文件

    支持日志文件行数限制，每次更新时只保留最近的 N 行记录
    """

    # 默认最大日志行数
    DEFAULT_MAX_LINES = 10000

    def __init__(self, log_file="results/output.out", max_lines=None):
        self.log_file = log_file
        self.max_lines = max_lines if max_lines is not None else self.DEFAULT_MAX_LINES
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self._line_count = 0  # 当前写入的行数计数器
        self._check_interval = 100  # 每 N 行检查一次文件大小

        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # 在打开文件前，先截断现有日志文件（如果超过限制）
        self._truncate_log_if_needed()

        # 创建文件输出流
        self.log_stream = open(log_file, 'a', encoding='utf-8')

    def _truncate_log_if_needed(self):
        """检查并截断日志文件，只保留最近的 max_lines 行"""
        try:
            if not os.path.exists(self.log_file):
                return

            # 读取现有日志文件的行数
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            current_line_count = len(lines)
            if current_line_count <= self.max_lines:
                return

            # 截断：只保留最近的 max_lines 行
            lines_to_keep = lines[-self.max_lines:]

            # 写回文件
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.writelines(lines_to_keep)

            # 添加截断标记
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"\n... [日志截断于 {timestamp}] 已保留最近 {self.max_lines} 行记录 ...\n\n")
        except Exception:
            # 如果截断失败，不影响日志记录功能
            pass

    def _periodic_truncate_check(self):
        """周期性检查并截断日志文件"""
        self._line_count += 1
        if self._line_count >= self._check_interval:
            self._line_count = 0
            # 需要先关闭文件流才能截断
            try:
                self.log_stream.close()
                self._truncate_log_if_needed()
                # 重新打开文件流
                self.log_stream = open(self.log_file, 'a', encoding='utf-8')
            except Exception:
                # 如果截断失败，尝试重新打开文件流
                try:
                    self.log_stream = open(self.log_file, 'a', encoding='utf-8')
                except Exception:
                    pass

    def write(self, text):
        # 写入到原始stdout（保持彩色）
        self.original_stdout.write(text)
        # 同时写入到日志文件（去除颜色代码）
        try:
            # 去除ANSI颜色代码
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_text = ansi_escape.sub('', text)
            self.log_stream.write(clean_text)
            self.log_stream.flush()
            # 周期性检查是否需要截断日志
            self._periodic_truncate_check()
        except Exception:
            pass

    def flush(self):
        self.original_stdout.flush()
        try:
            self.log_stream.flush()
        except Exception:
            pass

    def close(self):
        try:
            self.log_stream.close()
        except Exception:
            pass


class OutputHandler(DebugMixin):
    """输出处理器 - 负责格式化和输出结果"""

    def __init__(self, config):
        self.config = config
        self.debug_mode = config.debug_mode
        self.url_count = 0
        self.start_time = time.time()
        self.request_signature_count = {}
        self.is_duplicate = getattr(config, 'is_duplicate', 0)

        # 准备输出文件
        if config.output_file:
            os.makedirs(os.path.dirname(os.path.abspath(config.output_file)), exist_ok=True)
            with open(config.output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['URL', 'Status', 'Title', 'Length', 'Redirects', 'Depth', 'Sensitive Types', 'Sensitive Counts', 'Sensitive Details', 'Is Duplicate'])

            self._debug_print(f"输出文件已初始化: {config.output_file}")

    def _format_sensitive_data_for_csv(self, sensitive_raw):
        """格式化敏感信息数据用于CSV保存"""
        try:
            if not sensitive_raw:
                return "", "", ""

            sensitive_types = []
            sensitive_counts = []
            sensitive_details = []

            for item in sensitive_raw:
                try:
                    if isinstance(item, dict):
                        sensitive_type = item.get('type', '未知')
                        count = item.get('count', 0)
                        samples = item.get('samples', [])

                        sensitive_types.append(sensitive_type)
                        sensitive_counts.append(str(count))

                        if samples:
                            detail_samples_str = [str(sample) for sample in samples]
                            detail_str = f"{sensitive_type}:{'; '.join(detail_samples_str)}"
                        else:
                            detail_str = f"{sensitive_type}:无样本"

                        sensitive_details.append(detail_str)
                    else:
                        item_str = str(item)
                        sensitive_types.append("未知类型")
                        sensitive_counts.append("1")
                        sensitive_details.append(item_str)
                except Exception as e:
                    if self.config.debug_mode:
                        self._debug_print(f"处理敏感信息项时出错: {type(e).__name__}: {e}")
                    sensitive_types.append("处理错误")
                    sensitive_counts.append("0")
                    sensitive_details.append(f"处理错误: {type(e).__name__}")

            return "|".join(sensitive_types), "|".join(sensitive_counts), "|".join(sensitive_details)
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"格式化敏感信息数据时出错: {type(e).__name__}: {e}")
            return "格式化错误", "0", f"格式化错误: {type(e).__name__}"

    def get_status_color(self, status):
        """获取状态码对应的颜色"""
        if not self.config.color_output:
            return ''

        if isinstance(status, int):
            if 200 <= status < 300:
                return Fore.GREEN
            elif 300 <= status < 400:
                return Fore.YELLOW
            elif 400 <= status < 500:
                return Fore.RED
            elif 500 <= status < 600:
                return Fore.MAGENTA
        elif "Err" in str(status):
            return Fore.RED + Style.BRIGHT

        return Fore.CYAN

    def format_result_line(self, result):
        """格式化终端输出行"""
        try:
            # 提取基本信息
            depth_str = f"[深度:{result['depth']}]"
            status_str = f"[{result['status']}]"
            length_str = f"[{result['length']}]"
            time_str = f"[{result['time']:.2f}s]"

            # 获取状态颜色
            status_color = self.get_status_color(result['status'])

            # 处理标题
            title_str = self._format_title(result.get('title', ''))

            # 处理文件类型
            file_type_str, file_type_color = self._format_file_type(result.get('url', ''))

            # 处理敏感信息
            sensitive_str = self._format_sensitive_info(result.get('sensitive_raw', []))

            # 重复URL标记
            is_duplicate_signature = result.get('is_duplicate_signature', False)
            if is_duplicate_signature and self.is_duplicate == 1:
                return (f"{Fore.MAGENTA}{depth_str} {status_str} {length_str} {title_str} {result['url']} {time_str} {sensitive_str} {Style.RESET_ALL}")

            # 正常输出
            return (
                f"{Fore.BLUE}{depth_str}{Style.RESET_ALL} "
                f"{status_color}{status_str}{Style.RESET_ALL} "
                f"{Fore.WHITE}{length_str}{Style.RESET_ALL} "
                f"{file_type_color}{file_type_str}{Style.RESET_ALL} "
                f"{Fore.CYAN}{title_str}{Style.RESET_ALL} "
                f"{Fore.WHITE}{result['url']}{Style.RESET_ALL} "
                f"{Fore.YELLOW}{time_str}{Style.RESET_ALL}"
                f"{sensitive_str}"
            )
        except Exception as e:
            return f"{Fore.RED}格式化输出行出错: {type(e).__name__}: {e}{Style.RESET_ALL}"

    def _format_title(self, title):
        """格式化标题显示"""
        if title:
            return f"[{str(title)[:30]:^10}]"
        else:
            return "[===========]"

    def _format_file_type(self, url):
        """格式化文件类型显示"""
        url_path = url.split('?')[0] if url else ''
        filename = url_path.split('/')[-1]
        if '.' in filename:
            ext = filename.split('.')[-1].upper()
            return f"[{ext}]", Fore.LIGHTCYAN_EX
        else:
            return "[接口]", Fore.RED

    def _format_sensitive_info(self, sensitive_raw):
        """格式化敏感信息显示"""
        if not sensitive_raw:
            return ""

        sensitive_types = []
        for item in sensitive_raw:
            if isinstance(item, dict):
                sensitive_type = item.get('type', '未知')
                count = item.get('count', 0)
                display_format = f"{sensitive_type}X{count}"
                sensitive_types.append(display_format)
            else:
                sensitive_types.append(str(item))

        return Fore.RED + Style.BRIGHT + f" -> [{'，'.join(sensitive_types)}]"

    def print_result_line(self, line):
        """只负责终端输出"""
        with output_lock:
            print(line)

    def write_result_to_csv(self, result, file_path=None):
        """只负责写入一行到CSV"""
        try:
            if not file_path:
                file_path = self.config.output_file
            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                sensitive_types, sensitive_counts, sensitive_details = self._format_sensitive_data_for_csv(result.get('sensitive_raw'))
                link_type = self._get_link_type(result.get('url', ''))
                writer.writerow([
                    result.get('url', ''),
                    result.get('status', ''),
                    result.get('title', ''),
                    result.get('length', 0),
                    link_type,
                    result.get('redirects', ''),
                    result.get('depth', 0),
                    sensitive_types,
                    sensitive_counts,
                    sensitive_details,
                    '是' if result.get('is_duplicate_signature', False) else '否'
                ])
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"写入CSV文件时出错: {type(e).__name__}: {e}")
            print(f"{Fore.RED}写入CSV文件失败: {type(e).__name__}: {e}{Style.RESET_ALL}")

    def _get_link_type(self, url):
        """获取链接类型"""
        if not url:
            return "接口"

        url_path = url.split('?')[0]
        filename = url_path.split('/')[-1]
        if '.' in filename:
            return filename.split('.')[-1].upper()
        else:
            return "接口"

    def realtime_output(self, result):
        """彩色实时输出扫描结果

        输出过滤规则（按优先级）：
        1. 状态码过滤（status_code_filter）
        2. 黑名单域名（whitelist_domains不命中的）
        3. 扩展名黑名单
        4. 危险接口列表（danger_api_list）
        5. 排除规则（exclude_fuzzy）
        6. allowed_api_list（只检查是否匹配，不匹配则不写入CSV）
        """
        try:
            url = result.get('url', '')
            if not url:
                return

            # === 状态码过滤检查 ===
            if self._should_skip_status_code(result):
                self._debug_print(f"URL因状态码匹配过滤规则跳过输出和CSV: {url} (状态码: {result.get('status', '')})")
                return

            # === 域名过滤检查 ===
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc

            # 检查白名单（白名单可以覆盖黑名单）
            in_whitelist = False
            if self.config.whitelist_domains:
                for white_domain in self.config.whitelist_domains:
                    if domain_matches(white_domain, domain):
                        in_whitelist = True
                        break

            # 检查黑名单域名（跳过不在白名单中的）
            if not in_whitelist:
                for black_domain in self.config.blacklist_domains:
                    if domain_matches(black_domain, domain):
                        self._debug_print(f"URL在黑名单中，跳过输出和CSV: {url} (匹配: {black_domain})")
                        return

            # === 扩展名黑名单检查 ===
            if self._should_skip_url_extension(url):
                self._debug_print(f"URL因扩展名黑名单跳过输出和CSV: {url}")
                return

            # === 危险接口列表检查 ===
            if self._is_dangerous_url(url):
                self._debug_print(f"URL因危险接口列表跳过输出和CSV: {url}")
                return

            # === 排除规则检查 ===
            if self._should_exclude_fuzzy(url):
                self._debug_print(f"URL因排除规则跳过输出和CSV: {url}")
                return

            # === 标题过滤检查 ===
            if self._should_skip_title(result):
                self._debug_print(f"URL因标题匹配过滤规则跳过输出和CSV: {url} (标题: {result.get('title', '')})")
                return

            # === allowed_api_list 检查（只影响CSV写入，不影响控制台输出）===
            if not self._is_allowed_by_api_list(url):
                self._debug_print(f"URL未通过allowed_api_list过滤，不写入CSV: {url}")
                # 仍然进行控制台输出，但不写入CSV
                self._output_to_console(result)
                return

            # === URL重复检查（在输出前检查）===
            is_duplicate_signature = self._check_duplicate_signature(result)
            result['is_duplicate_signature'] = is_duplicate_signature

            if is_duplicate_signature:
                self._debug_print(f"URL已重复，跳过输出和CSV: {url}")
                # 如果配置了显示重复，则显示到控制台
                if self.is_duplicate == 1:
                    self._output_to_console(result)
                # 但不写入CSV
                return

            # 所有检查通过，正常输出和写入CSV
            self._output_to_console(result)

            # 写入CSV文件
            if self.config.output_file:
                self.write_result_to_csv(result, self.config.output_file)

        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"初始化输出处理时出错: {type(e).__name__}: {e}")
            return

    def _should_skip_url_extension(self, url):
        """检查URL扩展名是否在黑名单中

        注意：此方法会自动处理带查询参数的URL（如 image.png?v=1），
        通过 urlparse 解析路径部分进行扩展名匹配。
        """
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()
        for ext in self.config.extension_blacklist:
            if path.endswith(ext.lower()):
                return True
        return False

    def _is_dangerous_url(self, url):
        """检查URL是否为危险接口"""
        if not self.config.danger_filter_enabled:
            return False
        if url.endswith(".js"):  # 排除JS文件
            return False
        for danger_api in self.config.danger_api_list:
            if danger_api.lower() in url.lower():
                return True
        return False

    def _should_exclude_fuzzy(self, url):
        """检查URL是否匹配exclude_fuzzy排除规则"""
        if not self.config.exclude_fuzzy:
            return False
        for pattern in self.config.exclude_fuzzy:
            if pattern.lower() in url.lower():
                return True
        return False

    def _should_skip_title(self, result):
        """检查页面标题是否匹配过滤规则"""
        title = result.get('title', '')
        if not title:
            return False
        # 检查标题是否在过滤列表中（不区分大小写）
        for filter_title in self.config.title_filter_list:
            if title.lower() == filter_title.lower():
                return True
        return False

    def _should_skip_status_code(self, result):
        """检查HTTP状态码是否匹配过滤规则"""
        status = result.get('status', '')
        if not status:
            return False
        # 只检查整数状态码
        if isinstance(status, int):
            return status in self.config.status_code_filter
        return False

    def _output_to_console(self, result):
        """输出结果到控制台"""
        self.url_count += 1
        if self.config.debug_mode:
            self._debug_print(f"处理扫描结果 #{self.url_count}: {result.get('url', '未知URL')}")

        # 处理错误状态
        if isinstance(result.get('status'), str) and 'Err' in result['status']:
            result['status'] = 'Err'

        # 格式化并输出结果行（调用者已负责重复检查）
        line = self.format_result_line(result)
        self.print_result_line(line)

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
                self._debug_print(f"URL匹配allowed_api_list模式: {url} (匹配: {pattern})")
                return True

        self._debug_print(f"URL不匹配allowed_api_list中的任何模式: {url}")
        return False

    def _check_duplicate_signature(self, result):
        """检查URL是否已重复（基于URL判断）"""
        url = result.get('url', '')
        if not url:
            return False

        count = self.request_signature_count.get(url, 0)
        self.request_signature_count[url] = count + 1
        return count > 0

    def generate_report(self, results, report_file="full_report.csv"):
        """生成最终扫描报告"""
        try:
            if self.config.debug_mode:
                self._debug_print(f"开始生成最终报告: {report_file}")
                self._debug_print(f"报告包含 {len(results)} 个扫描结果")

            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(report_file)), exist_ok=True)

            # 写入表头
            with open(report_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['URL', '状态', '标题', '长度', '链接类型', '重定向', '深度', '敏感信息类型', '敏感信息数量', '敏感信息详细清单', '是否重复'])

            # 写入数据
            for result in results:
                self.write_result_to_csv(result, report_file)
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"生成报告时出错: {type(e).__name__}: {e}")
            print(f"{Fore.RED}生成报告失败: {type(e).__name__}: {e}{Style.RESET_ALL}")
            return

        if self.config.debug_mode:
            self._debug_print(f"最终报告生成完成: {report_file}")

        # 输出完成信息
        with output_lock:
            print(f"\n\n{Fore.GREEN}扫描完成! 共扫描 {len(results)} 个URL{Style.RESET_ALL} ")
            print(f"{Fore.GREEN}完整报告已保存至: {report_file}{Style.RESET_ALL} ")
            print(f"{Fore.GREEN}=============================================={Style.RESET_ALL} ")

    def append_results(self, results, report_file="full_report.csv"):
        """追加写入扫描结果到报告文件"""
        try:
            for result in results:
                self.write_result_to_csv(result, report_file)
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"追加结果到文件时出错: {type(e).__name__}: {e}")
            print(f"{Fore.RED}追加结果到文件失败: {type(e).__name__}: {e}{Style.RESET_ALL}")

    def output_external_unvisited(self, urls, report_file=None):
        """输出未访问的外部URL"""
        try:
            for url in urls:
                try:
                    output_line = (
                        f"{Fore.MAGENTA}[外部] [外部] [外部] [外部] [外部] {url} [外部] [外部] {Style.RESET_ALL}"
                    )
                    with output_lock:
                        print(output_line)
                    # 构造标准result字典
                    result = {
                        'url': url,
                        'status': '外部',
                        'title': '外部',
                        'length': 0,
                        'redirects': '',
                        'depth': 0,
                        'time': 0,
                        'sensitive': '',
                        'sensitive_raw': [],
                        'is_duplicate_signature': False,
                        'content_type': '',
                        'headers_count': 0,
                        'error_type': None,
                        'original_url': url,
                    }
                    if report_file:
                        self.write_result_to_csv(result, report_file)
                except Exception as e:
                    if self.config.debug_mode:
                        self._debug_print(f"处理外部URL时出错: {type(e).__name__}: {e}")
                    print(f"{Fore.RED}处理外部URL时出错: {type(e).__name__}: {e}{Style.RESET_ALL}")
        except Exception as e:
            if self.config.debug_mode:
                self._debug_print(f"输出外部URL时出错: {type(e).__name__}: {e}")
            print(f"{Fore.RED}输出外部URL失败: {type(e).__name__}: {e}{Style.RESET_ALL}")
