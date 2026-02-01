#!/usr/bin/env python
"""测试 ContentSearcher related_context 为空的问题"""

import sys
sys.path.insert(0, '/Users/zorro/project/doc4llm')

from doc4llm.doc_rag.searcher.content_searcher import ContentSearcher

# 测试用例
BASE_DIR = "/Users/zorro/project/md_docs_base"
DOMAIN_NOUNS = ["transcript"]
DOC_SETS = ["Claude_Code_Docs@latest/Data usage"]

def test_content_searcher():
    """测试 ContentSearcher 并检查 related_context"""
    searcher = ContentSearcher(
        base_dir=BASE_DIR,
        domain_nouns=DOMAIN_NOUNS,
        max_results=20,
        context_lines=100,
        debug=True  # 启用调试输出
    )

    queries = ["Development Partner Program"]
    results = searcher.search(queries, DOC_SETS)

    print("\n" + "="*60)
    print("搜索结果：")
    print("="*60)

    for i, result in enumerate(results, 1):
        print(f"\n结果 {i}:")
        print(f"  doc_set: {result.get('doc_set')}")
        print(f"  page_title: {result.get('page_title')}")
        print(f"  heading: {result.get('heading')}")
        print(f"  match_line_num: {result.get('match_line_num')}")
        print(f"  source: {result.get('source')}")
        print(f"  related_context: '{result.get('related_context')}'")
        print(f"  related_context length: {len(result.get('related_context', ''))}")

        # 检查 related_context
        if not result.get('related_context'):
            print("  !!! WARNING: related_context 为空 !!!")

    print("\n" + "="*60)
    print(f"总结果数: {len(results)}")
    print("="*60)

    return results

if __name__ == "__main__":
    test_content_searcher()
