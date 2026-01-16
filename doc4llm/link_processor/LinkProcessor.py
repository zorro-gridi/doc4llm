
from urllib.parse import urljoin, urlparse
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import re


class LinkProcessor:
    """链接处理器类，负责将相对链接转换为绝对链接"""

    # 需要处理的链接属性
    LINK_ATTRIBUTES = [
        'href',      # 超链接
        'src',       # 图片、脚本、iframe等资源
        'action',    # 表单动作
        'data-src',  # 懒加载图片
        'data-href', # 懒加载链接
        'cite',      # 引用链接
        'background', # 背景图片
    ]

    # 需要处理的标签
    LINK_TAGS = [
        'a', 'img', 'link', 'script', 'iframe', 'form',
        'source', 'track', 'video', 'audio', 'embed', 'object'
    ]

    def __init__(self, base_url: str):
        """
        初始化链接处理器

        Args:
            base_url: 基础URL，用于转换相对链接
        """
        self.base_url = base_url
        self.processed_count = 0

    def convert_relative_links(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        将HTML中的所有相对链接转换为绝对链接

        Args:
            soup: BeautifulSoup对象

        Returns:
            BeautifulSoup: 处理后的BeautifulSoup对象
        """
        self.processed_count = 0

        # 处理所有标签的链接属性
        for tag in soup.find_all(self.LINK_TAGS):
            for attr in self.LINK_ATTRIBUTES:
                if tag.has_attr(attr):
                    original_url = tag[attr]
                    absolute_url = self._make_absolute_url(original_url)
                    if absolute_url and absolute_url != original_url:
                        tag[attr] = absolute_url
                        self.processed_count += 1

        # 处理style属性中的背景图片
        for tag in soup.find_all(style=True):
            style_content = tag['style']
            processed_style = self._process_style_urls(style_content)
            if processed_style != style_content:
                tag['style'] = processed_style
                self.processed_count += 1

        print(f"转换了 {self.processed_count} 个相对链接为绝对链接")
        return soup

    def _make_absolute_url(self, url: str) -> str:
        """
        将相对URL转换为绝对URL

        Args:
            url: 原始URL

        Returns:
            str: 绝对URL
        """
        if not url or url.startswith(('http://', 'https://', 'mailto:', 'tel:', '#')):
            return url

        # 处理协议相对链接 (//example.com/path)
        if url.startswith('//'):
            parsed_base = urlparse(self.base_url)
            return f"{parsed_base.scheme}:{url}"

        # 处理根相对链接 (/path)
        if url.startswith('/'):
            parsed_base = urlparse(self.base_url)
            return f"{parsed_base.scheme}://{parsed_base.netloc}{url}"

        # 处理相对路径 (path or ./path or ../path)
        try:
            return urljoin(self.base_url, url)
        except Exception as e:
            print(f"链接转换错误: {url} -> {e}")
            return url

    def _process_style_urls(self, style_content: str) -> str:
        """
        处理style属性中的URL

        Args:
            style_content: CSS样式内容

        Returns:
            str: 处理后的样式内容
        """
        # 匹配url()中的链接
        url_pattern = r'url\([\'"]?([^\)\'"]+)[\'"]?\)'

        def replace_url(match):
            original_url = match.group(1)
            absolute_url = self._make_absolute_url(original_url)
            return f'url("{absolute_url}")'

        return re.sub(url_pattern, replace_url, style_content)
