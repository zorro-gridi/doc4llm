#!/usr/bin/env python
"""Test script for FALLBACK_2 fix verification."""
import sys
sys.path.insert(0, '/Users/zorro/project/doc4llm')

from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

def test_fallback2_parallel_mode():
    """Test that FALLBACK_2 results are not overwritten in PARALLEL mode."""
    print("=" * 60)
    print("Testing FALLBACK_2 in PARALLEL mode")
    print("=" * 60)

    api = DocSearcherAPI(
        base_dir="doc4llm/md_docs",
        debug=True,
        domain_nouns=["transcript"]  # 设置 domain_nouns 触发 FALLBACK_2
    )

    # Enable parallel mode
    api.fallback_mode = "parallel"

    query = "transcript"
    doc_sets = ["Claude_Code_Docs@latest"]

    print(f"\nQuery: {query}")
    print(f"Doc sets: {doc_sets}")
    print(f"Fallback mode: {api.fallback_mode}")
    print(f"Domain nouns: {api.domain_nouns}")
    print()

    result = api.search(query, doc_sets)

    print()
    print("=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    print(f"Success: {result.get('success')}")
    print(f"Results count: {len(result.get('results', []))}")
    print(f"Fallback used: {result.get('fallback_used')}")
    print(f"Message: {result.get('message')}")

    if result.get('results'):
        print(f"\nTop results:")
        for i, r in enumerate(result['results'][:5], 1):
            print(f"  {i}. {r.get('page_title', 'N/A')} (doc_set: {r.get('doc_set', 'N/A')})")
            if r.get('headings'):
                for h in r['headings'][:2]:
                    print(f"     - {h.get('text', 'N/A')}")
                    # 检查是否有 related_context
                    if h.get('related_context'):
                        ctx = h['related_context'][:100] + "..." if len(h['related_context']) > 100 else h['related_context']
                        print(f"       Context: {ctx}")

    # Verify FALLBACK_2 was used
    fallback_used = result.get('fallback_used') or ''
    if 'FALLBACK_2' in fallback_used:
        print("\n[PASS] FALLBACK_2 was used!")
    else:
        print(f"\n[WARN] FALLBACK_2 was NOT used. fallback_used={fallback_used}")

    return result

if __name__ == "__main__":
    test_fallback2_parallel_mode()
