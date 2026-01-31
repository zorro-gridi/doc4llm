from doc4llm.doc_rag.orchestrator import retrieve

result = retrieve(
    query="claude code 如何实现 hook 上下文注入？",
    base_dir="~/project/md_docs_base",
    skiped_keywords_path="/Users/zorro/project/doc4llm/doc4llm/doc_rag/searcher/skiped_keywords.txt",
    threshold=3000,
    embedding_reranker=False,
    searcher_reranker=True,
    llm_reranker=True,
    # stop_at_phase='2',  # 停在 Phase 1 查看 search_result
    debug=True,
    searcher_config={
        'embedding_provider': 'ms',
        'reranker_model_zh': 'Qwen/Qwen3-Embedding-8B',
        'reranker_model_en': 'Qwen/Qwen3-Embedding-8B',
        'embedding_model_id': 'Qwen/Qwen3-Embedding-8B',
        # 检索召回的阈值
        # 'reranker_threshold': 0.6,
        'hf_inference_provider': 'auto',
        # 'skiped_keywords_path': "doc4llm/doc_rag/searcher/skiped_keywords.txt",
        'rerank_scopes': ['page_title'],
        # 精准匹配的阈值
        # 当 rerank_sim 超过此阈值，其下属headings列表会被置空，表示将提取整个文档
        'threshold_precision': 0.7,
        'threshold_page_title': 3.0,
    }
)

# 打印最终输出（包含 Sources 部分）
print("\n" + "=" * 60)
print("最终输出 (Final Output)")
print("=" * 60)
print(result.output)