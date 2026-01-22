"""
文档URL爬取模块 - DocUrlCrawler

功能：
1. 从CSV文件中读取URL列表
2. 爬取每个URL的HTML页面
3. 仅提取目录（TOC）中的锚点链接，过滤正文中的锚点
4. 按照层级结构保存为Markdown文件，带层级编号

输出格式：
- 文件名：<Title>.md（使用页面标题）
- 内容（按层级结构）：
  ## 1. <一级索引名称>：<完整url>
  ### 1.1. <二级索引名称>：<完整url>
  #### 1.1.1. <三级索引名称>：<完整url>
  - 1.1.1.1. <四级索引名称>：<完整url>
"""

import os
import csv
import time
import threading
from urllib.parse import urlparse, unquote
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLOR_SUPPORT = True
except ImportError:
    COLOR_SUPPORT = False
    Fore = Style = type('', (), {'__getattr__': lambda *args: ''})()

from doc4llm.scanner.utils import DebugMixin, BloomFilter
from doc4llm.filter import ContentFilter
from doc4llm.filter.config import (
    TocFilterConfigLoader,
    TOC_CLASS_PATTERNS,
    TOC_LINK_CLASS_PATTERNS,
    TOC_PARENT_CLASS_PATTERNS,
    CONTENT_AREA_PATTERNS,
    NON_TOC_LINK_PATTERNS
)


class DocUrlCrawler(DebugMixin):
    """
    文档URL爬取器 - 提取页面目录中的锚点链接

    从CSV文件读取URL列表，爬取页面并仅提取目录（TOC）中的锚点链接，
    使用布隆过滤器去重，并添加层级编号。

    配置来源：
    - 默认配置：从 filter.config 模块加载
    - 自定义配置：从 config.json 的 toc_url_filter 配置段加载
    """

    def __init__(self, config):
        """
        初始化文档URL爬取器

        Args:
            config: ScannerConfig配置对象
        """
        # 初始化 DebugMixin
        super().__init__(debug_mode=config.debug_mode)

        self.config = config
        self.content_filter = ContentFilter()

        # 加载 TOC 过滤器配置
        # 从 config.json 的 toc_filter 配置段加载（如果存在）
        # TocFilterConfigLoader.load_from_config 期望包含 toc_filter 键的字典
        toc_filter_dict = {'toc_filter': config.toc_filter} if hasattr(config, 'toc_filter') else {}
        toc_filter_config = TocFilterConfigLoader.load_from_config(toc_filter_dict)

        # 使用配置文件中的值，如果没有则使用默认值
        self.TOC_CLASS_PATTERNS = toc_filter_config.get('toc_class_patterns', TOC_CLASS_PATTERNS)
        self.TOC_LINK_CLASS_PATTERNS = toc_filter_config.get('toc_link_class_patterns', TOC_LINK_CLASS_PATTERNS)
        self.TOC_PARENT_CLASS_PATTERNS = toc_filter_config.get('toc_parent_class_patterns', TOC_PARENT_CLASS_PATTERNS)
        self.CONTENT_AREA_PATTERNS = toc_filter_config.get('content_area_patterns', CONTENT_AREA_PATTERNS)
        self.NON_TOC_LINK_PATTERNS = toc_filter_config.get('non_toc_link_patterns', NON_TOC_LINK_PATTERNS)
        self.TOC_END_MARKERS = toc_filter_config.get('toc_end_markers', [])

        # 加载 exclude_fuzzy 黑名单配置
        filters = self.config.toc_url_filters or {}
        self.EXCLUDE_FUZZY = filters.get('exclude_fuzzy', [])

        # 使用布隆过滤器去重
        self.bloom_filter = BloomFilter(expected_elements=10000, false_positive_rate=0.001)

        # 统计信息
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'no_anchors': 0,
            'total_anchors': 0,
            'duplicates_filtered': 0
        }

        # 线程锁
        self.lock = threading.Lock()

        # 文档根目录
        self.doc_root_dir = self._build_doc_root_path()

    def _build_doc_root_path(self) -> str:
        """
        构建文档根目录路径
        格式: doc_dir/<doc_name>:<doc_version>/

        Returns:
            str: 文档根目录的绝对路径
        """
        # 获取文档名称（从配置或自动检测）
        doc_name = self.config.doc_name
        if not doc_name:
            # 从start_url中提取文档名称
            if self.config.start_url:
                parsed = urlparse(self.config.start_url)
                doc_name = parsed.netloc.replace('.', '_')
            else:
                doc_name = 'documentation'

        # 构建目录名称: <doc_name>:<doc_version>
        dir_name = f"{doc_name}:{self.config.doc_version}"

        # 构建完整路径
        full_path = os.path.join(self.config.doc_dir, dir_name)

        # 创建目录
        os.makedirs(full_path, exist_ok=True)

        if self.debug_mode:
            self._debug_print(f"文档根目录: {full_path}")

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
            cleaned = cleaned.replace(pattern, '')

        return cleaned.strip()

    def _is_in_toc(self, a_tag) -> bool:
        """
        判断锚点链接是否在目录（TOC）区域

        使用白名单优先的策略：
        1. 先检查白名单（包含规则）：如果匹配则返回 True
        2. 再检查黑名单（排除规则）：如果匹配则返回 False

        Args:
            a_tag: BeautifulSoup 的 a 标签元素

        Returns:
            bool: 是否在 TOC 中
        """
        try:
            # ========== 白名单优先检查（包含规则） ==========

            # 1. 检查直接父元素（如 li.toc-item）
            direct_parent = a_tag.parent
            if direct_parent and direct_parent.has_attr('class'):
                parent_classes = ' '.join(direct_parent['class']).lower()
                for pattern in self.TOC_PARENT_CLASS_PATTERNS:
                    if pattern in parent_classes:
                        return True

            # 2. 检查链接自身的 class 是否包含白名单模式
            if a_tag.has_attr('class'):
                classes = ' '.join(a_tag['class']).lower()
                for pattern in self.TOC_LINK_CLASS_PATTERNS:
                    if pattern in classes:
                        return True

            # 3. 向上遍历父元素，检查是否在 TOC 容器中
            parent = a_tag.parent
            depth = 0
            max_depth = 10

            while parent and depth < max_depth:
                # 检查父元素的 id
                if parent.has_attr('id'):
                    elem_id = parent['id'].lower()
                    for pattern in self.TOC_CLASS_PATTERNS:
                        if pattern in elem_id:
                            return True

                # 检查父元素的 class
                if parent.has_attr('class'):
                    classes = ' '.join(parent['class']).lower()
                    for pattern in self.TOC_CLASS_PATTERNS:
                        if pattern in classes:
                            return True

                parent = parent.parent
                depth += 1

            # ========== 黑名单检查（排除规则） ==========

            # 4. 检查链接自身的 class 是否包含黑名单模式
            if a_tag.has_attr('class'):
                classes = ' '.join(a_tag['class']).lower()
                for pattern in self.NON_TOC_LINK_PATTERNS:
                    if pattern in classes:
                        self._debug_print(f"过滤非TOC链接（黑名单class）: {classes[:50]}")
                        return False

            # 5. 检查父元素是否在正文内容区域
            parent = a_tag.parent
            depth = 0
            max_depth = 8

            while parent and depth < max_depth:
                # 检查父元素的 id
                if parent.has_attr('id'):
                    elem_id = parent['id'].lower()
                    # 排除包含 content 的 id（但保留 table-of-contents）
                    if 'content' in elem_id and 'table-of-contents' not in elem_id:
                        self._debug_print(f"过滤非TOC链接（content id）: {elem_id}")
                        return False

                # 检查父元素的 class
                if parent.has_attr('class'):
                    classes = ' '.join(parent['class']).lower()

                    # 排除正文内容区域的 class
                    for pattern in self.CONTENT_AREA_PATTERNS:
                        if pattern in classes:
                            self._debug_print(f"过滤非TOC链接（content area class）: {classes[:50]}")
                            return False

                parent = parent.parent
                depth += 1

            # 6. 默认情况下，如果不在白名单中，则认为不是 TOC 链接
            return False

        except Exception as e:
            self._debug_print(f"判断TOC时出错: {e}")
            return False

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

            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # 跳过表头

                for row in reader:
                    if row:  # 第一列是URL
                        url = row[0].strip()
                        if url and url.startswith(('http://', 'https://')):
                            urls.append(url)

            self._print_colored(f"从CSV文件读取到 {len(urls)} 个URL", Fore.CYAN)

        except Exception as e:
            self._print_colored(f"读取CSV文件时出错: {e}", Fore.RED)

        return urls

    def _fetch_page_content(self, url: str) -> Optional[Tuple[str, str]]:
        """
        获取网页内容

        Args:
            url: 目标URL

        Returns:
            Optional[Tuple[str, str]]: (html_content, page_title) 或 None
        """
        try:
            headers = self.config.headers.copy()

            response = requests.get(
                url,
                headers=headers,
                timeout=self.config.doc_timeout,
                proxies=self.config.proxy,
                verify=False,
                allow_redirects=True
            )

            response.raise_for_status()

            # 自动检测编码
            if response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding

            html_content = response.text
            final_url = response.url  # 获取最终URL（处理重定向后）

            # 提取页面标题
            soup = BeautifulSoup(html_content, 'html.parser')
            page_title = self.content_filter.get_page_title(final_url, soup)

            # 清理标题
            page_title = self._clean_title(page_title)

            return html_content, page_title

        except requests.exceptions.RequestException as e:
            self._debug_print(f"获取页面失败 {url}: {e}")
            return None
        except Exception as e:
            self._debug_print(f"处理页面时出错 {url}: {e}")
            return None

    def _extract_anchor_links(self, html_content: str, base_url: str) -> List[Dict[str, any]]:
        """
        仅提取目录（TOC）中的锚点链接，并分析层级结构

        Args:
            html_content: HTML内容
            base_url: 基础URL

        Returns:
            List[Dict]: [
                {
                    'name': 'anchor-name',
                    'text': 'Anchor Text',
                    'url': 'full-url#anchor',
                    'level': 1-4 (层级级别)
                }
            ]
        """
        anchor_links = []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 先构建一个 id 到元素的映射，用于快速查找锚点对应的元素
            # 同时存储 URL 解码后的 id，用于匹配
            id_to_element = {}
            for elem in soup.find_all(id=True):
                elem_id = elem['id']
                id_to_element[elem_id] = elem
                # 同时存储解码后的 id
                decoded_id = unquote(elem_id)
                if decoded_id != elem_id:
                    id_to_element[decoded_id] = elem

            # 根据 doc_toc_selector 配置决定搜索范围
            if self.config.doc_toc_selector:
                # 使用 CSS 选择器定位 TOC 容器
                self._debug_print(f"使用 CSS 选择器定位 TOC: {self.config.doc_toc_selector}")
                toc_containers = soup.select(self.config.doc_toc_selector)
                if not toc_containers:
                    self._debug_print(f"警告: 未找到匹配 '{self.config.doc_toc_selector}' 的 TOC 容器，尝试全页面搜索")

                # 在指定的 TOC 容器中搜索锚点链接
                for container in toc_containers:
                    for a_tag in container.find_all('a', href=True):
                        self._process_anchor_tag(a_tag, base_url, id_to_element, soup, anchor_links)
            else:
                # 回退到原有的白名单/黑名单策略
                self._debug_print("使用白名单/黑名单策略检测 TOC")
                # 查找所有 href 以 # 开头的 a 标签
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']

                    # 只处理页面内锚点（以 # 开头）
                    if str(href).startswith('#'):
                        # 只提取 TOC 目录中的链接
                        if not self._is_in_toc(a_tag):
                            continue

                        self._process_anchor_tag(a_tag, base_url, id_to_element, soup, anchor_links)

        except Exception as e:
            self._debug_print(f"提取锚点链接时出错: {e}")

        return anchor_links

    def _process_anchor_tag(self, a_tag, base_url: str, id_to_element: dict, soup: BeautifulSoup, anchor_links: List[Dict]):
        """
        处理单个锚点标签

        Args:
            a_tag: BeautifulSoup a 标签对象
            base_url: 基础URL
            id_to_element: id 到元素的映射
            soup: BeautifulSoup 对象
            anchor_links: 锚点链接列表（引用传递）
        """
        href = a_tag['href']

        # 只处理页面内锚点（以 # 开头）
        if not str(href).startswith('#'):
            return

        anchor_name = str(href)[1:]  # 去掉 #
        anchor_text = a_tag.get_text(strip=True)
        full_url = f"{base_url}{href}"

        # 使用 fuzzy_match 白名单过滤锚点名称
        if not self._match_anchor_pattern(anchor_name, anchor_text):
            self._debug_print(f"过滤不匹配的锚点: #{anchor_name} (text: {anchor_text})")
            return

        # 使用布隆过滤器去重
        if full_url in self.bloom_filter:
            with self.lock:
                self.stats['duplicates_filtered'] += 1
            self._debug_print(f"跳过重复链接: {full_url}")
            return

        # 添加到布隆过滤器
        self.bloom_filter.add(full_url)

        # 尝试解码 URL 编码的锚点名称
        decoded_anchor_name = unquote(anchor_name)

        # 检测锚点的层级级别（先尝试解码后的名称，再尝试原始名称）
        level = self._determine_anchor_level(decoded_anchor_name, id_to_element, soup)
        if level == 4:  # 如果解码后找不到，尝试原始名称
            level = self._determine_anchor_level(anchor_name, id_to_element, soup)

        # 解码锚点文本中的 URL 编码字符
        decoded_text = unquote(anchor_text) if anchor_text else anchor_name

        anchor_links.append({
            'name': anchor_name,
            'text': decoded_text,
            'url': full_url,
            'level': level
        })

    def _determine_anchor_level(self, anchor_name: str, id_to_element: dict, soup: BeautifulSoup) -> int:
        """
        判断锚点的层级级别

        层级映射：
        - h2 -> level 1 (##) 主要章节
        - h3 -> level 2 (###) 子章节
        - h4 -> level 3 (####) 更小的子章节
        - h5, h6, 其他 -> level 4 (-) 最小级别

        特殊处理：如果锚点对应的元素是 section，则查找该 section 内的第一个标题元素

        Args:
            anchor_name: 锚点名称（id）
            id_to_element: id 到元素的映射
            soup: BeautifulSoup 对象

        Returns:
            int: 层级级别 (1-4)
        """
        try:
            # 尝试找到锚点对应的元素
            if anchor_name in id_to_element:
                element = id_to_element[anchor_name]
                tag_name = element.name

                # 特殊处理：如果是 section 元素，查找其中的第一个标题
                if tag_name == 'section':
                    # 在 section 内查找第一个标题元素
                    heading = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if heading:
                        tag_name = heading.name
                        self._debug_print(f"section '{anchor_name}' 内的标题: {tag_name}")

                # 根据标签判断层级
                if tag_name == 'h2':
                    return 1
                elif tag_name == 'h3':
                    return 2
                elif tag_name == 'h4':
                    return 3
                elif tag_name in ['h5', 'h6']:
                    return 4

            # 如果找不到对应元素，尝试通过锚点名称的命名规则判断
            # 优先检查 fuzzy_match 配置：如果锚点匹配 fuzzy_match 模式，默认为 level 1
            filters = self.config.toc_url_filters or {}
            fuzzy_match = filters.get('fuzzy_match', [])

            if fuzzy_match:
                # 移除空的 pattern
                fuzzy_match = [p for p in fuzzy_match if p]

                for pattern in fuzzy_match:
                    pattern_lower = pattern.lower()

                    # 特殊处理：如果 pattern 是 "#"，表示所有锚点都是 level 1
                    if pattern_lower == '#':
                        return 1

                    # 检查锚点名称是否匹配
                    if pattern_lower in anchor_name.lower():
                        self._debug_print(f"fuzzy_match 匹配锚点名称: '{anchor_name}' 匹配模式 '{pattern}'，设为 level 1")
                        return 1

            if any(prefix in anchor_name.lower() for prefix in ['chapter', 'section', 'part']):
                return 1
            elif any(prefix in anchor_name.lower() for prefix in ['sub', 'subsection', 'topic']):
                return 2
            elif any(prefix in anchor_name.lower() for prefix in ['item', 'detail', 'note']):
                return 3

            # 默认为第四级
            return 4

        except Exception as e:
            self._debug_print(f"判断锚点层级时出错: {e}")
            return 4

    def _match_anchor_pattern(self, anchor_name: str, anchor_text: str) -> bool:
        """
        检查锚点是否匹配过滤规则

        过滤逻辑（优先级从高到低）：
        1. 黑名单检查（exclude_fuzzy）：匹配则返回 False（过滤）
        2. 白名单检查（fuzzy_match）：匹配则返回 True（保留）

        如果 exclude_fuzzy 和 fuzzy_match 都为空，则返回 True（保留所有锚点）

        Args:
            anchor_name: 锚点名称（href 中的 # 后面的部分）
            anchor_text: 锚点显示文本

        Returns:
            bool: 是否匹配（True=保留，False=过滤）
        """
        # ========== 黑名单检查（exclude_fuzzy）==========
        if self.EXCLUDE_FUZZY:
            # 移除空的 pattern
            exclude_fuzzy = [p for p in self.EXCLUDE_FUZZY if p]

            for pattern in exclude_fuzzy:
                pattern_lower = pattern.lower()

                # 检查锚点名称是否匹配黑名单
                if pattern_lower in anchor_name.lower():
                    self._debug_print(f"黑名单过滤锚点名称: '{anchor_name}' 匹配模式 '{pattern}'")
                    return False

                # 检查锚点文本是否匹配黑名单
                if anchor_text and pattern_lower in anchor_text.lower():
                    self._debug_print(f"黑名单过滤锚点文本: '{anchor_text}' 匹配模式 '{pattern}'")
                    return False

        # ========== 白名单检查（fuzzy_match）==========
        # 获取 fuzzy_match 配置
        filters = self.config.toc_url_filters or {}
        fuzzy_match = filters.get('fuzzy_match', [])

        # 如果 fuzzy_match 为空，不过滤，保留所有锚点
        if not fuzzy_match:
            return True

        # 移除空的 pattern
        fuzzy_match = [p for p in fuzzy_match if p]

        # 如果 fuzzy_match 为空（移除空值后），不过滤，保留所有锚点
        if not fuzzy_match:
            return True

        # 使用 OR 条件：只要匹配任一模式即保留
        for pattern in fuzzy_match:
            pattern_lower = pattern.lower()

            # 特殊处理：如果 pattern 是 "#"，表示保留所有锚点
            if pattern_lower == '#':
                return True

            # 检查锚点名称是否匹配
            if pattern_lower in anchor_name.lower():
                self._debug_print(f"锚点名称匹配: '{anchor_name}' 匹配模式 '{pattern}'")
                return True

            # 检查锚点文本是否匹配
            if anchor_text and pattern_lower in anchor_text.lower():
                self._debug_print(f"锚点文本匹配: '{anchor_text}' 匹配模式 '{pattern}'")
                return True

        # 没有匹配任何模式
        self._debug_print(f"过滤不匹配的锚点: #{anchor_name} (text: {anchor_text})")
        return False

    def _filter_toc_end_markers(self, anchor_links: List[Dict]) -> List[Dict]:
        """
        使用统一后处理模板过滤 TOC 锚点链接

        Args:
            anchor_links: 锚点链接列表

        Returns:
            List[Dict]: 过滤后的锚点链接列表
        """
        from doc4llm.filter.base import filter_by_end_markers

        return filter_by_end_markers(
            anchor_links,
            self.TOC_END_MARKERS,
            text_extractor=lambda link: link.get('text', '').strip(),
            debug_mode=self.debug_mode
        )

    def _add_hierarchy_numbers(self, anchor_links: List[Dict]) -> List[Dict]:
        """
        为锚点链接添加层级编号

        例如：
        - level 1: 1, 2, 3, ...
        - level 2: 1.1, 1.2, 2.1, 2.2, ...
        - level 3: 1.1.1, 1.1.2, ...
        - level 4: 1.1.1.1, 1.1.1.2, ...

        Args:
            anchor_links: 锚点链接列表

        Returns:
            List[Dict]: 添加了 hierarchy_number 字段的锚点链接列表
        """
        # 用于跟踪每个层级的编号
        counters = {1: 0, 2: 0, 3: 0, 4: 0}
        result = []

        for link in anchor_links:
            level = link.get('level', 4)

            # 重置更深层级的计数器
            for l in range(level + 1, 5):
                counters[l] = 0

            # 增加当前层级的计数器
            counters[level] += 1

            # 生成层级编号
            if level == 1:
                hierarchy_number = str(counters[1])
            elif level == 2:
                hierarchy_number = f"{counters[1]}.{counters[2]}"
            elif level == 3:
                hierarchy_number = f"{counters[1]}.{counters[2]}.{counters[3]}"
            else:  # level == 4
                hierarchy_number = f"{counters[1]}.{counters[2]}.{counters[3]}.{counters[4]}"

            # 复制链接并添加层级编号
            link_with_number = link.copy()
            link_with_number['hierarchy_number'] = hierarchy_number
            result.append(link_with_number)

        return result

    def _sanitize_filename(self, title: str, is_directory: bool = False) -> str:
        """
        清理文件名或目录名

        Args:
            title: 原始标题
            is_directory: 是否为目录名

        Returns:
            str: 清理后的文件名或目录名
        """
        # 委托给 ContentFilter
        return self.content_filter.sanitize_filename(title, is_directory=is_directory)

    def _save_anchor_links(self, title: str, anchor_links: List[Dict], base_url: str, doc_root_dir: str) -> bool:
        """
        保存锚点链接到 Markdown 文件（按层级格式，带层级编号）

        新位置: <doc_root_dir>/<PageDirectoryName>/docTOC.md

        文件名: docTOC.md
        内容格式:
        ## 1. <一级索引名称>：<完整url>
        ### 1.1. <二级索引名称>：<完整url>
        #### 1.1.1. <三级索引名称>：<完整url>
        - 1.1.1.1. <四级索引名称>：<完整url>

        Args:
            title: 页面标题
            anchor_links: 锚点链接列表（包含level字段）
            base_url: 原始URL
            doc_root_dir: 文档根目录

        Returns:
            bool: 是否保存成功
        """
        try:
            # 生成页面目录名
            page_dir_name = self._sanitize_filename(title, is_directory=True)

            # 构建完整目录路径
            page_directory = os.path.join(doc_root_dir, page_dir_name)

            # 构建 TOC 文件路径
            toc_file = os.path.join(page_directory, 'docTOC.md')

            # 确保目录存在
            os.makedirs(page_directory, exist_ok=True)

            # 应用 TOC 结束标识过滤
            filtered_anchor_links = self._filter_toc_end_markers(anchor_links)

            # 添加层级编号
            anchor_links_with_numbers = self._add_hierarchy_numbers(filtered_anchor_links)

            # 生成内容
            content = f"# {title}\n\n"
            content += f"原文链接: {base_url}\n\n"
            content += f"提取的锚点数量: {len(filtered_anchor_links)}\n\n"

            # 按照层级格式输出
            for link in anchor_links_with_numbers:
                level = link.get('level', 4)
                url = link.get('url', '')
                hierarchy_number = link.get('hierarchy_number', '')

                # 使用锚点文本作为索引名称（如果有且不为空）
                display_name = link.get('text', link.get('name', ''))

                # 根据层级使用不同的 Markdown 标记，并添加层级编号
                if level == 1:
                    content += f"## {hierarchy_number}. {display_name}：{url}\n\n"
                elif level == 2:
                    content += f"### {hierarchy_number}. {display_name}：{url}\n\n"
                elif level == 3:
                    content += f"#### {hierarchy_number}. {display_name}：{url}\n\n"
                else:  # level == 4 或其他
                    content += f"- {hierarchy_number}. {display_name}：{url}\n"

            # 保存文件
            with open(toc_file, 'w', encoding='utf-8') as f:
                f.write(content)

            self._debug_print(f"保存TOC文件成功: {toc_file}")
            return True

        except Exception as e:
            self._debug_print(f"保存TOC文件失败: {e}")
            return False

    def _process_single_url(self, url: str) -> Dict[str, any]:
        """
        处理单个URL的完整流程

        Args:
            url: 目标URL

        Returns:
            Dict[str, any]: 处理结果
        """
        result = {
            'url': url,
            'success': False,
            'filepath': None,
            'error': None,
            'title': None,
            'anchor_count': 0
        }

        try:
            # 获取页面内容
            fetch_result = self._fetch_page_content(url)
            if not fetch_result:
                result['error'] = '获取页面失败'
                with self.lock:
                    self.stats['failed'] += 1
                return result

            html_content, page_title = fetch_result

            # 提取锚点链接（仅TOC中的链接）
            anchor_links = self._extract_anchor_links(html_content, url)

            if not anchor_links:
                result['error'] = '未找到锚点链接'
                with self.lock:
                    self.stats['no_anchors'] += 1
                self._debug_print(f"未找到锚点链接: {url}")
                return result

            # 保存锚点链接
            if self._save_anchor_links(page_title, anchor_links, url, self.doc_root_dir):
                page_dir_name = self._sanitize_filename(page_title, is_directory=True)
                result['success'] = True
                result['filepath'] = os.path.join(self.doc_root_dir, page_dir_name, 'docTOC.md')
                result['title'] = page_title
                result['anchor_count'] = len(anchor_links)

                with self.lock:
                    self.stats['success'] += 1
                    self.stats['total_anchors'] += len(anchor_links)

                self._print_colored(
                    f"✓ {page_title[:40]}... ({len(anchor_links)} anchors)",
                    Fore.GREEN
                )
            else:
                result['error'] = '保存文件失败'
                with self.lock:
                    self.stats['failed'] += 1

        except Exception as e:
            result['error'] = str(e)
            with self.lock:
                self.stats['failed'] += 1
            self._debug_print(f"处理URL时出错 {url}: {e}")

        return result

    def process(self, csv_file: str):
        """
        主入口方法，批量处理URL

        Args:
            csv_file: CSV文件路径
        """
        # 读取URL列表
        urls = self._read_urls_from_csv(csv_file)

        if not urls:
            self._print_colored("没有找到有效的URL", Fore.YELLOW)
            return

        self.stats['total'] = len(urls)

        self._print_colored(f"\n{'='*60}", Fore.CYAN)
        self._print_colored(f"开始提取文档锚点链接（仅TOC目录）", Fore.CYAN)
        self._print_colored(f"CSV文件: {csv_file}", Fore.CYAN)
        self._print_colored(f"输出目录: {self.doc_root_dir}", Fore.CYAN)
        self._print_colored(f"URL数量: {len(urls)}", Fore.CYAN)
        self._print_colored(f"{'='*60}\n", Fore.CYAN)

        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self._process_single_url, url): url
                for url in urls
            }

            for future in as_completed(futures):
                url = futures[future]
                try:
                    result = future.result()
                    # 延迟控制
                    time.sleep(self.config.delay)
                except Exception as e:
                    self._debug_print(f"处理URL时出错 {url}: {e}")

        # 打印统计信息
        self._print_statistics()

    def _print_statistics(self):
        """打印统计信息"""
        self._print_colored(f"\n{'='*60}", Fore.CYAN)
        self._print_colored(f"提取完成统计", Fore.CYAN)
        self._print_colored(f"{'='*60}", Fore.CYAN)
        self._print_colored(f"总计URL: {self.stats['total']}", Fore.WHITE)
        self._print_colored(f"成功提取: {self.stats['success']}", Fore.GREEN)
        self._print_colored(f"失败: {self.stats['failed']}", Fore.RED)
        self._print_colored(f"无锚点: {self.stats['no_anchors']}", Fore.YELLOW)
        self._print_colored(f"过滤重复: {self.stats['duplicates_filtered']}", Fore.MAGENTA)
        self._print_colored(f"总锚点数: {self.stats['total_anchors']}", Fore.CYAN)
        self._print_colored(f"{'='*60}\n", Fore.CYAN)

    def _print_colored(self, message: str, color: str = Fore.WHITE):
        """彩色输出"""
        if COLOR_SUPPORT:
            print(f"{color}{message}{Style.RESET_ALL}")
        else:
            print(message)
