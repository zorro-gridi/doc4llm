"""
doc4llm Doc-RAG Pipeline Package

提供文档检索增强生成(RAG)工作流的所有组件。

Modules:
    - orchestrator: Complete RAG pipeline orchestrator
    - query_optimizer: LLM-based query optimization and expansion
    - query_router: LLM-based query classification and routing
    - params_parser: Phase transition parameter parsing
    - searcher: BM25-based document search
    - llm_reranker: LLM-based semantic re-ranking
    - scene_output: Scene-based output formatting
"""

from .orchestrator import DocRAGConfig, DocRAGResult, DocRAGOrchestrator, retrieve
from .query_router.query_router import QueryRouter, QueryRouterConfig, RoutingResult

__version__ = "1.0.0"

__all__ = [
    # Orchestrator
    "DocRAGConfig",
    "DocRAGResult",
    "DocRAGOrchestrator",
    "retrieve",
    # Query Router
    "QueryRouter",
    "QueryRouterConfig",
    "RoutingResult",
]
