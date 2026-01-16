from doc4llm.filter import (
    BaseContentFilter,
    ContentFilter,
    EnhancedContentFilter,
    create_filter,
)
from doc4llm.filter.config import FilterConfigLoader
from doc4llm.convertor.MarkdownConverter import MarkdownConverter
from doc4llm.link_processor.LinkProcessor import LinkProcessor

import os
import json
import requests
from typing import List, Optional, Dict, Any, Tuple

from bs4 import BeautifulSoup

from pathlib import Path

current_dir = Path(__file__).parent


class WebContentExtractor:
    """网页内容提取器主类"""

    def __init__(self,
                 content_filter: Optional[BaseContentFilter] = None,
                 output_dir: str = 'output',
                 proxies: Optional[Dict] = None,
                 use_enhanced: bool = False,
                 doc_preset: Optional[str] = None,
                 auto_detect: bool = True,
                 config_path: str = 'doc4llm/config/config.json'):
        """
        初始化网页内容提取器

        Args:
            content_filter: 自定义内容过滤器（继承自 BaseContentFilter）
            output_dir: 输出目录路径
            proxies: 代理设置
            use_enhanced: 是否使用增强版过滤器
            doc_preset: 文档框架预设 ('mintlify', 'docusaurus', 'vitepress', 'gitbook')
            auto_detect: 是否自动检测文档框架
            config_path: 配置文件路径（默认 'doc4llm/config/config.json'）
        """
        self.output_dir = output_dir
        self.proxies = proxies
        self.auto_detect = auto_detect

        # 创建过滤器实例（兼容新旧 API）
        if content_filter is not None:
            # 方式1: 直接传入自定义过滤器
            self.content_filter = content_filter
        else:
            # 尝试从 config.json 加载配置
            filter_config = self._load_filter_config(config_path, doc_preset)

            if filter_config and (use_enhanced or filter_config.get('content_end_markers') or filter_config.get('documentation_preset')):
                # 使用增强版过滤器，应用配置文件中的设置
                self.content_filter = EnhancedContentFilter(
                    non_content_selectors=filter_config.get('non_content_selectors'),
                    fuzzy_keywords=filter_config.get('fuzzy_keywords'),
                    log_levels=filter_config.get('log_levels'),
                    meaningless_content=filter_config.get('meaningless_content'),
                    preset=filter_config.get('documentation_preset') or doc_preset,
                    auto_detect_framework=auto_detect,
                    merge_mode=filter_config.get('merge_mode', 'extend')
                )
                # 应用高级配置
                if filter_config.get('content_end_markers'):
                    self.content_filter.content_end_markers = filter_config['content_end_markers']
                if filter_config.get('content_preserve_selectors'):
                    self.content_filter.content_preserve_selectors = filter_config['content_preserve_selectors']
                if filter_config.get('code_container_selectors'):
                    self.content_filter.code_container_selectors = filter_config['code_container_selectors']
            elif doc_preset:
                # 方式2: 指定了预设，使用增强版过滤器
                self.content_filter = create_filter(preset=doc_preset, auto_detect_framework=auto_detect)
            elif use_enhanced:
                # 方式3: 使用增强版过滤器（自动检测）
                self.content_filter = create_filter(preset=None, auto_detect_framework=auto_detect)
            else:
                # 方式4: 默认使用原始过滤器
                self.content_filter = ContentFilter()

        self.markdown_converter = MarkdownConverter()

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_filter_config(self, config_path: str, preset: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        从配置文件加载过滤器配置

        Args:
            config_path: 配置文件路径
            preset: 文档框架预设

        Returns:
            过滤器配置字典，如果加载失败则返回 None
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return FilterConfigLoader.load_from_config(config, preset)
        except FileNotFoundError:
            print(f"配置文件 {config_path} 不存在，使用默认配置")
            return None
        except json.JSONDecodeError as e:
            print(f"配置文件 {config_path} 格式错误: {e}")
            return None
        except Exception as e:
            print(f"加载配置文件 {config_path} 时出错: {e}")
            return None

    def _get_headers(self) -> Dict[str, str]:
        """
        获取请求头

        Returns:
            Dict[str, str]: 请求头字典
        """
        headers_path = Path(self.headers_path)
        if not headers_path.is_absolute():
            headers_path = current_dir.parent.parent / headers_path
        try:
            with open(headers_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告: headers 文件不存在: {headers_path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"警告: headers 文件格式错误: {e}")
            return {}

    def _fetch_webpage(self, url: str) -> Optional[requests.Response]:
        """
        获取网页内容

        Args:
            url: 目标URL

        Returns:
            Optional[requests.Response]: 响应对象或None
        """
        try:
            headers = self._get_headers()
            response = requests.get(
                url,
                headers=headers,
                timeout=30,
                proxies=self.proxies
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response
        except requests.exceptions.RequestException as e:
            print(f"网络请求错误: {e}")
            return None

    def _process_html_content(self, url: str, html_content: str) -> Optional[Tuple[str, str]]:
        """
        处理HTML内容

        Args:
            url: 网页URL
            html_content: HTML内容

        Returns:
            Optional[Tuple[str, str]]: (处理后的Markdown内容, 页面标题) 或 None
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            page_title = self.content_filter.get_page_title(url, soup)
            print(f"获取到页面标题: {page_title}")

            print("正在转换相对链接为绝对链接...")
            link_processor = LinkProcessor(url)
            soup = link_processor.convert_relative_links(soup)

            # 使用统一的处理流程
            print("正在过滤侧边栏、目录等非正文内容...")
            cleaned_soup = self.content_filter.filter_non_content_blocks(soup)
            cleaned_soup = self.content_filter.filter_logging_outputs(cleaned_soup)

            # 转换为Markdown
            markdown_content = self.markdown_converter.convert_to_markdown(str(cleaned_soup))

            # 后处理（所有过滤器都支持，增强版可能有额外功能）
            markdown_content = self.content_filter.filter_content_end_markers(markdown_content)
            markdown_content = self.content_filter.remove_meaningless_content(markdown_content)
            markdown_content = self.content_filter.post_process_markdown(markdown_content)

            # 添加标题和原文链接
            markdown_with_title = (
                f"# {page_title}\n\n原文链接: {url}\n\n{markdown_content}"
            )

            return markdown_with_title, page_title

        except Exception as e:
            print(f"HTML处理错误: {e}")
            return None

    def _save_to_file(self, content: str, title: str) -> Optional[str]:
        """
        保存内容到文件

        Args:
            content: 要保存的内容
            title: 页面标题

        Returns:
            Optional[str]: 文件路径或None
        """
        try:
            clean_title = self.content_filter.sanitize_filename(title)
            filename = f"{clean_title}.md"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            return filepath
        except Exception as e:
            print(f"文件保存错误: {e}")
            return None

    def convert_url_to_markdown(self, url: str) -> Optional[str]:
        """
        将网页转换为Markdown文件

        Args:
            url: 目标网页URL

        Returns:
            Optional[str]: 保存的文件路径或None
        """
        print(f"正在获取网页: {url}")

        response = self._fetch_webpage(url)
        if not response:
            return None

        result = self._process_html_content(url, response.text)
        if not result:
            return None

        markdown_content, page_title = result
        if not markdown_content:
            return None

        filepath = self._save_to_file(markdown_content, page_title)
        if filepath:
            print(f"成功转换并保存为: {filepath}")

        return filepath

    def batch_convert_urls(self, urls: List[str]) -> Dict[str, Any]:
        """
        批量转换多个URL

        Args:
            urls: URL列表

        Returns:
            Dict[str, Any]: 转换结果统计
        """
        success_count = 0
        failed_urls = []

        for idx, url in enumerate(urls, 1):
            print(f"\n正在处理第{idx}个URL: {url}")
            result = self.convert_url_to_markdown(url)

            if result:
                success_count += 1
            else:
                failed_urls.append(url)

            print("-" * 50)

        print(f"\n转换完成! 成功: {success_count}/{len(urls)}")

        return {
            'total': len(urls),
            'success': success_count,
            'failed': len(failed_urls),
            'failed_urls': failed_urls
        }
