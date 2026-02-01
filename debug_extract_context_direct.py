#!/usr/bin/env python
"""直接测试 _extract_context 方法"""

import sys
sys.path.insert(0, '/Users/zorro/project/doc4llm')

from pathlib import Path
from doc4llm.doc_rag.searcher.content_searcher import ContentSearcher

BASE_DIR = "/Users/zorro/project/md_docs_base"
DOC_SET = "Claude_Code_Docs@latest/Data usage"
content_file = Path(BASE_DIR) / DOC_SET / "docContent.md"

# 读取文件
lines = content_file.read_text(encoding="utf-8").split("\n")

print(f"文件总行数: {len(lines)}")

# 创建 ContentSearcher 实例
searcher = ContentSearcher(
    base_dir=BASE_DIR,
    domain_nouns=["transcript"],
    max_results=20,
    context_lines=100,
    debug=True
)

# 测试 _extract_context 方法
print("\n" + "="*60)
print("测试 _extract_context 方法")
print("="*60)

# 测试第15行
print("\n--- 测试 match_line=15 ---")
result15 = searcher._extract_context(lines, 15)
print(f"结果长度: {len(result15)}")
print(f"结果内容:\n{result15}")
print(f"是否为空白: {not result15 or not result15.strip()}")

# 测试第19行
print("\n--- 测试 match_line=19 ---")
result19 = searcher._extract_context(lines, 19)
print(f"结果长度: {len(result19)}")
print(f"结果内容:\n{result19[:200]}...")
print(f"是否为空白: {not result19 or not result19.strip()}")

# 测试第32行
print("\n--- 测试 match_line=32 ---")
result32 = searcher._extract_context(lines, 32)
print(f"结果长度: {len(result32)}")
print(f"结果内容:\n{result32}")
print(f"是否为空白: {not result32 or not result32.strip()}")
