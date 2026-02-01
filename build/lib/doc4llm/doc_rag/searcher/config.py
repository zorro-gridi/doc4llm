"""
Search Configuration - Configuration classes for the searcher module.

This module provides dataclasses for managing all search-related configuration
in a structured and type-safe way.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BM25Config:
    """BM25 ranking configuration.

    Attributes:
        k1: Term frequency saturation parameter (default 1.2)
        b: Length normalization parameter (default 0.75)
        min_token_length: Minimum token length to include (default 2)
        max_token_length: Maximum token length to include (default 30)
        lowercase: Whether to lowercase tokens (default True)
        stemming: Whether to apply word stemming (default True)
    """
    k1: float = 1.2
    b: float = 0.75
    min_token_length: int = 2
    max_token_length: int = 30
    lowercase: bool = True
    stemming: bool = True


@dataclass
class ThresholdConfig:
    """Matching threshold configuration.

    Attributes:
        page_title: Page title matching threshold (default 0.6)
        headings: Heading matching threshold (default 0.25)
        precision: Precision matching threshold for headings (default 0.7)
        doc_set: Doc-set matching threshold (default 0.6)
    """
    page_title: float = 0.6
    headings: float = 0.25
    precision: float = 0.7
    doc_set: float = 0.6


@dataclass
class RerankerConfig:
    """Transformer reranker configuration.

    Attributes:
        enabled: Whether to enable reranking (default False)
        model_zh: Chinese model ID (default "BAAI/bge-large-zh-v1.5")
        model_en: English model ID (default "BAAI/bge-large-en-v1.5")
        threshold: Minimum similarity score for headings (default 0.68)
        top_k: Maximum headings to keep after reranking (default None)
        lang_threshold: Language detection threshold (default 0.9)
        embedding_provider: Provider - "hf" or "ms" (default "ms")
        embedding_model_id: Custom model ID for ModelScope (default None)
        hf_inference_provider: HuggingFace inference provider (default "auto")
    """
    enabled: bool = False
    model_zh: str = "BAAI/bge-large-zh-v1.5"
    model_en: str = "BAAI/bge-large-en-v1.5"
    threshold: float = 0.68
    top_k: Optional[int] = None
    lang_threshold: float = 0.9
    embedding_provider: str = "ms"
    embedding_model_id: Optional[str] = None
    hf_inference_provider: str = "auto"


@dataclass
class FallbackConfig:
    """Fallback strategy configuration.

    Attributes:
        mode: Fallback execution mode - "serial" or "parallel" (default "parallel")
        fallback_2_local_rerank: Enable local reranking for fallback 2 (default True)
        fallback_2_local_rerank_ratio: Retention ratio for local reranking (0.0-1.0, default 0.8)
        local_device: Device for local reranking - "cpu" or "cuda" (default "cpu")
        local_model_zh: Chinese model for local reranking (default "BAAI/bge-base-zh-v1.5")
        local_model_en: English model for local reranking (default "BAAI/bge-base-en-v1.5")
    """
    mode: str = "parallel"
    fallback_2_local_rerank: bool = True
    fallback_2_local_rerank_ratio: float = 0.8
    local_device: str = "cpu"
    local_model_zh: str = "BAAI/bge-base-zh-v1.5"
    local_model_en: str = "BAAI/bge-base-en-v1.5"


@dataclass
class AnchorSearcherConfig:
    """Anchor/TOC searcher configuration.

    Attributes:
        threshold_headings: Heading matching threshold (default 0.25)
        threshold_precision: Precision matching threshold (default 0.7)
        debug: Enable debug mode (default False)
    """
    threshold_headings: float = 0.25
    threshold_precision: float = 0.7
    debug: bool = False


@dataclass
class ContentSearcherConfig:
    """Content searcher configuration.

    Attributes:
        domain_nouns: Domain-specific nouns for search (default empty list)
        max_results: Maximum results to return (default 20)
        context_lines: Lines of context to include (default 100)
        debug: Enable debug mode (default False)
    """
    domain_nouns: List[str] = field(default_factory=list)
    max_results: int = 20
    context_lines: int = 100
    debug: bool = False


@dataclass
class SearchConfig:
    """Complete search configuration.

    This is the top-level configuration class that combines all
    configuration aspects of the searcher module.

    Attributes:
        bm25: BM25 ranking configuration
        thresholds: Matching threshold configuration
        reranker: Transformer reranker configuration
        fallback: Fallback strategy configuration
        anchor: Anchor/TOC searcher configuration
        content: Content searcher configuration
        min_page_titles: Minimum page titles per doc-set (default 2)
        min_headings: Minimum headings per doc-set (default 2)
        debug: Enable debug mode (default False)
        domain_nouns: Domain-specific nouns (default empty list)
        predicate_verbs: Predicate verbs for preprocessing (default empty list)
        skiped_keywords: Keywords to skip during search (default empty list)
        skiped_keywords_path: Path to skiped_keywords.txt (default None)
        rerank_scopes: Rerank scope list (default ["page_title"])
        hierarchical_filter: Enable hierarchical heading filtering (default True)
    """
    bm25: BM25Config = field(default_factory=BM25Config)
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    reranker: RerankerConfig = field(default_factory=RerankerConfig)
    fallback: FallbackConfig = field(default_factory=FallbackConfig)
    anchor: AnchorSearcherConfig = field(default_factory=AnchorSearcherConfig)
    content: ContentSearcherConfig = field(default_factory=ContentSearcherConfig)
    min_page_titles: int = 2
    min_headings: int = 2
    debug: bool = False
    domain_nouns: List[str] = field(default_factory=list)
    predicate_verbs: List[str] = field(default_factory=list)
    skiped_keywords: List[str] = field(default_factory=list)
    skiped_keywords_path: Optional[str] = None
    rerank_scopes: List[str] = field(default_factory=lambda: ["page_title"])
    hierarchical_filter: bool = True

    def to_dict(self) -> dict:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        return {
            "bm25": {
                "k1": self.bm25.k1,
                "b": self.bm25.b,
            },
            "thresholds": {
                "page_title": self.thresholds.page_title,
                "headings": self.thresholds.headings,
                "precision": self.thresholds.precision,
                "doc_set": self.thresholds.doc_set,
            },
            "reranker": {
                "enabled": self.reranker.enabled,
                "model_zh": self.reranker.model_zh,
                "model_en": self.reranker.model_en,
                "threshold": self.reranker.threshold,
                "top_k": self.reranker.top_k,
                "lang_threshold": self.reranker.lang_threshold,
                "embedding_provider": self.reranker.embedding_provider,
                "embedding_model_id": self.reranker.embedding_model_id,
            },
            "fallback": {
                "mode": self.fallback.mode,
                "fallback_2_local_rerank": self.fallback.fallback_2_local_rerank,
                "fallback_2_local_rerank_ratio": self.fallback.fallback_2_local_rerank_ratio,
                "local_device": self.fallback.local_device,
            },
            "min_page_titles": self.min_page_titles,
            "min_headings": self.min_headings,
            "debug": self.debug,
            "domain_nouns": self.domain_nouns,
            "predicate_verbs": self.predicate_verbs,
            "skiped_keywords": self.skiped_keywords,
            "skiped_keywords_path": self.skiped_keywords_path,
            "rerank_scopes": self.rerank_scopes,
            "hierarchical_filter": self.hierarchical_filter,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SearchConfig":
        """Create configuration from dictionary.

        Args:
            data: Dictionary with configuration values

        Returns:
            SearchConfig instance
        """
        config = cls()

        if "bm25" in data:
            if "k1" in data["bm25"]:
                config.bm25.k1 = data["bm25"]["k1"]
            if "b" in data["bm25"]:
                config.bm25.b = data["bm25"]["b"]

        if "thresholds" in data:
            ts = data["thresholds"]
            if "page_title" in ts:
                config.thresholds.page_title = ts["page_title"]
            if "headings" in ts:
                config.thresholds.headings = ts["headings"]
            if "precision" in ts:
                config.thresholds.precision = ts["precision"]
            if "doc_set" in ts:
                config.thresholds.doc_set = ts["doc_set"]

        if "reranker" in data:
            rnk = data["reranker"]
            if "enabled" in rnk:
                config.reranker.enabled = rnk["enabled"]
            if "model_zh" in rnk:
                config.reranker.model_zh = rnk["model_zh"]
            if "model_en" in rnk:
                config.reranker.model_en = rnk["model_en"]
            if "threshold" in rnk:
                config.reranker.threshold = rnk["threshold"]
            if "top_k" in rnk:
                config.reranker.top_k = rnk["top_k"]
            if "lang_threshold" in rnk:
                config.reranker.lang_threshold = rnk["lang_threshold"]
            if "embedding_provider" in rnk:
                config.reranker.embedding_provider = rnk["embedding_provider"]
            if "embedding_model_id" in rnk:
                config.reranker.embedding_model_id = rnk["embedding_model_id"]

        if "fallback" in data:
            fb = data["fallback"]
            if "mode" in fb:
                config.fallback.mode = fb["mode"]
            if "fallback_2_local_rerank" in fb:
                config.fallback.fallback_2_local_rerank = fb["fallback_2_local_rerank"]
            if "fallback_2_local_rerank_ratio" in fb:
                config.fallback.fallback_2_local_rerank_ratio = fb["fallback_2_local_rerank_ratio"]
            if "local_device" in fb:
                config.fallback.local_device = fb["local_device"]

        # Simple scalar values
        scalar_fields = [
            ("min_page_titles", int),
            ("min_headings", int),
            ("debug", bool),
            ("domain_nouns", list),
            ("predicate_verbs", list),
            ("skiped_keywords", list),
            ("skiped_keywords_path", str),
            ("rerank_scopes", list),
            ("hierarchical_filter", bool),
        ]

        for field_name, field_type in scalar_fields:
            if field_name in data:
                value = data[field_name]
                if value is not None:
                    setattr(config, field_name, value)

        return config


__all__ = [
    "BM25Config",
    "ThresholdConfig",
    "RerankerConfig",
    "FallbackConfig",
    "AnchorSearcherConfig",
    "ContentSearcherConfig",
    "SearchConfig",
]
