#!/usr/bin/env python
"""测试 ContentSearcher 使用关键词 'transcript' 的搜索结果。"""

import json
from pathlib import Path

# 导入 ContentSearcher
import sys
sys.path.insert(0, str(Path(__file__).parent / "doc4llm"))
from doc4llm.doc_rag.searcher.content_searcher import ContentSearcher

# 知识库根目录
BASE_DIR = "/Users/zorro/project/md_docs_base"
DOC_SET = "Claude_Code_Docs@latest/Data usage"

def main():
    # 创建 ContentSearcher，使用 "transcript" 作为 domain_nouns
    searcher = ContentSearcher(
        base_dir=BASE_DIR,
        domain_nouns=["transcript"],
        max_results=20,
        context_lines=100,
        debug=True,
    )

    # 执行搜索
    queries = ["transcript"]
    doc_sets = [DOC_SET]

    print("=" * 80)
    print(f"搜索关键词: transcript")
    print(f"文档集: {DOC_SET}")
    print("=" * 80)

    results = searcher.search(queries, doc_sets)

    print(f"\n找到 {len(results)} 条结果:\n")

    for i, result in enumerate(results, 1):
        print(f"--- 结果 {i} ---")
        print(f"doc_set: {result['doc_set']}")
        print(f"page_title: {result['page_title']}")
        print(f"heading: {result['heading']}")
        print(f"toc_path: {result['toc_path']}")
        print(f"source_file: {result['source_file']}")
        print(f"match_line_num: {result['match_line_num']}")
        print(f"related_context:\n{result['related_context']}")
        print()

    # 保存结果到 JSON 文件
    output_file = Path(__file__).parent / "transcript_search_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到: {output_file}")

    return results

if __name__ == "__main__":
    main()
