"""
Test for DocSearcherAPI search interface.

Tests the search functionality with sample data input.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set base directory from sample data
SAMPLE_BASE_DIR = os.path.expanduser("~/project/md_docs_base")

# Knowledge base path - point to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Sample input data from user
SAMPLE_INPUT = {
    "query": [
        "claude code skill hook script output to context",
        "how to pass script output to claude code context",
        "claude code skill read script content integration",
        "claude code skill script execution context injection",
        "claude code skill 脚本 上下文 集成",
        "claude code skill execute script feed data context",
        "how to integrate script output in claude code skill",
        "claude code skill context hook tutorial",
        "claude code skill 脚本 读取 hook 上下文",
        "script output integration claude code skill guide"
    ],
    "target_doc_sets": [
        "Claude_Code_Docs@latest"
    ],
    "domain_nouns": [
        "skill",
        "script",
        "context"
    ],
    "predicate_verbs": [
        "hook",
        "read",
        "execute",
        "integrate",
        "feed",
        "pass",
        "inject"
    ],
    "reranker_threshold": 0.62,
    "scene": "faithful_how_to",
    "base_dir": SAMPLE_BASE_DIR,
    "reranker": True,
    "json": True
}


def test_search_basic():
    """Test basic search functionality without reranker."""
    from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

    searcher = DocSearcherAPI(
        base_dir=SAMPLE_INPUT["base_dir"],
        reranker_enabled=SAMPLE_INPUT["reranker"],
        reranker_threshold=SAMPLE_INPUT["reranker_threshold"],
        domain_nouns=SAMPLE_INPUT["domain_nouns"],
        predicate_verbs=SAMPLE_INPUT["predicate_verbs"],
    )

    result = searcher.search(
        query=SAMPLE_INPUT["query"],
        target_doc_sets=SAMPLE_INPUT["target_doc_sets"],
    )

    print("=" * 60)
    print("Test: Basic Search (reranker=False)")
    print("=" * 60)
    print(f"Success: {result.get('success')}")
    print(f"Doc Sets Found: {result.get('doc_sets_found')}")
    print(f"Results Count: {len(result.get('results', []))}")
    print(f"Fallback Used: {result.get('fallback_used')}")
    print(f"Message: {result.get('message')}")

    if result.get('results'):
        print(f"\nTop Results:")
        for i, page in enumerate(result['results'][:5], 1):
            print(f"  {i}. {page.get('page_title', 'N/A')}")
            headings = page.get('headings', [])
            for h in headings[:3]:
                print(f"     - {h.get('text', 'N/A')[:60]}...")

    print()
    return result


def test_search_with_single_query():
    """Test search with a single query string."""
    from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

    searcher = DocSearcherAPI(
        base_dir=SAMPLE_INPUT["base_dir"],
        reranker_enabled=False,
    )

    single_query = "claude code skill hook script output to context"
    result = searcher.search(
        query=single_query,
        target_doc_sets=SAMPLE_INPUT["target_doc_sets"],
    )

    print("=" * 60)
    print("Test: Single Query Search")
    print("=" * 60)
    print(f"Query: {single_query}")
    print(f"Success: {result.get('success')}")
    print(f"Results Count: {len(result.get('results', []))}")
    print()
    return result


def test_search_with_reranker():
    """Test search with reranker enabled."""
    from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

    # Only run this test if reranker is requested
    if not SAMPLE_INPUT["reranker"]:
        print("=" * 60)
        print("Test: Search with Reranker - SKIPPED (reranker=False in sample)")
        print("=" * 60)
        return None

    searcher = DocSearcherAPI(
        base_dir=SAMPLE_INPUT["base_dir"],
        reranker_enabled=True,
        reranker_threshold=SAMPLE_INPUT["reranker_threshold"],
        embedding_provider="ms",  # ModelScope provider
    )

    result = searcher.search(
        query=SAMPLE_INPUT["query"],
        target_doc_sets=SAMPLE_INPUT["target_doc_sets"],
    )

    print("=" * 60)
    print("Test: Search with Reranker (reranker=True)")
    print("=" * 60)
    print(f"Success: {result.get('success')}")
    print(f"Results Count: {len(result.get('results', []))}")

    if result.get('results'):
        print(f"\nTop Results with Rerank Scores:")
        for i, page in enumerate(result['results'][:5], 1):
            rerank_sim = page.get('rerank_sim', 'N/A')
            print(f"  {i}. {page.get('page_title', 'N/A')} (rerank_sim: {rerank_sim})")

    print()
    return result


def test_search_format_output():
    """Test output formatting methods."""
    from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

    searcher = DocSearcherAPI(
        base_dir=SAMPLE_INPUT["base_dir"],
        reranker_enabled=SAMPLE_INPUT["reranker"],
    )

    result = searcher.search(
        query=SAMPLE_INPUT["query"],
        target_doc_sets=SAMPLE_INPUT["target_doc_sets"],
    )

    print("=" * 60)
    print("Test: Output Formatting")
    print("=" * 60)

    # Test structured output
    structured = searcher.format_structured_output(
        result,
        queries=SAMPLE_INPUT["query"],
        reranker_enabled=SAMPLE_INPUT["reranker"]
    )
    print("Structured Output (JSON):")
    print(structured[:500] + "..." if len(structured) > 500 else structured)
    print()
    return result


def test_search_invalid_docset():
    """Test search with non-existent doc-set."""
    from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

    searcher = DocSearcherAPI(
        base_dir=SAMPLE_INPUT["base_dir"],
        reranker_enabled=False,
    )

    result = searcher.search(
        query=SAMPLE_INPUT["query"],
        target_doc_sets=["NonExistent_DocSet@latest"],
    )

    print("=" * 60)
    print("Test: Non-existent Doc-set")
    print("=" * 60)
    print(f"Success: {result.get('success')}")
    print(f"Message: {result.get('message')}")
    print()
    return result


def test_search_auto_detect_docset():
    """Test search with auto-detected doc-sets."""
    from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

    searcher = DocSearcherAPI(
        base_dir=SAMPLE_INPUT["base_dir"],
        reranker_enabled=False,
    )

    # Search without specifying target_doc_sets
    result = searcher.search(query="claude code hook script")

    print("=" * 60)
    print("Test: Auto-detect Doc-sets")
    print("=" * 60)
    print(f"Doc Sets Found: {result.get('doc_sets_found')}")
    print(f"Results Count: {len(result.get('results', []))}")
    print()
    return result


def run_all_tests():
    """Run all test cases."""
    print("\n" + "=" * 60)
    print("DocSearcherAPI Search Interface Tests")
    print("=" * 60)
    print(f"Base Directory: {SAMPLE_INPUT['base_dir']}")
    print(f"Target Doc-sets: {SAMPLE_INPUT['target_doc_sets']}")
    print(f"Reranker Enabled: {SAMPLE_INPUT['reranker']}")
    print()

    tests = [
        test_search_basic,
        test_search_with_single_query,
        test_search_with_reranker,
        test_search_format_output,
        test_search_invalid_docset,
        test_search_auto_detect_docset,
    ]

    results = {}
    for test in tests:
        try:
            results[test.__name__] = test()
        except Exception as e:
            print(f"Error in {test.__name__}: {e}")
            results[test.__name__] = {"error": str(e)}

    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, result in results.items():
        if result is None:
            print(f"  {name}: SKIPPED")
        elif "error" in result:
            print(f"  {name}: FAILED - {result['error']}")
        else:
            print(f"  {name}: {'PASSED' if result.get('success') else 'NO RESULTS'}")


if __name__ == "__main__":
    run_all_tests()
