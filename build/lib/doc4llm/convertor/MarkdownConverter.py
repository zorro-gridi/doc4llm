
"""
Markdown 格式转换器
将 HTML 内容转换为 Markdown 格式
"""

import re
import html2text


class MarkdownConverter:
    """Markdown格式转换器类"""

    def __init__(self):
        """初始化Markdown转换器"""
        self.converter = self._setup_html2text()

    def _setup_html2text(self) -> html2text.HTML2Text:
        """
        配置html2text转换器

        Returns:
            html2text.HTML2Text: 配置好的转换器实例
        """
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0
        h.unicode_snob = True
        h.ignore_emphasis = False
        return h

    def _clean_markdown(self, markdown: str) -> str:
        """
        清理 Markdown 格式问题

        修复 html2text 转换后的问题：
        1. 零宽空格和其他不可见 Unicode 字符
        2. 标题符号和文字之间的多余空格（多个空格变成一个）
        3. 标题符号和文字之间的多余换行符
        4. 连续的空行

        Args:
            markdown: 原始 Markdown 内容

        Returns:
            str: 清理后的 Markdown 内容
        """
        # 第零步：清理零宽空格和其他不可见字符
        # 这些字符来自 HTML 中的隐藏元素（如锚点链接）
        invisible_chars = [
            '\u200b',  # Zero Width Space
            '\u200c',  # Zero Width Non-Joiner
            '\u200d',  # Zero Width Joiner
            '\u2060',  # Word Joiner
            '\u00ad',  # Soft Hyphen
            '\ufeff',  # Zero Width No-Break Space
        ]
        for char in invisible_chars:
            markdown = markdown.replace(char, '')

        # 第一步：修复标题符号和文字之间的多余换行符
        # 匹配模式：## 后面跟着空格、换行符和更多空白
        # 示例：
        #   ## \n\n\nCreate your first Skill  -> ## Create your first Skill
        #   ##\n\n  Next steps              -> ## Next steps
        markdown = re.sub(
            r'^(#{1,6})\s*[\s\n]*?\n\s*',
            r'\1 ',
            markdown,
            flags=re.MULTILINE
        )

        # 第二步：修复标题符号和文字之间的多余空格
        # 匹配模式：## 后面跟着 2 个或更多空格，然后是文字
        # 示例：
        #   ##  Create   -> ## Create
        #   ###    Heading -> ### Heading
        markdown = re.sub(
            r'^(#{1,6})\s{2,}',
            r'\1 ',
            markdown,
            flags=re.MULTILINE
        )

        # 第三步：再次清理可能残留的空白组合
        # 匹配：## 后面跟着空格+换行+空格的组合
        markdown = re.sub(
            r'^(#{1,6})[\s\n]+(?=[^\s#])',
            r'\1 ',
            markdown,
            flags=re.MULTILINE
        )

        # 第四步：修复连续的空行（超过2个空行的压缩为1个）
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)

        return markdown

    def convert_to_markdown(self, html_content: str) -> str:
        """
        将HTML内容转换为Markdown格式

        Args:
            html_content: HTML内容字符串

        Returns:
            str: 转换后的Markdown内容
        """
        # 先使用 html2text 转换
        markdown = self.converter.handle(html_content)

        # 后处理清理格式问题
        markdown = self._clean_markdown(markdown)

        return markdown

    def add_image_urls(self, markdown: str, image_filter: list = None) -> str:
        """
        在每个图片下方添加纯 URL 链接

        Args:
            markdown: 原始 Markdown 内容
            image_filter: 可选，指定要处理的图片 URL 列表
                         None=不过滤所有图片，[]=不添加任何图片URL，list=只处理匹配的URL

        Returns:
            str: 处理后的 Markdown 内容
        """
        import re
        from urllib.parse import urlparse

        def _url_matches_filter(url: str, filter_list: list) -> bool:
            """检查URL是否匹配过滤器"""
            if not filter_list:
                return False
            try:
                parsed = urlparse(url)
                for pattern in filter_list:
                    if pattern in parsed.netloc or pattern in url:
                        return True
                return False
            except Exception:
                return False

        # 如果配置为空列表，不添加任何图片URL
        if image_filter is False or image_filter == []:
            return markdown

        def replace_func(match):
            alt_text = match.group(1)
            url = match.group(2)

            # 如果有过滤列表，只处理匹配的 URL
            if image_filter is not None and image_filter:
                if not _url_matches_filter(url, image_filter):
                    return match.group(0)

            return f'{match.group(0)}\n{url}'

        markdown = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_func, markdown)
        return markdown