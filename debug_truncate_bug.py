#!/usr/bin/env python
"""验证 _truncate_symmetric 截断逻辑问题"""

import sys
sys.path.insert(0, '/Users/zorro/project/doc4llm')

from pathlib import Path
from doc4llm.doc_rag.searcher.content_searcher import ContentSearcher

BASE_DIR = "/Users/zorro/project/md_docs_base"
DOC_SET = "Claude_Code_Docs@latest/Data usage"
content_file = Path(BASE_DIR) / DOC_SET / "docContent.md"

lines = content_file.read_text(encoding="utf-8").split("\n")
match_line = 15  # 匹配行
match_idx = match_line - 1  # 0-based index = 14

print(f"匹配行: {match_line}, match_idx: {match_idx}")
print()

# 模拟 current_size=2 时的 context_lines
context_size = 2
start_idx = max(0, match_idx - context_size)  # 12
end_idx = min(len(lines), match_idx + context_size + 1)  # 17

print(f"行范围: {start_idx+1} 到 {end_idx}")
print()

# 收集非空行
context_lines = []
for i in range(start_idx, end_idx):
    line = lines[i].strip()
    line = __import__('re').sub(r"^--+\s*", "", line)
    if line:
        context_lines.append((i+1, line))  # 保存行号

print("原始 context_lines:")
for line_num, line in context_lines:
    print(f"  行{line_num}: {line[:50]}...")
print(f"共 {len(context_lines)} 行")
print()

# 模拟 _truncate_symmetric
max_words = 100
left_idx = 0
right_idx = len(context_lines) - 1

print("模拟截断过程 (交替剔除):")
iteration = 0
while left_idx < right_idx:
    iteration += 1
    # 计算当前匹配行在 context_lines 中的索引
    # 原始 match_idx = 14, start_idx = 12
    # 匹配行在 context_lines 中的位置 = match_idx - start_idx = 2
    match_pos_in_context = match_idx - start_idx
    print(f"迭代 {iteration}: left_idx={left_idx}, right_idx={right_idx}, match_pos={match_pos_in_context}")

    # 检查匹配行是否已被剔除
    if match_pos_in_context < left_idx or match_pos_in_context > right_idx:
        print(f"  !!! 匹配行已被剔除 !!!")
        remaining_lines = context_lines[left_idx:right_idx+1]
        print(f"  剩余行: {[l[0] for l in remaining_lines]}")
        break

    # 交替剔除
    if (left_idx + right_idx) % 2 == 0:
        left_idx += 1
        print(f"  剔除左边 -> left_idx={left_idx}")
    else:
        right_idx -= 1
        print(f"  剔除右边 -> right_idx={right_idx}")

    # 检查
    if left_idx >= right_idx:
        print(f"  终止: left_idx >= right_idx")
        break

print()
print("="*60)
print("问题分析:")
print("="*60)
print(f"match_idx = {match_idx}")
print(f"start_idx = {start_idx}")
print(f"match_pos_in_context = {match_idx - start_idx} (行{context_lines[match_idx - start_idx][0]})")
print()
print("当 left_idx 增加到 3 时，match_pos=2 < left_idx=3")
print("匹配行被剔除！")
print()
print("根本原因: match_pos_in_context 是静态计算的，")
print("而不是根据每次截断后的 left_idx/right_idx 动态更新")
