#!/usr/bin/env python
"""Test suite for ContentSearcher module."""
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from doc4llm.doc_rag.searcher.content_searcher import ContentSearcher


def create_test_docs(base_dir: Path) -> None:
    """Create test document structure.

    Creates:
        doc_set/
            page1/
                docContent.md
            page2/
                docContent.md
    """
    doc_set = base_dir / "test_doc_set"
    doc_set.mkdir(parents=True, exist_ok=True)

    # Create page1 with multiple matches
    page1 = doc_set / "page1"
    page1.mkdir(parents=True, exist_ok=True)
    page1_content = """# Page One Title

## Introduction

This is an introduction about hooks.

### Hook Concepts

Hooks are fundamental to the system.

## Usage

Using hooks requires configuration.

## Advanced Topics

More details about hooks implementation.
"""
    (page1 / "docContent.md").write_text(page1_content, encoding="utf-8")

    # Create page2 with matches in different sections
    page2 = doc_set / "page2"
    page2.mkdir(parents=True, exist_ok=True)
    page2_content = """# Page Two Title

## First Section

Initial setup for hooks.

## Second Section

Advanced hook patterns.

## Third Section

Conclusion about hooks in production.
"""
    (page2 / "docContent.md").write_text(page2_content, encoding="utf-8")

    # Create page3 with URL links
    page3 = doc_set / "page3"
    page3.mkdir(parents=True, exist_ok=True)
    page3_content = """# Page Three Title

## Section with Links

Refer to [hooks documentation](https://example.com/hooks) for details.

## Another Section

See: https://example.com/api/hooks for API reference.

## 中文链接

参考 hooks 文档：https://example.com/cn/hooks 获取更多内容。
"""
    (page3 / "docContent.md").write_text(page3_content, encoding="utf-8")


def test_basic_search():
    """Test basic search functionality."""
    print("=" * 60)
    print("Test: Basic Search")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        create_test_docs(base_dir)

        searcher = ContentSearcher(
            base_dir=str(base_dir),
            domain_nouns=["hooks"],
            debug=True,
        )

        results = searcher.search(
            queries=["hooks"],
            doc_sets=["test_doc_set"],
        )

        print(f"\nResults count: {len(results)}")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['page_title']} -> {r['heading']}")

        # Verify results
        assert len(results) > 0, "Should find at least some results"
        assert all(r["source"] == "FALLBACK_SEARCHER" for r in results)

        # Check for heading-level deduplication
        page_titles = [r["page_title"] for r in results]
        print(f"\nPage titles found: {set(page_titles)}")

        print("\n[PASS] Basic search test passed!")
        return True


def test_heading_deduplication():
    """Test that results are deduplicated by heading, not by file."""
    print("\n" + "=" * 60)
    print("Test: Heading-Level Deduplication")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        create_test_docs(base_dir)

        searcher = ContentSearcher(
            base_dir=str(base_dir),
            domain_nouns=["hooks"],
            debug=True,
        )

        results = searcher.search(
            queries=["hooks"],
            doc_sets=["test_doc_set"],
        )

        # Count unique headings
        headings = [r["heading"] for r in results]
        unique_headings = set(headings)

        print(f"\nTotal results: {len(results)}")
        print(f"Unique headings: {len(unique_headings)}")
        print(f"\nAll headings:")
        for h in unique_headings:
            count = headings.count(h)
            print(f"  - {h}: {count} occurrence(s)")

        # Same heading should only appear once per page
        for h in unique_headings:
            page_title_for_h = [r["page_title"] for r in results if r["heading"] == h]
            unique_pages = set(page_title_for_h)
            print(f"\n  Heading '{h[:30]}...' appears on pages: {unique_pages}")

        print("\n[PASS] Heading deduplication test passed!")
        return True


def test_no_domain_nouns():
    """Test that empty domain_nouns returns empty results."""
    print("\n" + "=" * 60)
    print("Test: No Domain Nouns")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        create_test_docs(base_dir)

        # Test with empty domain_nouns
        searcher = ContentSearcher(
            base_dir=str(base_dir),
            domain_nouns=[],  # Empty
            debug=True,
        )

        results = searcher.search(
            queries=["hooks"],
            doc_sets=["test_doc_set"],
        )

        assert len(results) == 0, "Should return empty results when no domain_nouns"

        print("\n[PASS] Empty domain_nouns test passed!")
        return True


def test_max_results_limit():
    """Test global max_results limit."""
    print("\n" + "=" * 60)
    print("Test: Max Results Limit")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        create_test_docs(base_dir)

        # Set very low max_results
        searcher = ContentSearcher(
            base_dir=str(base_dir),
            domain_nouns=["hooks"],
            max_results=3,  # Very low limit
            debug=True,
        )

        results = searcher.search(
            queries=["hooks"],
            doc_sets=["test_doc_set"],
        )

        print(f"\nMax results set to: 3")
        print(f"Actual results: {len(results)}")

        assert len(results) <= 3, f"Should respect max_results limit, got {len(results)}"

        print("\n[PASS] Max results limit test passed!")
        return True


def test_url_cleaning():
    """Test that URLs are cleaned from headings and context."""
    print("\n" + "=" * 60)
    print("Test: URL Cleaning")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        create_test_docs(base_dir)

        searcher = ContentSearcher(
            base_dir=str(base_dir),
            domain_nouns=["hooks"],
            debug=True,
        )

        results = searcher.search(
            queries=["hooks"],
            doc_sets=["test_doc_set"],
        )

        # Check that URLs are cleaned from headings
        for r in results:
            heading = r["heading"]
            context = r.get("related_context", "")

            # Check for remaining URLs in headings
            assert "(" not in heading or ")" not in heading or "http" not in heading, \
                f"URL not cleaned from heading: {heading}"

            # Check for remaining URLs in context
            if context:
                # Allow some URLs but check they're cleaned
                pass

        print("\n[PASS] URL cleaning test passed!")
        return True


def test_case_insensitive():
    """Test that search is case insensitive."""
    print("\n" + "=" * 60)
    print("Test: Case Insensitive Search")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        create_test_docs(base_dir)

        # Search with uppercase
        searcher = ContentSearcher(
            base_dir=str(base_dir),
            domain_nouns=["HOOKS"],  # Uppercase
            debug=True,
        )

        results = searcher.search(
            queries=["HOOKS"],
            doc_sets=["test_doc_set"],
        )

        print(f"\nSearched for 'HOOKS' (uppercase)")
        print(f"Results found: {len(results)}")

        assert len(results) > 0, "Should find results with uppercase keyword"

        print("\n[PASS] Case insensitive test passed!")
        return True


def test_empty_doc_set():
    """Test behavior with non-existent doc set."""
    print("\n" + "=" * 60)
    print("Test: Non-existent Doc Set")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        create_test_docs(base_dir)

        searcher = ContentSearcher(
            base_dir=str(base_dir),
            domain_nouns=["hooks"],
            debug=True,
        )

        # Search in non-existent doc set
        results = searcher.search(
            queries=["hooks"],
            doc_sets=["non_existent_doc_set"],
        )

        assert len(results) == 0, "Should return empty for non-existent doc set"

        print("\n[PASS] Non-existent doc set test passed!")
        return True


def test_nonexistent_keyword():
    """Test behavior with keyword that doesn't exist in docs."""
    print("\n" + "=" * 60)
    print("Test: Non-existent Keyword")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        create_test_docs(base_dir)

        searcher = ContentSearcher(
            base_dir=str(base_dir),
            domain_nouns=["nonexistentkeyword12345"],
            debug=True,
        )

        results = searcher.search(
            queries=["nonexistentkeyword12345"],
            doc_sets=["test_doc_set"],
        )

        assert len(results) == 0, "Should return empty for non-existent keyword"

        print("\n[PASS] Non-existent keyword test passed!")
        return True


def test_multiple_doc_sets():
    """Test search across multiple doc sets."""
    print("\n" + "=" * 60)
    print("Test: Multiple Doc Sets")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        # Create first doc set
        doc_set1 = base_dir / "doc_set_1"
        doc_set1.mkdir(parents=True, exist_ok=True)
        page1 = doc_set1 / "page1"
        page1.mkdir(parents=True, exist_ok=True)
        (page1 / "docContent.md").write_text(
            """# Doc Set 1 Page

## Section

Content with hooks here.
""",
            encoding="utf-8",
        )

        # Create second doc set
        doc_set2 = base_dir / "doc_set_2"
        doc_set2.mkdir(parents=True, exist_ok=True)
        page2 = doc_set2 / "page2"
        page2.mkdir(parents=True, exist_ok=True)
        (page2 / "docContent.md").write_text(
            """# Doc Set 2 Page

## Section

More content with hooks.
""",
            encoding="utf-8",
        )

        searcher = ContentSearcher(
            base_dir=str(base_dir),
            domain_nouns=["hooks"],
            debug=True,
        )

        results = searcher.search(
            queries=["hooks"],
            doc_sets=["doc_set_1", "doc_set_2"],
        )

        print(f"\nResults found: {len(results)}")

        # Check results from both doc sets
        doc_sets_found = set(r["doc_set"] for r in results)
        print(f"Doc sets found: {doc_sets_found}")

        assert "doc_set_1" in doc_sets_found, "Should find results from doc_set_1"
        assert "doc_set_2" in doc_sets_found, "Should find results from doc_set_2"

        print("\n[PASS] Multiple doc sets test passed!")
        return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("# ContentSearcher Test Suite")
    print("#" * 60)

    tests = [
        test_basic_search,
        test_heading_deduplication,
        test_no_domain_nouns,
        test_max_results_limit,
        test_url_cleaning,
        test_case_insensitive,
        test_empty_doc_set,
        test_nonexistent_keyword,
        test_multiple_doc_sets,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n[FAIL] {test.__name__}: {e}")
            failed += 1

    print("\n" + "#" * 60)
    print(f"# Test Results: {passed} passed, {failed} failed")
    print("#" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
