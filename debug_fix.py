#!/usr/bin/env python
"""验证并修复 bug"""

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

print("="*60)
print("问题分析")
print("="*60)
print(f"current_size 序列: 2, 7, 12, 17, 22, 27, 32, 37, 42, 47, 52")
print(f"max_context_size = 50")
print()
print("当 current_size=47 时，47 < 50，扩展到 52")
print("当 current_size=52 时，52 > 50，循环退出")
print("result 从未设置，返回空字符串！")
print()

# 模拟修复后的逻辑
print("="*60)
print("修复方案：将 <= 改为 <")
print("="*60)

context_size = 2
max_words = 100
max_context_size = 50
expand_step = 5

current_size = context_size
result = ""

# 修复：将 while current_size <= max_context_size 改为 while current_size < max_context_size
while current_size < max_context_size:
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

    if word_count <= max_words:
        result = cleaned_text
        print(f"current_size={current_size}: 单词数={word_count} <= 100，通过！")
        break

    current_size += expand_step
    print(f"current_size={current_size - expand_step} -> {current_size}: 单词数={word_count} > 100，扩展")

if not result:
    print(f"\ncurrent_size={current_size} >= {max_context_size}，调用截断")
    # 收集所有行进行截断
    context_lines_all = []
    for i in range(len(lines)):
        line = lines[i].strip()
        line = re.sub(r"^--+\s*", "", line)
        if line:
            context_lines_all.append(line)

    # 找到匹配行在 context_lines_all 中的位置
    match_pos = None
    for idx, line in enumerate(context_lines_all):
        # 检查这一行是否包含匹配行的部分内容
        if str(match_line) in line or f"行{match_line}" in line:
            # 实际上我们需要找原始行号
            pass

    # 简化：直接截断
    left_idx = 0
    right_idx = len(context_lines_all) - 1
    current_text = "\n".join(context_lines_all)
    word_count = count_words(clean_context_from_urls(current_text))

    while word_count > max_words and left_idx < right_idx:
        if (left_idx + right_idx) % 2 == 0:
            left_idx += 1
        else:
            right_idx -= 1
        current_lines = context_lines_all[left_idx:right_idx+1]
        current_text = "\n".join(current_lines)
        word_count = count_words(clean_context_from_urls(current_text))

    result = clean_context_from_urls(current_text)

print(f"\n修复后结果长度: {len(result)}")
print(f"修复后结果:\n{result[:200]}...")
