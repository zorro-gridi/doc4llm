#!/usr/bin/env python3
"""
网页内容提取器模块

该模块提供将网页内容转换为Markdown格式的功能，包含智能过滤非正文内容、
日志输出清理等功能。

主要类:
    WebContentExtractor: 网页内容提取和转换的核心类
    ContentFilter: 内容过滤器，负责清理非正文内容
    MarkdownConverter: Markdown格式转换器

使用示例:
    >>> extractor = WebContentExtractor()
    >>> result = extractor.convert_url_to_markdown("https://example.com")
    >>> print(f"转换结果: {result}")
"""


import json
from doc4llm.filter import ContentFilter, EnhancedContentFilter
from doc4llm.filter.config import FilterConfigLoader
from doc4llm.extractor.WebContentExtractor import WebContentExtractor



def main():
    """主函数"""
    # 单个URL示例
    output_dir = 'AutoGen'
    output_dir = 'AgentScope'
    proxies = {'https': 'http://127.0.0.1:7890'}

    # 尝试从 config.json 加载配置
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        filter_config = FilterConfigLoader.load_from_config(config)

        # 如果配置了 content_end_markers 或其他高级配置，使用增强版过滤器
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
            # 应用高级配置
            if filter_config.get('content_end_markers'):
                content_filter.content_end_markers = filter_config['content_end_markers']
            if filter_config.get('content_preserve_selectors'):
                content_filter.content_preserve_selectors = filter_config['content_preserve_selectors']
            if filter_config.get('code_container_selectors'):
                content_filter.code_container_selectors = filter_config['code_container_selectors']
            print(f"使用增强版过滤器，配置: preset={filter_config.get('documentation_preset')}")
        else:
            content_filter = ContentFilter()
            print("使用标准内容过滤器")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"无法加载配置文件 ({e})，使用默认配置")
        content_filter = ContentFilter()

    extractor = WebContentExtractor(content_filter, output_dir=output_dir, proxies=proxies)

    test_urls = [
        "https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/agent-and-agent-runtime.html"
    ]

    for url in test_urls:
        result = extractor.convert_url_to_markdown(url)
        if result:
            print(f"成功转换: {result}")
        else:
            print(f"转换失败: {url}")


if __name__ == "__main__":
    main()
