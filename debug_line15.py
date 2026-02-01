#!/usr/bin/env python
"""深入调试 ContentSearcher related_context 为空的问题"""

import sys
sys.path.insert(0, '/Users/zorro/project/doc4llm')

from pathlib import Path
import re

BASE_DIR = "/Users/zorro/project/md_docs_base"
DOC_SET = "Claude_Code_Docs@latest/Data usage"
content_file = Path(BASE_DIR) / DOC_SET / "docContent.md"

print(f"读取文件: {content_file}")
lines = content_file.read_text(encoding="utf-8").split("\n")

print(f"\n总行数: {len(lines)}")
print("\n" + "="*60)
print("检查第15行附近的内容（注意：行号从1开始）")
print("="*60)

for i in range(10, 20):
    if i <= len(lines):
        line = lines[i-1]  # 0-based index
        print(f"行 {i}: '{line}'")
        print(f"  strip后: '{line.strip()}'")
        print(f"  长度: {len(line.strip())}")

print("\n" + "="*60)
print("检查包含 'transcript' 的行")
print("="*60)

pattern = re.compile(r"transcript", re.IGNORECASE)
for line_num, line in enumerate(lines, start=1):
    if pattern.search(line):
        print(f"行 {line_num}: '{line[:100]}...'")

print("\n" + "="*60)
print("检查 heading 格式")
print("="*60)

for i, line in enumerate(lines[:20], start=1):
    match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
    if match:
        print(f"行 {i}: heading级别={len(match.group(1))}, 文本='{match.group(2)[:50]}'")
