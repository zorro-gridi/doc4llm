"""
URL匹配和提取模块
负责从HTML内容中提取URL并进行验证
"""
import re
import threading
import urllib.parse
from bs4 import BeautifulSoup

from .utils import DebugMixin, Fore, Style, output_lock, BloomFilter
from .url_utils import URLConcatenator

try:
    import tldextract
    DOMAIN_EXTRACTION = True
except ImportError:
    DOMAIN_EXTRACTION = False


def domain_matches(pattern, domain):
    """
    精确域名匹配：从右向左匹配域名部分

    Args:
        pattern: 模式域名，如 "claude.com", "code.claude.com"
        domain: 待检查的完整域名，如 "www.claude.com", "api.code.claude.com"

    Returns:
        bool: 是否匹配

    匹配规则：
    - 完全相等：pattern == domain
    - 子域匹配：domain 的右侧部分等于 pattern
      例如：pattern="claude.com" 匹配 domain="www.claude.com"
            pattern="code.claude.com" 匹配 domain="api.code.claude.com"

    不匹配规则：
    - pattern="claude.com" 不匹配 domain="otherclaude.com"
    - pattern="code.claude.com" 不匹配 domain="other.claude.com"
    """
    if pattern == domain:
        return True

    pattern_parts = pattern.split('.')
    domain_parts = domain.split('.')

    # 子域匹配：domain 的右侧部分等于 pattern
    if len(domain_parts) > len(pattern_parts):
        if domain_parts[-len(pattern_parts):] == pattern_parts:
            return True

    return False


class URLMatcher(DebugMixin):
    """URL匹配和提取类"""

    # 全局危险接口过滤集合和锁
    danger_api_filtered = set()
    danger_api_lock = threading.Lock()

    def __init__(self, config, scanner=None):
        self.config = config
        self.debug_mode = config.debug_mode  # 设置debug_mode属性
        self.scanner = scanner  # 可选scanner实例
        self.visited_urls_global = BloomFilter(expected_elements=1000000, false_positive_rate=0.001)

    def is_valid_domain(self, url):
        """检查域名是否在允许范围内

        优先级规则：
        1. 白名单优先（所有scope模式）：如果域名在白名单中，直接允许（白名单可覆盖黑名单）
        2. 黑名单检查（所有scope模式）：如果域名在黑名单中，拒绝
        3. scope模式检查：根据url_scope_mode进行范围检查
        """
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc

        self._debug_print(f"检查域名有效性: {domain}")

        # 优先检查白名单（白名单可以覆盖黑名单，适用于所有scope模式）
        if self.config.whitelist_domains:
            for white_domain in self.config.whitelist_domains:
                if domain_matches(white_domain, domain):
                    self._debug_print(f"域名在白名单中 (覆盖黑名单): {domain} (匹配: {white_domain})")
                    return True

        # 检查黑名单（使用精确域名匹配）
        for black_domain in self.config.blacklist_domains:
            if domain_matches(black_domain, domain):
                self._debug_print(f"域名在黑名单中: {domain} (匹配: {black_domain})")
                return False

        # 如果scope模式为2，则跳过域名范围检查，但仍然会检查黑名单
        if self.config.url_scope_mode == 2:
            self._debug_print(f"域名检查通过 (scope模式2): {domain}")
            return True

        # 如果scope模式为3，则只允许白名单域名（已在上面检查，到这里说明不在白名单中）
        if self.config.url_scope_mode == 3:
            self._debug_print(f"域名不在白名单中 (scope模式3): {domain}")
            return False

        # scope=0: 只允许主域和子域
        if self.config.url_scope_mode == 0:
            if DOMAIN_EXTRACTION:
                ext = tldextract.extract(url)
                url_domain = f"{ext.domain}.{ext.suffix}"
                # 确保只匹配主域
                is_valid = url_domain == self.config.base_domain
            else:
                # 匹配主域或子域
                is_valid = domain == self.config.base_domain or domain.endswith('.' + self.config.base_domain)
        # 其他scope模式使用默认验证（主域匹配）
        else:
            if DOMAIN_EXTRACTION:
                ext = tldextract.extract(url)
                url_domain = f"{ext.domain}.{ext.suffix}"
                is_valid = url_domain == self.config.base_domain
            else:
                is_valid = domain == self.config.base_domain or domain.endswith('.' + self.config.base_domain)

        self._debug_print(f"域名检查结果: {domain} -> {'有效' if is_valid else '无效'} (scope={self.config.url_scope_mode})")

        return is_valid

    def should_skip_url(self, url):
        """检查URL是否应该跳过（基于扩展名）

        注意：此方法会自动处理带查询参数的URL（如 image.png?v=1），
        通过 urlparse 解析路径部分进行扩展名匹配。
        """
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()

        # 检查扩展名黑名单（忽略大小写）
        for ext in self.config.extension_blacklist:
            if path.endswith(ext.lower()):
                self._debug_print(f"URL因扩展名跳过: {url} (扩展名: {ext})")
                return True

        self._debug_print(f"URL检查通过: {url}")

        return False

    def should_exclude_fuzzy(self, url):
        """检查URL是否匹配exclude_fuzzy排除规则"""
        if not self.config.exclude_fuzzy:
            return False

        for pattern in self.config.exclude_fuzzy:
            if pattern.lower() in url.lower():
                self._debug_print(f"URL被exclude_fuzzy规则跳过: {url} (匹配: {pattern})")
                return True

        return False

    def is_allowed_by_api_list(self, url):
        """检查URL是否匹配allowed_api_list中的模式（模糊匹配）"""
        # 如果allowed_api_list为空，则允许所有URL
        if not self.config.allowed_api_list:
            return True

        # 提取URL路径进行匹配
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()
        # 同时检查完整URL（包含查询参数）
        full_url = url.lower()

        for pattern in self.config.allowed_api_list:
            pattern_lower = pattern.lower()
            # 检查路径或完整URL中是否包含模式
            if pattern_lower in path or pattern_lower in full_url:
                self._debug_print(f"URL匹配allowed_api_list模式: {url} (匹配: {pattern})")
                return True

        self._debug_print(f"URL不匹配allowed_api_list中的任何模式: {url}")
        return False

    def extract_urls(self, content, base_url):
        """从内容中提取URL - 全新匹配逻辑，专注于路径字符串"""
        try:
            urls = set()

            self._debug_print(f"开始从内容提取URL: base_url={base_url}")

            # 处理文本内容
            text_content = self._process_content(content)
            if text_content is None:
                return set()
        except Exception as e:
            self._debug_print(f"初始化URL提取时出错: {type(e).__name__}: {e}")
            return set()

        # 按类别匹配URL模式
        self._match_path_patterns(text_content, base_url, urls)
        self._match_tag_patterns(text_content, base_url, urls)
        self._match_webpack_patterns(text_content, base_url, urls)

        # 使用BeautifulSoup作为备选方案
        try:
            self._extract_with_bs(text_content, base_url, urls)
        except Exception as e:
            self._debug_print(f"BeautifulSoup提取时出错: {type(e).__name__}: {e}")

        self._debug_print(f"URL提取完成，共找到 {len(urls)} 个URL")

        return urls

    def _process_content(self, content):
        """处理内容，确保是字符串格式"""
        try:
            return content.decode('utf-8', 'ignore') if isinstance(content, bytes) else content
        except Exception as e:
            self._debug_print(f"内容解码失败: {type(e).__name__}: {e}")
            return str(content) if content else ""

    def _match_path_patterns(self, text_content, base_url, urls):
        """匹配路径模式"""
        # 主要regex匹配模式：捕获引号内的路径字符串
        path_patterns = [
            r'[\"\'](/[^\"\'\s]+)[\"\']',  # 双引号或单引号包裹的绝对路径
            r'[\"\'](\.{1,2}/[^\"\'\s]+)[\"\']',  # 双引号或单引号包裹的相对路径
            r'[\"\'](\\\\*/[^\"\'\s]+)[\"\']',  # 匹配这种"href":"\/admin\/Auth\/adminList.html"
            r'`(/([^`\s]+))`',  # 反引号包裹的绝对路径
            r'`(\\.{1,2}/[^`\s]+)`',  # 反引号包裹的相对路径
            r'\b(?:href|src|action)\s*=\s*[\"\']?([^\"\'\s>]+)',  # HTML属性值
            # 新增：匹配assets下的静态资源（js/css/img等）
            r'(assets/[a-zA-Z0-9_\-./]+\.(js|css|png|jpg|jpeg|svg|gif|woff2?|ttf|eot|mp4|mp3|json|map))',
            # 完整URL
            r'[\'\"`]((?:https?://|//)[^\s\'\"`]+)[\'\"`]',
            # 绝对路径
            r'[\'\"`](/[^\s\'\"`]+)[\'\"`]',
            # 相对路径
            r'[\'\"`](\.{1,2}/[^\s\'\"`]+)[\'\"`]',
            # CSS url()
            r'url\([\'"]?([^\s\'\")]+)[\'"]?\)',
            # JS动态URL
            r'\.(?:get|post|put|delete|patch|options|head|connect)\([\'\"`]([^\s\'\"`]+)[\'\"`]',
            r'window\.location\s*=\s*[\'\"`]([^\s\'\"`]+)[\'\"`]',
            r'window\.open\([\'\"`]([^\s\'\"`]+)[\'\"`]',
            r'fetch\([\'\"`]([^\s\'\"`]+)[\'\"`]',
            r'axios\.(?:get|post|put|delete|patch|options|head|connect)\([\'\"`]([^\s\'\"`]+)[\'\"`]',
            r'\.src\s*=\s*[\'\"`]([^\s\'\"`]+)[\'\"`]',
            r'\.href\s*=\s*[\'\"`]([^\s\'\"`]+)[\'\"`]',
            r'\.action\s*=\s*[\'\"`]([^\s\'\"`]+)[\'\"`]',
            # JSON格式URL
            r'[\'\"`]url[\'\"`]\s*:\s*[\'\"`]([^\s\'\"`]+)[\'\"`]',
            r'[\'\"`](?:src|href)[\'\"`]\s*:\s*[\'\"`]([^\s\'\"`]+)[\'\"`]',
            # 模板字符串中的URL
            r'`(https?://[^`]+)`',
            r'`(?:/{1,2}|\.{1,2}/)[^`]+`',
            # 单页面应用路由
            r'router\.(?:push|replace)\([\'\"`]([^\s\'\"`]+)[\'\"`]',
            r'<Route\s+path=[\'\"`]([^\s\'\"`]+)[\'\"`]',
            # API端点模式
            r'[\'\"`]/api/v\d+/[^\s\'\"`]+[\'\"`]',
            r'[\'\"`]/\w+/\w+\.(?:php|aspx|jsp)[\?]?[^\s\'\"`]*[\'\"`]',
            # 新增: 匹配无引号的相对路径 (如 $.get(entrance))
            r'(?:\.get|\.post|\.ajax|fetch|axios\.get|axios\.post)\s*\(\s*([\'\"`]?)([a-zA-Z0-9_/-]+)\1',
            r'[\'\"`](/?DataInterface\\.do(?:\?[^\s\'\"`]*)?)[\'\"`]',  # 新增DataInterface.do路径
            # 新增: 匹配jQuery风格的调用 ($.get("entrance"))
            r'\$\.(?:get|post|ajax)\s*\(\s*[\'\"`]([^\s\'\"`]+)[\'\"`]',
            # 增强模板字符串匹配: 支持相对路径
            r'`(?:https?://[^`]+|/{1,2}[^`]+|\.{1,2}/[^`]+)`',
            # 新增: 匹配JS中的动态路由定义
            r'router\.(?:addRoute|addRoutes)\s*\(\s*[\'\"`]([^\s\'\"`]+)[\'\"`]',
            # 新增: 匹配CommonJS导入 (如 require("./api"))
            r'require\s*\(\s*[\'\"`](\.[^\s\'\"`]+)[\'\"`]',
            # 新增: 匹配ES6动态导入 (如 import("./module"))
            r'import\s*\(\s*[\'\"`](\.[^\s\'\"`]+)[\'\"`]'
        ]

        # 匹配主要路径模式
        try:
            for pattern in path_patterns:
                self._match_and_add(pattern, text_content, base_url, urls)
        except Exception as e:
            self._debug_print(f"匹配主要路径模式时出错: {type(e).__name__}: {e}")

    def _match_tag_patterns(self, text_content, base_url, urls):
        """匹配HTML标签中的路径属性"""
        # 辅助匹配模式：捕获HTML标签中的路径属性（支持属性顺序任意，增加常用标签）
        tag_patterns = [
            # 兼容单双引号、无引号、属性顺序变化
            r'<script\b[^>]*?\bsrc\s*=\s*([\'\"])(.*?)\1',   # script标签的src属性（单双引号）
            r'<script\b[^>]*?\bsrc\s*=\s*([^\s>]+)',           # script标签的src属性（无引号）
            r'<link\b[^>]*?\bhref\s*=\s*([\'\"])(.*?)\1',    # link标签的href属性（单双引号）
            r'<link\b[^>]*?\bhref\s*=\s*([^\s>]+)',             # link标签的href属性（无引号）
            r'<img\b[^>]*?\bsrc\s*=\s*([\'\"])(.*?)\1',      # img标签的src属性（单双引号）
            r'<img\b[^>]*?\bsrc\s*=\s*([^\s>]+)',               # img标签的src属性（无引号）
            r'<a\b[^>]*?href\s*=\s*([\'\"])(.*?)\1',          # a标签的href属性（单双引号）
            r'<a\b[^>]*?href\s*=\s*([^\s>]+)',                   # a标签的href属性（无引号）
            r'<form\b[^>]*?\baction\s*=\s*([\'\"])(.*?)\1',   # form标签的action属性（单双引号）
            r'<form\b[^>]*?\baction\s*=\s*([^\s>]+)',            # form标签的action属性（无引号）
            r'<iframe\b[^>]*?\bsrc\s*=\s*([\'\"])(.*?)\1',    # iframe标签的src属性（单双引号）
            r'<iframe\b[^>]*?\bsrc\s*=\s*([^\s>]+)',             # iframe标签的src属性（无引号）
            r'<video\b[^>]*?\bsrc\s*=\s*([\'\"])(.*?)\1',     # video标签的src属性（单双引号）
            r'<video\b[^>]*?\bsrc\s*=\s*([^\s>]+)',              # video标签的src属性（无引号）
            r'<audio\b[^>]*?\bsrc\s*=\s*([\'\"])(.*?)\1',     # audio标签的src属性（单双引号）
            r'<audio\b[^>]*?\bsrc\s*=\s*([^\s>]+)',              # audio标签的src属性（无引号）
            r'<source\b[^>]*?\bsrc\s*=\s*([\'\"])(.*?)\1',    # source标签的src属性（单双引号）
            r'<source\b[^>]*?\bsrc\s*=\s*([^\s>]+)',             # source标签的src属性（无引号）
            r'<embed\b[^>]*?\bsrc\s*=\s*([\'\"])(.*?)\1',     # embed标签的src属性（单双引号）
            r'<embed\b[^>]*?\bsrc\s*=\s*([^\s>]+)',              # embed标签的src属性（无引号）
            r'<object\b[^>]*?\bdata\s*=\s*([\'\"])(.*?)\1',   # object标签的data属性（单双引号）
            r'<object\b[^>]*?\bdata\s*=\s*([^\s>]+)',            # object标签的data属性（无引号）
            r'<track\b[^>]*?\bsrc\s*=\s*([\'\"])(.*?)\1',     # track标签的src属性（单双引号）
            r'<track\b[^>]*?\bsrc\s*=\s*([^\s>]+)',              # track标签的src属性（无引号）
            r'<applet\b[^>]*?\bcode\s*=\s*([\'\"])(.*?)\1',   # applet标签的code属性（单双引号）
            r'<applet\b[^>]*?\bcode\s*=\s*([^\s>]+)',            # applet标签的code属性（无引号）
            r'<frame\b[^>]*?\bsrc\s*=\s*([\'\"])(.*?)\1',     # frame标签的src属性（单双引号）
            r'<frame\b[^>]*?\bsrc\s*=\s*([^\s>]+)',              # frame标签的src属性（无引号）
            r'<portal\b[^>]*?\bsrc\s*=\s*([\'\"])(.*?)\1',    # portal标签的src属性（单双引号）
            r'<portal\b[^>]*?\bsrc\s*=\s*([^\s>]+)',             # portal标签的src属性（无引号）
            r'<button\b[^>]*?\bformaction\s*=\s*([\'\"])(.*?)\1', # button标签的formaction属性（单双引号）
            r'<button\b[^>]*?\bformaction\s*=\s*([^\s>]+)',          # button标签的formaction属性（无引号）
            r'<input\b[^>]*?\bsrc\s*=\s*([\'\"])(.*?)\1',     # input标签的src属性（单双引号）
            r'<input\b[^>]*?\bsrc\s*=\s*([^\s>]+)',              # input标签的src属性（无引号）
            r'<input\b[^>]*?\bformaction\s*=\s*([\'\"])(.*?)\1', # input标签的formaction属性（单双引号）
            r'<input\b[^>]*?\bformaction\s*=\s*([^\s>]+)',          # input标签的formaction属性（无引号）
            r'<area\b[^>]*?\bhref\s*=\s*([\'\"])(.*?)\1',      # area标签的href属性（单双引号）
            r'<area\b[^>]*?\bhref\s*=\s*([^\s>]+)',               # area标签的href属性（无引号）
            r'<base\b[^>]*?\bhref\s*=\s*([\'\"])(.*?)\1',      # base标签的href属性（单双引号）
            r'<base\b[^>]*?\bhref\s*=\s*([^\s>]+)',               # base标签的href属性（无引号）
            r'<meta\b[^>]*?\bcontent\s*=\s*([\'\"])(.*?)\1',   # meta标签的content属性（单双引号）
            r'<meta\b[^>]*?\bcontent\s*=\s*([^\s>]+)',            # meta标签的content属性（无引号）
        ]

        # 匹配HTML标签中的路径属性
        try:
            for pattern in tag_patterns:
                self._match_and_add(pattern, text_content, base_url, urls)
        except Exception as e:
            self._debug_print(f"匹配HTML标签模式时出错: {type(e).__name__}: {e}")

    def _match_webpack_patterns(self, text_content, base_url, urls):
        """匹配webpack模式"""
        # webpack 匹配
        webpack_patterns = [
            r'\"(chunk-[\w\d]+)\":\"([\w\d]+)\"'
        ]
        # webpack 单独匹配
        try:
            for pattern in webpack_patterns:
                self._match_webpack_add(pattern, text_content, base_url, urls)
        except Exception as e:
            self._debug_print(f"匹配webpack模式时出错: {type(e).__name__}: {e}")

    def _match_webpack_add(self, pattern, text_content, base_url, url_set):
        """使用webpack匹配 并添加URL"""
        try:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            if self.config.debug_mode and matches:
                self._debug_print(f"使用webpack匹配 '{pattern}' 找到 {len(matches)} 个匹配")
            if matches:
                for match in matches:
                    # match匹配结果 ('chunk-a2d74a98', '1ea71fd1') 拼接成chunk.a2d74a98.1ea71fd1.js
                    url = f"{match[0]}.{match[1]}.js"
                    if self._is_valid_webpack_url(url):
                        # 对base_url进行处理，只保留根路径，然后拼接url
                        parsed = urllib.parse.urlparse(base_url)
                        root_url = f"{parsed.scheme}://{parsed.netloc}/"
                        # 暂时固定死拼接路径，后期可以优化
                        full_url = urllib.parse.urljoin(root_url, f"static/js/{url}")
                        if full_url not in UltimateURLScanner.visited_urls_global and 'chunk' in full_url:
                            url_set.add(full_url)
        except Exception as e:
            self._debug_print(f"URL匹配错误 (模式: {pattern}): {str(e)}")

    def _is_valid_webpack_url(self, url):
        """检查webpack生成的URL是否有效"""
        return len(url) < 28 and len(url) > 20

    def _match_and_add(self, pattern, text_content, base_url, url_set):
        """使用正则表达式匹配并添加URL"""
        try:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            if self.config.debug_mode and matches:
                self._debug_print(f"正则匹配模式 '{pattern}' 找到 {len(matches)} 个匹配")
            for match in matches:
                # 处理可能的元组结果
                url = self._extract_url_from_match(match)
                if url:
                    try:
                        self._process_url(url, base_url, url_set, f"Regex: {pattern}")
                    except Exception as e:
                        self._debug_print(f"[_match_and_add]: 正则失败，{e}")
        except Exception as e:
            self._debug_print(f"URL匹配错误 (模式: {pattern}): {str(e)}")

    def _extract_url_from_match(self, match):
        """从匹配结果中提取URL"""
        # 处理可能的元组结果
        if isinstance(match, tuple):
            # 取第一个非空匹配组
            return next((m for m in match if m), "")
        else:
            return match

    def _extract_with_bs(self, text_content, base_url, url_set):
        """使用BeautifulSoup提取URL"""
        try:
            self._debug_print("开始使用BeautifulSoup提取URL")

            soup = BeautifulSoup(text_content, 'html.parser')

            # 提取所有标签中可能包含URL的属性
            tags = {
                'a': 'href',
                'link': 'href',
                'script': 'src',
                'img': 'src',
                'iframe': 'src',
                'form': 'action',
                'meta': 'content',
                'object': 'data',
                'embed': 'src',
                'source': 'src',
                'audio': 'src',
                'video': 'src',
                'track': 'src',
                'applet': 'code',
                'frame': 'src',
                'portal': 'src',
                'button': 'formaction',
                'input': ['src', 'formaction'],
                'area': 'href',
                'base': 'href'
            }

            bs_count = 0
            for tag, attrs in tags.items():
                if not isinstance(attrs, list):
                    attrs = [attrs]

                for element in soup.find_all(tag):
                    for attr in attrs:
                        if element.has_attr(attr):
                            url = element[attr]
                            bs_count += 1
                            self._debug_print(f"BeautifulSoup找到: {tag}[{attr}] = {url}")
                            self._process_url(url, base_url, url_set, "BeautifulSoup")

            self._debug_print(f"BeautifulSoup提取完成，共处理 {bs_count} 个属性")

        except Exception as e:
            self._debug_print(f"BeautifulSoup解析错误: {str(e)}")

    def _process_url(self, url, base_url, url_set, source=""):
        """处理单个URL，拼接成URL，添加到集合中"""
        self._debug_print(f"处理单个URL: {url} , base_url -> {base_url} , source -> {source}")

        # 预处理URL
        processed_url = self._preprocess_url(url)
        if not processed_url:
            return

        # 处理完整URL（包含http/https）
        if 'http' in processed_url:
            self._process_full_urls(processed_url, url_set)
            return

        # 处理协议相对URL
        processed_url = self._handle_protocol_relative_url(processed_url, base_url)

        # 清理URL
        processed_url = self._clean_url(processed_url)

        # 应用智能拼接
        self._apply_url_concatenation(processed_url, base_url, url_set)

    def _preprocess_url(self, url):
        """预处理URL，清理和验证"""
        if not url or url.strip() == "":
            self._debug_print(f"跳过空URL")
            return None

        # 跳过常见无效URL
        if url.startswith(('javascript:', 'data:', 'mailto:', 'tel:')):
            self._debug_print(f"跳过无效URL: {url}")
            return None

        # 只保留URL允许的字符，遇到第一个不合法字符就截断
        m = re.match(r'^[a-zA-Z0-9:/?&=._~#%\\-]+', url)
        if m:
            url = m.group(0)
        else:
            return None  # 如果没有合法URL部分，直接跳过

        # 去除首尾引号和空格
        return url.strip().strip('\'"')

    def _process_full_urls(self, url, url_set):
        """处理包含完整协议的URL"""
        # 如果有多个http, 匹配字符串分割成多个URL，分别添加到集合中
        urls = re.findall(r'http[s]?://[^ ]+', url)
        for full_url in urls:
            if full_url:
                # 外部URL收集逻辑
                if not self.is_valid_domain(full_url):
                    # 只有当url_scope_mode不是0时，才收集外部URL
                    if self.scanner is not None and self.config.url_scope_mode != 0:
                        with self.scanner.external_urls_lock:
                            if full_url not in self.scanner.external_urls:
                                self.scanner.external_urls.add(full_url)
                                self.scanner.external_url_queue.put(full_url)
                    self._debug_print(f"外部URL已收集: {full_url}")
                    return  # 外部URL不加入主扫描集合
                else:
                    # 内部完整URL添加：检查域名、扩展名、allowed_api_list
                    if full_url not in url_set and not self.should_skip_url(full_url) and self.is_allowed_by_api_list(full_url):
                        url_set.add(full_url)
                        self._debug_print(f"完整URL已添加到集合: {full_url}")

    def _handle_protocol_relative_url(self, url, base_url):
        """处理协议相对URL"""
        if url.startswith('//'):
            parsed_base = urllib.parse.urlparse(base_url)
            new_url = f"{parsed_base.scheme}:{url}"
            self._debug_print(f"协议相对URL处理: {new_url}")
            return new_url
        return url

    def _clean_url(self, url):
        """清理URL中的特殊字符"""
        # 去掉url中的所有的'\'
        return url.replace('\\', '')

    def _apply_url_concatenation(self, url, base_url, url_set):
        """应用URL拼接逻辑"""
        concatenator = URLConcatenator(self.config.debug_mode)
        concatenator.base_url = [base_url]  # 确保是列表格式
        concatenator.relative_url = [url]  # 确保是列表格式
        concatenator.custom_base_url = self.config.custom_base_url
        concatenator.path_route = self.config.path_route
        concatenator.api_route = self.config.api_route
        url_list = concatenator.process_and_return_urls()

        for normalized in url_list:
            self._debug_print(f"URL处理结果:{base_url} + {url} -> {normalized}")
            # 危险接口过滤检测
            if self.config.danger_filter_enabled:
                if self._is_dangerous_url(normalized):
                    self._handle_dangerous_url(normalized)
                    return

            # URL过滤检查：域名、扩展名、排除规则、allowed_api_list
            if normalized and self.is_valid_domain(normalized) and not self.should_skip_url(normalized) and not self.should_exclude_fuzzy(normalized) and self.is_allowed_by_api_list(normalized):
                url_set.add(normalized)
                self._debug_print(f"URL已添加到集合: {normalized}")
            else:
                self._debug_print(f"URL被过滤: {normalized}")

    def _is_dangerous_url(self, url):
        """检查URL是否为危险接口"""
        if not url.endswith(".js"):  # 排除JS文件
            for danger_api in self.config.danger_api_list:
                if danger_api.lower() in url.lower():
                    return danger_api
        return False

    def _handle_dangerous_url(self, url):
        """处理危险URL"""
        # 首先检查URL是否危险，并获取匹配的危险API
        danger_api = self._is_dangerous_url(url)

        if not danger_api:
            return  # 如果不是危险URL，直接返回

        # 使用线程锁确保输出安全，并过滤重复
        with URLMatcher.danger_api_lock:
            if url not in URLMatcher.danger_api_filtered:
                URLMatcher.danger_api_filtered.add(url)
                # 紫色输出 - 使用全局输出锁确保不与其他输出混合
                with output_lock:
                    print(Fore.MAGENTA + f"[危险] [危险] [危险] [危险] [跳过危险接口] {url} 包含 ({danger_api})" + Style.RESET_ALL)
                self._debug_print(f"[危险] [危险] [危险] [危险] [跳过危险接口] {url} 包含 ({danger_api})")
            else:
                # 重复的危险接口，只记录debug信息
                self._debug_print(f"[危险] [危险] [危险] [危险] [重复危险接口] {url} 包含 ({danger_api})")


# 为了避免循环导入，这里需要提前声明UltimateURLScanner类
# 实际导入会在运行时进行
UltimateURLScanner = None
