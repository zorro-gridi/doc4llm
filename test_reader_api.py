#!/usr/bin/env python
"""测试 DocReaderAPI.extract_multi_by_headings 的返回结果"""

import sys

# 激活 k8s 环境
import subprocess
result = subprocess.run(["conda", "activate", "k8s"], capture_output=True, text=True, shell=True)

# 使用输入数据样例
test_input = {
    "sections": [
        {
            "title": "Agent Skills",
            "headings": [
                "Agent Skills"
            ],
            "doc_set": "OpenCode_Docs@latest"
        },
        {
            "title": "Tools",
            "headings": [
                "3.10. skill"
            ],
            "doc_set": "OpenCode_Docs@latest"
        }
    ]
}

from doc4llm.doc_rag.reader.doc_reader_api import DocReaderAPI

def main():
    print("=" * 60)
    print("测试 DocReaderAPI.extract_multi_by_headings")
    print("=" * 60)

    reader_api = DocReaderAPI(
        knowledge_base_path="knowledge_base.json",
        base_dir=None,
    )

    sections = test_input["sections"]
    print(f"\n输入 sections:")
    import json
    print(json.dumps(sections, ensure_ascii=False, indent=2))

    print("\n" + "-" * 60)
    print("执行 extract_multi_by_headings...")
    print("-" * 60 + "\n")

    extraction_result = reader_api.extract_multi_by_headings(
        sections=sections,
        threshold=2100
    )

    # 输出返回结果的所有属性
    print("返回结果 (ExtractionResult):")
    print(f"  - document_count: {extraction_result.document_count}")
    print(f"  - total_line_count: {extraction_result.total_line_count}")
    print(f"  - threshold: {extraction_result.threshold}")
    print(f"  - requires_processing: {extraction_result.requires_processing}")
    print(f"  - individual_counts: {extraction_result.individual_counts}")

    print(f"\n提取的 contents 数量: {len(extraction_result.contents)}")
    print("\n提取的内容键值:")
    for key in extraction_result.contents.keys():
        print(f"  - {key}")

    # 显示部分内容预览
    print("\n" + "-" * 60)
    print("内容预览 (前500字符):")
    print("-" * 60)
    for key, content in extraction_result.contents.items():
        print(f"\n[{key}]:")
        print(content[:500] if len(content) > 500 else content)
        print("...")

    return extraction_result

if __name__ == "__main__":
    result = main()
