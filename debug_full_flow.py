#!/usr/bin/env python
"""完整模拟 _extract_context 的行为"""

import sys
sys.path.insert(0, '/Users/zorro/project/doc4llm')

from pathlib import Path
import re
from doc4llm.doc_rag.searcher.common_utils import count_words, clean_context_from_urls

BASE_DIR = "/Users/zorro/project/md_docs_base"
DOC_SET = "Claude_Code_Docs@latest/Data usage"
content_file = Path(BASE_DIR) / DOC_SET / "docContent.md"

lines = content_file.read_text(encoding="utf-8").split("\n")

match_line = 15
match_idx = match_line - 1

context_size = 2
max_words = 100
max_context_size = 50
expand_step = 5

current_size = context_size
iteration = 0
reached_max = False

print("="*60)
print("模拟 _extract_context 的完整流程")
print("="*60)

while current_size <= max_context_size:
    iteration += 1
    start_idx = max(0, match_idx - current_size)
    end_idx = min(len(lines), match_idx + current_size + 1)

    context_lines = []
    for i in range(start_idx, end_idx):
        line = lines[i].strip()
        line = re.sub(r"^--+\s*", "", line)
        if line:
            context_lines.append(line)

    context_text = "\n".join(context_lines)
    cleaned_text = clean_context_from_urls(context_text)
    word_count = count_words(cleaned_text)

    print(f"\n迭代{iteration}: current_size={current_size}")
    print(f"  行范围: {start_idx+1}-{end_idx}")
    print(f"  非空行数: {len(context_lines)}")
    print(f"  单词数: {word_count}/{max_words}")

    if word_count <= max_words:
        print(f"  ✓ 通过，返回")
        result = cleaned_text
        break

    if current_size < max_context_size:
        current_size += expand_step
        print(f"  ✗ 超过，扩展到 {current_size}")
    else:
        print(f"  ✗ 达到 max_context_size={max_context_size}，调用截断")
        reached_max = True
        break

if reached_max:
    print("\n" + "="*60)
    print("模拟 _truncate_symmetric")
    print("="*60)

    # 重新收集 context_lines（不限制范围，使用最大范围）
    start_idx = 0
    end_idx = len(lines)

    context_lines = []
    for i in range(start_idx, end_idx):
        line = lines[i].strip()
        line = re.sub(r"^--+\s*", "", line)
        if line:
            context_lines.append(line)

    context_text = "\n".join(context_lines)
    cleaned_text = clean_context_from_urls(context_text)
    word_count = count_words(cleaned_text)

    print(f"完整 context_lines: {len(context_lines)} 行")
    print(f"总单词数: {word_count}")

    # 截断
    left_idx = 0
    right_idx = len(context_lines) - 1

    print(f"\n截断过程:")
    trunc_iter = 0
    while word_count > max_words and left_idx < right_idx:
        trunc_iter += 1

        if (left_idx + right_idx) % 2 == 0:
            left_idx += 1
            action = "剔除左边"
        else:
            right_idx -= 1
            action = "剔除右边"

        current_lines = context_lines[left_idx:right_idx+1]
        current_text = "\n".join(current_lines)
        cleaned = clean_context_from_urls(current_text)
        word_count = count_words(cleaned)

        print(f"  迭代{trunc_iter}: {action} -> left_idx={left_idx}, right_idx={right_idx}, words={word_count}")

        if left_idx >= right_idx:
            break

    print(f"\n最终: left_idx={left_idx}, right_idx={right_idx}")
    print(f"剩余行数: {right_idx - left_idx + 1}")

    if word_count > max_words:
        words = cleaned.split()
        if len(words) > max_words:
            cleaned = " ".join(words[:max_words])
            word_count = len(words[:max_words])
            print(f"单词截断: {word_count}")

    print(f"\n最终结果长度: {len(cleaned)}")
    print(f"最终结果:\n{cleaned[:200]}...")

    result = cleaned

print("\n" + "="*60)
print("最终结果")
print("="*60)
print(f"结果长度: {len(result)}")
print(f"结果内容: '{result[:100]}...'")
print(f"是否为空: {not result}")
