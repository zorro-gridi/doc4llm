from doc4llm.doc_rag.orchestrator import retrieve

result = retrieve(
    query="检索文档查找claude code skill返回的结果如何注入到对话的上下文? hook; skill; context. 并参考文档检索结果将名为rag skill的执行结果注入到上下文",
    base_dir="~/project/md_docs_base",
    skiped_keywords_path="doc4llm/doc_rag/searcher/skiped_keywords.txt",
    threshold=3000,
    embedding_reranker=False,
    searcher_reranker=False,
    llm_reranker=True,
    stop_at_phase='1',
    debug=True,
    searcher_config={
        'embedding_provider': 'hf',
        'reranker_model_zh': 'Qwen/Qwen3-Embedding-8B',
        'reranker_model_en': 'Qwen/Qwen3-Embedding-8B',
        'reranker_threshold': 0.6,
        'hf_inference_provider': 'auto',
    }
)

print(result.output)      # Formatted Markdown
# print(result.scene)       # Classification (e.g., "how_to")
# print(result.sources)     # Source document metadata