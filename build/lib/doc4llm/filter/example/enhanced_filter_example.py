#!/usr/bin/env python3
"""
增强版内容过滤器使用示例
Enhanced Content Filter Usage Examples

演示如何使用增强版内容过滤器处理现代文档站点
"""

from doc4llm.filter import ContentFilter, EnhancedContentFilter, create_filter
from doc4llm.extractor.WebContentExtractor import WebContentExtractor


def example_basic_usage():
    """基础使用 - 使用默认设置"""
    print("=" * 60)
    print("示例 1: 基础使用（增强版过滤器）")
    print("=" * 60)

    # 使用增强版过滤器（自动检测文档框架）
    extractor = WebContentExtractor(
        content_filter=None,  # 增强版会自动创建
        output_dir='output_enhanced',
        use_enhanced=True,
        doc_preset=None  # 自动检测
    )

    # 转换单个URL
    url = "https://code.claude.com/docs/en/skills"
    result = extractor.convert_url_to_markdown(url)

    if result:
        print(f"\n✓ 成功转换: {result}")
    else:
        print(f"\n✗ 转换失败")


def example_mintlify_site():
    """处理 Mintlify 文档站点"""
    print("\n" + "=" * 60)
    print("示例 2: Mintlify 文档站点（Claude 文档）")
    print("=" * 60)

    # 使用 Mintlify 预设
    extractor = WebContentExtractor(
        content_filter=None,
        output_dir='output_mintlify',
        use_enhanced=True,
        doc_preset='mintlify'
    )

    urls = [
        "https://code.claude.com/docs/en/skills",
        "https://code.claude.com/docs/en/output-styles",
    ]

    for url in urls:
        print(f"\n处理: {url}")
        result = extractor.convert_url_to_markdown(url)
        if result:
            print(f"✓ 成功: {result}")


def example_custom_filter():
    """自定义过滤器配置"""
    print("\n" + "=" * 60)
    print("示例 3: 自定义过滤器配置")
    print("=" * 60)

    # 创建自定义增强版过滤器
    custom_filter = EnhancedContentFilter(
        # 添加自定义非正文选择器
        non_content_selectors=[
            '.my-custom-sidebar',
            '[data-testid="advertisement"]',
        ],
        # 添加自定义模糊关键词
        fuzzy_keywords=['promo', 'sponsored'],
        # 自动检测框架
        auto_detect_framework=True
    )

    extractor = WebContentExtractor(
        content_filter=custom_filter,
        output_dir='output_custom',
        use_enhanced=True
    )

    url = "https://example.com/docs"
    result = extractor.convert_url_to_markdown(url)


def example_direct_filter_usage():
    """直接使用增强版过滤器"""
    print("\n" + "=" * 60)
    print("示例 4: 直接使用增强版过滤器")
    print("=" * 60)

    from bs4 import BeautifulSoup
    import requests

    # 获取网页
    url = "https://code.claude.com/docs/en/skills"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 创建过滤器
    content_filter = create_filter(preset='mintlify', auto_detect_framework=True)

    # 过滤内容
    cleaned_soup = content_filter.filter_non_content_blocks(soup)

    # 检测到的框架
    if content_filter.detected_framework:
        print(f"检测到文档框架: {content_filter.detected_framework}")

    # 转换为Markdown（需要 html2text）
    import html2text
    h = html2text.HTML2Text()
    h.ignore_links = False
    markdown_content = h.handle(str(cleaned_soup))

    # 移除 "Next steps" 等后续内容
    markdown_content = content_filter.filter_content_end_markers(markdown_content)

    print("\n提取的内容预览（前500字符）:")
    print(markdown_content[:500] + "...")


def example_comparison():
    """对比原始过滤器和增强版过滤器"""
    print("\n" + "=" * 60)
    print("示例 5: 原始 vs 增强版过滤器对比")
    print("=" * 60)

    url = "https://code.claude.com/docs/en/skills"

    # 使用原始过滤器
    print("\n--- 使用原始 ContentFilter ---")
    original_filter = ContentFilter()
    extractor_original = WebContentExtractor(
        content_filter=original_filter,
        output_dir='output_original',
        use_enhanced=False
    )
    result_original = extractor_original.convert_url_to_markdown(url)

    # 使用增强版过滤器
    print("\n--- 使用增强版 EnhancedContentFilter ---")
    extractor_enhanced = WebContentExtractor(
        content_filter=None,
        output_dir='output_enhanced',
        use_enhanced=True,
        doc_preset='mintlify'
    )
    result_enhanced = extractor_enhanced.convert_url_to_markdown(url)

    # 对比文件大小
    if result_original and result_enhanced:
        import os
        size_original = os.path.getsize(result_original)
        size_enhanced = os.path.getsize(result_enhanced)

        print(f"\n文件大小对比:")
        print(f"  原始过滤器: {size_original} bytes")
        print(f"  增强版过滤器: {size_enhanced} bytes")
        print(f"  减少: {size_original - size_enhanced} bytes "
              f"({100 * (size_original - size_enhanced) / size_original:.1f}%)")


def example_framework_presets():
    """不同文档框架的预设"""
    print("\n" + "=" * 60)
    print("示例 6: 不同文档框架预设")
    print("=" * 60)

    # 支持的文档框架
    frameworks = {
        'mintlify': 'Claude Code Docs',
        'docusaurus': 'React / Docusaurus 文档',
        'vitepress': 'Vue / VitePress 文档',
        'gitbook': 'GitBook 文档',
    }

    print("\n支持的文档框架预设:")
    for framework, description in frameworks.items():
        print(f"  - {framework}: {description}")

    print("\n使用方法:")
    print("  extractor = WebContentExtractor(")
    print("      content_filter=None,")
    print("      use_enhanced=True,")
    print("      doc_preset='mintlify'  # 指定框架")
    print("  )")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("增强版内容过滤器使用示例")
    print("=" * 60)

    # 取消注释以运行不同示例
    example_basic_usage()
    # example_mintlify_site()
    # example_custom_filter()
    # example_direct_filter_usage()
    # example_comparison()
    # example_framework_presets()


if __name__ == '__main__':
    main()
