#!/usr/bin/env python3
"""
Test script for HybridMatcher (Rule-based + LLM fallback)

Demonstrates the hybrid approach: fast rule-based matching with LLM enhancement
when results are unsatisfactory.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from doc4llm.tool.md_doc_extractor import (
    MarkdownDocExtractor,
    HybridMatcher,
    hybrid_search,
)


def print_separator(char="="):
    print(char * 70)


def test_fast_path():
    """Test fast path: rule-based matching is sufficient."""
    print_separator()
    print("Test 1: Fast Path (Rule-Based Only)")
    print_separator()

    # 简单查询，规则匹配应该足够
    result = hybrid_search(
        "skills",
        base_dir="md_docs",
        debug_mode=True
    )

    print(f"\nResults: {len(result['results'])} documents")
    for i, r in enumerate(result['results'][:3], 1):
        print(f"  {i}. {r['title']} (sim={r['similarity']:.2f})")

    enhancement = result['enhancement']
    print(f"\nLLM Enhanced: {enhancement.triggered}")
    if not enhancement.triggered:
        print("  → Rule-based matching was sufficient ✓")


def test_llm_fallback():
    """Test LLM fallback: when rule-based results are poor."""
    print_separator()
    print("\nTest 2: LLM Fallback (Poor Results)")
    print_separator()

    # 检查是否有 API key
    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("⚠ Skipping: ANTHROPIC_AUTH_TOKEN not set")
        print("  To test LLM features: export ANTHROPIC_AUTH_TOKEN='your-key'")
        return

    # 复杂查询，可能需要 LLM
    result = hybrid_search(
        "how do I create my first custom skill",
        base_dir="md_docs",
        debug_mode=True
    )

    print(f"\nResults: {len(result['results'])} documents")
    for i, r in enumerate(result['results'][:3], 1):
        print(f"  {i}. {r['title']} (sim={r['similarity']:.2f})")

    enhancement = result['enhancement']
    print(f"\nLLM Enhanced: {enhancement.triggered}")
    if enhancement.triggered:
        print(f"  Reason: {enhancement.reason}")
        print(f"  Intent: {enhancement.intent}")
        print(f"  Refined Query: {enhancement.query_refinement}")
        print(f"  Original: {enhancement.original_count} → Enhanced: {enhancement.enhanced_count}")


def test_force_llm():
    """Test forcing LLM enhancement."""
    print_separator()
    print("\nTest 3: Force LLM Enhancement")
    print_separator()

    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("⚠ Skipping: ANTHROPIC_AUTH_TOKEN not set")
        return

    extractor = MarkdownDocExtractor(base_dir="md_docs")
    matcher = HybridMatcher(extractor, debug_mode=True)

    # 即使简单的查询也强制使用 LLM
    result = matcher.match(
        "skills",
        force_llm=True,  # 强制使用 LLM
        max_results=5
    )

    print(f"\nResults: {len(result['results'])} documents")
    enhancement = result['enhancement']
    print(f"LLM Enhanced: {enhancement.triggered} (forced)")
    print(f"Intent: {enhancement.intent}")


def test_comparison():
    """Compare rule-based vs hybrid."""
    print_separator()
    print("\nTest 4: Comparison Table")
    print_separator()

    queries = [
        "skills",                    # 简单 - 不需要 LLM
        "how to configure",          # 中等 - 可能需要 LLM
        "why isn't my plugin working", # 复杂 - 需要 LLM
    ]

    print(f"{'Query':<35} | {'Results':<8} | {'LLM':<6} |")
    print("-" * 55)

    for query in queries:
        result = hybrid_search(
            query,
            base_dir="md_docs",
            debug_mode=False
        )

        llm_status = "✓" if result['enhancement'].triggered else "-"
        print(f"{query:<35} | {len(result['results']):<8} | {llm_status:<6} |")


def test_trigger_conditions():
    """Test various LLM trigger conditions."""
    print_separator()
    print("\nTest 5: LLM Trigger Conditions")
    print_separator()

    extractor = MarkdownDocExtractor(base_dir="md_docs")

    # 配置更宽松的触发条件
    matcher = HybridMatcher(
        extractor,
        config={
            "llm_trigger_min_results": 5,  # 需要更多结果才触发
            "llm_trigger_max_similarity": 0.9,  # 需要更高的相似度
        },
        debug_mode=True
    )

    # 这个查询应该触发 LLM（结果少且相似度低）
    result = matcher.match("xyznonexistentquery", debug_mode=False)

    print(f"\nQuery: 'xyznonexistentquery'")
    print(f"Results: {len(result['results'])}")
    print(f"LLM Triggered: {result['enhancement'].triggered}")
    print(f"Reason: {result['enhancement'].reason}")


def test_intent_recognition():
    """Test LLM intent recognition."""
    print_separator()
    print("\nTest 6: Intent Recognition")
    print_separator()

    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("⚠ Skipping: ANTHROPIC_AUTH_TOKEN not set")
        return

    test_queries = [
        ("how do I create a skill", "tutorial"),
        ("what is the difference between x and y", "comparison"),
        ("my code throws an error", "troubleshooting"),
        ("configure the settings", "configuration"),
    ]

    extractor = MarkdownDocExtractor(base_dir="md_docs")
    matcher = HybridMatcher(extractor, debug_mode=False)

    print(f"{'Query':<40} | {'Detected Intent':<20} |")
    print("-" * 65)

    for query, expected_intent in test_queries:
        result = matcher.match(query, force_llm=True)
        actual_intent = result['enhancement'].intent

        match = "✓" if actual_intent == expected_intent or expected_intent in actual_intent else "≈"
        print(f"{query:<40} | {actual_intent:<20} | {match}")


if __name__ == "__main__":
    # Check if md_docs exists
    if not Path("md_docs").exists():
        print("Error: md_docs directory not found!")
        print("Please run this script from the project root directory.")
        sys.exit(1)

    print("=" * 70)
    print(" Hybrid Matcher Test Suite")
    print(" Rule-based + LLM Fallback")
    print("=" * 70)

    # Check for API key
    has_api_key = bool(os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    if has_api_key:
        print("✓ ANTHROPIC_AUTH_TOKEN found - LLM features enabled")
    else:
        print("⚠ ANTHROPIC_AUTH_TOKEN not set - LLM features disabled")
        print("  Set with: export ANTHROPIC_AUTH_TOKEN='your-key'")

    # Run tests
    test_fast_path()
    test_llm_fallback()
    test_force_llm()
    test_comparison()
    test_trigger_conditions()
    test_intent_recognition()

    print_separator()
    print("\nAll tests completed!")
    print_separator()
