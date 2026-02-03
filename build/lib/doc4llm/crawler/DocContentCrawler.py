"""
文档爬取模块 - DocContentCrawler

功能：
1. 从CSV文件中读取已扫描的URL列表
2. 根据URL过滤规则筛选需要爬取的URL
3. 构建层次化的目录结构保存文档
4. 爬取网页内容并转换为Markdown格式
5. 支持子域名、模糊匹配等过滤方式
"""

import os
import csv
import time
import threading
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Set, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

# Playwright 导入（可选依赖）
try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Playwright stealth 导入（可选依赖）
try:
    from playwright_stealth import stealth_sync

    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False

try:
    from colorama import init, Fore, Style

    init(autoreset=True)
    COLOR_SUPPORT = True
except ImportError:
    COLOR_SUPPORT = False
    Fore = Style = type("", (), {"__getattr__": lambda *args: ""})()

from doc4llm.filter import ContentFilter, EnhancedContentFilter
from doc4llm.filter.config import FilterConfigLoader
from doc4llm.convertor.MarkdownConverter import MarkdownConverter
from doc4llm.convertor.MermaidParser import MermaidParser
from doc4llm.link_processor.LinkProcessor import LinkProcessor


class DocContentCrawler:
    """
    文档爬取器类

    从扫描结果CSV文件中读取URL，爬取网页内容并保存为层次化的Markdown文档
    """

    def __init__(self, config):
        """
        初始化文档爬取器

        Args:
            config: ScannerConfig配置对象
        """
        self.config = config
        self.debug_mode = config.debug_mode

        # Playwright 配置
        self.playwright_enabled = config.playwright_enabled
        self.playwright_timeout = config.playwright_timeout
        self.playwright_headless = config.playwright_headless
        self.playwright_force = config.playwright_force

        # 指纹伪装配置
        self.playwright_stealth = getattr(config, "playwright_stealth", True)
        self.playwright_platform = getattr(config, "playwright_platform", "win32")
        self.playwright_screen_width = getattr(config, "playwright_screen_width", 1920)
        self.playwright_screen_height = getattr(
            config, "playwright_screen_height", 1080
        )
        self.playwright_device_scale_factor = getattr(
            config, "playwright_device_scale_factor", 1
        )
        self.playwright_timezone = getattr(
            config, "playwright_timezone", "Asia/Shanghai"
        )
        self.playwright_locale = getattr(config, "playwright_locale", "zh-CN")

        # Cookie 配置
        self.playwright_cookies_file = getattr(config, "playwright_cookies_file", None)
        self.playwright_cookies = getattr(config, "playwright_cookies", [])

        # 从 config.content_filter 加载过滤器配置
        self.content_filter = self._load_content_filter()

        self.markdown_converter = MarkdownConverter()
        self.mermaid_parser = MermaidParser()

        # 统计信息
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "filtered": 0,
        }

        # 线程锁
        self.lock = threading.Lock()

        # 已爬取的URL集合（避免重复）
        self.crawled_urls: Set[str] = set()

        # 输出目录结构
        self.doc_root_dir = self._build_doc_root_path()

        # doc爬取模式下，清空URL过滤器条件（爬取所有URL）
        self._clear_doc_filters()

    def _clear_doc_filters(self):
        """
        清空文档URL过滤器条件
        在doc爬取模式下，不进行子域名和模糊匹配过滤
        只保留扩展名黑名单检查
        """
        if self.config.toc_url_filters:
            # 清空正过滤器（子域名和模糊匹配）
            self.config.toc_url_filters["subdomains"] = []
            self.config.toc_url_filters["fuzzy_match"] = []
            # 保留排除过滤器（exclude_fuzzy）用于排除某些路径
            # 保留扩展名黑名单检查
        if self.debug_mode:
            self._debug_print("doc爬取模式：已清空URL过滤器条件，将爬取所有URL")

    def _load_content_filter(self):
        """
        从 config.content_filter 加载过滤器配置

        Returns:
            ContentFilter 或 EnhancedContentFilter 实例
        """
        try:
            # 使用传入的 config 对象中的 content_filter 配置，而不是读取文件
            filter_config = FilterConfigLoader.load_from_config(
                {"content_filter": self.config.content_filter}
            )

            # 如果配置了 content_end_markers 或其他高级配置，使用增强版过滤器
            if filter_config and (
                filter_config.get("content_end_markers")
                or filter_config.get("documentation_preset")
                or filter_config.get("force_remove_selectors")
            ):
                content_filter = EnhancedContentFilter(
                    non_content_selectors=filter_config.get("non_content_selectors"),
                    fuzzy_keywords=filter_config.get("fuzzy_keywords"),
                    log_levels=filter_config.get("log_levels"),
                    meaningless_content=filter_config.get("meaningless_content"),
                    preset=filter_config.get("documentation_preset"),
                    auto_detect_framework=True,
                    merge_mode=filter_config.get("merge_mode", "extend"),
                    force_remove_selectors=filter_config.get("force_remove_selectors"),
                )
                # 应用高级配置
                if filter_config.get("content_end_markers"):
                    content_filter.content_end_markers = filter_config[
                        "content_end_markers"
                    ]
                if filter_config.get("content_preserve_selectors"):
                    content_filter.content_preserve_selectors = filter_config[
                        "content_preserve_selectors"
                    ]
                if filter_config.get("code_container_selectors"):
                    content_filter.code_container_selectors = filter_config[
                        "code_container_selectors"
                    ]
                if filter_config.get("protected_tag_blacklist"):
                    content_filter.protected_tag_blacklist = filter_config[
                        "protected_tag_blacklist"
                    ]

                print("使用增强版过滤器（支持 content_end_markers）")
                return content_filter
            else:
                print("使用标准内容过滤器")
                return ContentFilter()
        except Exception as e:
            print(f"无法加载内容过滤器配置 ({e})，使用标准内容过滤器")
            return ContentFilter()

    def _build_doc_root_path(self) -> str:
        """
        构建文档根目录路径
        格式: doc_dir/<doc_name>@<doc_version>/

        Returns:
            str: 文档根目录的绝对路径
        """
        # 获取文档名称（从配置或自动检测）
        doc_name = self.config.doc_name
        if not doc_name:
            # 从start_url中提取文档名称
            if self.config.start_url:
                parsed = urlparse(self.config.start_url)
                doc_name = parsed.netloc.replace(".", "_")
            else:
                doc_name = "documentation"

        # 构建目录名称: <doc_name>@<doc_version>
        dir_name = f"{doc_name}@{self.config.doc_version}"

        # 构建完整路径
        full_path = os.path.join(self.config.doc_dir, dir_name)

        # 创建目录
        os.makedirs(full_path, exist_ok=True)

        if self.debug_mode:
            print(f"[DEBUG] 文档根目录: {full_path}")

        return full_path

    def _clean_title(self, title: str) -> str:
        """
        清理页面标题，移除配置的指定文本

        Args:
            title: 原始页面标题

        Returns:
            str: 清理后的标题（已strip首尾空白符）
        """
        if not title:
            return title

        cleaned = title
        for pattern in self.config.title_cleanup_patterns:
            cleaned = cleaned.replace(pattern, "")

        return cleaned.strip()

    def _generate_page_directory_name(self, url: str, page_title: str = "") -> str:
        """
        生成页面目录名

        优先级：
        1. 如果有页面标题，使用标题作为目录名
        2. 如果没有标题，使用 URL 路径作为目录名

        Args:
            url: 页面URL
            page_title: HTML页面标题

        Returns:
            str: 清理后的目录名
        """
        if page_title:
            # 使用页面标题作为目录名
            dir_name = self.content_filter.sanitize_filename(
                page_title, is_directory=True
            )
        else:
            # 回退：使用 URL 路径
            parsed = urlparse(url)
            path = parsed.path.rstrip("/")

            if path:
                # 使用路径最后一段
                path_parts = [p for p in path.split("/") if p and not p.startswith(".")]
                if path_parts:
                    dir_name = path_parts[-1]
                else:
                    dir_name = "index"
            else:
                # 使用域名作为目录名
                dir_name = parsed.netloc.replace(".", "_")

            # 清理目录名
            dir_name = self.content_filter.sanitize_filename(
                dir_name, is_directory=True
            )

        return dir_name

    def _debug_print(self, message: str):
        """调试输出"""
        if self.debug_mode:
            print(f"{Fore.MAGENTA}[DEBUG]{Style.RESET_ALL} {message}")

    def _get_playwright_proxy(self):
        """
        获取 Playwright 代理配置

        Returns:
            dict 或 None: Playwright 代理配置
        """
        if self.config.proxy:
            # proxy 格式: {'http': 'http://proxy:port', 'https': 'https://proxy:port'}
            http_proxy = self.config.proxy.get("http") or self.config.proxy.get("https")
            if http_proxy:
                return {"server": http_proxy}
        return None

    def _apply_fingerprint_stealth(self, page):
        """
        应用 stealth 插件指纹伪装

        Args:
            page: Playwright page 对象
        """
        if not STEALTH_AVAILABLE or not self.playwright_stealth:
            self._debug_print("Stealth 插件不可用或已禁用，跳过指纹伪装")
            return

        try:
            self._debug_print(
                f"应用 stealth 指纹伪装: platform={self.playwright_platform}"
            )

            stealth_sync(
                page,
                platform=self.playwright_platform,
                screen_width=self.playwright_screen_width,
                screen_height=self.playwright_screen_height,
                device_scale_factor=self.playwright_device_scale_factor,
                timezone=self.playwright_timezone,
                locale=self.playwright_locale,
            )

            self._debug_print("Stealth 指纹伪装应用成功")
        except Exception as e:
            self._debug_print(f"应用 stealth 指纹伪装失败: {e}")

    def _load_playwright_cookies(self) -> list:
        """
        加载 Playwright Cookie（支持文件和内联配置）

        Returns:
            list: Cookie 列表
        """
        cookies = []

        # 从文件加载
        if self.playwright_cookies_file:
            cookies.extend(self._load_cookies_from_file(self.playwright_cookies_file))

        # 从内联配置加载
        if self.playwright_cookies:
            cookies.extend(self.playwright_cookies)

        if cookies:
            self._debug_print(f"已加载 {len(cookies)} 个 Cookie")

        return cookies

    def _load_cookies_from_file(self, file_path: str) -> list:
        """
        从 Netscape 格式的 cookies.txt 文件加载 Cookie

        Args:
            file_path: Cookie 文件路径

        Returns:
            list: Cookie 列表
        """
        cookies = []

        if not os.path.exists(file_path):
            self._debug_print(f"Cookie 文件不存在: {file_path}")
            return cookies

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("\t")
                        if len(parts) >= 7:
                            cookie = {
                                "name": parts[5],
                                "value": parts[6],
                                "domain": parts[0],
                                "path": parts[2],
                                "expires": float(parts[4]) if parts[4] else -1,
                                "httpOnly": parts[6].upper() == "TRUE",
                                "secure": parts[3].upper() == "TRUE",
                            }
                            cookies.append(cookie)

            self._debug_print(f"从文件加载了 {len(cookies)} 个 Cookie: {file_path}")
        except Exception as e:
            self._debug_print(f"加载 Cookie 文件失败: {e}")

        return cookies

    def _needs_client_side_rendering(self, soup: BeautifulSoup) -> bool:
        """
        检测页面是否需要客户端渲染（JavaScript 动态内容）

        检测条件（满足任一即触发 Playwright）：
        1. 强制模式：playwright_force=True 时始终返回 True
        2. Next.js bailout 标记：template 标签含 BAILOUT_TO_CLIENT_SIDE_RENDERING
        3. LangChain 特定标记：[data-component-name="mermaid-container"] 内容为空
        4. 通用动态渲染标记：
           - [data-ice] (Mintlify hydration)
           - client-only 类名
           - 大量空容器 (>3 个)

        Args:
            soup: BeautifulSoup 解析后的 HTML

        Returns:
            bool: True 表示需要客户端渲染
        """
        # 1. 强制模式：启用 playwright_force 时始终使用 Playwright
        if self.playwright_force:
            self._debug_print("强制模式：使用 Playwright 获取所有页面")
            return True

        if not PLAYWRIGHT_AVAILABLE or not self.playwright_enabled:
            return False

        # 1. 检测 Next.js bailout 标记
        templates = soup.find_all("template")
        for template in templates:
            if template.get(
                "data-nextjs-router"
            ) == "push" or "BAILOUT_TO_CLIENT_SIDE_RENDERING" in str(template):
                self._debug_print("检测到 Next.js bailout 标记，需要客户端渲染")
                return True

        # 2. 检测 LangChain 特定标记 (mermaid 容器)
        mermaid_containers = soup.find_all(
            attrs={"data-component-name": "mermaid-container"}
        )
        for container in mermaid_containers:
            # 如果容器几乎是空的，可能需要 JS 渲染
            text = container.get_text(strip=True)
            if not text or len(text) < 10:
                self._debug_print("检测到空的 mermaid-container，需要客户端渲染")
                return True

        # 3. 检测 Mintlify hydration 标记
        mintlify_elements = soup.find_all(attrs={"data-ice": True})
        if mintlify_elements:
            # 检查是否有空的内容容器
            empty_containers = 0
            for elem in mintlify_elements:
                text = elem.get_text(strip=True)
                if not text:
                    empty_containers += 1
            if empty_containers > 0:
                self._debug_print(
                    f"检测到 {empty_containers} 个空的 Mintlify hydration 容器，需要客户端渲染"
                )
                return True

        # 4. 检测 client-only 类名
        client_only_elements = soup.find_all(
            class_=lambda x: x and "client-only" in " ".join(x) if x else False
        )
        if client_only_elements:
            self._debug_print(
                f"检测到 {len(client_only_elements)} 个 client-only 元素，需要客户端渲染"
            )
            return True

        # 5. 检测大量空容器 (可能表示动态内容占位符)
        empty_containers = soup.find_all(
            lambda tag: (
                tag.name in ["div", "span"]
                and not tag.get("class")
                and not tag.findChildren()
                and len(tag.get_text(strip=True)) == 0
            )
        )
        if len(empty_containers) > 5:
            self._debug_print(
                f"检测到 {len(empty_containers)} 个空容器，可能需要客户端渲染"
            )
            # 降低阈值，避免误判
            if len(empty_containers) > 10:
                return True

        # 6. 检测常见的动态渲染框架标记
        dynamic_markers = [
            ("data-astro-slot", True),  # Astro components
            ("data-svelte", True),  # Svelte components
            ("data-vue", True),  # Vue components
            ("react-root", True),  # React root
            ("data-server-rendered", "false"),  # Explicit client render
        ]

        for attr, value in dynamic_markers:
            elements = soup.find_all(attrs={attr: value})
            if elements:
                self._debug_print(
                    f"检测到动态渲染标记 [{attr}={value}]，需要客户端渲染"
                )
                return True

        return False

    def _wait_for_mermaid_render(self, page, timeout: int = 10000) -> bool:
        """
        等待 mermaid 图表渲染完成（通用方案）

        策略：
        1. 检测页面是否有 mermaid 相关元素或脚本
        2. 如果有 .mermaid 类元素，等待其内容变成 SVG 或 g 元素
        3. 执行 JavaScript 检查 mermaid 是否正在运行
        4. 如果检测不到渲染，直接返回 True

        Args:
            page: Playwright page 对象
            timeout: 超时时间（毫秒）

        Returns:
            bool: 是否等待成功（超时也算成功，避免阻塞）
        """
        try:
            # 检查页面是否有 mermaid 相关元素（同步调用）
            has_mermaid = page.evaluate("""
                () => {
                    // 检查多种可能的 mermaid 标记
                    const selectors = [
                        '.mermaid',           // 标准 class
                        'pre.mermaid',        // pre 标签
                        'div.mermaid',        // div 标签
                        '[data-component-name="mermaid-container"]',  // LangChain
                        'mermaid',            // 自定义标签
                        'code.language-mermaid'  // 代码块
                    ];

                    for (const sel of selectors) {
                        if (document.querySelector(sel)) {
                            return true;
                        }
                    }

                    // 检查是否有 mermaid 脚本
                    const scripts = document.querySelectorAll('script[src*="mermaid"]');
                    return scripts.length > 0;
                }
            """)

            if not has_mermaid:
                self._debug_print("页面没有 mermaid 相关元素，跳过等待")
                return True

            self._debug_print("检测到 mermaid 元素，等待渲染完成...")

            # 方案1: 等待 .mermaid 元素内的 SVG 或 g 元素出现
            try:
                # 尝试多种选择器
                page.wait_for_selector(
                    ".mermaid svg, .mermaid > svg, svg.flowchart",
                    timeout=min(timeout, 10000),  # 延长到 10 秒
                    state="attached",
                )
                self._debug_print("Mermaid SVG 渲染完成")
                return True
            except Exception:
                pass

            # 方案2: 等待一段时间让 JS 完成渲染（如果方案1超时）
            try:
                page.wait_for_timeout(3000)  # 等待 5 秒
                self._debug_print("等待 mermaid 渲染（5秒）")

                # 再次检查 SVG 是否出现
                svg_count = page.locator("svg.flowchart").count()
                if svg_count > 0:
                    self._debug_print(f"Mermaid 渲染完成，找到 {svg_count} 个图表")
                    return True
            except Exception:
                pass

            self._debug_print("Mermaid 渲染等待完成（超时或完成）")
            return True

        except Exception as e:
            self._debug_print(f"检查 mermaid 状态失败: {e}")
            return True

    def _fetch_with_playwright(self, url: str, headers: dict) -> Optional[str]:
        """
        使用 Playwright 获取渲染后的页面内容

        Args:
            url: 目标 URL
            headers: 请求头（用于设置 User-Agent 等）

        Returns:
            str: 渲染后的 HTML 内容，或 None（获取失败时）
        """
        if not PLAYWRIGHT_AVAILABLE:
            self._debug_print("Playwright 不可用，无法使用浏览器渲染")
            return None

        try:
            self._debug_print(f"使用 Playwright 获取渲染后的页面: {url}")

            # 提取 User-Agent
            user_agent = headers.get("User-Agent", "Mozilla/5.0")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.playwright_headless)

                context_options = {
                    "user_agent": user_agent,
                    "ignore_https_errors": True,
                    # 新增指纹参数
                    "screen": {
                        "width": self.playwright_screen_width,
                        "height": self.playwright_screen_height,
                    },
                    "device_scale_factor": self.playwright_device_scale_factor,
                    "locale": self.playwright_locale,
                }

                # 设置时区
                if self.playwright_timezone:
                    context_options["timezone_id"] = self.playwright_timezone

                # 添加代理配置
                proxy = self._get_playwright_proxy()
                if proxy:
                    context_options["proxy"] = proxy

                context = browser.new_context(**context_options)

                # 添加 Cookie
                cookies = self._load_playwright_cookies()
                if cookies:
                    context.add_cookies(cookies)

                page = context.new_page()

                # 应用 stealth 指纹伪装
                self._apply_fingerprint_stealth(page)

                # 设置超时
                page.set_default_timeout(self.playwright_timeout * 1000)

                # 使用 domcontentloaded 避免 SPA 网络活动导致的超时
                page.goto(url, wait_until="domcontentloaded")

                # 等待 mermaid 渲染完成
                self._wait_for_mermaid_render(
                    page, timeout=self.playwright_timeout * 1000
                )

                # 短暂等待网络稳定
                page.wait_for_load_state("networkidle", timeout=5000)

                # 获取渲染后的 HTML
                html_content = page.content()

                context.close()
                browser.close()

                self._debug_print(
                    f"Playwright 获取成功，HTML 长度: {len(html_content)} 字符"
                )
                return html_content

        except Exception as e:
            self._debug_print(f"Playwright 获取失败 {url}: {e}")
            return None

    def _print_colored(self, message: str, color: str = Fore.WHITE):
        """彩色输出"""
        if COLOR_SUPPORT:
            print(f"{color}{message}{Style.RESET_ALL}")
        else:
            print(message)

    def _is_valid_url_for_crawl(self, url: str) -> bool:
        """
        检查URL是否适合爬取

        Args:
            url: 待检查的URL

        Returns:
            bool: True表示应该爬取，False表示应该跳过
        """
        # 基本URL验证
        if not url or not url.startswith(("http://", "https://")):
            return False

        # 检查是否已爬取
        if url in self.crawled_urls:
            return False

        # 获取URL过滤器配置
        filters = self.config.toc_url_filters or {}

        # 检查子域名过滤
        subdomains = filters.get("subdomains", [])
        matches_subdomain = False
        if subdomains:
            parsed = urlparse(url)
            # 检查是否匹配任一子域名前缀
            matches_subdomain = any(
                parsed.netloc.startswith(subdomain) for subdomain in subdomains
            )

        # 检查模糊匹配包含（必须包含其中一个路径）
        fuzzy_match = filters.get("fuzzy_match", [])
        matches_fuzzy = False
        if fuzzy_match:
            matches_fuzzy = any(pattern in url for pattern in fuzzy_match)

        # URL必须匹配至少一个正过滤器（如果配置了的话）
        # 如果配置了任一正过滤器，URL必须匹配其中之一
        has_positive_filters = subdomains or fuzzy_match
        if has_positive_filters:
            if not (matches_subdomain or matches_fuzzy):
                self._debug_print(f"URL未匹配任何正过滤器，跳过: {url}")
                with self.lock:
                    self.stats["filtered"] += 1
                return False

        # 检查排除模糊匹配（不能包含这些路径）
        exclude_fuzzy = filters.get("exclude_fuzzy", [])
        if exclude_fuzzy:
            should_exclude = any(pattern in url for pattern in exclude_fuzzy)
            if should_exclude:
                self._debug_print(f"URL被排除规则跳过: {url}")
                with self.lock:
                    self.stats["filtered"] += 1
                return False

        # 检查扩展名黑名单
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        for ext in self.config.extension_blacklist:
            if path.endswith(ext.lower()):
                self._debug_print(f"URL被扩展名黑名单跳过: {url} (ext: {ext})")
                with self.lock:
                    self.stats["skipped"] += 1
                return False

        return True

    def _generate_directory_structure(
        self, url: str, title: str = ""
    ) -> Dict[str, str]:
        """
        生成页面内容保存的目录结构

        新结构：
        <doc_dir>/<doc_name>@<doc_version>/<PageDirectoryName>/
        ├── docContent.md

        Args:
            url: 目标URL
            title: 页面标题

        Returns:
            Dict[str, str]: {
                'directory': 页面目录完整路径,
                'content_file': docContent.md 文件完整路径
            }
        """
        # 生成页面目录名
        page_dir_name = self._generate_page_directory_name(url, title)

        # 构建完整目录路径
        page_directory = os.path.join(self.doc_root_dir, page_dir_name)

        # 构建内容文件路径
        content_file = os.path.join(page_directory, "docContent.md")

        if self.debug_mode:
            self._debug_print(f"生成目录结构: {url} -> {page_directory}/docContent.md")

        return {"directory": page_directory, "content_file": content_file}

    def _fetch_page_content(self, url: str) -> Optional[Tuple[str, str, str]]:
        """
        获取网页内容

        流程：
        1. 使用 requests 获取原始 HTML
        2. 检测是否需要客户端渲染
        3. 如果需要，使用 Playwright 获取渲染后的 HTML
        4. 提取页面标题

        Args:
            url: 目标URL

        Returns:
            Optional[Tuple[str, str, str]]: (html_content, page_title, final_url) 或 None
        """
        try:
            headers = self.config.headers.copy()

            # 步骤 1: 使用 requests 获取原始 HTML
            response = requests.get(
                url,
                headers=headers,
                timeout=self.config.doc_timeout,
                proxies=self.config.proxy,
                verify=False,
                allow_redirects=True,
            )

            response.raise_for_status()

            # 自动检测编码
            if response.encoding == "ISO-8859-1":
                response.encoding = response.apparent_encoding

            html_content = response.text
            final_url = response.url  # 获取最终URL（处理重定向后）

            # 步骤 2: 检测是否需要客户端渲染
            soup = BeautifulSoup(html_content, "html.parser")

            if self._needs_client_side_rendering(soup):
                self._debug_print(
                    f"检测到动态内容，使用 Playwright 获取渲染后的页面: {url}"
                )

                # 步骤 3: 使用 Playwright 获取渲染后的 HTML
                rendered_html = self._fetch_with_playwright(final_url, headers)

                if rendered_html:
                    # 重新解析渲染后的 HTML
                    html_content = rendered_html
                    soup = BeautifulSoup(html_content, "html.parser")
                else:
                    # Playwright 失败，回退到原始 HTML，打印警告
                    self._print_colored(
                        f"⚠ Playwright 获取失败，回退到原始 HTML: {final_url}",
                        Fore.YELLOW,
                    )

            # 步骤 4: 提取页面标题
            page_title = self.content_filter.get_page_title(final_url, soup)

            # 清理标题
            page_title = self._clean_title(page_title)

            return html_content, page_title, final_url

        except requests.exceptions.RequestException as e:
            self._debug_print(f"获取页面失败 {url}: {e}")
            return None
        except Exception as e:
            self._debug_print(f"处理页面时出错 {url}: {e}")
            return None

    def _convert_to_markdown(self, html_content: str, url: str, page_title: str) -> str:
        """
        将HTML内容转换为Markdown格式

        Args:
            html_content: HTML内容
            url: 原始URL
            page_title: 页面标题

        Returns:
            str: Markdown内容
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 转换相对链接为绝对链接
            link_processor = LinkProcessor(url)
            soup = link_processor.convert_relative_links(soup)

            # 过滤非正文内容
            cleaned_soup = self.content_filter.filter_non_content_blocks(soup)
            cleaned_soup = self.content_filter.filter_logging_outputs(cleaned_soup)

            # 处理 data-src 懒加载图片：将 data-src 复制到 src
            for img in cleaned_soup.find_all("img"):
                data_src = img.get("data-src")
                if data_src and not img.get("src"):
                    img["src"] = data_src

            # 新方法：将 mermaid 元素替换为占位符，保持位置信息
            html_with_placeholders, mermaid_map = self.mermaid_parser.replace_mermaid_with_placeholders(
                str(cleaned_soup)
            )

            # 转换为Markdown（占位符会被保留在相应位置）
            markdown_content = self.markdown_converter.convert_to_markdown(
                html_with_placeholders
            )

            # 在 Markdown 中恢复 mermaid 图表到原始位置
            if mermaid_map:
                markdown_content = self.mermaid_parser.restore_mermaid_in_markdown(
                    markdown_content, mermaid_map
                )

            # 过滤内容结束标识（如 "Next steps" 后的内容）
            markdown_content = self.content_filter.filter_content_end_markers(
                markdown_content
            )

            # 移除无意义内容
            markdown_content = self.content_filter.remove_meaningless_content(
                markdown_content
            )

            # 添加图片URL（在图片下方显示纯URL）
            extract_images = self.config.extract_image_list
            if extract_images is not None:
                markdown_content = self.markdown_converter.add_image_urls(
                    markdown_content, extract_images
                )

            # 添加元数据头部
            header = f"# {page_title}\n\n"
            header += f"> **原文链接**: {url}\n\n"
            header += "---\n\n"

            return header + markdown_content

        except Exception as e:
            self._debug_print(f"转换Markdown时出错: {e}")
            # 返回基本格式
            return f"# {page_title}\n\n原文链接: {url}\n\n转换失败，请查看原网页。"

    def _save_markdown_file(self, content: str, filepath: str) -> bool:
        """
        保存Markdown文件

        Args:
            content: Markdown内容
            filepath: 文件保存路径

        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(
                os.path.dirname(filepath) if os.path.dirname(filepath) else ".",
                exist_ok=True,
            )

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            self._debug_print(f"保存文件成功: {filepath}")
            return True

        except Exception as e:
            self._debug_print(f"保存文件失败 {filepath}: {e}")
            return False

    def _crawl_single_url(self, url: str) -> Dict[str, any]:
        """
        爬取单个URL

        Args:
            url: 目标URL

        Returns:
            Dict[str, any]: 爬取结果
        """
        result = {
            "url": url,
            "success": False,
            "filepath": None,
            "error": None,
            "title": None,
        }

        try:
            # 检查URL是否有效
            if not self._is_valid_url_for_crawl(url):
                result["error"] = "URL被过滤"
                return result

            # 获取页面内容
            fetch_result = self._fetch_page_content(url)
            if not fetch_result:
                result["error"] = "获取页面失败"
                with self.lock:
                    self.stats["failed"] += 1
                return result

            html_content, page_title, final_url = fetch_result

            # 使用最终URL（处理重定向）
            crawl_url = final_url

            # 再次检查最终URL是否已爬取
            if crawl_url in self.crawled_urls:
                result["error"] = "URL已爬取（重定向）"
                with self.lock:
                    self.stats["skipped"] += 1
                return result

            # 转换为Markdown
            markdown_content = self._convert_to_markdown(
                html_content, crawl_url, page_title
            )

            # 生成文件保存路径
            dir_structure = self._generate_directory_structure(crawl_url, page_title)

            # 保存文件
            if self._save_markdown_file(
                markdown_content, dir_structure["content_file"]
            ):
                result["success"] = True
                result["filepath"] = dir_structure["content_file"]
                result["title"] = page_title

                with self.lock:
                    self.stats["success"] += 1
                    self.crawled_urls.add(crawl_url)

                self._print_colored(
                    f"✓ {page_title[:50]} -> {os.path.basename(dir_structure['directory'])}/",
                    Fore.GREEN,
                )
            else:
                result["error"] = "保存文件失败"
                with self.lock:
                    self.stats["failed"] += 1

        except Exception as e:
            result["error"] = str(e)
            with self.lock:
                self.stats["failed"] += 1
            self._debug_print(f"爬取URL时出错 {url}: {e}")

        return result

    def _read_urls_from_csv(self, csv_file: str) -> List[str]:
        """
        从CSV文件中读取URL列表

        Args:
            csv_file: CSV文件路径

        Returns:
            List[str]: URL列表
        """
        urls = []

        try:
            if not os.path.exists(csv_file):
                self._print_colored(f"CSV文件不存在: {csv_file}", Fore.YELLOW)
                return urls

            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)  # 跳过表头

                for row in reader:
                    if row:  # 第一列是URL
                        url = row[0].strip()
                        if url and url.startswith(("http://", "https://")):
                            urls.append(url)

            self._print_colored(f"从CSV文件读取到 {len(urls)} 个URL", Fore.CYAN)

        except Exception as e:
            self._print_colored(f"读取CSV文件时出错: {e}", Fore.RED)

        return urls

    def _extract_links_from_page(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """
        从页面中提取链接（用于递归爬取）

        Args:
            soup: BeautifulSoup对象
            base_url: 基础URL

        Returns:
            Set[str]: 提取的链接集合
        """
        links = set()

        try:
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]

                # 转换为绝对链接
                absolute_url = urljoin(base_url, href)

                # 只处理同域名的链接
                base_parsed = urlparse(base_url)
                link_parsed = urlparse(absolute_url)

                if base_parsed.netloc == link_parsed.netloc:
                    links.add(absolute_url)

        except Exception as e:
            self._debug_print(f"提取链接时出错: {e}")

        return links

    def _recursive_crawl(self, url: str, depth: int = 0, max_depth: int = 10):
        """
        递归爬取网页

        Args:
            url: 起始URL
            depth: 当前深度
            max_depth: 最大深度
        """
        if depth > max_depth:
            return

        if url in self.crawled_urls:
            return

        # 爬取当前页面
        result = self._crawl_single_url(url)

        if not result["success"]:
            return

        # 获取页面内容并提取链接
        try:
            fetch_result = self._fetch_page_content(url)
            if fetch_result:
                html_content, _, _ = fetch_result
                soup = BeautifulSoup(html_content, "html.parser")
                links = self._extract_links_from_page(soup, url)

                # 递归爬取子页面
                for link in links:
                    if self._is_valid_url_for_crawl(link):
                        time.sleep(self.config.delay)  # 延迟
                        self._recursive_crawl(link, depth + 1, max_depth)

        except Exception as e:
            self._debug_print(f"递归爬取时出错: {e}")

    def process_documentation_site(self, start_url: str = None):
        """
        处理文档站点（主入口方法）

        Args:
            start_url: 起始URL（如果为None则使用config中的start_url）
        """
        start_url = start_url or self.config.start_url

        if not start_url:
            self._print_colored("错误: 未指定起始URL", Fore.RED)
            return

        self._print_colored(f"\n{'=' * 60}", Fore.CYAN)
        self._print_colored(f"开始爬取文档站点", Fore.CYAN)
        self._print_colored(f"起始URL: {start_url}", Fore.CYAN)
        self._print_colored(f"输出目录: {self.doc_root_dir}", Fore.CYAN)
        self._print_colored(f"最大深度: {self.config.doc_max_depth}", Fore.CYAN)
        self._print_colored(f"{'=' * 60}\n", Fore.CYAN)

        # 方式1: 如果有output_file且mode不为2（递归模式），则从CSV读取
        # mode: 0=仅爬取CSV, 1=抓取文档内容, 2=抓取锚点链接
        if self.config.output_file and os.path.exists(self.config.output_file):
            self._print_colored("从CSV文件读取URL列表...", Fore.CYAN)
            urls = self._read_urls_from_csv(self.config.output_file)

            if urls:
                self.stats["total"] = len(urls)
                self._crawl_urls_batch(urls)
            else:
                self._print_colored("CSV文件中没有有效的URL", Fore.YELLOW)

        # 方式2: 递归爬取（从start_url开始）
        else:
            self._print_colored("使用递归爬取模式...", Fore.CYAN)
            self._recursive_crawl(start_url, max_depth=self.config.doc_max_depth)

        # 打印统计信息
        self._print_statistics()

    def _crawl_urls_batch(self, urls: List[str]):
        """
        批量爬取URL列表

        Args:
            urls: URL列表
        """
        self._print_colored(f"开始批量爬取 {len(urls)} 个URL...\n", Fore.CYAN)

        # 使用线程池并发爬取
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self._crawl_single_url, url): url for url in urls
            }

            for future in as_completed(futures):
                url = futures[future]
                try:
                    result = future.result()
                    # 延迟控制
                    time.sleep(self.config.delay)
                except Exception as e:
                    self._debug_print(f"处理URL时出错 {url}: {e}")

    def _print_statistics(self):
        """打印统计信息"""
        self._print_colored(f"\n{'=' * 60}", Fore.CYAN)
        self._print_colored(f"爬取完成统计", Fore.CYAN)
        self._print_colored(f"{'=' * 60}", Fore.CYAN)
        self._print_colored(f"总计URL: {self.stats['total']}", Fore.WHITE)
        self._print_colored(f"成功: {self.stats['success']}", Fore.GREEN)
        self._print_colored(f"失败: {self.stats['failed']}", Fore.RED)
        self._print_colored(f"跳过: {self.stats['skipped']}", Fore.YELLOW)
        self._print_colored(f"过滤: {self.stats['filtered']}", Fore.MAGENTA)
        self._print_colored(f"输出目录: {self.doc_root_dir}", Fore.CYAN)
        self._print_colored(f"{'=' * 60}\n", Fore.CYAN)
