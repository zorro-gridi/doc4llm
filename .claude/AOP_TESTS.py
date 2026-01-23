#!/usr/bin/env python3
"""
AOP (Agent Output Protocol) Test Suite

Tests various AOP marker scenarios.
"""

from AOP_VALIDATION import AOPValidator, validate_agent_output


def test_valid_final_marker():
    """Test valid AOP-FINAL marker."""
    output = """=== AOP-FINAL | agent=doc-retriever | format=markdown | lines=450 ===

# Document Content

This is the content.

=== END-AOP-FINAL ==="""

    result = validate_agent_output(output)
    assert result['valid'] == True, f"Expected valid, got errors: {result['errors']}"
    assert result['marker_type'] == 'FINAL'
    print("✓ test_valid_final_marker passed")


def test_valid_error_marker():
    """Test valid AOP-ERROR marker."""
    output = """=== AOP-ERROR | agent=doc-qa-agentic | code=NO_RESULTS ===

No documents found matching your query.

=== END-AOP-ERROR ==="""

    result = validate_agent_output(output)
    assert result['valid'] == True, f"Expected valid, got errors: {result['errors']}"
    assert result['marker_type'] == 'ERROR'
    print("✓ test_valid_error_marker passed")


def test_missing_end_marker():
    """Test missing end marker."""
    output = """=== AOP-FINAL | agent=test ===

Content without end marker."""

    result = validate_agent_output(output)
    assert result['valid'] == False, "Expected invalid (missing end marker)"
    assert any('END-AOP-FINAL' in e for e in result['errors'])
    print("✓ test_missing_end_marker passed")


def test_invalid_marker_type():
    """Test invalid marker type."""
    output = """=== AOP-INVALID | agent=test ===

Content.

=== END-AOP-INVALID ==="""

    result = validate_agent_output(output)
    assert result['valid'] == False, "Expected invalid (invalid marker type)"
    assert any('Invalid AOP type' in e for e in result['errors'])
    print("✓ test_invalid_marker_type passed")


def test_missing_required_attributes():
    """Test missing required attributes."""
    output = """=== AOP-FINAL ===

Content.

=== END-AOP-FINAL ==="""

    result = validate_agent_output(output)
    assert result['valid'] == False, "Expected invalid (missing required attributes)"
    assert any('Missing required' in e for e in result['errors'])
    print("✓ test_missing_required_attributes passed")


def test_no_marker():
    """Test output with no AOP marker."""
    output = """This is plain output without any markers."""

    result = validate_agent_output(output)
    assert result['valid'] == False, "Expected invalid (no marker)"
    assert any('No AOP start marker' in e for e in result['errors'])
    print("✓ test_no_marker passed")


def test_marker_mismatch():
    """Test mismatched start and end markers."""
    output = """=== AOP-FINAL | agent=test ===

Content.

=== END-AOP-ERROR ==="""

    result = validate_agent_output(output)
    assert result['valid'] == False, "Expected invalid (marker mismatch)"
    assert any('Marker mismatch' in e for e in result['errors'])
    print("✓ test_marker_mismatch passed")


def test_multiple_markers():
    """Test multiple markers in sequence."""
    output = """=== AOP-CONTEXT | type=metadata ===
{"version": "1.0"}
=== END-AOP-CONTEXT ===

=== AOP-FINAL | agent=doc-retriever | lines=100 ===

Main content here.

=== END-AOP-FINAL ==="""

    result = validate_agent_output(output)
    assert result['valid'] == True, f"Expected valid, got errors: {result['errors']}"
    print("✓ test_multiple_markers passed")


def test_doc_retriever_realistic():
    """Test realistic doc-retriever output."""
    output = """=== AOP-FINAL | agent=doc-retriever | format=markdown | lines=450 | source=https://code.claude.com/docs/en/skills ===

# Agent Skills

[Full 450 lines of content here...]

---
**Source:** https://code.claude.com/docs/en/skills
**Path:** md_docs/Claude_Code_Docs@latest/Agent Skills/docContent.md
**Document Set:** Claude_Code_Docs@latest

=== END-AOP-FINAL ==="""

    result = validate_agent_output(output)
    assert result['valid'] == True, f"Expected valid, got errors: {result['errors']}"
    assert result['attributes']['agent'] == 'doc-retriever'
    assert result['attributes']['format'] == 'markdown'
    assert result['attributes']['lines'] == '450'
    assert 'source' in result['attributes']
    print("✓ test_doc_retriever_realistic passed")


def test_doc_qa_agentic_realistic():
    """Test realistic doc-qa-agentic output."""
    output = """=== AOP-FINAL | agent=doc-qa-agentic | confidence=0.92 | sources=3 ===

## Hooks Configuration and Deployment

I searched through 2 topics to answer your question.

### Configuration
Hooks are configured in `.claude/hooks.json`...

**From:** Hooks reference

### Deployment Considerations
For deployment, consider...

**From:** Deployment guide

**Confidence:** 92%

**Sources:**
1. Hooks reference (relevance: 0.92)
2. Get started with hooks (relevance: 0.85)

=== END-AOP-FINAL ==="""

    result = validate_agent_output(output)
    assert result['valid'] == True, f"Expected valid, got errors: {result['errors']}"
    assert result['attributes']['agent'] == 'doc-qa-agentic'
    assert result['attributes']['confidence'] == '0.92'
    assert result['attributes']['sources'] == '3'
    print("✓ test_doc_qa_agentic_realistic passed")


def run_all_tests():
    """Run all tests."""
    tests = [
        test_valid_final_marker,
        test_valid_error_marker,
        test_missing_end_marker,
        test_invalid_marker_type,
        test_missing_required_attributes,
        test_no_marker,
        test_marker_mismatch,
        test_multiple_markers,
        test_doc_retriever_realistic,
        test_doc_qa_agentic_realistic,
    ]

    passed = 0
    failed = 0

    print("Running AOP Test Suite...")
    print("=" * 50)

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")

    return failed == 0


if __name__ == '__main__':
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
