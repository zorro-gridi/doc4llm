"""
Query Optimizer Package

提供基于 LLM 的查询优化和扩展功能。

Classes:
    QueryOptimizer: 查询优化器主类
    QueryOptimizerConfig: 配置数据类
    OptimizationResult: 优化结果数据类

Example:
    >>> from doc4llm.doc_rag.query_optimizer import QueryOptimizer
    >>> optimizer = QueryOptimizer()
    >>> result = optimizer("如何创建 ray cluster?")
    >>> for q in result.optimized_queries:
    ...     print(q.get("query"))
"""

from .query_optimizer import QueryOptimizer, QueryOptimizerConfig, OptimizationResult

__version__ = "1.0.0"
__all__ = ["QueryOptimizer", "QueryOptimizerConfig", "OptimizationResult"]
