#!/usr/bin/env python
"""测试 DocReaderAPI 读取 docContent.md 的情况"""

import json
import os

# 切换到项目目录
os.chdir("/Users/zorro/project/doc4llm")

# 读取 docContent.md 的实际内容
agent_skills_path = "doc4llm/md_docs/OpenCode_Docs@latest/Agent Skills/docContent.md"
tools_path = "doc4llm/md_docs/OpenCode_Docs@latest/Tools/docContent.md"

print("=" * 60)
print("读取原始 docContent.md 文件")
print("=" * 60)

if os.path.exists(agent_skills_path):
    with open(agent_skills_path, "r", encoding="utf-8") as f:
        agent_content = f.read()
    print(f"\n[Agent Skills/docContent.md]")
    print(f"文件大小: {len(agent_content)} 字符")
    print(f"行数: {len(agent_content.splitlines())}")
    print(f"\n前 1000 字符:")
    print(agent_content[:1000])
else:
    print(f"文件不存在: {agent_skills_path}")

print("\n" + "-" * 60)

if os.path.exists(tools_path):
    with open(tools_path, "r", encoding="utf-8") as f:
        tools_content = f.read()
    print(f"\n[Tools/docContent.md]")
    print(f"文件大小: {len(tools_content)} 字符")
    print(f"行数: {len(tools_content.splitlines())}")
    print(f"\n前 1000 字符:")
    print(tools_content[:1000])
else:
    print(f"文件不存在: {tools_path}")

# 现在测试 DocReaderAPI
print("\n" + "=" * 60)
print("测试 DocReaderAPI.extract_multi_by_headings")
print("=" * 60)

from doc4llm.doc_rag.reader.doc_reader_api import DocReaderAPI

test_sections = {
    "sections": [
        {
            "title": "Agent Skills",
            "headings": ["Agent Skills"],
            "doc_set": "OpenCode_Docs@latest"
        },
        {
            "title": "Tools",
            "headings": ["3.10. skill"],
            "doc_set": "OpenCode_Docs@latest"
        }
    ]
}

reader_api = DocReaderAPI(
    knowledge_base_path="knowledge_base.json",
    base_dir=None,
)

print(f"\n输入 sections:")
print(json.dumps(test_sections["sections"], ensure_ascii=False, indent=2))

result = reader_api.extract_multi_by_headings(
    sections=test_sections["sections"],
    threshold=2100
)

print(f"\n返回结果:")
print(f"  - document_count: {result.document_count}")
print(f"  - total_line_count: {result.total_line_count}")
print(f"  - requires_processing: {result.requires_processing}")
print(f"  - individual_counts: {result.individual_counts}")

print(f"\n提取的 contents:")
for key, content in result.contents.items():
    print(f"\n[{key}]")
    print(f"行数: {len(content.splitlines())}")
    print(f"内容:\n{content}")
