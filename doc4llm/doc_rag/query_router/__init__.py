"""
Query Router Package

提供基于 LLM 的查询分类和路由功能。

Classes:
    QueryRouter: 查询路由器主类
    QueryRouterConfig: 配置数据类
    RoutingResult: 路由结果数据类

Functions:
    None

Example:
    >>> from doc4llm.doc_rag.query_router import QueryRouter
    >>> router = QueryRouter()
    >>> result = router("如何创建 ray cluster?")
    >>> print(result.scene)
    how_to
"""

from .query_router import QueryRouter, QueryRouterConfig, RoutingResult

__all__ = ["QueryRouter", "QueryRouterConfig", "RoutingResult"]
