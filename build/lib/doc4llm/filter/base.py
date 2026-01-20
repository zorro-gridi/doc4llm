"""
内容过滤器抽象基类
Content Filter Abstract Base Class

定义内容过滤器的统一接口，确保不同实现之间的兼容性
"""

from abc import ABC, abstractmethod
from typing import Optional, Union, List, Dict, Any, Callable
from bs4 import BeautifulSoup
import re


class BaseContentFilter(ABC):
    """
    内容过滤器抽象基类
    所有内容过滤器实现都应该继承这个类
    """

    def __init__(self):
        self.removed_count = 0
        self.removed_log_count = 0

    @abstractmethod
    def get_page_title(self, url: str, soup: BeautifulSoup) -> str:
        """
        从网页中获取标题

        Args:
            url: 网页URL
            soup: BeautifulSoup对象

        Returns:
            str: 页面标题
        """
        pass

    @abstractmethod
    def filter_non_content_blocks(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        过滤非正文内容（侧边栏、导航等）

        Args:
            soup: BeautifulSoup对象

        Returns:
            BeautifulSoup: 清理后的对象
        """
        pass

    @abstractmethod
    def filter_logging_outputs(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        过滤代码块中的日志输出

        Args:
            soup: BeautifulSoup对象

        Returns:
            BeautifulSoup: 清理后的对象
        """
        pass

    @abstractmethod
    def remove_meaningless_content(self, content: str) -> str:
        """
        删除没有意义的文本

        Args:
            content: 原始文本内容

        Returns:
            str: 清理后的文本内容
        """
        pass

    @abstractmethod
    def sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符

        Args:
            filename: 原始文件名

        Returns:
            str: 清理后的文件名
        """
        pass

    # 可选方法的默认实现
    def filter_content_end_markers(self, markdown_content: str) -> str:
        """
        过滤 Markdown 中的结束标识（如 "Next steps"）
        默认实现：使用配置的 content_end_markers 进行过滤

        Args:
            markdown_content: Markdown 内容

        Returns:
            str: 清理后的 Markdown 内容
        """
        # 使用统一工具函数 - markers 应该由子类设置
        markers = getattr(self, 'content_end_markers', [])
        return filter_by_end_markers(markdown_content, markers, debug_mode=False)

    def pre_process_html(self, soup: BeautifulSoup, url: str) -> BeautifulSoup:
        """
        HTML 预处理（可选）
        默认实现：不做处理，子类可以覆盖

        Args:
            soup: BeautifulSoup对象
            url: 页面URL

        Returns:
            BeautifulSoup: 预处理后的对象
        """
        return soup

    def post_process_markdown(self, markdown_content: str) -> str:
        """
        Markdown 后处理（可选）
        默认实现：不做处理，子类可以覆盖

        Args:
            markdown_content: Markdown 内容

        Returns:
            str: 后处理后的 Markdown 内容
        """
        return markdown_content

    # 便捷的完整处理流程
    def process_full(self, soup: BeautifulSoup, markdown_content: str, url: str = "") -> tuple:
        """
        完整的处理流程

        Args:
            soup: BeautifulSoup对象
            markdown_content: 转换后的 Markdown 内容
            url: 页面URL（可选）

        Returns:
            tuple: (清理后的soup, 清理后的markdown)
        """
        # HTML 预处理
        soup = self.pre_process_html(soup, url)

        # 过滤非正文内容
        soup = self.filter_non_content_blocks(soup)

        # 过滤日志输出
        soup = self.filter_logging_outputs(soup)

        # Markdown 后处理
        markdown_content = self.filter_content_end_markers(markdown_content)
        markdown_content = self.remove_meaningless_content(markdown_content)
        markdown_content = self.post_process_markdown(markdown_content)

        return soup, markdown_content


# ============================================================================
# Unified Content Post-Processing Template
# ============================================================================

def _compile_flexible_pattern(text: str, is_markdown: bool = False) -> str:
    """
    将用户输入的纯文本转换为灵活的正则表达式模式

    Args:
        text: 用户输入的纯文本
        is_markdown: 是否为 Markdown 内容（Markdown 可能包含标题前缀）

    Returns:
        str: 编译后的正则表达式模式字符串

    Examples:
        >>> _compile_flexible_pattern("Next steps", is_markdown=True)
        '^(##+\\s*)?\\s*Next\\s+steps\\s*$'

        >>> _compile_flexible_pattern("See also", is_markdown=False)
        '^\\s*See\\s+also\\s*$'
    """
    # 将用户输入的空格替换为 \s+ 模式（使用占位符避免后续被转义）
    # 例如 "Next steps" -> "Next\\x00SPACE\\x00steps"
    placeholder = '\x00SPACE\x00'
    text_with_placeholder = re.sub(r'\s+', placeholder, text)

    # 转义所有特殊字符（此时占位符中的特殊字符也会被转义）
    escaped = re.escape(text_with_placeholder)

    # 将转义后的占位符替换为真正的 \s+
    pattern = escaped.replace(re.escape(placeholder), r'\s+')

    # 添加开始锚点和可选的前缀空白
    # 对于 Markdown，允许可选的标题前缀（##, ###, 等）
    if is_markdown:
        # Markdown: 允许标题前缀（##, ###, 等）+ 可选的数字编号
        prefix = r'^(##+\s*)?(?:\d+\.\s*)?'  # 可选的 Markdown 标题前缀和数字编号
    else:
        # 非 Markdown: 只允许行首空白
        prefix = r'^\s*'

    # 不使用行尾锚点，允许标记后有任意内容（如 URL、标点等）
    return f'{prefix}{pattern}'


def filter_by_end_markers(
    content: Union[str, List[Dict[str, Any]]],
    markers: List[str],
    text_extractor: Optional[Callable] = None,
    debug_mode: bool = False
) -> Union[str, List[Dict[str, Any]]]:
    """
    统一的内容后处理模板

    使用正则表达式匹配结束标识，移除从标识行开始的所有后续内容。
    支持字符串（Markdown内容）和列表（TOC锚点链接）两种数据类型。

    自动将用户输入的纯文本转换为灵活的正则表达式：
    - 转义特殊字符
    - 允许变长的空白字符（"Next steps" 可匹配 "Next  steps"）
    - 对于 Markdown 内容，支持可选的标题前缀（##, ###, 等）
    - 区分大小写（精确匹配）

    Args:
        content: 内容，可以是字符串（markdown）或字典列表（TOC锚点链接）
        markers: 结束标识列表（用户输入的纯文本，会自动转换为正则表达式）
        text_extractor: 对于列表类型，用于从每个项目中提取文本的回调函数
        debug_mode: 是否输出调试信息

    Returns:
        与输入类型相同：过滤后的字符串或列表

    Examples:
        >>> # 字符串用法（markdown内容）
        >>> markdown = "# Title\\n\\nContent\\n\\n## Next steps\\n\\nMore content"
        >>> filtered = filter_by_end_markers(markdown, ['Next steps'])
        >>> print(filtered)
        "# Title\\n\\nContent"

        >>> # 列表用法（TOC锚点链接）
        >>> anchors = [
        ...     {'text': 'Introduction', 'url': '#intro'},
        ...     {'text': 'See also', 'url': '#seealso'},
        ...     {'text': 'Related', 'url': '#related'}
        ... ]
        >>> filtered = filter_by_end_markers(
        ...     anchors,
        ...     ['See also', 'Related'],
        ...     text_extractor=lambda item: item.get('text', '')
        ... )
        >>> print(len(filtered))
        1
    """
    # 如果没有提供标识，直接返回原内容
    if not markers:
        return content

    # 处理字符串输入（markdown内容）
    if isinstance(content, str):
        lines = content.split('\n')
        result_lines = []

        # 将用户输入的文本转换为 Markdown 正则表达式模式
        compiled_patterns = [_compile_flexible_pattern(m, is_markdown=True) for m in markers]

        for line in lines:
            should_stop = False
            for pattern in compiled_patterns:
                if re.search(pattern, line):
                    if debug_mode:
                        print(f"[ContentPostProcess] 检测到结束标识: {line.strip()}")
                    should_stop = True
                    break

            if should_stop:
                break

            result_lines.append(line)

        return '\n'.join(result_lines)

    # 处理列表输入（TOC锚点链接）
    elif isinstance(content, list):
        if not text_extractor:
            raise ValueError("当content为列表类型时，必须提供text_extractor参数")

        # 将用户输入的文本转换为普通正则表达式模式
        compiled_patterns = [_compile_flexible_pattern(m, is_markdown=False) for m in markers]

        result_items = []

        for item in content:
            text = text_extractor(item)
            should_stop = False

            for pattern in compiled_patterns:
                if re.search(pattern, str(text)):
                    if debug_mode:
                        print(f"[ContentPostProcess] 检测到TOC结束标识: {text}")
                    should_stop = True
                    break

            if should_stop:
                break

            result_items.append(item)

        if debug_mode and len(result_items) < len(content):
            print(f"[ContentPostProcess] TOC过滤: {len(content)} -> {len(result_items)} 项")

        return result_items

    else:
        raise TypeError(f"不支持的内容类型: {type(content)}")
