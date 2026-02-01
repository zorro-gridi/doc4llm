#!/usr/bin/env python
"""在 _extract_context 中添加调试打印"""

import sys
sys.path.insert(0, '/Users/zorro/project/doc4llm')

# 直接修改方法添加调试
from pathlib import Path
import re
from typing import List

BASE_DIR = "/Users/zorro/project/md_docs_base"
DOC_SET = "Claude_Code_Docs@latest/Data usage"
content_file = Path(BASE_DIR) / DOC_SET / "docContent.md"

lines = content_file.read_text(encoding="utf-8").split("\n")

def count_words(text):
    return len(text.split())

def clean_context_from_urls(context):
    return re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", context)

def truncate_symmetric(lines: List[str], match_idx: int, max_words: int) -> str:
    """带调试的截断函数"""
    print(f"\n  [_truncate_symmetric] 调用")
    print(f"    lines数量: {len(lines)}")
    print(f"    match_idx: {match_idx}")
    print(f"    max_words: {max_words}")

    if not lines:
        print(f"    返回空: lines为空")
        return ""

    current_text = "\n".join(lines)
    word_count = count_words(current_text)
    print(f"    初始单词数: {word_count}")

    if word_count <= max_words:
        print(f"    返回: 单词数在限制内")
        return current_text

    left_idx = 0
    right_idx = len(lines) - 1
    iteration = 0

    while word_count > max_words and left_idx < right_idx:
        iteration += 1
        if (left_idx + right_idx) % 2 == 0:
            left_idx += 1
            action = "剔除左边"
        else:
            right_idx -= 1
            action = "剔除右边"

        current_lines = lines[left_idx : right_idx + 1]
        current_text = "\n".join(current_lines)
        word_count = count_words(current_text)

        print(f"    迭代{iteration}: {action} -> left_idx={left_idx}, right_idx={right_idx}, words={word_count}")

        if left_idx >= right_idx:
            break

    print(f"    最终: left_idx={left_idx}, right_idx={right_idx}")

    # 边界情况
    if word_count > max_words and current_text:
        words = current_text.split()
        if len(words) > max_words:
            current_text = " ".join(words[:max_words])
            word_count = len(words[:max_words])
            print(f"    截断单词到: {word_count}")

    print(f"    返回结果 (长度={len(current_text)})")
    return current_text


def extract_context_debug(lines: List[str], match_line: int, context_size: int = 2) -> str:
    """带调试的 _extract_context"""
    if not lines:
        return ""

    if match_line < 1 or match_line > len(lines):
        return ""

    match_idx = match_line - 1
    max_words = 100
    max_context_size = 50
    expand_step = 5

    current_size = context_size
    result = ""

    print(f"\n[_extract_context] match_line={match_line}, match_idx={match_idx}")

    while current_size <= max_context_size:
        start_idx = max(0, match_idx - current_size)
        end_idx = min(len(lines), match_idx + current_size + 1)

        print(f"\n  current_size={current_size}: start={start_idx}, end={end_idx}")

        context_lines = []
        for i in range(start_idx, end_idx):
            line = lines[i].strip()
            line = re.sub(r"^--+\s*", "", line)
            if line:
                context_lines.append((i+1, line[:30] + "..." if len(line) > 30 else line))

        print(f"    过滤后: {len(context_lines)} 行")
        for ln, lc in context_lines:
            print(f"      行{ln}: {lc}")

        context_text = "\n".join([l[1] for l in context_lines])
        context_text = clean_context_from_urls(context_text)
        word_count = count_words(context_text)

        print(f"    单词数: {word_count}/{max_words}")

        if word_count <= max_words:
            print(f"    ✓ 通过，返回结果")
            result = context_text
            break

        if current_size < max_context_size:
            current_size += expand_step
            print(f"    ✗ 超过，扩展到 {current_size}")
        else:
            print(f"    ✗ 达到最大，调用截断")
            # 计算 match_idx 在 context_lines 中的位置
            # 需要找到匹配行在过滤后列表中的索引
            match_pos = None
            for idx, (ln, _) in enumerate(context_lines):
                if ln == match_line:
                    match_pos = idx
                    break

            print(f"    匹配行 {match_line} 在 context_lines 中的索引: {match_pos}")

            result = truncate_symmetric(
                [l[1] for l in context_lines],
                match_pos if match_pos is not None else 0,
                max_words
            )
            break

    print(f"\n[_extract_context] 最终返回: '{result[:50]}...' (长度={len(result)})")
    return result

# 测试
print("="*60)
print("测试 _extract_context (第15行)")
print("="*60)
result = extract_context_debug(lines, 15)
print(f"\n最终结果: '{result}'")
