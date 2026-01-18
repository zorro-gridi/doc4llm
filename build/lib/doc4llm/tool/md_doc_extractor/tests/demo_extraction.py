"""
演示脚本：使用标题从 docContent.md 提取文档内容
"""
import re
from pathlib import Path

from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor


# 配置路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
BASE_DIR = PROJECT_ROOT / "md_docs"
DOC_NAME = "code_claude_com"
DOC_VERSION = "latest"
DOC_TITLE = "Agent Skills - Claude Code Docs"

DOC_CONTENT_PATH = BASE_DIR / f"{DOC_NAME}:{DOC_VERSION}" / DOC_TITLE / "docContent.md"
DOC_TOC_PATH = BASE_DIR / f"{DOC_NAME}:{DOC_VERSION}" / DOC_TITLE / "docTOC.md"


def parse_toc_titles(toc_path: Path) -> list[str]:
    """从 docTOC.md 解析标题列表"""
    content = toc_path.read_text(encoding="utf-8")
    titles = []

    for line in content.splitlines():
        line = line.strip()
        match = re.match(r'^(#{2,4})\s+(.+?)\s*：https://', line)
        if match:
            title = match.group(2).strip()
            title = re.sub(r'^\d+(\.\d+)*\.\s+', '', title)
            if title:
                titles.append(title)

    return titles


def main():
    """主函数：演示文档提取"""
    print("=" * 80)
    print("文档内容提取演示")
    print("=" * 80)

    # 解析所有标题
    all_titles = parse_toc_titles(DOC_TOC_PATH)
    print(f"\n📋 docTOC.md 中的标题总数: {len(all_titles)}")

    # 选择几个标题进行测试
    test_titles = [
        "Create your first Skill",
        "How Skills work",
        "Configure Skills",
    ]

    print(f"\n🔍 测试标题: {test_titles}")
    print("-" * 80)

    # 方式1: 目录模式 - 使用完整文档标题提取
    print("\n【方式1】目录模式 - 提取完整文档")
    print("-" * 80)
    extractor = MarkdownDocExtractor(base_dir=str(BASE_DIR))

    full_content = extractor.extract_by_title(DOC_TITLE)
    print(f"查询标题: {DOC_TITLE}")
    print(f"返回内容长度: {len(full_content)} 字符")
    print(f"内容预览 (前200字符):\n{full_content[:200]}...")

    # 方式2: 单文件模式 - 直接读取文件
    print("\n" + "=" * 80)
    print("【方式2】单文件模式 - 直接读取")
    print("-" * 80)
    single_extractor = MarkdownDocExtractor(single_file_path=str(DOC_CONTENT_PATH))

    content = single_extractor.extract_by_title()
    print(f"查询标题: (无 - 直接读取)")
    print(f"返回内容长度: {len(content)} 字符")
    print(f"内容预览 (前200字符):\n{content[:200]}...")

    # 方式3: 单文件模式 - 使用标题匹配
    print("\n" + "=" * 80)
    print("【方式3】单文件模式 - 标题匹配")
    print("-" * 80)

    for title in test_titles:
        content = single_extractor.extract_by_title(title)
        if content and content != "":
            print(f"\n✅ 查询标题: {title}")
            print(f"   返回内容长度: {len(content)} 字符")
            # 显示前150个字符
            preview = content[:150].replace('\n', ' ')
            print(f"   内容预览: {preview}...")
        else:
            print(f"\n❌ 查询标题: {title}")
            print(f"   结果: 未找到匹配内容")

    # 方式4: 列出可用文档
    print("\n" + "=" * 80)
    print("【方式4】列出可用文档")
    print("-" * 80)
    docs = extractor.list_available_documents()
    print(f"可用文档数量: {len(docs)}")
    print(f"文档列表:")
    for i, doc in enumerate(docs[:5], 1):
        print(f"  {i}. {doc}")
    if len(docs) > 5:
        print(f"  ... 还有 {len(docs) - 5} 个文档")

    # 方式5: 批量提取
    print("\n" + "=" * 80)
    print("【方式5】批量提取")
    print("-" * 80)
    results = extractor.extract_by_titles([DOC_TITLE])
    for title, content in results.items():
        print(f"✅ 标题: {title}")
        print(f"   内容长度: {len(content)} 字符")

    # 方式6: 搜索文档
    print("\n" + "=" * 80)
    print("【方式6】搜索文档 (模糊匹配)")
    print("-" * 80)
    search_extractor = MarkdownDocExtractor(
        base_dir=str(BASE_DIR),
        search_mode="fuzzy",
        fuzzy_threshold=0.3
    )
    search_results = search_extractor.search_documents("Agent Skills")
    print(f"搜索关键词: 'Agent Skills'")
    print(f"找到 {len(search_results)} 个匹配结果:")
    for result in search_results:
        print(f"  - 标题: {result['title']}")
        print(f"    相似度: {result['similarity']:.2f}")

    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
