#!/usr/bin/env python
"""详细调试 _extract_context 方法第15行为空的问题"""

import sys
import re
sys.path.insert(0, '/Users/zorro/project/doc4llm')

from pathlib import Path
from doc4llm.doc_rag.searcher.content_searcher import ContentSearcher

BASE_DIR = "/Users/zorro/project/md_docs_base"
DOC_SET = "Claude_Code_Docs@latest/Data usage"
content_file = Path(BASE_DIR) / DOC_SET / "docContent.md"

lines = content_file.read_text(encoding="utf-8").split("\n")

searcher = ContentSearcher(
    base_dir=BASE_DIR,
    domain_nouns=["transcript"],
    max_results=20,
    context_lines=100,
    debug=True
)

# 测试第15行，添加详细调试
print("="*60)
print("详细调试 match_line=15")
print("="*60)

match_line = 15
context_size = 2
max_words = 100
max_context_size = 50
expand_step = 5
match_idx = match_line - 1

print(f"match_idx: {match_idx}")
print(f"context_size: {context_size}")
print()

current_size = context_size

while current_size <= max_context_size:
    print(f"--- current_size={current_size} ---")

    start_idx = max(0, match_idx - current_size)
    end_idx = min(len(lines), match_idx + current_size + 1)

    print(f"start_idx={start_idx}, end_idx={end_idx}")

    context_lines = []
    for i in range(start_idx, end_idx):
        line = lines[i]
        original = line
        line_stripped = line.strip()
        line_after_dash = re.sub(r"^--+\s*", "", line_stripped)

        print(f"  行{i+1}: strip='{line_stripped[:30]}...' -> after_dash='{line_after_dash[:30]}...' -> bool={bool(line_after_dash)}")

        if line_after_dash:
            context_lines.append(line_after_dash)

    print(f"context_lines count: {len(context_lines)}")

    # 清理 URL 并统计单词
    context_text = "\n".join(context_lines)
    print(f"原始 context_text 长度: {len(context_text)}")

    context_text_clean = searcher._clean_context_from_urls(context_text)
    print(f"清理 URL 后长度: {len(context_text_clean)}")

    word_count = searcher._count_words(context_text_clean)
    print(f"单词数: {word_count} (限制: {max_words})")

    if word_count <= max_words:
        print(f"✓ 通过检查，返回结果")
        print(f"最终结果: '{context_text_clean[:100]}...'")
        break

    if current_size < max_context_size:
        current_size += expand_step
        print(f"  扩展到 {current_size}")
    else:
        print(f"  达到最大，进行截断")
        break

print("\n" + "="*60)
print("对比: 第19行为什么正常")
print("="*60)

match_line = 19
match_idx = match_line - 1
current_size = context_size

while current_size <= max_context_size:
    start_idx = max(0, match_idx - current_size)
    end_idx = min(len(lines), match_idx + current_size + 1)

    context_lines = []
    for i in range(start_idx, end_idx):
        line = lines[i]
        line_after_dash = re.sub(r"^--+\s*", "", line.strip())
        if line_after_dash:
            context_lines.append(line_after_dash)

    context_text = "\n".join(context_lines)
    context_text_clean = searcher._clean_context_from_urls(context_text)
    word_count = searcher._count_words(context_text_clean)

    print(f"current_size={current_size}: 单词数={word_count}, 行数={len(context_lines)}")

    if word_count <= max_words:
        print(f"✓ 通过检查")
        break

    if current_size < max_context_size:
        current_size += expand_step
