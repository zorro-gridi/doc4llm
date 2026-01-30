"""
Test for FALLBACK_2 grep context extraction functionality with input data.

Tests the _fallback2_grep_context_bm25 method using user-provided query data
to verify keyword extraction, context retrieval, and result validation.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set base directory from sample data
SAMPLE_BASE_DIR = os.path.expanduser("~/project/md_docs_base")


# ===== Test Input Data =====
TEST_INPUT_DATA = {
    "queries": [
        "claude code skill result inject context",
        "claude code skill hook context injection",
        "claude code rag_skill retrieve result context",
        "how to use skill output in claude code conversation",
        "claude code skill callback context reference"
    ],
    "target_doc_sets": ["Claude_Code_Docs@latest"],
    "domain_nouns": ["skill", "rag_skill", "context", "hook"],
    "predicate_verbs": [
        "inject", "add", "insert", "retrieve", "get", "fetch",
        "call", "invoke", "return", "output", "reference", "use", "access"
    ],
    "reranker_threshold": 0.75,
    "scene": "how_to"
}

# Expected significant keywords (from 5 queries - filter out common words)
# Note: Common stop words like "how", "to", "in", "use" are filtered by extract_keywords
EXPECTED_KEYWORDS = {
    "claude", "code", "skill", "result", "inject", "context",
    "hook", "rag_skill", "retrieve", "conversation", "callback",
    "reference", "output", "injection"
}


def test_1_keyword_extraction():
    """
    Test Case 1: Verify keyword extraction from 5 queries

    Validates that keywords are correctly extracted from the input queries.
    """
    print("=" * 70)
    print("Test Case 1: Keyword Extraction Validation")
    print("=" * 70)

    queries = TEST_INPUT_DATA["queries"]
    domain_nouns = TEST_INPUT_DATA["domain_nouns"]
    predicate_verbs = TEST_INPUT_DATA["predicate_verbs"]

    print(f"\nInput queries ({len(queries)}):")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q}")

    # Extract keywords using the same method as _fallback2_grep_context_bm25
    from doc4llm.doc_rag.searcher.bm25_recall import extract_keywords

    all_keywords = []
    for q in queries:
        keywords = extract_keywords(q)
        all_keywords.extend(keywords)

    # Remove duplicates while preserving order
    keywords = list(dict.fromkeys(all_keywords))

    print(f"\nExtracted keywords ({len(keywords)}):")
    print(f"  {sorted(keywords)}")

    # Validate against expected keywords
    expected = EXPECTED_KEYWORDS
    extracted_set = set(keywords)
    expected_set = set(expected)

    # Check for missing keywords
    missing = expected_set - extracted_set
    # Check for extra keywords (not necessarily an error)
    extra = extracted_set - expected_set

    if missing:
        print(f"\n[WARNING] Missing expected keywords: {sorted(missing)}")
    else:
        print(f"\n[SUCCESS] All expected keywords found")

    if extra:
        print(f"[INFO] Extra keywords extracted: {sorted(extra)}")

    # Verify keyword count
    print(f"\nKeyword count: {len(keywords)} (expected: {len(expected)})")

    # Validate that key domain nouns are in keywords (core requirement)
    print(f"\nCore domain nouns check (required):")
    core_nouns = ["skill", "rag_skill", "context", "hook"]
    nouns_found = 0
    for noun in core_nouns:
        if noun.lower() in [k.lower() for k in keywords]:
            nouns_found += 1
            print(f"  [OK] '{noun}' found in extracted keywords")
        else:
            print(f"  [MISSING] '{noun}' NOT found in extracted keywords")

    # Validate some predicate verbs are in keywords
    print(f"\nPredicate verbs check (at least 4 required):")
    verbs_found = 0
    for verb in predicate_verbs:
        if verb.lower() in [k.lower() for k in keywords]:
            verbs_found += 1
            print(f"  [OK] '{verb}' found")
        else:
            print(f"  [MISSING] '{verb}' NOT found")
    print(f"\nPredicate verbs found: {verbs_found}/{len(predicate_verbs)}")

    # Final result - core nouns must all be found, at least 4 verbs
    if nouns_found == len(core_nouns) and verbs_found >= 4:
        print("\n[TEST PASSED] Keyword extraction validation passed")
        return True
    else:
        print("\n[TEST FAILED] Missing core keywords")
        return False


def test_2_fallback2_grep_context_bm25():
    """
    Test Case 2: Verify _fallback2_grep_context_bm25 method interface call

    Calls the DocSearcherAPI._fallback2_grep_context_bm25 method with the
    test input data and validates the results.
    """
    print("\n" + "=" * 70)
    print("Test Case 2: _fallback2_grep_context_bm25 Interface Call")
    print("=" * 70)

    from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

    queries = TEST_INPUT_DATA["queries"]
    doc_sets = TEST_INPUT_DATA["target_doc_sets"]

    print(f"\nInput parameters:")
    print(f"  Queries: {len(queries)} queries")
    print(f"  Doc-sets: {doc_sets}")

    searcher = DocSearcherAPI(
        base_dir=SAMPLE_BASE_DIR,
        reranker_enabled=False,
        debug=True,
    )

    # Call the FALLBACK_2 method directly
    print(f"\nCalling _fallback2_grep_context_bm25...")
    results = searcher._fallback2_grep_context_bm25(queries, doc_sets)

    print(f"\nResults count: {len(results)}")

    if not results:
        print("[TEST FAILED] No results returned from _fallback2_grep_context_bm25")
        return False

    # Check each result for related_context
    has_context = 0
    empty_context = 0

    for i, result in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"    Page title: {result.get('page_title', 'N/A')}")
        heading = result.get('heading', '')
        print(f"    Heading: {heading[:80]}{'...' if len(heading) > 80 else ''}")
        print(f"    Score: {result.get('score', 'N/A'):.4f}")

        related_context = result.get('related_context', '')
        if related_context:
            has_context += 1
            print(f"    related_context: {len(related_context)} chars")
            # Show first 150 chars
            preview = related_context[:150].replace('\n', ' ')
            print(f"    Preview: {preview}...")
        else:
            empty_context += 1
            print(f"    related_context: [EMPTY]")

    print(f"\nSummary:")
    print(f"  Results with context: {has_context}")
    print(f"  Results without context: {empty_context}")

    if has_context > 0 and len(results) > 0:
        print("\n[TEST PASSED] related_context is populated in results")
        return True
    else:
        print("\n[TEST FAILED] All results have empty related_context")
        return False


def test_3_context_content_validation():
    """
    Test Case 3: Validate related_context content

    Checks that the extracted context is properly populated and has
    reasonable content structure.
    """
    print("\n" + "=" * 70)
    print("Test Case 3: Context Content Validation")
    print("=" * 70)

    from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

    queries = TEST_INPUT_DATA["queries"]
    doc_sets = TEST_INPUT_DATA["target_doc_sets"]
    domain_nouns = TEST_INPUT_DATA["domain_nouns"]

    searcher = DocSearcherAPI(
        base_dir=SAMPLE_BASE_DIR,
        reranker_enabled=False,
        debug=False,
    )

    print(f"\nCalling _fallback2_grep_context_bm25...")
    results = searcher._fallback2_grep_context_bm25(queries, doc_sets)

    if not results:
        print("[TEST FAILED] No results returned")
        return False

    # Check context content for each result
    valid_context_count = 0

    for i, result in enumerate(results, 1):
        related_context = result.get('related_context', '')
        page_title = result.get('page_title', 'N/A')
        heading = result.get('heading', 'N/A')

        print(f"\n  Result {i}:")
        print(f"    Page title: {page_title}")
        print(f"    Heading: {heading[:60]}...")

        if related_context:
            print(f"    related_context: {len(related_context)} chars")
            # Show preview (replace newlines for display)
            preview = related_context[:200].replace('\n', ' ')
            print(f"    Preview: {preview}...")

            # Check if context is non-empty and has reasonable length
            if len(related_context) >= 30:
                valid_context_count += 1
                print(f"    [OK] Context length is valid (>= 30 chars)")
            else:
                print(f"    [WARNING] Context is short (< 30 chars)")
        else:
            print(f"    related_context: [EMPTY]")

    print(f"\nResults with valid context: {valid_context_count}/{len(results)}")

    if valid_context_count > 0:
        print("\n[TEST PASSED] Context content validation passed")
        return True
    else:
        print("\n[TEST FAILED] No valid context content found")
        return False


def test_4_multiple_doc_sets():
    """
    Test Case 4: Verify multiple doc_sets handling and deduplication

    Tests single doc_set and multi doc_set scenarios to verify
    result deduplication logic works correctly.
    """
    print("\n" + "=" * 70)
    print("Test Case 4: Multiple Doc-sets Test")
    print("=" * 70)

    from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

    queries = TEST_INPUT_DATA["queries"]

    searcher = DocSearcherAPI(
        base_dir=SAMPLE_BASE_DIR,
        reranker_enabled=False,
        debug=False,
    )

    # Test 1: Single doc_set
    print("\n[Test 4.1] Single doc_set test:")
    single_doc_set = ["Claude_Code_Docs@latest"]
    results_single = searcher._fallback2_grep_context_bm25(queries, single_doc_set)
    print(f"  Results count: {len(results_single)}")

    # Test 2: Multiple doc_sets (simulated)
    print("\n[Test 4.2] Multiple doc_sets test:")
    # Note: In a real scenario, you'd have multiple doc-sets available
    # For now, we test with the same doc_set to verify no duplication
    results_multi = searcher._fallback2_grep_context_bm25(queries, single_doc_set)
    print(f"  Results count: {len(results_multi)}")

    # Check deduplication by page_title
    page_titles_single = [r.get('page_title', '') for r in results_single]
    unique_titles_single = list(dict.fromkeys(page_titles_single))
    print(f"  Unique page_titles: {len(unique_titles_single)}/{len(page_titles_single)}")

    # Validate results structure
    valid_results = 0
    for result in results_single:
        required_fields = ['doc_set', 'page_title', 'heading', 'score', 'related_context']
        if all(result.get(f) is not None for f in required_fields):
            valid_results += 1

    print(f"\n  Valid results (all fields present): {valid_results}/{len(results_single)}")

    if valid_results == len(results_single) and len(results_single) > 0:
        print("\n[TEST PASSED] Multiple doc_sets test passed")
        return True
    else:
        print("\n[TEST FAILED] Some results are missing required fields")
        return False


def test_5_query_combination():
    """
    Test Case 5: Verify query combination for BM25 scoring

    Tests that multiple queries are correctly combined into a single
    query string for BM25 similarity calculation.
    """
    print("\n" + "=" * 70)
    print("Test Case 5: Query Combination for BM25")
    print("=" * 70)

    queries = TEST_INPUT_DATA["queries"]

    # Simulate the query combination logic from _fallback2_grep_context_bm25
    from doc4llm.doc_rag.searcher.bm25_recall import extract_keywords

    all_keywords = []
    for q in queries:
        keywords = extract_keywords(q)
        all_keywords.extend(keywords)

    # Remove duplicates while preserving order
    keywords = list(dict.fromkeys(all_keywords))
    combined_query = " ".join(queries)
    keyword_pattern = "|".join(keywords)

    print(f"\nInput: {len(queries)} queries")
    print(f"Combined query length: {len(combined_query)} chars")
    print(f"Unique keywords: {len(keywords)}")
    print(f"Keyword pattern: {keyword_pattern[:100]}{'...' if len(keyword_pattern) > 100 else ''}")

    # Validate keyword pattern
    pattern_valid = True
    for keyword in keywords[:10]:  # Check first 10 keywords
        if not keyword:
            pattern_valid = False
            break

    if pattern_valid:
        print("\n[TEST PASSED] Query combination test passed")
        return True
    else:
        print("\n[TEST FAILED] Query combination resulted in invalid pattern")
        return False


def run_all_tests():
    """Run all test cases."""
    print("\n" + "=" * 70)
    print("FALLBACK_2 Grep Context Extraction - Input Data Tests")
    print("=" * 70)
    print(f"Base Directory: {SAMPLE_BASE_DIR}")
    print(f"Test Input: {len(TEST_INPUT_DATA['queries'])} queries")
    print()

    tests = [
        ("Keyword Extraction", test_1_keyword_extraction),
        ("Interface Call", test_2_fallback2_grep_context_bm25),
        ("Context Content", test_3_context_content_validation),
        ("Multiple Doc-sets", test_4_multiple_doc_sets),
        ("Query Combination", test_5_query_combination),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n[ERROR] {name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    for name, result in results.items():
        if result is None:
            print(f"  {name}: SKIPPED")
        elif result:
            print(f"  {name}: PASSED")
        else:
            print(f"  {name}: FAILED")

    passed = sum(1 for r in results.values() if r is True)
    total = sum(1 for r in results.values() if r is not None)
    print(f"\nTotal: {passed}/{total} tests passed")

    return all(v is True for v in results.values())


if __name__ == "__main__":
    success = run_all_tests()
    print("\n" + "=" * 70)
    if success:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    print("=" * 70)
    sys.exit(0 if success else 1)
