#!/usr/bin/env python3
"""
Test script for BM25Matcher

Demonstrates the BM25-based document matching capabilities.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from doc4llm.tool.md_doc_retrieval import (
    BM25Matcher,
    BM25Config,
    calculate_bm25_similarity,
    tokenize_text,
    MarkdownDocExtractor,
    AgenticDocMatcher,
)


def print_separator(char="="):
    print(char * 60)


def test_basic_bm25_search():
    """Test basic BM25 search."""
    print_separator()
    print("Test 1: Basic BM25 Search")
    print_separator()

    documents = {
        "doc1": "Machine learning is a subset of artificial intelligence",
        "doc2": "Deep learning uses neural networks for pattern recognition",
        "doc3": "Python is a popular programming language for machine learning",
        "doc4": "Natural language processing uses machine learning techniques",
        "doc5": "JavaScript is used for web development and frontend",
    }

    matcher = BM25Matcher()
    matcher.build_index(documents)

    # Search for machine learning
    query = "machine learning"
    results = matcher.search(query, top_k=3)

    print(f"\nQuery: '{query}'")
    print(f"Found {len(results)} results:")
    for i, (doc_id, score) in enumerate(results, 1):
        content = documents[doc_id][:60] + "..." if len(documents[doc_id]) > 60 else documents[doc_id]
        print(f"\n{i}. {doc_id} (score: {score:.3f})")
        print(f"   Content: {content}")


def test_multi_term_query():
    """Test multi-term query handling."""
    print_separator()
    print("\nTest 2: Multi-Term Query")
    print_separator()

    documents = {
        "doc1": "Agent skills can be created using the skill command",
        "doc2": "The skill system allows custom tool creation",
        "doc3": "Slash commands provide quick access to features",
        "doc4": "Custom agents can be built with Python code",
        "doc5": "The configuration file supports custom settings",
    }

    matcher = BM25Matcher()
    matcher.build_index(documents)

    # Multi-term query
    query = "custom skill creation"
    results = matcher.search(query, top_k=3)

    print(f"\nQuery: '{query}'")
    print(f"Found {len(results)} results:")
    for i, (doc_id, score) in enumerate(results, 1):
        content = documents[doc_id][:60] + "..." if len(documents[doc_id]) > 60 else documents[doc_id]
        print(f"\n{i}. {doc_id} (score: {score:.3f})")
        print(f"   Content: {content}")


def test_rare_term_boosting():
    """Test that rare terms get higher IDF scores."""
    print_separator()
    print("\nTest 3: Rare Term Boosting (IDF)")
    print_separator()

    # Create documents where "machine" is common but "transformer" is rare
    documents = {
        "doc1": "machine learning machine learning machine learning",
        "doc2": "deep learning and machine learning algorithms",
        "doc3": "transformer architecture for natural language processing",
        "doc4": "machine learning models and datasets",
    }

    matcher = BM25Matcher()
    matcher.build_index(documents)

    # Query with rare term
    query = "transformer"
    results = matcher.search(query, top_k=2)

    print(f"\nQuery: '{query}' (rare term)")
    print(f"Found {len(results)} results:")
    for i, (doc_id, score) in enumerate(results, 1):
        content = documents[doc_id][:60] + "..." if len(documents[doc_id]) > 60 else documents[doc_id]
        print(f"\n{i}. {doc_id} (score: {score:.3f})")
        print(f"   Content: {content}")


def test_document_length_normalization():
    """Test document length normalization."""
    print_separator()
    print("\nTest 4: Document Length Normalization")
    print_separator()

    documents = {
        "doc1": "machine learning",  # Short, precise
        "doc2": "machine learning is a field of artificial intelligence that uses statistical techniques",  # Long
        "doc3": "machine learning algorithms",
    }

    # Test with different length normalization parameters
    for b_value in [0.0, 0.5, 1.0]:
        config = BM25Config(k1=1.2, b=b_value)
        matcher = BM25Matcher(config)
        matcher.build_index(documents)

        query = "machine learning"
        results = matcher.search(query, top_k=3)

        print(f"\nWith b={b_value} (length normalization):")
        for doc_id, score in results:
            print(f"  {doc_id}: {score:.3f}")


def test_custom_config():
    """Test custom BM25 configuration."""
    print_separator()
    print("\nTest 5: Custom Configuration")
    print_separator()

    documents = {
        "doc1": "python programming language development",
        "doc2": "javascript web frontend framework",
        "doc3": "python data science machine learning",
    }

    # Custom config with different k1 and b values
    config = BM25Config(
        k1=2.0,  # Higher TF saturation
        b=0.5,   # Lower length normalization
        min_token_length=3,
        stop_words={"the", "a", "an", "for", "with"}
    )

    matcher = BM25Matcher(config)
    matcher.build_index(documents)

    query = "python programming"
    results = matcher.search(query, top_k=2)

    print(f"\nQuery: '{query}'")
    print(f"Config: k1={config.k1}, b={config.b}")
    print(f"Found {len(results)} results:")
    for i, (doc_id, score) in enumerate(results, 1):
        content = documents[doc_id][:50] + "..." if len(documents[doc_id]) > 50 else documents[doc_id]
        print(f"\n{i}. {doc_id} (score: {score:.3f})")
        print(f"   Content: {content}")


def test_search_with_metadata():
    """Test search with detailed metadata."""
    print_separator()
    print("\nTest 6: Search with Metadata")
    print_separator()

    documents = {
        "doc1": "Agent skills enable custom tool creation",
        "doc2": "Skills can be configured with hooks",
        "doc3": "The agent framework supports multiple skill types",
    }

    matcher = BM25Matcher()
    matcher.build_index(documents)

    query = "agent skills hooks"
    result = matcher.search_with_metadata(
        query,
        top_k=3,
        return_query_tokens=True
    )

    print(f"\nQuery: '{query}'")
    print(f"Total documents in index: {result['total_docs']}")
    print(f"Average document length: {result['avg_doc_length']:.1f}")
    print(f"Query tokens: {result.get('query_tokens', [])}")
    print(f"Matched terms: {result['matched_terms']}")

    print(f"\nResults:")
    for i, (doc_id, score) in enumerate(result['results'], 1):
        print(f"\n{i}. {doc_id} (score: {score:.3f})")
        print(f"   Content: {documents[doc_id]}")


def test_tokenization():
    """Test tokenization function."""
    print_separator()
    print("\nTest 7: Tokenization")
    print_separator()

    text = "Hello World! This is a test of tokenization with STOP-WORDS and numbers 123."

    tokens = tokenize_text(
        text,
        lowercase=True,
        min_length=2
    )

    print(f"\nOriginal text: {text}")
    print(f"Tokens: {tokens}")


def test_quick_similarity():
    """Test quick similarity calculation."""
    print_separator()
    print("\nTest 8: Quick Similarity Calculation")
    print_separator()

    query = "machine learning algorithms"
    content = "Machine learning is a subset of AI that uses algorithms to learn from data"

    score = calculate_bm25_similarity(query, content)

    print(f"\nQuery: '{query}'")
    print(f"Content: '{content[:50]}...'")
    print(f"BM25 Similarity: {score:.3f}")


def test_agentic_bm25_integration():
    """Test BM25 integration with AgenticDocMatcher."""
    print_separator()
    print("\nTest 9: AgenticDocMatcher with BM25 (Stage 3)")
    print_separator()

    try:
        extractor = MarkdownDocExtractor(base_dir="md_docs")
        matcher = AgenticDocMatcher(extractor, debug_mode=True)

        query = "agent configuration"
        results = matcher.match(query, max_results=5)

        print(f"\nQuery: '{query}'")
        print(f"Found {len(results)} results:")

        for i, r in enumerate(results, 1):
            print(f"\n{i}. {r['title']}")
            print(f"   Similarity: {r['similarity']:.2f}")
            print(f"   Source: {r['source']}")
            print(f"   Match Type: {r['match_type']}")
            if r.get('sections_matched'):
                print(f"   Sections: {', '.join(r['sections_matched'])}")

        # Check if BM25 was used
        bm25_used = any(r['match_type'] == 'content_preview_bm25' for r in results)
        print(f"\nBM25 used for content matching: {bm25_used}")

    except Exception as e:
        print(f"\nError: {e}")
        print("(This test requires md_docs directory with documents)")


def test_index_stats():
    """Test index statistics."""
    print_separator()
    print("\nTest 10: Index Statistics")
    print_separator()

    documents = {
        "doc1": "machine learning is ai",
        "doc2": "deep learning neural networks",
        "doc3": "python programming language",
    }

    matcher = BM25Matcher()
    matcher.build_index(documents)

    stats = matcher.get_index_stats()
    print(f"\nIndex Statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Average document length: {stats['avg_doc_length']:.1f}")
    print(f"  Total unique terms: {stats['total_unique_terms']}")
    print(f"  Config k1: {stats['config']['k1']}")
    print(f"  Config b: {stats['config']['b']}")

    print(f"\nDocument Statistics:")
    for doc_id in documents:
        doc_stats = matcher.get_doc_stats(doc_id)
        if doc_stats:
            print(f"\n  {doc_id}:")
            print(f"    Length: {doc_stats['length']}")
            print(f"    Unique terms: {doc_stats['unique_terms']}")
            print(f"    Top terms: {doc_stats['top_terms'][:5]}")


def run_all_tests():
    """Run all tests."""
    print_separator("=")
    print("BM25 Matcher Test Suite")
    print_separator("=")

    tests = [
        test_basic_bm25_search,
        test_multi_term_query,
        test_rare_term_boosting,
        test_document_length_normalization,
        test_custom_config,
        test_search_with_metadata,
        test_tokenization,
        test_quick_similarity,
        test_agentic_bm25_integration,
        test_index_stats,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[FAILED] {test.__name__}: {e}")

    print_separator()
    print(f"\nTest Summary: {passed} passed, {failed} failed")
    print_separator()


if __name__ == "__main__":
    run_all_tests()
