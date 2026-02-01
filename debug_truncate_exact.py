#!/usr/bin/env python
"""精确模拟 _truncate_symmetric 的行为"""

import sys
sys.path.insert(0, '/Users/zorro/project/doc4llm')

from pathlib import Path
import re

BASE_DIR = "/Users/zorro/project/md_docs_base"
DOC_SET = "Claude_Code_Docs@latest/Data usage"
content_file = Path(BASE_DIR) / DOC_SET / "docContent.md"

lines = content_file.read_text(encoding="utf-8").split("\n")

# 模拟第15行的上下文提取
match_line = 15
match_idx = match_line - 1  # 14
context_size = 2

start_idx = max(0, match_idx - context_size)  # 12
end_idx = min(len(lines), match_idx + context_size + 1)  # 17

print(f"match_line={match_line}, match_idx={match_idx}")
print(f"start_idx={start_idx}, end_idx={end_idx}")
print()

# 收集非空行
context_lines = []
for i in range(start_idx, end_idx):
    line = lines[i].strip()
    line = re.sub(r"^--+\s*", "", line)
    if line:
        context_lines.append(line)

print(f"context_lines ({len(context_lines)} 行):")
for i, line in enumerate(context_lines):
    print(f"  [{i}] {line[:50]}...")
print()

# 模拟 _truncate_symmetric
def count_words(text):
    return len(text.split())

max_words = 100
current_text = "\n".join(context_lines)
word_count = count_words(current_text)

print(f"初始单词数: {word_count}")
print()

left_idx = 0
right_idx = len(context_lines) - 1

print("截断过程:")
iteration = 0
while word_count > max_words and left_idx < right_idx:
    iteration += 1
    print(f"  迭代{iteration}: left_idx={left_idx}, right_idx={right_idx}, words={word_count}")

    # 交替剔除
    if (left_idx + right_idx) % 2 == 0:
        left_idx += 1
        action = "剔除左边"
    else:
        right_idx -= 1
        action = "剔除右边"

    current_lines = context_lines[left_idx : right_idx + 1]
    current_text = "\n".join(current_lines)
    word_count = count_words(current_text)

    print(f"    {action} -> 剩余 [{left_idx}:{right_idx+1}] = {len(current_lines)} 行")
    print(f"    当前行: {[l[:30]+'...' if len(l)>30 else l for l in current_lines]}")
    print(f"    新单词数: {word_count}")

print()
print(f"最终 left_idx={left_idx}, right_idx={right_idx}")
print(f"最终行数: {right_idx - left_idx + 1}")
print(f"最终单词数: {word_count}")

# 检查匹配行是否还在
# match_idx - start_idx = 14 - 12 = 2
# 但 context_lines 的索引需要重新计算
# 原始行索引 -> context_lines 索引的映射被跳过的空行破坏了！

print()
print("="*60)
print("问题分析")
print("="*60)
print(f"匹配行原始索引 (match_idx): {match_idx}")
print(f"起始索引 (start_idx): {start_idx}")
print(f"相对位置 (match_idx - start_idx): {match_idx - start_idx}")
print()
print("但在 context_lines 中：")
print(f"  [0] -> 原始行 {start_idx+1} = 行13")
print(f"  [1] -> 原始行 15 (跳过行14)")
print(f"  [2] -> 原始行 17 (跳过行16)")
print()
print("传入 _truncate_symmetric 的 match_idx=2 指向行17，")
print("而不是实际匹配行行15！")
print()
print("这是因为空行被过滤后，索引映射失效了。")
