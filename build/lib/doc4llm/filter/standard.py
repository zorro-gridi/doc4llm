"""
标准内容过滤器模块
Standard Content Filter Module

提供基础的网页内容过滤功能，适用于大多数传统网站结构。
使用 extend 模式合并自定义配置，保留默认选择器。

Author: doc4llm Team
"""

import os
import re
from urllib.parse import urlparse
from typing import List, Optional

from bs4 import BeautifulSoup
from .base import BaseContentFilter
from .config import (
    SEMANTIC_NON_CONTENT_SELECTORS,
    GENERAL_NON_CONTENT_SELECTORS,
    FUZZY_KEYWORDS as DEFAULT_FUZZY_KEYWORDS,
    LOG_LEVELS as DEFAULT_LOG_LEVELS,
    MEANINGLESS_CONTENT as DEFAULT_MEANINGLESS_CONTENT,
    CODE_CONTAINER_SELECTORS,
    CONTENT_END_MARKERS,
    merge_selectors,
)


class ContentFilter(BaseContentFilter):
    """
    内容过滤器类，负责清理网页中的非正文内容

    使用 extend 模式：自定义选择器会追加到默认选择器之后，
    而不是完全替换默认选择器。

    Examples:
        >>> # 使用默认配置
        >>> filter_obj = ContentFilter()
        >>>
        >>> # 添加自定义选择器（extend 模式）
        >>> filter_obj = ContentFilter(
        ...     NON_CONTENT_SELECTORS=['.custom-sidebar']
        ... )
        >>> # 最终选择器 = 默认选择器 + ['.custom-sidebar']
    """

    def __init__(
        self,
        NON_CONTENT_SELECTORS: Optional[List[str]] = None,
        FUZZY_KEYWORDS: Optional[List[str]] = None,
        LOG_LEVELS: Optional[List[str]] = None,
        MEANINGLESS_CONTENT: Optional[List[str]] = None
    ):
        """
        初始化内容过滤器

        Args:
            NON_CONTENT_SELECTORS: 自定义非正文选择器（会扩展默认选择器）
            FUZZY_KEYWORDS: 自定义模糊匹配关键词（会扩展默认关键词）
            LOG_LEVELS: 自定义日志级别标识（会扩展默认级别）
            MEANINGLESS_CONTENT: 自定义无意义内容（会扩展默认内容）

        Note:
            所有参数使用 extend 模式，即自定义内容会追加到默认列表中。
            如需完全替换，请使用 EnhancedContentFilter 并设置 merge_mode='replace'。
        """
        self.removed_count = 0
        self.removed_log_count = 0

        # 使用 extend 模式合并选择器：默认 + 自定义
        self.NON_CONTENT_SELECTORS = merge_selectors(
            SEMANTIC_NON_CONTENT_SELECTORS + GENERAL_NON_CONTENT_SELECTORS,
            NON_CONTENT_SELECTORS,
            mode='extend'
        )

        self.FUZZY_KEYWORDS = merge_selectors(
            DEFAULT_FUZZY_KEYWORDS,
            FUZZY_KEYWORDS,
            mode='extend'
        )

        self.LOG_LEVELS = merge_selectors(
            DEFAULT_LOG_LEVELS,
            LOG_LEVELS,
            mode='extend'
        )

        self.MEANINGLESS_CONTENT = merge_selectors(
            DEFAULT_MEANINGLESS_CONTENT,
            MEANINGLESS_CONTENT,
            mode='extend'
        )

        self.CODE_CONTAINER_SELECTORS = CODE_CONTAINER_SELECTORS

        # 内容结束标识（extend 模式）
        self.content_end_markers = merge_selectors(
            CONTENT_END_MARKERS,
            None,  # 标准模式不支持自定义
            mode='extend'
        )

    def sanitize_filename(self, filename: str, is_directory: bool = False) -> str:
        """
        清理文件名或目录名，移除非法字符

        Args:
            filename: 原始文件名或目录名
            is_directory: 是否为目录名（目录名有更严格的规则和更长的长度限制）

        Returns:
            str: 清理后的文件名或目录名
        """
        import unicodedata

        # 移除非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, '', filename)

        # Unicode 标准化 (NFKC 分解)
        filename = unicodedata.normalize('NFKC', filename)

        # 替换多个空格为单个空格
        filename = re.sub(r'\s+', ' ', filename)

        # 移除前导和尾随的点和空格
        filename = filename.strip('. ')

        # 纯数字目录名处理（Windows 兼容性）
        if is_directory and filename.isdigit():
            filename = f'dir_{filename}'

        # 限制长度（目录可以比文件更长）
        max_length = 200 if is_directory else 100
        if len(filename) > max_length:
            filename = filename[:max_length].strip()

        # 空名称的回退处理
        if not filename:
            filename = 'untitled'

        return filename

    def get_page_title(self, url: str, soup: BeautifulSoup) -> str:
        """
        从网页中获取标题

        Args:
            url: 网页URL
            soup: BeautifulSoup对象

        Returns:
            str: 页面标题
        """
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        h1_tag = soup.find('h1')
        if h1_tag and h1_tag.get_text():
            return h1_tag.get_text().strip()

        parsed_url = urlparse(url)
        path = parsed_url.path
        if path and path != '/':
            return os.path.basename(path) or parsed_url.netloc

        return parsed_url.netloc

    def filter_non_content_blocks(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        过滤高可能性的非正文内容

        Args:
            soup: BeautifulSoup对象

        Returns:
            BeautifulSoup: 清理后的BeautifulSoup对象
        """
        self.removed_count = 0

        # 移除精确匹配的元素
        for selector in self.NON_CONTENT_SELECTORS:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    try:
                        elem.decompose()
                        self.removed_count += 1
                    except Exception:
                        continue
            except Exception as e:
                print(f"处理选择器 {selector} 时出现警告: {e}")
                continue

        # 模糊匹配：class或id包含特定关键词的元素
        for keyword in self.FUZZY_KEYWORDS:
            try:
                # 匹配class包含关键词的元素
                class_elements = soup.find_all(
                    class_=re.compile(keyword, re.IGNORECASE)
                )
                # 匹配id包含关键词的元素
                id_elements = soup.find_all(
                    id=re.compile(keyword, re.IGNORECASE)
                )

                all_elements = set(class_elements + id_elements)

                for elem in all_elements:
                    if elem.find_parent() is not None:
                        try:
                            elem_classes = ' '.join(elem.get('class', [])).lower()
                            elem_id = (elem.get('id') or '').lower()
                            elem_role = (elem.get('role') or '').lower()

                            if (keyword in elem_classes or
                                keyword in elem_id or
                                keyword in elem_role or
                                elem.name in ['aside', 'nav', 'footer']):
                                elem.decompose()
                                self.removed_count += 1
                        except Exception:
                            continue
            except Exception as e:
                print(f"处理模糊关键词 {keyword} 时出现警告: {e}")
                continue

        print(f"移除了 {self.removed_count} 个非正文区块")
        return soup

    def filter_logging_outputs(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        过滤代码块中的Python logging输出

        Args:
            soup: BeautifulSoup对象

        Returns:
            BeautifulSoup: 清理后的BeautifulSoup对象
        """
        self.removed_log_count = 0

        # 日志模式匹配
        log_patterns = [
            re.compile(r'\s*(' + '|'.join(self.LOG_LEVELS) + r')\w+:\s*.+',
                      re.MULTILINE),
            re.compile(r'(' + '|'.join(self.LOG_LEVELS) + r')', re.MULTILINE)
        ]

        # 检查代码块容器
        for selector in self.CODE_CONTAINER_SELECTORS:
            try:
                for container in soup.select(selector):
                    if not container.parent:
                        continue

                    container_text = container.get_text()
                    lower_text = container_text.lower()

                    has_log_level = any(
                        level.lower() in lower_text for level in self.LOG_LEVELS
                    )
                    matches_pattern = any(
                        pattern.search(container_text) for pattern in log_patterns
                    )

                    if has_log_level and matches_pattern:
                        container.decompose()
                        self.removed_log_count += 1
            except Exception as e:
                print(f"处理代码容器 {selector} 时警告: {e}")
                continue

        # 检查其他可能的日志容器
        for element in soup.find_all(string=True):
            parent = element.parent
            if not parent or parent.name in ['code', 'pre']:
                continue

            element_text = parent.get_text()
            lower_text = element_text.lower()

            has_log_level = any(
                level.lower() in lower_text for level in self.LOG_LEVELS
            )
            matches_pattern = any(
                pattern.search(element_text) for pattern in log_patterns
            )

            elem_classes = ' '.join(parent.get('class', [])).lower()
            elem_id = (parent.get('id') or '').lower()
            is_log_container = any(
                kw in elem_classes or kw in elem_id
                for kw in ['log', 'logging', 'debug', 'output']
            )

            if has_log_level and matches_pattern and is_log_container:
                parent.decompose()
                self.removed_log_count += 1

        print(f"移除了 {self.removed_log_count} 个可能的日志输出区块")
        return soup

    def remove_meaningless_content(self, content: str) -> str:
        """
        删除没有意义的文本

        Args:
            content: 原始文本内容

        Returns:
            str: 清理后的文本内容
        """
        for text in self.MEANINGLESS_CONTENT:
            content = content.replace(text, '')
        return content

    def filter_content_end_markers(self, markdown_content: str) -> str:
        """
        使用配置的内容结束标识过滤 markdown 内容

        Args:
            markdown_content: Markdown 内容

        Returns:
            str: 过滤后的 Markdown 内容
        """
        from .base import filter_by_end_markers
        return filter_by_end_markers(
            markdown_content,
            self.content_end_markers,
            debug_mode=False
        )
