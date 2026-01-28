"""
Test script for TransformerMatcher.

验证 TransformerMatcher 的接口功能和语言自动检测能力。
"""

import sys
from doc4llm.tool.md_doc_retrieval import TransformerMatcher, TransformerConfig

from huggingface_hub import set_client_factory
import httpx

def create_proxy_client() -> httpx.Client:
    return httpx.Client(proxy=proxy)

set_client_factory(create_proxy_client)


def test_transformer_matcher_initialization():
    """Test TransformerMatcher initialization with default and custom config."""
    print("=== Initialization Test ===\n")

    # Test 1: Default configuration
    print("Test 1: Default configuration")
    try:
        matcher = TransformerMatcher()
        print(f"  Model (zh): {matcher.config.model_zh}")
        print(f"  Model (en): {matcher.config.model_en}")
        print(f"  Device: {matcher.config.device}")
        print(f"  Batch size: {matcher.config.batch_size}")
        print(f"  Lang threshold: {matcher.config.lang_threshold}")
        print("  PASSED: Default initialization successful\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False

    # Test 2: Custom configuration
    print("Test 2: Custom configuration")
    try:
        custom_config = TransformerConfig(
            model_zh="BAAI/bge-small-zh-v1.5",
            model_en="BAAI/bge-small-en-v1.5",
            device="cpu",
            batch_size=16,
            lang_threshold=0.5
        )
        custom_matcher = TransformerMatcher(config=custom_config)
        print(f"  Custom model (zh): {custom_matcher.config.model_zh}")
        print(f"  Custom model (en): {custom_matcher.config.model_en}")
        print(f"  Custom batch size: {custom_matcher.config.batch_size}")
        print("  PASSED: Custom initialization successful\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False

    return True


def test_transformer_matcher_rerank():
    """Test TransformerMatcher rerank method."""
    print("=== Rerank Method Test ===\n")

    matcher = TransformerMatcher()

    # Test 1: English queries
    print("Test 1: English query reranking")
    query = 'create rules'
    corpus = [
        'Create a plugin',
        'a plugin',
        'agents',
        'Create agents',
        'Rules'
    ]
    print(f"  Query: {query}")
    print(f"  Candidates: {corpus}")

    try:
        results = matcher.rerank(query, corpus)
        print("  Results (sorted by similarity):")
        for text, score in results:
            print(f"    {score:.4f} | {text}")
        print("  PASSED: English rerank successful\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False

    # Test 2: Chinese queries
    print("Test 2: Chinese query reranking")
    query_zh = '创建规则'
    corpus_zh = [
        '创建一个插件',
        '插件开发',
        '规则管理',
        '创建代理',
        '规则引擎'
    ]
    print(f"  Query: {query_zh}")
    print(f"  Candidates: {corpus_zh}")

    try:
        results_zh = matcher.rerank(query_zh, corpus_zh)
        print("  Results (sorted by similarity):")
        for text, score in results_zh:
            print(f"    {score:.4f} | {text}")
        print("  PASSED: Chinese rerank successful\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False

    # Test 3: Empty candidates
    print("Test 3: Empty candidates handling")
    try:
        results_empty = matcher.rerank("test", [])
        assert results_empty == [], f"Expected empty list, got {results_empty}"
        print("  PASSED: Empty candidates handled correctly\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False

    return True


def test_transformer_matcher_rerank_batch():
    """Test TransformerMatcher rerank_batch method."""
    print("=== Rerank Batch Method Test ===\n")

    matcher = TransformerMatcher()

    queries = ['create rules', 'agents']
    corpus = [
        'Create a plugin',
        'a plugin',
        'agents',
        'Create agents',
        'Rules'
    ]
    print(f"  Queries: {queries}")
    print(f"  Candidates: {corpus}")

    try:
        sim_matrix, returned_candidates = matcher.rerank_batch(queries, corpus)
        print(f"  Similarity matrix shape: {sim_matrix.shape}")
        print(f"  Returned candidates count: {len(returned_candidates)}")
        print("  Similarity matrix:")
        print(f"    {sim_matrix}")
        print("  PASSED: Batch rerank successful\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False

    # Test with Chinese queries
    print("Test: Chinese batch reranking")
    queries_zh = ['创建规则', '插件开发']
    corpus_zh = [
        '规则管理',
        '创建插件',
        '插件开发',
        '规则引擎'
    ]
    print(f"  Queries: {queries_zh}")
    print(f"  Candidates: {corpus_zh}")

    try:
        sim_matrix_zh, returned_candidates_zh = matcher.rerank_batch(queries_zh, corpus_zh)
        print(f"  Similarity matrix shape: {sim_matrix_zh.shape}")
        print("  Similarity matrix:")
        print(f"    {sim_matrix_zh}")
        print("  PASSED: Chinese batch rerank successful\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False

    # Test empty inputs
    print("Test: Empty inputs handling")
    try:
        empty_matrix, empty_candidates = matcher.rerank_batch([], corpus)
        assert empty_matrix.size == 0, f"Expected empty matrix, got {empty_matrix}"
        print("  PASSED: Empty queries handled correctly\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False

    return True


def test_language_detection():
    """Test TransformerMatcher language auto-detection."""
    print("=== Language Detection Test ===\n")

    matcher = TransformerMatcher()

    # Test cases for language detection
    test_cases = [
        ("Hello world", "en"),
        ("This is a test sentence", "en"),
        ("你好世界", "zh"),
        ("这是一个测试句子", "zh"),
        ("混合语言测试 English and 中文", "zh"),  # >30% Chinese chars
        ("Hello 中文 English", "en"),  # <30% Chinese chars
        ("", "en"),  # Empty string defaults to en
    ]

    all_passed = True
    for text, expected_lang in test_cases:
        detected_lang = matcher._detect_language(text)
        status = "PASSED" if detected_lang == expected_lang else "FAILED"
        if detected_lang != expected_lang:
            all_passed = False
        print(f"  [{status}] '{text[:30]}...' -> {detected_lang} (expected: {expected_lang})")

    if all_passed:
        print("  PASSED: All language detection tests passed\n")
    else:
        print("  FAILED: Some language detection tests failed\n")

    return all_passed


def test_mixed_language_rerank():
    """Test TransformerMatcher with mixed Chinese-English content."""
    print("=== Mixed Language Rerank Test ===\n")

    matcher = TransformerMatcher()

    # Test 1: Query in one language, candidates in both
    print("Test 1: Chinese query with mixed candidates")
    query = '如何创建插件'
    candidates = [
        'How to create a plugin',
        'Create a new agent',
        '如何创建规则',
        'Plugin installation guide',
        '规则管理方法'
    ]
    print(f"  Query: {query}")
    print(f"  Candidates: {candidates}")

    try:
        results = matcher.rerank(query, candidates)
        print("  Results (sorted by similarity):")
        for text, score in results:
            print(f"    {score:.4f} | {text}")
        # Verify results are sorted
        scores = [score for _, score in results]
        is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
        assert is_sorted, "Results not properly sorted by similarity"
        print("  PASSED: Mixed language rerank successful\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False

    # Test 2: English query with mixed candidates
    print("Test 2: English query with mixed candidates")
    query_en = 'how to create rules'
    candidates_mixed = [
        '如何创建插件',
        'Create agents',
        '规则管理',
        'rule configuration',
        '插件开发指南'
    ]
    print(f"  Query: {query_en}")
    print(f"  Candidates: {candidates_mixed}")

    try:
        results_en = matcher.rerank(query_en, candidates_mixed)
        print("  Results (sorted by similarity):")
        for text, score in results_en:
            print(f"    {score:.4f} | {text}")
        print("  PASSED: English query with mixed candidates successful\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False

    return True


def run_all_tests():
    """Run all TransformerMatcher tests."""
    print("=" * 60)
    print("TransformerMatcher Interface Test Suite")
    print("=" * 60 + "\n")

    # Check for HF_KEY environment variable
    import os
    hf_key = os.environ.get("HF_KEY")
    if not hf_key:
        print("WARNING: HF_KEY environment variable not set.")
        print("Please set it in doc4llm/.env or as an environment variable.\n")
        print("Test results will fail without valid HuggingFace API key.\n")

    tests = [
        ("Initialization", test_transformer_matcher_initialization),
        ("Language Detection", test_language_detection),
        ("Rerank Method", test_transformer_matcher_rerank),
        ("Rerank Batch Method", test_transformer_matcher_rerank_batch),
        ("Mixed Language Rerank", test_mixed_language_rerank),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print("="*60)
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        if not passed:
            all_passed = False
        print(f"  [{status}] {name}")

    print()
    if all_passed:
        print("All tests PASSED!")
        return 0
    else:
        print("Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
