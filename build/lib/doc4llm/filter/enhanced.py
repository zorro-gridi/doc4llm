"""
增强版内容过滤器 - 支持现代文档站点和智能正文识别
Enhanced Content Filter - Supports modern documentation sites and smart content detection

Author: Claude Code
Date: 2025-01-16
"""

import os
import re
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse
from .base import BaseContentFilter
from .config import (
    SEMANTIC_NON_CONTENT_SELECTORS,
    GENERAL_NON_CONTENT_SELECTORS,
    FUZZY_KEYWORDS as DEFAULT_FUZZY_KEYWORDS,
    LOG_LEVELS as DEFAULT_LOG_LEVELS,
    MEANINGLESS_CONTENT as DEFAULT_MEANINGLESS_CONTENT,
    CODE_CONTAINER_SELECTORS,
    CONTENT_PRESERVE_SELECTORS,
    CONTENT_END_MARKERS,
    DOCUMENTATION_FRAMEWORK_PRESETS,
    merge_selectors,
    get_filter_config,
)


class EnhancedContentFilter(BaseContentFilter):
    """
    增强版内容过滤器，支持智能正文识别和现代文档站点的特殊结构

    支持 extend 和 replace 两种合并模式：
    - extend: 保留默认选择器并追加自定义选择器（默认）
    - replace: 完全使用自定义选择器

    Examples:
        >>> # 使用默认配置
        >>> filter_obj = EnhancedContentFilter()
        >>>
        >>> # 使用 Mintlify 预设
        >>> filter_obj = EnhancedContentFilter(preset='mintlify')
        >>>
        >>> # 使用 replace 模式
        >>> filter_obj = EnhancedContentFilter(
        ...     non_content_selectors=['.custom-nav'],
        ...     merge_mode='replace'
        ... )
    """

    def __init__(
        self,
        non_content_selectors: Optional[List[str]] = None,
        fuzzy_keywords: Optional[List[str]] = None,
        log_levels: Optional[List[str]] = None,
        meaningless_content: Optional[List[str]] = None,
        preset: Optional[str] = None,
        auto_detect_framework: bool = True,
        merge_mode: str = 'extend'
    ):
        """
        初始化增强版内容过滤器

        Args:
            non_content_selectors: 自定义非正文选择器
            fuzzy_keywords: 自定义模糊匹配关键词
            log_levels: 自定义日志级别
            meaningless_content: 自定义无意义内容
            preset: 文档框架预设 ('mintlify', 'docusaurus', 'vitepress', 'gitbook')
            auto_detect_framework: 是否自动检测文档框架
            merge_mode: 合并模式 ('extend' 或 'replace')
        """
        self.removed_count = 0
        self.removed_log_count = 0
        self.detected_framework = None
        self.merge_mode = merge_mode
        self.preset = preset
        self.auto_detect_framework = auto_detect_framework

        # 获取配置（自动应用预设和合并模式）
        config = get_filter_config(
            preset=preset,
            custom_non_content_selectors=non_content_selectors,
            custom_fuzzy_keywords=fuzzy_keywords,
            custom_log_levels=log_levels,
            custom_meaningless_content=meaningless_content,
            merge_mode=merge_mode
        )

        self.non_content_selectors = config['non_content_selectors']
        self.fuzzy_keywords = config['fuzzy_keywords']
        self.log_levels = config['log_levels']
        self.meaningless_content = config['meaningless_content']
        self.content_end_markers = config['content_end_markers']
        self.content_preserve_selectors = config['content_preserve_selectors']
        self.code_container_selectors = config['code_container_selectors']

    def detect_framework(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """
        检测当前页面使用的文档框架

        Args:
            soup: BeautifulSoup 对象
            url: 页面 URL

        Returns:
            检测到的框架名称或 None
        """
        # 检查 Mintlify
        if (soup.select('[class*="mintlify"]') or
            'mintlify' in str(soup).lower() or
            'mintlify' in url.lower()):
            return 'mintlify'

        # 检查 Docusaurus
        if (soup.select('[class*="docMainContainer"]') or
            soup.select('[class*="docusaurus"]') or
            'docusaurus' in str(soup).lower()):
            return 'docusaurus'

        # 检查 VitePress
        if (soup.select('.VPDoc') or
            soup.select('[class*="VitePress"]') or
            'vitepress' in str(soup).lower()):
            return 'vitepress'

        # 检查 GitBook
        if (soup.select('.gitbook-content') or
            'gitbook' in str(soup).lower()):
            return 'gitbook'

        return None

    def sanitize_filename(self, filename: str, is_directory: bool = False) -> str:
        """
        清理文件名或目录名

        Args:
            filename: 原始文件名或目录名
            is_directory: 是否为目录名（目录名有更长的长度限制）

        Returns:
            str: 清理后的文件名或目录名
        """
        import unicodedata

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
        """获取页面标题"""
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

    def find_main_content_area(self, soup: BeautifulSoup) -> Optional[Tag]:
        """
        使用启发式算法找到主要内容区域

        Args:
            soup: BeautifulSoup 对象

        Returns:
            主要内容区域的 Tag 对象
        """
        # 1. 优先查找语义化标签
        for selector in ['article', 'main']:
            main = soup.find(selector)
            if main:
                return main

        # 2. 查找带有 role="main" 的元素
        main = soup.find(attrs={'role': 'main'})
        if main:
            return main

        # 3. 使用启发式评分
        candidates = []
        for tag in soup.find_all(['div', 'section', 'article']):
            score = self._score_content_tag(tag)
            if score > 0:
                candidates.append((tag, score))

        if candidates:
            # 返回得分最高的元素
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        # 4. 如果都没找到，返回 body
        return soup.find('body')

    def _score_content_tag(self, tag: Tag) -> int:
        """
        为标签计算内容可能性得分

        Args:
            tag: BeautifulSoup Tag 对象

        Returns:
            得分（越高越可能是正文）
        """
        score = 0
        tag_str = str(tag).lower()

        # 类名和ID中的正面指标
        class_list = tag.get('class')
        classes = ' '.join(class_list if class_list else []).lower()
        tag_id = (tag.get('id') or '')
        if isinstance(tag_id, str):
            tag_id = tag_id.lower()

        # 包含 content、article、post 等关键词
        positive_keywords = ['content', 'article', 'post', 'main', 'body',
                            'markdown', 'prose', 'mdx', 'text']
        for keyword in positive_keywords:
            if keyword in classes or keyword in tag_id:
                score += 10

        # 包含 sidebar、nav 等负面关键词
        negative_keywords = ['sidebar', 'nav', 'menu', 'footer', 'header',
                            'ad', 'banner', 'toc', 'pagination']
        for keyword in negative_keywords:
            if keyword in classes or keyword in tag_id:
                score -= 20

        # 检查文本长度（正文通常较长）
        text_length = len(tag.get_text(strip=True))
        if text_length > 500:
            score += 5
        elif text_length < 100:
            score -= 10

        # 检查段落数量
        p_count = len(tag.find_all('p'))
        if p_count > 3:
            score += 3

        # 检查标题层级（正文通常有标题）
        has_h1 = tag.find('h1')
        has_h2 = tag.find('h2')
        if has_h1:
            score += 5
        if has_h2:
            score += 2

        # 检查代码块（技术文档通常有代码）
        code_count = len(tag.find_all(['pre', 'code']))
        if code_count > 0:
            score += code_count

        return max(score, 0)

    def _is_protected_element(self, elem: Tag) -> bool:
        """
        检查元素是否匹配 content_preserve_selectors（应该被保护）

        Args:
            elem: BeautifulSoup Tag 对象

        Returns:
            True 如果元素应该被保护，False 否则
        """
        if not self.content_preserve_selectors:
            return False

        # 检查元素本身是否匹配保护选择器
        for selector in self.content_preserve_selectors:
            try:
                # 检查元素的标签名
                if selector.lower() == elem.name.lower():
                    return True
                # 检查 CSS 选择器匹配
                if elem.select_one(selector):
                    return True
            except Exception:
                continue

        # 检查父元素是否匹配保护选择器（级联保护）
        parent = elem.find_parent()
        while parent:
            for selector in self.content_preserve_selectors:
                try:
                    if selector.lower() == parent.name.lower():
                        return True
                    if parent.select_one(selector):
                        return True
                except Exception:
                    continue
            parent = parent.find_parent()

        return False

    def filter_non_content_blocks(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        过滤非正文内容（增强版）

        Args:
            soup: BeautifulSoup 对象

        Returns:
            清理后的 BeautifulSoup 对象
        """
        self.removed_count = 0

        # 自动检测文档框架
        if self.auto_detect_framework:
            self.detected_framework = self.detect_framework(soup, '')
            if self.detected_framework:
                print(f"检测到文档框架: {self.detected_framework}")
                # 应用框架特定的排除选择器
                framework_config = DOCUMENTATION_FRAMEWORK_PRESETS.get(self.detected_framework, {})
                self.non_content_selectors.extend(framework_config.get('exclude_selectors', []))

        # 尝试找到主要内容区域
        main_content = self.find_main_content_area(soup)
        if main_content and main_content.name != 'body':
            print(f"找到主要内容区域: <{main_content.name}>")
            # 将主要内容区域转换为新的 soup
            soup = BeautifulSoup(str(main_content), 'html.parser')

        # 移除精确匹配的元素
        for selector in self.non_content_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    try:
                        # 检查元素是否被保护
                        if self._is_protected_element(elem):
                            print(f"保护元素: <{elem.name} class=\"{' '.join(elem.get('class', []))}\">")
                            continue
                        elem.decompose()
                        self.removed_count += 1
                    except Exception:
                        continue
            except Exception as e:
                print(f"处理选择器 {selector} 时出现警告: {e}")
                continue

        # 模糊匹配
        for keyword in self.fuzzy_keywords:
            try:
                class_elements = soup.find_all(
                    class_=re.compile(keyword, re.IGNORECASE)
                )
                id_elements = soup.find_all(
                    id=re.compile(keyword, re.IGNORECASE)
                )

                all_elements = set(class_elements + id_elements)

                for elem in all_elements:
                    if elem.find_parent() is not None:
                        try:
                            elem_class_list = elem.get('class')
                            elem_classes = ' '.join(elem_class_list if elem_class_list else []).lower()
                            elem_id = elem.get('id') or ''
                            elem_id = elem_id.lower() if isinstance(elem_id, str) else ''
                            elem_role = elem.get('role') or ''
                            elem_role = elem_role.lower() if isinstance(elem_role, str) else ''

                            if (keyword in elem_classes or
                                keyword in elem_id or
                                keyword in elem_role or
                                elem.name in ['aside', 'nav', 'footer']):
                                # 检查元素是否被保护
                                if self._is_protected_element(elem):
                                    print(f"保护元素: <{elem.name} class=\"{' '.join(elem.get('class', []))}\">")
                                    continue
                                elem.decompose()
                                self.removed_count += 1
                        except Exception:
                            continue
            except Exception as e:
                print(f"处理模糊关键词 {keyword} 时出现警告: {e}")
                continue

        print(f"移除了 {self.removed_count} 个非正文区块")
        return soup

    def filter_content_end_markers(self, markdown_content: str) -> str:
        """
        使用统一后处理模板过滤 Markdown 内容中的结束标识

        Args:
            markdown_content: Markdown 内容

        Returns:
            str: 清理后的 Markdown 内容
        """
        from .base import filter_by_end_markers
        return filter_by_end_markers(
            markdown_content,
            self.content_end_markers,
            debug_mode=True  # 增强模式输出调试信息
        )

    def filter_logging_outputs(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        过滤代码块中的日志输出

        Args:
            soup: BeautifulSoup 对象

        Returns:
            清理后的 BeautifulSoup 对象
        """
        self.removed_log_count = 0

        log_patterns = [
            re.compile(r'\s*(' + '|'.join(self.log_levels) + r')\w+:\s*.+', re.MULTILINE),
            re.compile(r'(' + '|'.join(self.log_levels) + r')', re.MULTILINE)
        ]

        for selector in self.code_container_selectors:
            try:
                for container in soup.select(selector):
                    if not container.parent:
                        continue

                    container_text = container.get_text()
                    lower_text = container_text.lower()

                    has_log_level = any(
                        level.lower() in lower_text for level in self.log_levels
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

        print(f"移除了 {self.removed_log_count} 个可能的日志输出区块")
        return soup

    def remove_meaningless_content(self, content: str) -> str:
        """
        删除没有意义的文本

        Args:
            content: 原始文本内容

        Returns:
            清理后的文本内容
        """
        for text in self.meaningless_content:
            content = re.sub(re.escape(text), '', content, flags=re.IGNORECASE)
        return content

    def process(self, soup: BeautifulSoup, markdown_content: str) -> Tuple[BeautifulSoup, str]:
        """
        完整的处理流程

        Args:
            soup: BeautifulSoup 对象
            markdown_content: 转换后的 Markdown 内容

        Returns:
            (清理后的 soup, 清理后的 markdown)
        """
        # 1. 过滤非正文区块
        cleaned_soup = self.filter_non_content_blocks(soup)

        # 2. 过滤日志输出
        cleaned_soup = self.filter_logging_outputs(cleaned_soup)

        # 3. 过滤内容结束标识（在 Markdown 层面）
        cleaned_markdown = self.filter_content_end_markers(markdown_content)

        # 4. 移除无意义内容
        cleaned_markdown = self.remove_meaningless_content(cleaned_markdown)

        return cleaned_soup, cleaned_markdown


# 便捷函数
def create_filter(preset: Optional[str] = None, **kwargs) -> EnhancedContentFilter:
    """
    创建增强版内容过滤器的便捷函数

    Args:
        preset: 文档框架预设 ('mintlify', 'docusaurus', 'vitepress', 'gitbook')
        **kwargs: 其他配置参数

    Returns:
        EnhancedContentFilter 实例
    """
    return EnhancedContentFilter(preset=preset, **kwargs)
