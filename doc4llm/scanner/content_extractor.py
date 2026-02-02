"""
内联内容提取器模块

功能：
1. 在扫描过程中实时提取内容和TOC，避免重复HTTP请求
2. 复用扫描器已获取的HTML响应，进行内容和TOC提取
3. 线程安全的文件操作和统计管理

使用场景：
- mode=1: 提取文档内容
- mode=2: 提取TOC锚点链接
- mode=3: 同时提取内容和TOC
"""

import os
import time
import threading
from urllib.parse import urlparse, unquote
from typing import Dict, Optional, Tuple, List
import requests
from bs4 import BeautifulSoup

try:
    from colorama import Fore, Style
    COLOR_SUPPORT = True
except ImportError:
    COLOR_SUPPORT = False
    Fore = Style = type('', (), {'__getattr__': lambda *args: ''})()

from doc4llm.filter import ContentFilter, EnhancedContentFilter
from doc4llm.filter.config import FilterConfigLoader, TocFilterConfigLoader
from doc4llm.filter.config import (
    TOC_CLASS_PATTERNS,
    TOC_LINK_CLASS_PATTERNS,
    TOC_PARENT_CLASS_PATTERNS,
    CONTENT_AREA_PATTERNS,
    NON_TOC_LINK_PATTERNS
)
from doc4llm.convertor.MarkdownConverter import MarkdownConverter
from doc4llm.link_processor.LinkProcessor import LinkProcessor
from doc4llm.scanner.utils import BloomFilter, DebugMixin


class ContentExtractor(DebugMixin):
    """
    内联内容提取器

    在扫描过程中实时提取内容和TOC，避免重复HTTP请求。
    仅使用已获取的HTML响应进行提取，不发起额外的网络请求。
    """

    def __init__(self, config):
        """
        初始化内容提取器

        Args:
            config: ScannerConfig配置对象
        """
        # 初始化 DebugMixin
        super().__init__(debug_mode=config.debug_mode)

        self.config = config
        self.debug_mode = config.debug_mode

        # 初始化过滤器
        self.content_filter = self._load_content_filter()

        # 加载 TOC 过滤器配置
        toc_filter_dict = {'toc_filter': config.toc_filter} if hasattr(config, 'toc_filter') else {}
        toc_filter_config = TocFilterConfigLoader.load_from_config(toc_filter_dict)

        self.TOC_CLASS_PATTERNS = toc_filter_config.get('toc_class_patterns', TOC_CLASS_PATTERNS)
        self.TOC_LINK_CLASS_PATTERNS = toc_filter_config.get('toc_link_class_patterns', TOC_LINK_CLASS_PATTERNS)
        self.TOC_PARENT_CLASS_PATTERNS = toc_filter_config.get('toc_parent_class_patterns', TOC_PARENT_CLASS_PATTERNS)
        self.CONTENT_AREA_PATTERNS = toc_filter_config.get('content_area_patterns', CONTENT_AREA_PATTERNS)
        self.NON_TOC_LINK_PATTERNS = toc_filter_config.get('non_toc_link_patterns', NON_TOC_LINK_PATTERNS)
        self.TOC_END_MARKERS = toc_filter_config.get('toc_end_markers', [])

        # 使用布隆过滤器去重
        self.bloom_filter = BloomFilter(expected_elements=10000, false_positive_rate=0.001)

        # Markdown转换器
        self.markdown_converter = MarkdownConverter()
        self.link_processor = None  # 延迟初始化，需要URL

        # 统计信息
        self.stats = {
            'content_extracted': 0,
            'toc_extracted': 0,
            'content_failed': 0,
            'toc_failed': 0,
            'content_skipped': 0,
            'toc_no_anchors': 0
        }

        # 线程锁
        self.lock = threading.Lock()

        # 输出目录结构
        self.doc_root_dir = self._build_doc_root_path()

        # 已爬取的URL集合（避免重复）
        self.crawled_urls = set()

    def _load_content_filter(self):
        """
        从 config.content_filter 加载过滤器配置

        Returns:
            ContentFilter 或 EnhancedContentFilter 实例
        """
        try:
            filter_config = FilterConfigLoader.load_from_config({'content_filter': self.config.content_filter})

            if filter_config and (filter_config.get('content_end_markers') or
                                 filter_config.get('documentation_preset')):
                content_filter = EnhancedContentFilter(
                    non_content_selectors=filter_config.get('non_content_selectors'),
                    fuzzy_keywords=filter_config.get('fuzzy_keywords'),
                    log_levels=filter_config.get('log_levels'),
                    meaningless_content=filter_config.get('meaningless_content'),
                    preset=filter_config.get('documentation_preset'),
                    auto_detect_framework=True,
                    merge_mode=filter_config.get('merge_mode', 'extend')
                )
                if filter_config.get('content_end_markers'):
                    content_filter.content_end_markers = filter_config['content_end_markers']
                if filter_config.get('content_preserve_selectors'):
                    content_filter.content_preserve_selectors = filter_config['content_preserve_selectors']
                if filter_config.get('code_container_selectors'):
                    content_filter.code_container_selectors = filter_config['code_container_selectors']

                return content_filter
            else:
                return ContentFilter()
        except Exception as e:
            if self.debug_mode:
                self._debug_print(f"无法加载内容过滤器配置 ({e})，使用标准内容过滤器")
            return ContentFilter()

    def _build_doc_root_path(self) -> str:
        """
        构建文档根目录路径
        格式: doc_dir/<doc_name>@<doc_version>/

        Returns:
            str: 文档根目录的绝对路径
        """
        doc_name = self.config.doc_name
        if not doc_name:
            if self.config.start_url:
                parsed = urlparse(self.config.start_url)
                doc_name = parsed.netloc.replace('.', '_')
            else:
                doc_name = 'documentation'

        dir_name = f"{doc_name}@{self.config.doc_version}"
        full_path = os.path.join(self.config.doc_dir, dir_name)

        # 创建目录
        os.makedirs(full_path, exist_ok=True)

        if self.debug_mode:
            self._debug_print(f"文档根目录: {full_path}")

        return full_path

    def _generate_page_directory_name(self, url: str, page_title: str = "") -> str:
        """
        生成页面目录名

        Args:
            url: 页面URL
            page_title: HTML页面标题

        Returns:
            str: 清理后的目录名
        """
        if page_title:
            dir_name = self.content_filter.sanitize_filename(
                page_title,
                is_directory=True
            )
        else:
            parsed = urlparse(url)
            path = parsed.path.rstrip('/')

            if path:
                path_parts = [p for p in path.split('/') if p and not p.startswith('.')]
                if path_parts:
                    dir_name = path_parts[-1]
                else:
                    dir_name = 'index'
            else:
                dir_name = parsed.netloc.replace('.', '_')

            dir_name = self.content_filter.sanitize_filename(
                dir_name,
                is_directory=True
            )

        return dir_name

    def _is_url_already_crawled(self, url: str) -> bool:
        """检查URL是否已爬取"""
        with self.lock:
            if url in self.crawled_urls:
                return True
            # 不添加到集合中，仅在保存成功后添加
        return False

    def _mark_url_as_crawled(self, url: str):
        """标记URL为已爬取"""
        with self.lock:
            self.crawled_urls.add(url)

    def _sanitize_filename(self, title: str, is_directory: bool = False) -> str:
        """
        清理文件名或目录名

        Args:
            title: 原始标题
            is_directory: 是否为目录名

        Returns:
            str: 清理后的文件名或目录名
        """
        return self.content_filter.sanitize_filename(title, is_directory=is_directory)

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

    def _should_skip_title(self, title: str) -> bool:
        """
        检查页面标题是否匹配过滤规则

        Args:
            title: 页面标题

        Returns:
            bool: 是否应跳过此标题
        """
        if not title:
            return False
        for filter_title in self.config.title_filter_list:
            if title.lower() == filter_title.lower():
                return True
        return False

    def extract_inline(self, result: Dict, response, mode: int):
        """
        主入口：从扫描结果中提取内容和/或TOC

        Args:
            result: 扫描结果字典
            response: HTTP响应对象
            mode: 提取模式 (1=内容, 2=TOC, 3=两者)
        """
        # 检查是否启用内联提取
        if not self.config.enable_inline_extraction:
            return

        # 检查模式
        if mode not in [1, 2, 3]:
            return

        # 检查响应状态
        if not response or response.status_code != 200:
            return

        url = result.get('url', '')
        title = result.get('title', '')

        # === 标题清理 ===
        title = self._clean_title(title)

        # === 标题过滤检查 ===
        if self._should_skip_title(title):
            if self.debug_mode:
                self._debug_print(f"因标题匹配过滤规则跳过提取: {url} (标题: {title})")
            return

        # 检查是否已爬取
        if self._is_url_already_crawled(url):
            if self.debug_mode:
                self._debug_print(f"URL已爬取，跳过: {url}")
            return

        try:
            # 获取HTML内容
            html_content = response.text

            # 初始化 link_processor（需要URL）
            if not self.link_processor:
                self.link_processor = LinkProcessor(url)
            else:
                # 如果URL不同，更新link_processor的base_url
                # 注意：这里简化处理，实际可能需要新的实例
                pass

            # mode 1 或 3: 提取内容
            if mode in [1, 3]:
                self._extract_content_inline(url, title, html_content)

            # mode 2 或 3: 提取TOC
            if mode in [2, 3]:
                self._extract_toc_inline(url, title, html_content)

            # 标记为已爬取
            self._mark_url_as_crawled(url)

        except Exception as e:
            if self.debug_mode:
                self._debug_print(f"内联提取失败: {url}, 错误: {e}")

    def _extract_content_inline(self, url: str, title: str, html_content: str):
        """
        提取文档内容（内联模式）

        Args:
            url: 页面URL
            title: 页面标题
            html_content: HTML内容
        """
        try:
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # 提取页面标题（如果传入的title为空）
            if not title:
                title = self.content_filter.get_page_title(url, soup)

            # 清理标题
            title = self._clean_title(title)

            # 转换相对链接为绝对链接
            link_processor = LinkProcessor(url)
            soup = link_processor.convert_relative_links(soup)

            # 过滤非正文内容
            cleaned_soup = self.content_filter.filter_non_content_blocks(soup)
            cleaned_soup = self.content_filter.filter_logging_outputs(cleaned_soup)

            # 处理 data-src 懒加载图片：将 data-src 复制到 src
            for img in cleaned_soup.find_all('img'):
                data_src = img.get('data-src')
                if data_src and not img.get('src'):
                    img['src'] = data_src

            # 转换为Markdown
            markdown_content = self.markdown_converter.convert_to_markdown(str(cleaned_soup))

            # 过滤内容结束标识
            markdown_content = self.content_filter.filter_content_end_markers(markdown_content)

            # 移除无意义内容
            markdown_content = self.content_filter.remove_meaningless_content(markdown_content)

            # 添加图片URL（在图片下方显示纯URL）
            extract_images = self.config.extract_image_list
            if extract_images is not None:
                markdown_content = self.markdown_converter.add_image_urls(markdown_content, extract_images)

            # 添加元数据头部
            header = f"# {title}\n\n"
            header += f"> **原文链接**: {url}\n\n"
            header += "---\n\n"

            final_content = header + markdown_content

            # 生成文件保存路径
            page_dir_name = self._generate_page_directory_name(url, title)
            page_directory = os.path.join(self.doc_root_dir, page_dir_name)
            content_file = os.path.join(page_directory, 'docContent.md')

            # 保存文件
            os.makedirs(page_directory, exist_ok=True)
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(final_content)

            # 更新统计
            with self.lock:
                self.stats['content_extracted'] += 1

            if self.debug_mode:
                self._debug_print(f"✓ 内容提取成功: {title[:50]}... -> {page_dir_name}/")

        except Exception as e:
            if self.debug_mode:
                self._debug_print(f"内容提取失败: {url}, 错误: {e}")
            with self.lock:
                self.stats['content_failed'] += 1

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
                        return False

            # 5. 检查父元素是否在正文内容区域
            parent = a_tag.parent
            depth = 0
            max_depth = 8

            while parent and depth < max_depth:
                # 检查父元素的 id
                if parent.has_attr('id'):
                    elem_id = parent['id'].lower()
                    if 'content' in elem_id and 'table-of-contents' not in elem_id:
                        return False

                # 检查父元素的 class
                if parent.has_attr('class'):
                    classes = ' '.join(parent['class']).lower()
                    for pattern in self.CONTENT_AREA_PATTERNS:
                        if pattern in classes:
                            return False

                parent = parent.parent
                depth += 1

            # 6. 默认情况下，如果不在白名单中，则认为不是 TOC 链接
            return False

        except Exception as e:
            if self.debug_mode:
                self._debug_print(f"判断TOC时出错: {e}")
            return False

    def _determine_anchor_level(self, anchor_name: str, id_to_element: dict, soup: BeautifulSoup) -> int:
        """
        判断锚点的层级级别

        层级映射：
        - h2 -> level 1 (##) 主要章节
        - h3 -> level 2 (###) 子章节
        - h4 -> level 3 (####) 更小的子章节
        - h5, h6, 其他 -> level 4 (-) 最小级别

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
                    heading = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if heading:
                        tag_name = heading.name

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
            if any(prefix in anchor_name.lower() for prefix in ['chapter', 'section', 'part']):
                return 1
            elif any(prefix in anchor_name.lower() for prefix in ['sub', 'subsection', 'topic']):
                return 2
            elif any(prefix in anchor_name.lower() for prefix in ['item', 'detail', 'note']):
                return 3

            # 默认为第四级
            return 4

        except Exception as e:
            if self.debug_mode:
                self._debug_print(f"判断锚点层级时出错: {e}")
            return 4

    def _extract_anchor_links(self, html_content: str, base_url: str) -> List[Dict[str, any]]:
        """
        仅提取目录（TOC）中的锚点链接，并分析层级结构

        Args:
            html_content: HTML内容
            base_url: 基础URL

        Returns:
            List[Dict]: 锚点链接列表
        """
        anchor_links = []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 构建 id 到元素的映射
            id_to_element = {}
            for elem in soup.find_all(id=True):
                elem_id = elem['id']
                id_to_element[elem_id] = elem
                decoded_id = unquote(elem_id)
                if decoded_id != elem_id:
                    id_to_element[decoded_id] = elem

            # 根据 doc_toc_selector 配置决定搜索范围
            if self.config.doc_toc_selector:
                toc_containers = soup.select(self.config.doc_toc_selector)
                if not toc_containers and self.debug_mode:
                    self._debug_print(f"警告: 未找到匹配 '{self.config.doc_toc_selector}' 的 TOC 容器")

                for container in toc_containers:
                    for a_tag in container.find_all('a', href=True):
                        self._process_anchor_tag(a_tag, base_url, id_to_element, soup, anchor_links)
            else:
                # 回退到白名单/黑名单策略
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    if str(href).startswith('#'):
                        if not self._is_in_toc(a_tag):
                            continue
                        self._process_anchor_tag(a_tag, base_url, id_to_element, soup, anchor_links)

        except Exception as e:
            if self.debug_mode:
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

        if not str(href).startswith('#'):
            return

        anchor_name = str(href)[1:]
        anchor_text = a_tag.get_text(strip=True)
        full_url = f"{base_url}{href}"

        # 使用布隆过滤器去重
        if full_url in self.bloom_filter:
            return

        self.bloom_filter.add(full_url)

        # 尝试解码 URL 编码的锚点名称
        decoded_anchor_name = unquote(anchor_name)

        # 检测锚点的层级级别
        level = self._determine_anchor_level(decoded_anchor_name, id_to_element, soup)
        if level == 4:
            level = self._determine_anchor_level(anchor_name, id_to_element, soup)

        # 解码锚点文本中的 URL 编码字符
        decoded_text = unquote(anchor_text) if anchor_text else anchor_name

        anchor_links.append({
            'name': anchor_name,
            'text': decoded_text,
            'url': full_url,
            'level': level
        })

    def _add_hierarchy_numbers(self, anchor_links: List[Dict]) -> List[Dict]:
        """
        为锚点链接添加层级编号

        Args:
            anchor_links: 锚点链接列表

        Returns:
            List[Dict]: 添加了 hierarchy_number 字段的锚点链接列表
        """
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

            link_with_number = link.copy()
            link_with_number['hierarchy_number'] = hierarchy_number
            result.append(link_with_number)

        return result

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

    def _extract_toc_inline(self, url: str, title: str, html_content: str):
        """
        提取TOC锚点链接（内联模式）

        Args:
            url: 页面URL
            title: 页面标题
            html_content: HTML内容
        """
        try:
            # 解析HTML获取标题（如果传入的title为空）
            if not title:
                soup = BeautifulSoup(html_content, 'html.parser')
                title = self.content_filter.get_page_title(url, soup)

            # 清理标题
            title = self._clean_title(title)

            # 提取锚点链接
            anchor_links = self._extract_anchor_links(html_content, url)

            if not anchor_links:
                with self.lock:
                    self.stats['toc_no_anchors'] += 1
                if self.debug_mode:
                    self._debug_print(f"未找到锚点链接: {url}")
                return

            # 应用 TOC 结束标识过滤
            filtered_anchor_links = self._filter_toc_end_markers(anchor_links)

            # 添加层级编号
            anchor_links_with_numbers = self._add_hierarchy_numbers(filtered_anchor_links)

            # 生成目录结构
            page_dir_name = self._generate_page_directory_name(url, title)
            page_directory = os.path.join(self.doc_root_dir, page_dir_name)
            toc_file = os.path.join(page_directory, 'docTOC.md')

            # 确保目录存在
            os.makedirs(page_directory, exist_ok=True)

            # 生成内容
            content = f"# {title}\n\n"
            content += f"原文链接: {url}\n\n"
            content += f"提取的锚点数量: {len(filtered_anchor_links)}\n\n"

            # 按照层级格式输出
            for link in anchor_links_with_numbers:
                level = link.get('level', 4)
                link_url = link.get('url', '')
                hierarchy_number = link.get('hierarchy_number', '')
                display_name = link.get('text', link.get('name', ''))

                if level == 1:
                    content += f"## {hierarchy_number}. {display_name}：{link_url}\n\n"
                elif level == 2:
                    content += f"### {hierarchy_number}. {display_name}：{link_url}\n\n"
                elif level == 3:
                    content += f"#### {hierarchy_number}. {display_name}：{link_url}\n\n"
                else:  # level == 4
                    content += f"- {hierarchy_number}. {display_name}：{link_url}\n"

            # 保存文件
            with open(toc_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # 更新统计
            with self.lock:
                self.stats['toc_extracted'] += 1

            if self.debug_mode:
                self._debug_print(f"✓ TOC提取成功: {title[:40]}... ({len(filtered_anchor_links)} anchors)")

        except Exception as e:
            if self.debug_mode:
                self._debug_print(f"TOC提取失败: {url}, 错误: {e}")
            with self.lock:
                self.stats['toc_failed'] += 1

    def print_statistics(self):
        """打印统计信息"""
        if not COLOR_SUPPORT:
            print(f"\n{'='*60}")
            print(f"内联提取完成统计")
            print(f"{'='*60}")
            print(f"内容提取成功: {self.stats['content_extracted']}")
            print(f"内容提取失败: {self.stats['content_failed']}")
            print(f"TOC提取成功: {self.stats['toc_extracted']}")
            print(f"TOC提取失败: {self.stats['toc_failed']}")
            print(f"无锚点页面: {self.stats['toc_no_anchors']}")
            print(f"输出目录: {self.doc_root_dir}")
            print(f"{'='*60}\n")
        else:
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}内联提取完成统计{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}内容提取成功: {self.stats['content_extracted']}{Style.RESET_ALL}")
            print(f"{Fore.RED}内容提取失败: {self.stats['content_failed']}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}TOC提取成功: {self.stats['toc_extracted']}{Style.RESET_ALL}")
            print(f"{Fore.RED}TOC提取失败: {self.stats['toc_failed']}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}无锚点页面: {self.stats['toc_no_anchors']}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}输出目录: {self.doc_root_dir}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
