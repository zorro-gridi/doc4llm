"""
LLM Reranker 模块

基于 LLM 的文档检索结果重排序。

Features:
    - 基于 LLM 的语义相似度评分
    - 自动填充 rerank_sim 字段
    - 过滤低评分结果 (rerank_sim < 0.5)
    - 支持同步/异步调用
    - 保留 thinking 推理过程
"""

from doc4llm.doc_rag.llm_reranker.llm_reranker import (
    LLMReranker,
    LLMRerankerConfig,
    RerankerResult,
)

__all__ = [
    "LLMReranker",
    "LLMRerankerConfig",
    "RerankerResult",
]
