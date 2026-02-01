#!/usr/bin/env python
"""深入调试 _extract_context 方法"""

import sys
sys.path.insert(0, '/Users/zorro/project/doc4llm')

from pathlib import Path
import re

BASE_DIR = "/Users/zorro/project/md_docs_base"
DOC_SET = "Claude_Code_Docs@latest/Data usage"
content_file = Path(BASE_DIR) / DOC_SET / "docContent.md"

lines = content_file.read_text(encoding="utf-8").split("\n")
match_line = 15  # 结果1的匹配行

print(f"match_line: {match_line}")
print(f"match_idx (0-based): {match_line - 1}")
print()

# 模拟 _extract_context 的逻辑
context_size = 2
max_words = 100
max_context_size = 50
expand_step = 5
match_idx = match_line - 1

print("="*60)
print("模拟 _extract_context 的执行过程")
print("="*60)

current_size = context_size
iteration = 0

while current_size <= max_context_size:
    iteration += 1
    print(f"\n--- 迭代 {iteration}: current_size={current_size} ---")

    start_idx = max(0, match_idx - current_size)
    end_idx = min(len(lines), match_idx + current_size + 1)

    print(f"start_idx: {start_idx}, end_idx: {end_idx}")
    print(f"提取行范围: {start_idx+1} 到 {end_idx}")

    context_lines = []
    for i in range(start_idx, end_idx):
        line = lines[i].strip()
        # 移除 leading "--"
        line = re.sub(r"^--+\s*", "", line)
        if line:  # 清理后非空则保留
            context_lines.append((i+1, line[:50] + "..." if len(line) > 50 else line))

    print(f"过滤后的行数: {len(context_lines)}")
    for line_num, line_preview in context_lines:
        print(f"  行{line_num}: {line_preview}")

    # 统计单词
    context_text = "\n".join([l[1] for l in context_lines])
    # 清理 URL
    context_text_clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", context_text)
    # 统计单词
    words = context_text_clean.split()
    word_count = len(words)

    print(f"单词数: {word_count} (限制: {max_words})")

    if word_count <= max_words:
        print(f"✓ 单词数在限制内，返回结果")
        print(f"最终结果:\n{context_text_clean}")
        break

    # 超过单词限制
    print(f"✗ 单词数超过限制")
    if current_size < max_context_size:
        current_size += expand_step
        print(f"  扩展 context_size 到 {current_size}")
    else:
        print(f"  达到最大 context_size，进行截断")
        # 截断逻辑
        left_idx = 0
        right_idx = len(context_lines) - 1
        current_word_count = word_count

        while current_word_count > max_words and left_idx < right_idx:
            if (left_idx + right_idx) % 2 == 0:
                left_idx += 1
            else:
                right_idx -= 1
            current_lines = context_lines[left_idx:right_idx+1]
            current_text = "\n".join([l[1] for l in current_lines])
            current_text_clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", current_text)
            current_word_count = len(current_text_clean.split())

        print(f"截断后单词数: {current_word_count}")
        break
