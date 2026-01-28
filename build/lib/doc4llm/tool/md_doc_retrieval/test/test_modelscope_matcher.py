"""
Test script for ModelScopeMatcher.

验证 ModelScopeMatcher 与 TransformerMatcher 的接口兼容性。
"""

from doc4llm.tool.md_doc_retrieval import ModelScopeMatcher, ModelScopeConfig


def test_modelscope_matcher():
    """Test ModelScopeMatcher basic functionality."""
    print("=== ModelScopeMatcher Test ===\n")

    # 使用默认配置
    matcher = ModelScopeMatcher()

    query = 'create rules'
    corpus = [
        'Create a plugin',
        'a plugin',
        'agents',
        'Create agents',
        'Rules'
    ]

    print(f"Query: {query}")
    print(f"Candidates: {corpus}")
    print()

    # 测试 rerank
    print("Rerank Results:")
    results = matcher.rerank(query, corpus)
    for text, score in results:
        print(f"{score:.4f} | {text}")

    print()

    # 测试 rerank_batch
    queries = ['create rules', 'agents']
    print("Batch Rerank Results:")
    sim_matrix, returned_candidates = matcher.rerank_batch(queries, corpus)
    print(f"Similarity matrix shape: {sim_matrix.shape}")
    print(f"Returned candidates: {returned_candidates}")
    print(f"Similarity matrix:\n{sim_matrix}")


if __name__ == "__main__":
    test_modelscope_matcher()
