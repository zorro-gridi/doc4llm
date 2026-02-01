"""
Heading re-ranking logic using transformer-based semantic matching.

This module provides the HeadingReranker class which re-ranks BM25-recalled
headings using semantic similarity scores from a transformer model.

Example:
    >>> from doc4llm.tool.md_doc_retrieval import TransformerMatcher
    >>> from reranker import HeadingReranker, RerankerConfig
    >>> matcher = TransformerMatcher()
    >>> config = RerankerConfig(enabled=True, min_score_threshold=0.68)
    >>> reranker = HeadingReranker(config, matcher)
    >>> reranked_headings = reranker.rerank_headings("query text", headings)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import numpy as np

# Import from md_doc_retrieval package
import sys
from pathlib import Path

# Add the doc4llm package to the path
script_dir = Path(__file__).resolve().parent
for _ in range(4):  # Search up to 4 levels up
    if (script_dir / "doc4llm").exists():
        sys.path.insert(0, str(script_dir))
        break
    script_dir = script_dir.parent

from doc4llm.tool.md_doc_retrieval.transformer_matcher import TransformerMatcher
from doc4llm.tool.md_doc_retrieval.modelscope_matcher import ModelScopeMatcher


@dataclass
class RerankerConfig:
    """Configuration for heading re-ranking.

    Attributes:
        enabled: Whether to enable transformer re-ranking (default: False)
        min_score_threshold: Minimum similarity score to keep a heading (default: 0.68)
        top_k: Maximum number of headings to keep after re-ranking (default: None = all)
    """
    enabled: bool = False
    min_score_threshold: float = 0.68  # Filter low-relevance headings
    top_k: Optional[int] = None  # Keep top K headings


class HeadingReranker:
    """Re-ranker for headings using transformer-based semantic matching.

    This class takes BM25-recalled headings and re-ranks them by semantic
    similarity to the query using a transformer model.

    The re-ranking process:
    1. Extract heading texts from the input list
    2. Compute embeddings for query and all headings
    3. Calculate cosine similarity scores
    4. Filter by min_score_threshold
    5. Keep top_k results if specified
    6. Return re-ranked headings with updated scores
    """

    def __init__(
        self,
        config: RerankerConfig,
        matcher: Union[TransformerMatcher, ModelScopeMatcher]
    ):
        """Initialize the heading reranker.

        Args:
            config: Reranker configuration
            matcher: TransformerMatcher or ModelScopeMatcher instance for computing embeddings
        """
        self.config = config
        self.matcher = matcher

    def rerank_headings(
        self,
        query: str,
        headings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Re-rank headings by semantic similarity to query.

        Args:
            query: Search query string
            headings: List of heading dicts with at least 'text' key.
                     Each heading may also have 'level', 'score', 'is_basic', etc.

        Returns:
            Re-ranked list of headings with updated 'score' field.
            Headings with score < min_score_threshold are filtered out.
            If top_k is set, only the top K results are returned.
        """
        if not headings:
            return []

        # Extract heading texts for batch processing
        heading_texts = [h.get("text", "") for h in headings]

        # Re-rank using transformer matcher
        reranked_results = self.matcher.rerank(query, heading_texts)

        # Build a map from original heading index to new score
        text_to_score = {text: score for text, score in reranked_results}

        # Update headings with new scores and filter by threshold
        reranked_headings = []
        for heading in headings:
            text = heading.get("text", "")
            if text not in text_to_score:
                continue

            semantic_score = text_to_score[text]

            if semantic_score < self.config.min_score_threshold:
                continue

            original_bm25_score = heading.get("bm25_sim") or 0.0
            updated_heading = dict(heading)
            updated_heading["bm25_sim"] = original_bm25_score
            updated_heading["rerank_sim"] = semantic_score
            updated_heading["is_basic"] = True
            if "is_precision" in heading:
                updated_heading["is_precision"] = (
                    semantic_score >= (self.config.min_score_threshold + 0.2)
                )

            reranked_headings.append(updated_heading)

        reranked_headings.sort(key=lambda h: h.get("rerank_sim") or 0.0, reverse=True)

        # Apply top_k limit if specified
        if self.config.top_k is not None and self.config.top_k > 0:
            reranked_headings = reranked_headings[:self.config.top_k]

        return reranked_headings


def fallback_2_local_rerank_headings(
    matcher: Union[TransformerMatcher, ModelScopeMatcher],
    pages: List[Dict[str, Any]],
    queries: List[str],
    preprocess_func: Optional[callable] = None,
    top_k_ratio: float = 0.6,
) -> None:
    """对 FALLBACK_2 结果进行本地向量化语义匹配，保留 top K%.

    使用 related_context 文本与预处理后的 queries 进行语义匹配。

    Args:
        matcher: 本地 TransformerMatcher 或 ModelScopeMatcher 实例
        pages: 页面列表，每个 page 包含 headings
        queries: 查询列表
        preprocess_func: 可选的预处理函数 (self._preprocess_for_rerank)
        top_k_ratio: 保留比例，0.0-1.0 之间 (default 0.6 = top 60%)
    """
    if not pages or not queries or not matcher:
        return

    # 收集 source 为 "FALLBACK_2" 的 headings 及其 related_context
    heading_infos = []  # [(page_idx, heading_idx, heading_dict), ...]
    for page_idx, page in enumerate(pages):
        for h_idx, heading in enumerate(page.get("headings", [])):
            # 只处理 source 为 FALLBACK_2 的 headings
            if heading.get("source") == "FALLBACK_2":
                related_context = heading.get("related_context", "")
                if related_context:
                    heading_infos.append((page_idx, h_idx, heading, related_context))

    if not heading_infos:
        return

    # 预处理 queries
    if preprocess_func:
        processed_queries = [preprocess_func(q) for q in queries]
    else:
        processed_queries = queries

    # 提取 related_context 文本
    context_texts = [info[3] for info in heading_infos]

    # 批量向量化匹配
    query_embs = matcher.encode(processed_queries)
    context_embs = matcher.encode(context_texts)

    # 计算相似度矩阵 [Q, C]，Q=queries数量, C=contexts数量
    sim_matrix = query_embs @ context_embs.T

    # 计算每个 heading 的最终匹配分数：取与 queries 列表中相似度最高的得分
    heading_scores = np.max(sim_matrix, axis=0)  # axis=0 对每列取最大值

    # 计算 top K% 的阈值（按数量保留）
    sorted_scores = sorted(heading_scores, reverse=True)
    if sorted_scores:
        cutoff_idx = int(len(sorted_scores) * top_k_ratio)
        threshold = sorted_scores[cutoff_idx] if cutoff_idx < len(sorted_scores) else sorted_scores[-1]
    else:
        threshold = 0.0

    # 过滤 headings，保留 top K%
    for idx, (page_idx, h_idx, _, _) in enumerate(heading_infos):
        score = heading_scores[idx]
        if score < threshold:
            pages[page_idx]["headings"][h_idx] = None  # 标记删除

    # 清理已删除的 headings
    for page in pages:
        page["headings"] = [h for h in page.get("headings", []) if h is not None]


__all__ = [
    "HeadingReranker",
    "RerankerConfig",
    "fallback_2_local_rerank_headings",
    "batch_rerank_pages_and_headings",
]


def batch_rerank_pages_and_headings(
    pages: List[Dict[str, Any]],
    queries: List[str],
    matcher: Union[TransformerMatcher, ModelScopeMatcher],
    scopes: List[str],
    reranker_threshold: float,
    threshold_precision: float,
    preprocess_func: Optional[callable] = None,
    preprocess_headings_func: Optional[callable] = None,
) -> None:
    """批量计算多个 page 和 heading 与多个 query 的语义相似度。

    注意：所有参数必须由调用方明确传递，不使用默认值以避免语义漂移。

    Args:
        pages: Page 字典列表，每个 page 包含 page_title 和 headings
        queries: Query 字符串列表
        matcher: TransformerMatcher 或 ModelScopeMatcher 实例
        scopes: Rerank 范围列表，支持 ["page_title"], ["headings"], ["page_title", "headings"]
        reranker_threshold: Reranker 阈值（调用方从配置传递）
        threshold_precision: 精度阈值（调用方从配置传递）
        preprocess_func: 可选的 page_title 预处理函数
        preprocess_headings_func: 可选的 headings 预处理函数
    """
    if not pages or not queries or not matcher:
        return
    if not scopes:
        return

    # Step 1: 收集 page_titles（始终执行预处理）
    page_titles = []
    for page_idx, page in enumerate(pages):
        title = page.get("page_title", "")
        if preprocess_func:
            title = preprocess_func(title)
            page["page_title"] = title
        page_titles.append(title)

    # Step 2: 批量计算 page_title 相似度
    if "page_title" in scopes and page_titles:
        sim_matrix, _ = matcher.rerank_batch(queries, page_titles)
        for page_idx, _ in enumerate(page_titles):
            max_score = float(np.max(sim_matrix[:, page_idx]))
            pages[page_idx]["rerank_sim"] = max_score
            pages[page_idx]["source"] = "RERANKER"
            # 如果只匹配 page_title，检查阈值并清空 headings
            if scopes == ["page_title"]:
                cond1 = max_score >= reranker_threshold
                cond2 = max_score >= threshold_precision
                if cond1 and cond2:
                    pages[page_idx]["headings"] = []

    # Step 3: 收集 headings 并批量计算相似度
    if "headings" in scopes:
        headings = []  # [(page_idx, heading_idx, text), ...]
        for page_idx, page in enumerate(pages):
            original_headings = page.get("headings", [])
            if not original_headings:
                continue
            if preprocess_headings_func:
                processed_headings = preprocess_headings_func(original_headings)
            else:
                processed_headings = original_headings
            for h_idx, heading in enumerate(processed_headings):
                headings.append((page_idx, h_idx, heading["text"]))
            page["headings"] = processed_headings

        if headings:
            heading_texts = [h[2] for h in headings]
            sim_matrix, _ = matcher.rerank_batch(queries, heading_texts)
            for heading_idx, (page_idx, h_idx, _) in enumerate(headings):
                max_score = float(np.max(sim_matrix[:, heading_idx]))
                if h_idx < len(pages[page_idx]["headings"]):
                    pages[page_idx]["headings"][h_idx]["rerank_sim"] = max_score
                    pages[page_idx]["headings"][h_idx]["is_basic"] = (
                        max_score >= reranker_threshold
                    )
                    pages[page_idx]["headings"][h_idx]["source"] = "RERANKER"
