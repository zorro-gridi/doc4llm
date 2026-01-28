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

            # Filter by threshold
            if semantic_score < self.config.min_score_threshold:
                continue

            # Preserve original BM25 score before updating with semantic score
            original_bm25_score = heading.get("score", 0.0)
            updated_heading = dict(heading)
            updated_heading["bm25_sim"] = original_bm25_score  # Preserve BM25 score
            updated_heading["score"] = semantic_score  # This becomes reranker score
            # Update is_basic and is_precision based on new score
            updated_heading["is_basic"] = True  # Passed threshold, so it's basic
            # Keep original is_precision if exists, otherwise set based on higher threshold
            if "is_precision" in heading:
                updated_heading["is_precision"] = (
                    semantic_score >= (self.config.min_score_threshold + 0.2)
                )

            reranked_headings.append(updated_heading)

        # Sort by score descending
        reranked_headings.sort(key=lambda h: h.get("score", 0.0), reverse=True)

        # Apply top_k limit if specified
        if self.config.top_k is not None and self.config.top_k > 0:
            reranked_headings = reranked_headings[:self.config.top_k]

        return reranked_headings


__all__ = [
    "HeadingReranker",
    "RerankerConfig",
]
