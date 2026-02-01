#!/usr/bin/env python
"""使用 common_utils 中的 count_words 测试"""

import sys
sys.path.insert(0, '/Users/zorro/project/doc4llm')

from pathlib import Path
import re
from doc4llm.doc_rag.searcher.common_utils import count_words, clean_context_from_urls

BASE_DIR = "/Users/zorro/project/md_docs_base"
DOC_SET = "Claude_Code_Docs@latest/Data usage"
content_file = Path(BASE_DIR) / DOC_SET / "docContent.md"

lines = content_file.read_text(encoding="utf-8").split("\n")

# 第15行的上下文
match_line = 15
match_idx = match_line - 1  # 14
context_size = 2

start_idx = max(0, match_idx - context_size)  # 12
end_idx = min(len(lines), match_idx + context_size + 1)  # 17

print(f"match_line={match_line}")
print(f"start_idx={start_idx}, end_idx={end_idx}")
print()

# 收集非空行
context_lines = []
for i in range(start_idx, end_idx):
    line = lines[i].strip()
    line = re.sub(r"^--+\s*", "", line)
    if line:
        context_lines.append(line)

print("context_lines:")
for i, line in enumerate(context_lines):
    print(f"  [{i}] {line[:60]}...")
print()

# 使用 common_utils 中的函数
context_text = "\n".join(context_lines)
print(f"原始文本长度: {len(context_text)}")
print()

# 清理 URL
cleaned_text = clean_context_from_urls(context_text)
print(f"清理URL后长度: {len(cleaned_text)}")
print()

# 统计单词
word_count = count_words(cleaned_text)
print(f"count_words 结果: {word_count}")
print()

# 对比简单 split
simple_count = len(cleaned_text.split())
print(f"简单 split 结果: {simple_count}")
print()

# 分析差异
print("="*60)
print("分析差异")
print("="*60)
print(f"count_words 移除标点后再分词")
print(f"让我看看清理后的文本:")
print(f"'{cleaned_text[:200]}...'")
print()

# 检查标点符号的影响
punctuation_removed = re.sub(r"[^\w\s]", "", cleaned_text)
print(f"移除标点后: '{punctuation_removed[:200]}...'")
punctuation_words = punctuation_removed.split()
print(f"移除标点后的词数: {len(punctuation_words)}")
