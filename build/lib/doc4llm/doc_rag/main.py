from doc4llm.doc_rag.orchestrator import retrieve

result = retrieve(
    query="如何创建 claude code skills?",
    knowledge_base_path=".opencode/knowledge_base.json",
    skiped_keywords_path="doc4llm/doc_rag/searcher/skiped_keywords.txt",
    threshold=3000,
    llm_reranker=True,
    debug=True,
)

print(result.output)      # Formatted Markdown
# print(result.scene)       # Classification (e.g., "how_to")
# print(result.sources)     # Source document metadata