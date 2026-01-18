#!/usr/bin/env python3
"""
Test script for AgenticDocMatcher

Demonstrates the agentic document matching capabilities.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from doc4llm.tool.md_doc_extractor import (
    MarkdownDocExtractor,
    AgenticDocMatcher,
    agentic_search,
)


def print_separator(char="="):
    print(char * 60)


def test_basic_search():
    """Test basic agentic search."""
    print_separator()
    print("Test 1: Basic Agentic Search")
    print_separator()

    results = agentic_search("skills", base_dir="md_docs", debug_mode=True)

    print(f"\nFound {len(results)} results:")
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['title']}")
        print(f"   Similarity: {r['similarity']:.2f}")
        print(f"   Source: {r['source']}")
        print(f"   Match Type: {r['match_type']}")
        if r.get('sections_matched'):
            print(f"   Sections: {', '.join(r['sections_matched'])}")


def test_with_matcher_instance():
    """Test with explicit matcher instance."""
    print_separator()
    print("\nTest 2: With Custom Configuration")
    print_separator()

    extractor = MarkdownDocExtractor(base_dir="md_docs")
    matcher = AgenticDocMatcher(
        extractor,
        config={
            "min_results": 2,
            "min_similarity": 0.4,
        },
        debug_mode=True
    )

    results = matcher.match("commit message", max_results=5)

    print(f"\nFound {len(results)} results:")
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['title']}")
        print(f"   Similarity: {r['similarity']:.2f}")
        print(f"   Source: {r['source']}")
        if r.get('content_preview'):
            preview = r['content_preview'][:100] + "..." if len(r.get('content_preview', '')) > 100 else r.get('content_preview', '')
            print(f"   Preview: {preview}")


def test_comparison():
    """Compare agentic vs traditional search."""
    print_separator()
    print("\nTest 3: Agentic vs Traditional Search Comparison")
    print_separator()

    query = "how to configure"

    # Traditional search
    print("\n--- Traditional Search ---")
    extractor = MarkdownDocExtractor(base_dir="md_docs")
    traditional_results = extractor.semantic_search_titles(query, max_results=5)

    print(f"Traditional: {len(traditional_results)} results")
    for r in traditional_results:
        print(f"  - {r['title']} ({r['match_type']}, sim={r['similarity']:.2f})")

    # Agentic search
    print("\n--- Agentic Search ---")
    matcher = AgenticDocMatcher(extractor, debug_mode=False)
    agentic_results = matcher.match(query, max_results=5)

    print(f"Agentic: {len(agentic_results)} results")
    for r in agentic_results:
        print(f"  - {r['title']} ({r['source']}, sim={r['similarity']:.2f})")


def test_debug_mode():
    """Test with debug mode to see the decision process."""
    print_separator()
    print("\nTest 4: Debug Mode (Decision Process)")
    print_separator()

    extractor = MarkdownDocExtractor(base_dir="md_docs")
    matcher = AgenticDocMatcher(extractor, debug_mode=True)

    # Use a query that will trigger multiple stages
    _ = matcher.match("plugin", max_results=3)


if __name__ == "__main__":
    # Check if md_docs exists
    if not Path("md_docs").exists():
        print("Error: md_docs directory not found!")
        print("Please run this script from the project root directory.")
        sys.exit(1)

    # Run tests
    test_basic_search()
    test_with_matcher_instance()
    test_comparison()
    test_debug_mode()

    print_separator()
    print("\nAll tests completed!")
    print_separator()
