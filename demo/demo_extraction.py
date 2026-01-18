"""
演示脚本：使用标题从 docContent.md 提取文档内容和章节内容
"""
import re
from pathlib import Path

from doc4llm.tool.md_doc_retrieval import (
    MarkdownDocExtractor,
    extract_section_by_title,
)


# 配置路径
# 从 tests/demo_extraction.py 到项目根目录: tests -> doc4llm
PROJECT_ROOT = Path(__file__).parent.parent
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
    """主函数：演示文档和章节提取"""
    print("=" * 80)
    print("文档内容提取演示 - 支持文档级别和章节级别提取")
    print("=" * 80)

    # 读取完整文档内容
    full_content = DOC_CONTENT_PATH.read_text(encoding="utf-8")

    # 解析所有标题
    all_titles = parse_toc_titles(DOC_TOC_PATH)
    print(f"\n📋 docTOC.md 中的章节标题总数: {len(all_titles)}")

    # 选择几个标题进行测试
    test_titles = [
        "Create your first Skill",
        "How Skills work",
        "Configure Skills",
        "Write SKILL.md",
    ]

    print(f"\n🔍 测试章节标题: {test_titles}")
    print("-" * 80)

    # ========================================================================
    # 文档级别提取（整个文档）
    # ========================================================================
    print("\n【一】文档级别提取 - 提取完整文档")
    print("=" * 80)

    extractor = MarkdownDocExtractor(base_dir=str(BASE_DIR))
    doc_content = extractor.extract_by_title(DOC_TITLE)

    print(f"查询标题: {DOC_TITLE}")
    print(f"返回内容长度: {len(doc_content)} 字符")
    print(f"内容预览 (前150字符):\n{doc_content[:150]}...")

    # ========================================================================
    # 章节级别提取（文档内的章节）
    # ========================================================================
    print("\n" + "=" * 80)
    print("【二】章节级别提取 - 提取文档内的特定章节")
    print("=" * 80)

    for title in test_titles:
        section = extract_section_by_title(full_content, title)
        if section:
            lines = section.splitlines()
            print(f"\n✅ 章节: {title}")
            print(f"   行数: {len(lines)} 行")
            print(f"   字符数: {len(section)} 字符")
            # 显示前3行作为预览
            preview_lines = lines[:3]
            preview = '\n   '.join(preview_lines)
            print(f"   内容预览:\n   {preview}...")
        else:
            print(f"\n❌ 章节: {title}")
            print(f"   结果: 未找到匹配章节")

    # ========================================================================
    # 单文件模式 - 直接读取
    # ========================================================================
    print("\n" + "=" * 80)
    print("【三】单文件模式 - 直接读取文件")
    print("=" * 80)

    single_extractor = MarkdownDocExtractor(single_file_path=str(DOC_CONTENT_PATH))
    content = single_extractor.extract_by_title()

    print(f"查询标题: (无 - 直接读取)")
    print(f"返回内容长度: {len(content)} 字符")

    # 用单文件模式 + 章节提取
    print("\n--- 单文件模式 + 章节提取 ---")
    for title in test_titles[:2]:  # 只测试前2个
        section = extract_section_by_title(content, title)
        if section:
            print(f"\n✅ {title}: {len(section)} 字符")

    # ========================================================================
    # 批量提取多个章节
    # ========================================================================
    print("\n" + "=" * 80)
    print("【四】批量提取多个章节")
    print("=" * 80)

    sections = {}
    for title in test_titles:
        section = extract_section_by_title(full_content, title)
        if section:
            sections[title] = section

    print(f"请求提取 {len(test_titles)} 个章节")
    print(f"成功提取 {len(sections)} 个章节:")
    for title, content in sections.items():
        print(f"  - {title}: {len(content)} 字符")

    # ========================================================================
    # 统计信息
    # ========================================================================
    print("\n" + "=" * 80)
    print("【五】统计信息")
    print("=" * 80)

    print(f"文档标题: {DOC_TITLE}")
    print(f"文档总长度: {len(full_content)} 字符")
    print(f"文档总行数: {len(full_content.splitlines())} 行")
    print(f"docTOC.md 章节数: {len(all_titles)} 个")
    print(f"成功提取的章节: {len(sections)} 个")

    # 找到最长的章节
    if sections:
        longest = max(sections.items(), key=lambda x: len(x[1]))
        print(f"最长的章节: '{longest[0]}' ({len(longest[1])} 字符)")

    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
