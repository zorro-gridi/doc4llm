"""
Test for FALLBACK_2 grep context extraction functionality.

Tests the _fallback2_grep_context_bm25 method to verify that related_context
is correctly extracted from docContent.md files using grep commands.
"""

import os
import sys
import subprocess
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set base directory from sample data
SAMPLE_BASE_DIR = os.path.expanduser("~/project/md_docs_base")


def test_grep_direct_context_extraction():
    """
    Test Case 1: Verify grep directly extracts context from docContent.md

    This test simulates the FALLBACK_2 grep logic to extract context
    from docContent.md files.
    """
    print("=" * 70)
    print("Test Case 1: Direct grep context extraction from docContent.md")
    print("=" * 70)

    doc_set = "Claude_Code_Docs@latest"
    keyword_pattern = "hook|command|script"
    doc_content_path = Path(SAMPLE_BASE_DIR) / doc_set / "Hooks reference" / "docContent.md"

    print(f"Test file: {doc_content_path}")
    print(f"Keyword pattern: {keyword_pattern}")

    # Check if file exists
    if not doc_content_path.exists():
        print(f"[SKIP] File not found: {doc_content_path}")
        return False

    # Run grep with context (-B 10 -A 10)
    cmd = [
        "grep",
        "-i",
        "-B", "10",
        "-A", "10",
        "-E", keyword_pattern,
        str(doc_content_path)
    ]

    print(f"\nExecuting: {' '.join(cmd)}")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = proc.stdout.strip()

        print(f"\nReturn code: {proc.returncode}")
        print(f"Output length: {len(output)} chars")

        if output:
            print(f"\n[SUCCESS] grep returned {len(output.split(chr(10)))} lines of context")
            print("\nFirst 500 chars of output:")
            print("-" * 50)
            print(output[:500])
            print("-" * 50)
            return True
        else:
            print("\n[FAIL] grep returned empty output")
            if proc.stderr:
                print(f"stderr: {proc.stderr}")
            return False

    except Exception as e:
        print(f"[ERROR] grep execution failed: {e}")
        return False


def test_fallback2_grep_context_bm25():
    """
    Test Case 2: Verify _fallback2_grep_context_bm25 method

    This test calls the actual DocSearcherAPI method to verify that
    related_context is correctly populated in the results.
    """
    print("\n" + "=" * 70)
    print("Test Case 2: _fallback2_grep_context_bm25 method test")
    print("=" * 70)

    from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

    searcher = DocSearcherAPI(
        base_dir=SAMPLE_BASE_DIR,
        reranker_enabled=False,
        debug=True,
    )

    queries = ["hook command"]
    doc_sets = ["Claude_Code_Docs@latest"]

    print(f"Queries: {queries}")
    print(f"Doc-sets: {doc_sets}")

    # Call the FALLBACK_2 method directly
    results = searcher._fallback2_grep_context_bm25(queries, doc_sets)

    print(f"\nResults count: {len(results)}")

    if not results:
        print("[FAIL] No results returned from _fallback2_grep_context_bm25")
        return False

    # Check each result for related_context
    has_context = 0
    empty_context = 0

    for i, result in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"    Page title: {result.get('page_title', 'N/A')}")
        print(f"    Heading: {result.get('heading', 'N/A')[:60]}...")
        print(f"    Score: {result.get('score', 'N/A')}")

        related_context = result.get('related_context', '')
        if related_context:
            has_context += 1
            print(f"    related_context: {len(related_context)} chars")
            print(f"    related_context preview: {related_context[:200]}...")
        else:
            empty_context += 1
            print(f"    related_context: [EMPTY]")

    print(f"\nSummary: {has_context} with context, {empty_context} without context")

    if has_context > 0:
        print("\n[SUCCESS] related_context is populated in results")
        return True
    else:
        print("\n[FAIL] All results have empty related_context")
        return False


def test_grep_context_with_empty_lines():
    """
    Test Case 3: Verify grep handles empty lines and edge cases

    This test verifies that the context extraction logic correctly
    handles empty lines and lines starting with '--'.
    """
    print("\n" + "=" * 70)
    print("Test Case 3: Grep context with empty lines handling")
    print("=" * 70)

    doc_set = "Claude_Code_Docs@latest"
    keyword_pattern = "hook|command|script"
    doc_content_path = Path(SAMPLE_BASE_DIR) / doc_set / "Hooks reference" / "docContent.md"

    if not doc_content_path.exists():
        print(f"[SKIP] File not found: {doc_content_path}")
        return None

    # Run grep with larger context window
    cmd = [
        "grep",
        "-i",
        "-B", "20",
        "-A", "20",
        "-E", keyword_pattern,
        str(doc_content_path)
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = proc.stdout.strip()

        if not output:
            print("[SKIP] No grep output to analyze")
            return None

        lines = output.split("\n")

        # Analyze the output for empty lines and -- markers
        empty_lines = [i for i, l in enumerate(lines) if not l.strip()]
        separator_lines = [i for i, l in enumerate(lines) if l.strip().startswith("--")]
        matching_lines = [i for i, l in enumerate(lines) if "hook" in l.lower() or "command" in l.lower() or "script" in l.lower()]

        print(f"\nLine analysis:")
        print(f"  Total lines: {len(lines)}")
        print(f"  Empty lines: {len(empty_lines)}")
        print(f"  Separator lines (--): {len(separator_lines)}")
        print(f"  Matching lines: {len(matching_lines)}")

        # Show context around first match
        if matching_lines:
            first_match = matching_lines[0]
            context_start = max(0, first_match - 3)
            context_end = min(len(lines), first_match + 4)

            print(f"\nContext around first match (line {first_match + 1}):")
            print("-" * 50)
            for i in range(context_start, context_end):
                marker = " >>> " if i == first_match else "     "
                print(f"{marker}Line {i+1}: {lines[i]}")
            print("-" * 50)

        print("\n[SUCCESS] Empty line handling test completed")
        return True

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False


def test_grep_vs_python_regex():
    """
    Test Case 4: Compare grep output with Python regex matching

    This test compares the grep command output with Python's regex
    matching to verify the pattern is correctly applied.
    """
    print("\n" + "=" * 70)
    print("Test Case 4: Grep vs Python regex comparison")
    print("=" * 70)

    import re

    doc_set = "Claude_Code_Docs@latest"
    keyword_pattern = "hook|command|script"
    doc_content_path = Path(SAMPLE_BASE_DIR) / doc_set / "Hooks reference" / "docContent.md"

    if not doc_content_path.exists():
        print(f"[SKIP] File not found: {doc_content_path}")
        return None

    # Read file content
    content = doc_content_path.read_text(encoding='utf-8')

    # Python regex match
    pattern = re.compile(keyword_pattern, re.IGNORECASE)
    matches = [(i+1, line) for i, line in enumerate(content.split('\n')) if pattern.search(line)]

    print(f"Python regex matches: {len(matches)}")

    # Grep match
    cmd = ["grep", "-i", "-n", "-E", keyword_pattern, str(doc_content_path)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        grep_lines = [l for l in proc.stdout.strip().split('\n') if l]
        print(f"Grep matches: {len(grep_lines)}")

        if matches:
            print("\nFirst 5 Python regex matches:")
            for i, (line_num, line) in enumerate(matches[:5], 1):
                print(f"  Line {line_num}: {line[:70]}...")

            print("\nFirst 5 grep matches:")
            for i, line in enumerate(grep_lines[:5], 1):
                print(f"  {line[:70]}...")

        # Compare results
        if len(matches) == len(grep_lines):
            print("\n[SUCCESS] Grep and Python regex match counts are equal")
            return True
        else:
            print(f"\n[WARNING] Match counts differ: grep={len(grep_lines)}, python={len(matches)}")
            return False

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False


def test_context_extraction_logic():
    """
    Test Case 5: Verify the context extraction logic in _fallback2_grep_context_bm25

    This test extracts and verifies the exact logic used for context extraction.
    """
    print("\n" + "=" * 70)
    print("Test Case 5: Context extraction logic verification")
    print("=" * 70)

    doc_set = "Claude_Code_Docs@latest"
    keyword_pattern = "hook|command|script"
    doc_content_path = Path(SAMPLE_BASE_DIR) / doc_set / "Hooks reference" / "docContent.md"

    if not doc_content_path.exists():
        print(f"[SKIP] File not found: {doc_content_path}")
        return None

    # Simulate the grep context extraction from _fallback2_grep_context_bm25
    cmd_context = [
        "grep",
        "-i",
        "-B", "10",
        "-A", "10",
        "-E", keyword_pattern,
        str(doc_content_path)
    ]

    try:
        proc = subprocess.run(cmd_context, capture_output=True, text=True, timeout=30)
        output_context = proc.stdout.strip()

        if not output_context:
            print("[FAIL] No grep output for context extraction")
            return False

        context_lines = output_context.split("\n")
        context_parts = []

        print(f"\nProcessing {len(context_lines)} context lines...")

        for i, line in enumerate(context_lines):
            if re.search(keyword_pattern, line, re.IGNORECASE):
                print(f"  Found match at line {i+1}")

                # Collect context before (2 lines)
                for j in range(max(0, i - 2), i):
                    if j < len(context_lines):
                        context_line = context_lines[j]
                        stripped = context_line.strip()
                        if stripped and not stripped.startswith("--"):
                            if ".md:" in context_line:
                                content = context_line.split(".md:", 1)[1]
                            elif ".md-" in context_line:
                                content = context_line.split(".md-", 1)[1] if len(context_line) > context_line.index(".md-") + 3 else ""
                            else:
                                content = stripped
                            if content:
                                context_parts.append(content.strip())

                # Collect context after (2 lines)
                for j in range(i + 1, min(len(context_lines), i + 3)):
                    if j < len(context_lines):
                        context_line = context_lines[j]
                        stripped = context_line.strip()
                        if stripped and not stripped.startswith("--"):
                            if ".md:" in context_line:
                                content = context_line.split(".md:", 1)[1]
                            elif ".md-" in context_line:
                                content = context_line.split(".md-", 1)[1] if len(context_line) > context_line.index(".md-") + 3 else ""
                            else:
                                content = stripped
                            if content:
                                context_parts.append(content.strip())

                break  # Only process first match

        related_context = "".join(context_parts)

        print(f"\nExtracted context parts: {len(context_parts)}")
        print(f"Total context length: {len(related_context)} chars")

        if related_context:
            print("\n[SUCCESS] Context extraction logic works correctly")
            print(f"\nContext preview:\n{related_context[:300]}...")
            return True
        else:
            print("\n[FAIL] Context extraction returned empty result")
            return False

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all test cases."""
    print("\n" + "=" * 70)
    print("FALLBACK_2 Grep Context Extraction Tests")
    print("=" * 70)
    print(f"Base Directory: {SAMPLE_BASE_DIR}")
    print()

    tests = [
        ("Direct grep context extraction", test_grep_direct_context_extraction),
        ("_fallback2_grep_context_bm25 method", test_fallback2_grep_context_bm25),
        ("Empty lines handling", test_grep_context_with_empty_lines),
        ("Grep vs Python regex", test_grep_vs_python_regex),
        ("Context extraction logic", test_context_extraction_logic),
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
    sys.exit(0 if success else 1)
