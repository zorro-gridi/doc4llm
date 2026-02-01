"""
Markdown Document Searcher API - BM25 based retrieval with transformer reranking.

This module provides CLI + API interface for searching markdown documents
in the doc4llm knowledge base. Uses BM25 scoring for doc-set, page_title,
and heading matching. Supports transformer-based semantic re-ranking.

Core BM25 Parameters:
    k1: Term frequency saturation parameter (default 1.2)
    b: Length normalization parameter (default 0.75)

Matching Thresholds:
    threshold_page_title: Page title match threshold, uses full TOC (default 0.6)
    threshold_headings: Heading match threshold, single heading text (default 0.25)
    threshold_precision: Precision match threshold for headings (default 0.7)

Reranker Parameters:
    reranker_enabled: Enable transformer re-ranking (default False)
    reranker_threshold: Minimum similarity score for headings (default 0.5)
    reranker_top_k: Maximum number of headings to keep after re-ranking (default None)
    embedding_provider: Reranker provider - "hf" (HuggingFace TransformerMatcher) or "ms" (ModelScope ModelScopeMatcher) (default "ms")
    embedding_model_id: Custom model ID for ModelScope provider (default: Qwen/Qwen3-Embedding-8B)
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .content_searcher import ContentSearcher
from .anchor_searcher import AnchorSearcher, AnchorSearcherConfig
from .text_preprocessor import TextPreprocessor, LanguageDetector
from .search_utils import debug_print
from .fallback_merger import FallbackMerger
from .common_utils import filter_query_keywords, extract_heading_level, normalize_heading_text

import numpy as np

# Import local modules
from .bm25_recall import (
    BM25Recall,
    BM25Config,
    calculate_bm25_similarity,
)
from .output_format import OutputFormatter
from .reranker import HeadingReranker, RerankerConfig, batch_rerank_pages_and_headings

# Import transformer matcher from md_doc_retrieval
import sys

for _ in range(4):  # Search up to 4 levels up
    if (Path(__file__).parent.parent / "doc4llm").exists():
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        break

from doc4llm.tool.md_doc_retrieval.transformer_matcher import (
    TransformerMatcher,
    TransformerConfig,
)


# Sentinel value to detect if a parameter was explicitly passed
_NOT_SET = object()



@dataclass
class DocSearcherAPI:
    """
    Markdown Document Searcher API.

    Provides BM25-based document retrieval from docTOC.md files with optional
    transformer-based semantic re-ranking.

    Args:
        base_dir: Knowledge base root directory (loaded from knowledge_base.json)
        config: Configuration data (JSON dict) or path to .json config file.
                Supports all parameters listed below via JSON keys.
        bm25_k1: BM25 k1 parameter (default 1.2)
        bm25_b: BM25 b parameter (default 0.75)
        threshold_page_title: Page title matching threshold (default 0.6)
        threshold_headings: Heading matching threshold (default 0.25)
        threshold_precision: Precision matching threshold (default 0.7)
        threshold_doc_set: Doc-set matching threshold (default 0.6)
        min_page_titles: Minimum page titles per doc-set (default 1)
        min_headings: Minimum headings per doc-set (default 2)
        debug: Enable debug mode (default False)
        reranker_enabled: Enable transformer re-ranking (default False)
        reranker_model_zh: Chinese model ID (default "BAAI/bge-large-zh-v1.5")
        reranker_model_en: English model ID (default "BAAI/bge-large-en-v1.5")
        reranker_threshold: Minimum similarity score for headings (default 0.5)
        reranker_top_k: Maximum headings to keep after re-ranking (default None)
        reranker_lang_threshold: Language detection threshold (default 0.3)
        hierarchical_filter: Enable hierarchical heading filtering (default True)
        fallback_mode: Fallback strategy execution mode, "serial" or "parallel" (default "parallel")
        embedding_provider: Reranker provider - "hf" (HuggingFace TransformerMatcher) or "ms" (ModelScope ModelScopeMatcher) (default "ms")
        embedding_model_id: Custom model ID for ModelScope provider (default: Qwen/Qwen3-Embedding-8B)
        hf_inference_provider: HuggingFace inference provider for HF embedding provider (default: "auto")
        domain_nouns: List of domain-specific nouns for text preprocessing (default [])
        predicate_verbs: List of predicate verbs for text preprocessing (default [])
        skiped_keywords: List of keywords to skip during search (default [])
        skiped_keywords_path: Custom path for skiped_keywords.txt file (default None)
        rerank_scopes: Rerank scope list - ["page_title"], ["headings"], or ["page_title", "headings"] (default ["page_title"])

    Attributes:
        base_dir: Knowledge base root directory
        config: Configuration dictionary
    """

    base_dir: str
    config: Optional[Union[Dict[str, Any], str]] = None
    bm25_k1: float = _NOT_SET
    bm25_b: float = _NOT_SET
    threshold_page_title: float = _NOT_SET
    threshold_headings: float = _NOT_SET
    threshold_precision: float = _NOT_SET
    threshold_doc_set: float = _NOT_SET
    min_page_titles: int = _NOT_SET
    min_headings: int = _NOT_SET
    debug: bool = _NOT_SET
    reranker_enabled: bool = _NOT_SET
    reranker_model_zh: str = _NOT_SET
    reranker_model_en: str = _NOT_SET
    local_reranker_model_zh: str = _NOT_SET
    local_reranker_model_en: str = _NOT_SET
    reranker_threshold: float = _NOT_SET
    reranker_top_k: Optional[int] = _NOT_SET
    reranker_lang_threshold: float = _NOT_SET
    hierarchical_filter: bool = _NOT_SET
    fallback_mode: str = _NOT_SET
    embedding_provider: str = _NOT_SET
    embedding_model_id: Optional[str] = _NOT_SET
    hf_inference_provider: str = _NOT_SET
    domain_nouns: List[str] = _NOT_SET
    predicate_verbs: List[str] = _NOT_SET
    skiped_keywords: List[str] = _NOT_SET
    skiped_keywords_path: Optional[str] = _NOT_SET
    rerank_scopes: List[str] = _NOT_SET
    fallback_2_local_rerank: bool = _NOT_SET
    fallback_2_local_device: str = _NOT_SET
    fallback_2_local_rerank_ratio: float = _NOT_SET

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from dict or .json file.

        Returns:
            Configuration dictionary
        """
        if self.config is None:
            return {}

        if isinstance(self.config, dict):
            return self.config

        if isinstance(self.config, str) and self.config.endswith(".json"):
            config_path = Path(self.config).expanduser()
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                print(
                    f"[WARNING] Config file not found: '{self.config}'. Using default config."
                )
                return {}

        return {}

    def __post_init__(self):
        # Load config from dict or file
        loaded_config = self._load_config()

        # Validate base_dir before applying config
        if self.base_dir:
            path = Path(self.base_dir).expanduser()
            if not path.exists():
                raise ValueError(f"base_dir does not exist: '{self.base_dir}'")
            if not path.is_dir():
                raise ValueError(f"base_dir is not a directory: '{self.base_dir}'")
            self.base_dir = str(path.resolve())
        else:
            raise ValueError(f"base_dir must be set!")

        # Define the actual default values
        default_values = {
            # BM25 parameters
            "bm25_k1": 1.2,
            "bm25_b": 0.75,
            # Threshold parameters
            "threshold_page_title": 0.6,
            "threshold_headings": 0.25,
            "threshold_precision": 0.7,
            "threshold_doc_set": 0.6,
            # Minimum count parameters
            "min_page_titles": 2,
            "min_headings": 2,
            # Debug mode
            "debug": False,
            # Reranker parameters
            "reranker_enabled": False,
            "reranker_model_zh": "BAAI/bge-large-zh-v1.5",
            "reranker_model_en": "BAAI/bge-large-en-v1.5",
            "local_reranker_model_zh": "BAAI/bge-base-zh-v1.5",
            "local_reranker_model_en": "BAAI/bge-base-en-v1.5",
            "reranker_threshold": 0.68,
            "reranker_top_k": None,
            "reranker_lang_threshold": 0.9,
            # Filter parameters
            "hierarchical_filter": True,
            "fallback_mode": "parallel",
            # Embedding provider
            "embedding_provider": "ms",
            "embedding_model_id": None,
            "hf_inference_provider": "auto",
            # Preprocessing parameters (lists use empty list as default)
            "domain_nouns": [],
            "predicate_verbs": [],
            "skiped_keywords": [],
            "skiped_keywords_path": None,
            "rerank_scopes": ["page_title"],
            # FALLBACK_2 local rerank parameters
            "fallback_2_local_rerank": True,
            "fallback_2_local_device": "cpu",
            "fallback_2_local_rerank_ratio": 0.8,
        }

        # Build config dict and set instance attributes
        # Priority: explicit parameter > config > default
        self.config = {}
        for key, default_value in default_values.items():
            current_value = getattr(self, key, _NOT_SET)

            if current_value is not _NOT_SET:
                # User explicitly passed this parameter
                self.config[key] = current_value
            elif key in loaded_config:
                # Use config value
                self.config[key] = loaded_config[key]
                setattr(self, key, loaded_config[key])
            else:
                # Use default value
                self.config[key] = default_value
                setattr(self, key, default_value)

        # Validate fallback_mode parameter
        if self.fallback_mode not in ("serial", "parallel"):
            raise ValueError(
                f"fallback_mode must be 'serial' or 'parallel', got: {self.fallback_mode}"
            )

        # Validate embedding_provider parameter
        if self.embedding_provider not in ("hf", "ms"):
            raise ValueError(
                f"embedding_provider must be 'hf' or 'ms', got: {self.embedding_provider}"
            )

        # Validate rerank_scopes parameter
        valid_scopes = {"page_title", "headings"}
        if self.rerank_scopes:
            invalid_scopes = set(self.rerank_scopes) - valid_scopes
            if invalid_scopes:
                raise ValueError(
                    f"Invalid rerank_scopes: {invalid_scopes}. "
                    f"Valid options: {sorted(valid_scopes)}"
                )

        # Initialize reranker if enabled
        self._reranker: Optional[HeadingReranker] = None
        if self.reranker_enabled:
            if self.embedding_provider == "hf":
                # HuggingFace TransformerMatcher
                from doc4llm.tool.md_doc_retrieval.transformer_matcher import (
                    TransformerMatcher,
                    TransformerConfig,
                )

                transformer_config = TransformerConfig(
                    model_zh=self.reranker_model_zh,
                    model_en=self.reranker_model_en,
                    lang_threshold=self.reranker_lang_threshold,
                    hf_inference_provider=self.hf_inference_provider,
                )
                matcher = TransformerMatcher(transformer_config)
            elif self.embedding_provider == "ms":
                # ModelScope ModelScopeMatcher
                from doc4llm.tool.md_doc_retrieval.modelscope_matcher import (
                    ModelScopeMatcher,
                    ModelScopeConfig,
                )

                model_id = self.embedding_model_id or "Qwen/Qwen3-Embedding-8B"
                modelscope_config = ModelScopeConfig(model_id=model_id)
                matcher = ModelScopeMatcher(modelscope_config)
            else:
                raise ValueError(
                    f"Unknown embedding_provider: {self.embedding_provider}. "
                    f"Supported values: 'hf' (HuggingFace), 'ms' (ModelScope)"
                )

            reranker_config = RerankerConfig(
                enabled=True,
                min_score_threshold=self.reranker_threshold,
                top_k=self.reranker_top_k,
            )
            self._reranker = HeadingReranker(reranker_config, matcher)

        # 初始化 FALLBACK_2 本地向量化匹配器
        self._fallback_2_local_matcher: Optional[TransformerMatcher] = None
        if self.reranker_enabled and self.fallback_2_local_rerank:
            from doc4llm.tool.md_doc_retrieval.transformer_matcher import (
                TransformerMatcher as LocalTransformerMatcher,
                TransformerConfig,
            )
            # 使用独立的本地模型参数（若未设置则回退到 reranker_model 配置）
            local_model_zh = (
                self.local_reranker_model_zh or self.reranker_model_zh
            )
            local_model_en = (
                self.local_reranker_model_en or self.reranker_model_en
            )
            transformer_config = TransformerConfig(
                use_local=True,  # 强制使用本地模式
                device=self.fallback_2_local_device,
                local_model_zh=local_model_zh,
                local_model_en=local_model_en,
                lang_threshold=self.reranker_lang_threshold,
            )
            self._fallback_2_local_matcher = LocalTransformerMatcher(transformer_config)

        # Initialize FALLBACK_1 AnchorSearcher (pure Python implementation)
        anchor_config = AnchorSearcherConfig(
            threshold_headings=self.threshold_headings,
            threshold_precision=self.threshold_precision,
            debug=self.debug,
        )
        self._anchor_searcher = AnchorSearcher(base_dir=self.base_dir, config=anchor_config)

        # Initialize TextPreprocessor
        self._text_preprocessor = TextPreprocessor(
            domain_nouns=self.domain_nouns,
            predicate_verbs=self.predicate_verbs,
            skiped_keywords=self.skiped_keywords,
            reranker_lang_threshold=self.reranker_lang_threshold,
        )

        # Initialize LanguageDetector
        self._language_detector = LanguageDetector(
            base_dir=self.base_dir,
            lang_threshold=self.reranker_lang_threshold,
            debug=self.debug,
        )

        # Load skiped_keywords.txt for protected keywords
        if self.skiped_keywords_path:
            skiped_file = Path(self.skiped_keywords_path).expanduser().resolve()
        else:
            skiped_file = Path(__file__).parent / "skiped_keywords.txt"
        if skiped_file.exists():
            self.skiped_keywords = [
                line.strip()
                for line in skiped_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

    def _debug_print(self, message: str):
        """Print debug message."""
        if self.debug:
            print(f"[DEBUG] {message}")

    # ===== Text Preprocessing Delegation Methods =====

    def _detect_language(self, text: str) -> str:
        """Detect text language based on Chinese character ratio."""
        return self._text_preprocessor.detect_language(text)

    def _get_english_stem(self, word: str) -> str:
        """Get English word stem (simple implementation for common plurals)."""
        return self._text_preprocessor._get_english_stem(word)

    def _contains_domain_noun(self, text: str) -> bool:
        """Check if text contains any domain noun (supports English stemming and Chinese substring)."""
        return self._text_preprocessor.contains_domain_noun(text)

    def _preprocess_for_rerank(self, text: str) -> str:
        """Preprocess text for rerank calculation."""
        return self._text_preprocessor.preprocess_for_rerank(text)

    def _preprocess_headings_for_rerank(
        self,
        headings: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Preprocess headings list for rerank calculation."""
        return self._text_preprocessor.preprocess_headings_for_rerank(headings)

    def _get_protected_keywords(self) -> set:
        """Get protected keywords (intersection of skiped_keywords and domain_nouns)."""
        return self._text_preprocessor.get_protected_keywords()

    def _filter_query_keywords(
        self, query: str, skiped_keywords: Optional[List[str]] = None
    ) -> str:
        """Filter out skiped keywords from query string."""
        if skiped_keywords is not None:
            return filter_query_keywords(query, skiped_keywords)
        else:
            # Use TextPreprocessor's skiped_keywords
            return self._text_preprocessor.filter_query_keywords(query)

    # ===== Language Detection Methods =====

    def _detect_docset_language(self, doc_set: str, sample_size: int = 5) -> str:
        """Detect the primary language of a doc-set by sampling docTOC.md files."""
        return self._language_detector.detect_docset_language(doc_set, sample_size)

    def _validate_language_consistency(
        self, query: Union[str, List[str]], doc_set: str
    ) -> None:
        """
        Validate that query language matches corpus language.

        Args:
            query: Search query string or list of query strings
            doc_set: Target doc-set name

        Raises:
            ValueError: If query and corpus languages don't match
        """
        # Detect query language
        queries = [query] if isinstance(query, str) else query
        combined_query = " ".join(queries)
        query_lang = self._detect_language(combined_query)
        self._debug_print(f"Detected query language: {query_lang}")

        # Detect corpus language
        corpus_lang = self._detect_docset_language(doc_set)
        self._debug_print(f"Detected corpus language: {corpus_lang}")

        # Check consistency
        if query_lang != corpus_lang:
            lang_names = {"zh": "中文", "en": "英文"}
            raise ValueError(
                f"Language mismatch detected: Query is in {lang_names[query_lang]} "
                f"but corpus '{doc_set}' is primarily in {lang_names[corpus_lang]}. "
                f"Please use {lang_names[corpus_lang]} queries for this corpus, "
                f"or specify a different doc-set that matches your query language."
            )

    def _find_doc_sets(self) -> List[str]:
        """Find all doc-set directories."""
        base = Path(self.base_dir)
        if not base.exists():
            return []
        doc_sets = []
        for item in base.iterdir():
            if item.is_dir() and "@" in item.name:
                doc_sets.append(item.name)
        return sorted(doc_sets)

    # ===== Fallback Merger =====

    def _merge_fallback_results(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge results from different fallback strategies."""
        merger = FallbackMerger()
        return merger.merge(results)

    def search(
        self, query: Union[str, List[str]], target_doc_sets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute document search.

        Main flow:
            STATE 1: Determine target doc-sets (from target_doc_sets param or auto-detect)
            STATE 2: Identify page-titles using BM25
            STATE 3: Identify headings using BM25
            STATE 4: (Optional) Re-rank headings using transformer
            STATE 5: Return results

        Fallback strategies:
            FALLBACK_1: grep TOC search
            FALLBACK_2: grep context + BM25 re-scoring

        Args:
            query: Search query string or list of query strings
            target_doc_sets: Target doc-sets from md-doc-query-optimizer output.
                             If provided, skip internal Jaccard matching and use directly.
                             If None, auto-detect from available doc-sets.

        Returns:
            Dictionary with:
                - success: bool
                - doc_sets_found: List[str]
                - results: List of matched pages
                - fallback_used: str | None
                - message: str
        """
        # Normalize query to list
        queries = [query] if isinstance(query, str) else query
        # Combine queries for BM25 similarity calculations
        combined_query = " ".join(queries)

        # ===== Query 预处理 - 过滤 skiped_keywords =====
        if self.domain_nouns and self.skiped_keywords:
            # 计算需要过滤的关键词（排除受保护的关键词）
            protected_keywords = self._get_protected_keywords()
            skiped_keywords_filter = [
                kw
                for kw in self.skiped_keywords
                if kw.lower() not in {pk.lower() for pk in protected_keywords}
            ]

            if skiped_keywords_filter:
                filtered_queries = []
                for q in queries:
                    filtered_q = self._filter_query_keywords(q, skiped_keywords_filter)
                    if filtered_q:
                        filtered_queries.append(filtered_q)

                if not filtered_queries:
                    return {
                        "success": False,
                        "doc_sets_found": [],
                        "results": [],
                        "fallback_used": None,
                        "message": "All queries filtered out by skiped_keywords.txt",
                    }

                queries = filtered_queries
                combined_query = " ".join(queries)
        # ===== Query 预处理结束 =====

        # Initialize fallback tracking flags
        toc_fallback = False
        grep_fallback = False

        available_doc_sets = self._find_doc_sets()
        if not available_doc_sets:
            return {
                "success": False,
                "doc_sets_found": [],
                "results": [],
                "fallback_used": None,
                "message": "No doc-sets found",
            }

        # Use provided target_doc_sets or auto-detect
        if target_doc_sets:
            search_doc_sets = [ds for ds in target_doc_sets if ds in available_doc_sets]
            self._debug_print(f"Using provided target_doc_sets: {search_doc_sets}")
        else:
            search_doc_sets = available_doc_sets
            self._debug_print(f"Auto-detected doc-sets: {search_doc_sets}")

        if not search_doc_sets:
            return {
                "success": False,
                "doc_sets_found": [],
                "results": [],
                "fallback_used": None,
                "message": "No matching documentation set found - perform online search",
            }

        # Skip Jaccard matching when target_doc_sets is provided
        # Process all provided doc-sets
        all_results = []

        # BM25 recall initialization (outside loop for efficiency)
        bm25_recall = BM25Recall(
            base_dir=self.base_dir,
            k1=self.bm25_k1,
            b=self.bm25_b,
            threshold_page_title=self.threshold_page_title,
            threshold_headings=self.threshold_headings,
            threshold_precision=self.threshold_precision,
            debug=self.debug,
        )

        for doc_set in search_doc_sets:
            self._debug_print(f"Processing doc-set: {doc_set}")

            # Validate language consistency for each doc-set
            self._validate_language_consistency(query, doc_set)

            # BM25 recall for this doc-set
            scored_pages = bm25_recall.recall_pages(
                doc_set, query, min_headings=self.min_headings
            )
            self._debug_print(f"  Found {len(scored_pages)} scored pages")

            # Transformer re-ranking for headings (only if enabled)
            if self.reranker_enabled and self._reranker:
                self._debug_print("  Applying transformer re-ranking to headings")
                # 使用批量 reranking 替代循环调用
                batch_rerank_pages_and_headings(
                    pages=scored_pages,
                    queries=queries,
                    matcher=self._reranker.matcher,
                    scopes=self.rerank_scopes,
                    reranker_threshold=self.reranker_threshold,
                    threshold_precision=self.threshold_precision,
                    preprocess_func=self._preprocess_for_rerank if self.domain_nouns else None,
                    preprocess_headings_func=self._preprocess_headings_for_rerank,
                )

                for page in scored_pages:
                    original_headings_len = len(page.get("headings", []))

                    # 过滤 headings：根据 is_basic（reranker_threshold）过滤
                    filtered_headings = [
                        h for h in page.get("headings", []) if h.get("is_basic", True)
                    ]

                    # 应用 hierarchical filter
                    if self.hierarchical_filter:
                        from .heading_filter import filter_headings_hierarchically

                        filtered_headings = filter_headings_hierarchically(
                            filtered_headings, page["page_title"]
                        )

                    page["headings"] = filtered_headings
                    page["heading_count"] = len(filtered_headings)
                    page["precision_count"] = sum(
                        1 for h in filtered_headings if h.get("is_precision", False)
                    )
                    self._debug_print(
                        f"    Page: {page['page_title']}, headings: {original_headings_len} -> {len(filtered_headings)}, rerank_sim: {page.get('rerank_sim')}"
                    )

            for page in scored_pages:
                self._debug_print(
                    f"  Page: {page['page_title']}, bm25_sim: {page.get('bm25_sim')}, headings: {page['heading_count']}/{page.get('precision_count', 0)} precision"
                )
                # BM25 召回的结果全部保留
                all_results.append(page)

        self._debug_print(f"Total pages in all_results: {len(all_results)}")

        # Always execute fallback strategies when reranker is disabled
        fallback_used = None
        toc_fallback = False
        grep_fallback = False

        # ========== PARALLEL MODE (default) ==========
        if self.fallback_mode == "parallel":
            self._debug_print(
                "Executing PARALLEL fallback mode (always when reranker disabled)"
            )
            toc_fallback = True
            grep_fallback = True

            all_fallback_results = []
            fallback_strategies = []

            # Execute FALLBACK_1 (without applying reranker yet)
            grep_results = self._anchor_searcher.search(queries, search_doc_sets)
            if grep_results:
                from .bm25_recall import calculate_bm25_similarity, BM25Config

                for result in grep_results:
                    result["bm25_sim"] = calculate_bm25_similarity(
                        combined_query,
                        result.get("heading", ""),
                        BM25Config(k1=self.bm25_k1, b=self.bm25_b),
                    )
                    result["is_basic"] = result["bm25_sim"] >= self.threshold_headings
                    result["is_precision"] = (
                        result["bm25_sim"] >= self.threshold_precision
                    )

                page_map = {}
                for r in grep_results:
                    key = (r["doc_set"], r["page_title"])
                    if key not in page_map:
                        page_map[key] = {
                            "doc_set": r["doc_set"],
                            "page_title": r["page_title"],
                            "toc_path": r["toc_path"],
                            "headings": [],
                            "heading_count": 0,
                            "precision_count": 0,
                            "bm25_sim": r["bm25_sim"],
                            "is_basic": r["is_basic"],
                            "is_precision": r["is_precision"],
                        }
                    page_map[key]["headings"].append(
                        {
                            "text": r["heading"],
                            "level": extract_heading_level(r["heading"]),
                            "bm25_sim": r["bm25_sim"],
                            "is_basic": r["is_basic"],
                            "is_precision": r["is_precision"],
                            "source": r.get("source", "FALLBACK_1"),
                        }
                    )
                    page_map[key]["heading_count"] += 1
                    if r["is_precision"]:
                        page_map[key]["precision_count"] += 1

                all_fallback_results.extend(page_map.values())
                fallback_strategies.append("FALLBACK_1")

            # FALLBACK_2 results (ContentSearcher)
            context_results = []
            if self.domain_nouns:
                self._debug_print("Using FALLBACK_2: Pythonic context search")
                searcher = ContentSearcher(
                    base_dir=self.base_dir,
                    domain_nouns=self.domain_nouns,
                    max_results=20,
                    context_lines=100,
                    debug=self.debug,
                )
                context_results = searcher.search(queries, search_doc_sets)
                # 添加兼容性字段
                for result in context_results:
                    result["bm25_sim"] = 0.0
                    result["is_basic"] = True
                    result["is_precision"] = False
                self._debug_print(f"FALLBACK_2: found {len(context_results)} results")
            self._debug_print(f"DEBUG: context_results count = {len(context_results)}")
            if context_results:
                # Convert "heading" to "headings" list for consistency
                for page in context_results:
                    page["headings"] = [
                        {
                            "text": page["heading"],
                            "level": extract_heading_level(page["heading"]),
                            "bm25_sim": page["bm25_sim"],
                            "is_basic": page.get("is_basic", True),
                            "is_precision": page.get("is_precision", False),
                            "related_context": page.get("related_context", ""),
                            "source": page.get("source", "FALLBACK_2"),
                        }
                    ]
                    page["heading_count"] = 1
                    page["precision_count"] = (
                        1 if page.get("is_precision", False) else 0
                    )

                all_fallback_results.extend(context_results)
                fallback_strategies.append("FALLBACK_2")
                self._debug_print(f"DEBUG: after extend, all_fallback_results count = {len(all_fallback_results)}")
                self._debug_print(f"DEBUG: fallback_strategies = {fallback_strategies}")

            # Merge results from both fallback strategies
            if all_fallback_results:
                merged_fallback = self._merge_fallback_results(all_fallback_results)
                self._debug_print(f"DEBUG: merged_fallback count = {len(merged_fallback)}")

                # 去重：BM25 召回结果与 fallback 结果合并
                # 策略：FALLBACK 结果增强 BM25 结果（添加 related_context）
                seen_pages = {}
                deduped_results = []
                for page in scored_pages + merged_fallback:
                    key = (page["doc_set"], page["page_title"])
                    if key not in seen_pages:
                        seen_pages[key] = page
                        deduped_results.append(page)
                    else:
                        existing = seen_pages[key]
                        # 增强模式：FALLBACK 结果更新 BM25 结果的 headings
                        fallback_headings = page.get("headings", [])
                        bm25_headings = existing.get("headings", [])

                        # 遍历 fallback headings，更新或添加到 existing headings
                        for fb_heading in fallback_headings:
                            fb_text = fb_heading.get("text", "")
                            fb_normalized = normalize_heading_text(fb_text)
                            fb_related_ctx = fb_heading.get("related_context", "")
                            fb_source = fb_heading.get("source", "")

                            # 查找是否已存在相同 heading（使用规范化匹配）
                            existing_heading = None
                            existing_normalized = None
                            for eh in bm25_headings:
                                eh_normalized = normalize_heading_text(eh.get("text", ""))
                                if eh_normalized == fb_normalized:
                                    existing_heading = eh
                                    existing_normalized = eh_normalized
                                    break

                            if existing_heading:
                                # 如果已存在 heading，更新 related_context 和 source
                                if fb_related_ctx and not existing_heading.get("related_context"):
                                    existing_heading["related_context"] = fb_related_ctx
                                if fb_source and fb_source == "FALLBACK_2":
                                    existing_heading["source"] = fb_source
                            else:
                                # 如果不存在，添加到 headings 列表
                                bm25_headings.append(fb_heading)

                        # 保留 BM25 结果的基本属性，只更新 headings
                        existing["headings"] = bm25_headings
                        existing["heading_count"] = len(bm25_headings)
                        existing["precision_count"] = sum(
                            1 for h in bm25_headings if h.get("is_precision", False)
                        )

                all_results = deduped_results
                self._debug_print(f"DEBUG: all_results set to deduped_results, count = {len(all_results)}")

                # FALLBACK_2 本地向量化匹配（基于 related_context）
                if (self.fallback_2_local_rerank and
                    self._fallback_2_local_matcher and
                    all_results):
                    from .reranker import fallback_2_local_rerank_headings
                    fallback_2_local_rerank_headings(
                        matcher=self._fallback_2_local_matcher,
                        pages=all_results,
                        queries=queries,
                        preprocess_func=self._preprocess_for_rerank if self.domain_nouns else None,
                        top_k_ratio=self.fallback_2_local_rerank_ratio,
                    )

                # Apply reranker once to merged results
                if self.reranker_enabled and self._reranker:
                    self._debug_print(
                        "  Applying transformer re-ranking to merged PARALLEL fallback results"
                    )
                    # 使用批量 reranking
                    batch_rerank_pages_and_headings(
                        pages=all_results,
                        queries=queries,
                        matcher=self._reranker.matcher,
                        scopes=self.rerank_scopes,
                        reranker_threshold=self.reranker_threshold,
                        threshold_precision=self.threshold_precision,
                        preprocess_func=self._preprocess_for_rerank if self.domain_nouns else None,
                        preprocess_headings_func=self._preprocess_headings_for_rerank,
                    )

                    for page in all_results:
                        # 当 rerank_scopes 不包含 "headings" 时，跳过 heading rerank 处理
                        if "headings" not in self.rerank_scopes:
                            continue
                        if not page.get("headings"):
                            continue

                        reranked_headings = []
                        for heading in page["headings"]:
                            semantic_score = heading.get("rerank_sim") or 0.0
                            if (
                                semantic_score
                                < self._reranker.config.min_score_threshold
                            ):
                                continue
                            original_bm25_score = heading.get("bm25_sim") or 0.0
                            updated_heading = dict(heading)
                            updated_heading["bm25_sim"] = original_bm25_score
                            updated_heading["rerank_sim"] = semantic_score
                            updated_heading["is_basic"] = True
                            precision_threshold = (
                                self._reranker.config.min_score_threshold + 0.2
                            )
                            updated_heading["is_precision"] = (
                                semantic_score >= precision_threshold
                            )
                            reranked_headings.append(updated_heading)

                        # BUG FIX: 如果没有 heading 通过阈值，保留原始 heading（包含 related_context）
                        if not reranked_headings:
                            reranked_headings = list(page["headings"])

                        reranked_headings.sort(
                            key=lambda h: h.get("rerank_sim") or 0.0, reverse=True
                        )
                        if (
                            self._reranker.config.top_k is not None
                            and self._reranker.config.top_k > 0
                        ):
                            reranked_headings = reranked_headings[
                                : self._reranker.config.top_k
                            ]
                        page["headings"] = reranked_headings
                        page["heading_count"] = len(reranked_headings)
                        page["precision_count"] = sum(
                            1
                            for h in reranked_headings
                            if h.get("is_precision", False)
                        )

                # Set fallback_used outside reranker condition block (for reranker_enabled=False)
                if all_fallback_results:
                    fallback_used = (
                        "+".join(fallback_strategies) if fallback_strategies else None
                    )
                    self._debug_print(f"DEBUG: fallback_used set to {fallback_used}")

            # ========== SERIAL MODE (backward compatible) ==========
            if self.fallback_mode == "serial":
                self._debug_print(
                    "Executing SERIAL fallback mode (always when reranker disabled)"
                )

                # FALLBACK_1
                toc_fallback = True
                grep_results = self._anchor_searcher.search(query, search_doc_sets)

                if grep_results:
                    from .bm25_recall import calculate_bm25_similarity, BM25Config

                    for result in grep_results:
                        result["bm25_sim"] = calculate_bm25_similarity(
                            combined_query,
                            result.get("heading", ""),
                            BM25Config(k1=self.bm25_k1, b=self.bm25_b),
                        )
                        result["is_basic"] = (
                            result["bm25_sim"] >= self.threshold_headings
                        )
                        result["is_precision"] = (
                            result["bm25_sim"] >= self.threshold_precision
                        )

                    page_map = {}
                    for r in grep_results:
                        key = (r["doc_set"], r["page_title"])
                        if key not in page_map:
                            page_map[key] = {
                                "doc_set": r["doc_set"],
                                "page_title": r["page_title"],
                                "toc_path": r["toc_path"],
                                "headings": [],
                                "heading_count": 0,
                                "precision_count": 0,
                                "bm25_sim": r["bm25_sim"],
                                "is_basic": r["is_basic"],
                                "is_precision": r["is_precision"],
                            }
                        page_map[key]["headings"].append(
                            {
                                "text": r["heading"],
                                "level": extract_heading_level(r["heading"]),
                                "bm25_sim": r["bm25_sim"],
                                "is_basic": r["is_basic"],
                                "is_precision": r["is_precision"],
                            }
                        )
                        page_map[key]["heading_count"] += 1
                        if r["is_precision"]:
                            page_map[key]["precision_count"] += 1

                    # Apply reranker if enabled for FALLBACK_1 (serial mode)
                    if self.reranker_enabled and self._reranker:
                        self._debug_print(
                            "  Applying transformer re-ranking to FALLBACK_1 results"
                        )
                        batch_rerank_pages_and_headings(
                            pages=list(page_map.values()),
                            queries=queries,
                            matcher=self._reranker.matcher,
                            scopes=self.rerank_scopes,
                            reranker_threshold=self.reranker_threshold,
                            threshold_precision=self.threshold_precision,
                            preprocess_func=self._preprocess_for_rerank if self.domain_nouns else None,
                            preprocess_headings_func=self._preprocess_headings_for_rerank,
                        )

                        for page in page_map.values():
                            # 当 rerank_scopes 不包含 "headings" 时，跳过 heading rerank 处理
                            if "headings" not in self.rerank_scopes:
                                continue
                            if not page.get("headings"):
                                continue

                            reranked_headings = []
                            for heading in page["headings"]:
                                semantic_score = heading.get("rerank_sim") or 0.0
                                if (
                                    semantic_score
                                    < self._reranker.config.min_score_threshold
                                ):
                                    continue
                                original_bm25_score = heading.get("bm25_sim") or 0.0
                                updated_heading = dict(heading)
                                updated_heading["bm25_sim"] = original_bm25_score
                                updated_heading["rerank_sim"] = semantic_score
                                updated_heading["is_basic"] = True
                                precision_threshold = (
                                    self._reranker.config.min_score_threshold + 0.2
                                )
                                updated_heading["is_precision"] = (
                                    semantic_score >= precision_threshold
                                )
                                reranked_headings.append(updated_heading)
                            reranked_headings.sort(
                                key=lambda h: h.get("rerank_sim") or 0.0, reverse=True
                            )
                            if (
                                self._reranker.config.top_k is not None
                                and self._reranker.config.top_k > 0
                            ):
                                reranked_headings = reranked_headings[
                                    : self._reranker.config.top_k
                                ]
                            page["headings"] = reranked_headings
                            page["heading_count"] = len(reranked_headings)
                            page["precision_count"] = sum(
                                1
                                for h in reranked_headings
                                if h.get("is_precision", False)
                            )

                    all_results.extend(list(page_map.values()))
                    fallback_used = "FALLBACK_1"

                # FALLBACK_2 (ContentSearcher)
                # 在 FALLBACK_1 之后执行，使用 domain_nouns 进行精确匹配
                grep_fallback = True
                context_results = []
                if self.domain_nouns:
                    self._debug_print("Using FALLBACK_2: Pythonic context search")
                    searcher = ContentSearcher(
                        base_dir=self.base_dir,
                        domain_nouns=self.domain_nouns,
                        max_results=20,
                        context_lines=100,
                        debug=self.debug,
                    )
                    context_results = searcher.search(queries, search_doc_sets)
                    # 添加兼容性字段
                    for result in context_results:
                        result["bm25_sim"] = 0.0
                        result["is_basic"] = True
                        result["is_precision"] = False
                    self._debug_print(f"FALLBACK_2: found {len(context_results)} results")

                if context_results:
                    # Apply reranker if enabled for FALLBACK_2 (serial mode)
                    if self.reranker_enabled and self._reranker:
                        self._debug_print(
                            "  Applying transformer re-ranking to FALLBACK_2 results"
                        )
                        # 使用批量 reranking
                        batch_rerank_pages_and_headings(
                            pages=context_results,
                            queries=queries,
                            matcher=self._reranker.matcher,
                            scopes=self.rerank_scopes,
                            reranker_threshold=self.reranker_threshold,
                            threshold_precision=self.threshold_precision,
                            preprocess_func=self._preprocess_for_rerank if self.domain_nouns else None,
                            preprocess_headings_func=self._preprocess_headings_for_rerank,
                        )

                        for page in context_results:
                            # 当 rerank_scopes 不包含 "headings" 时，跳过 heading rerank 处理
                            if "headings" not in self.rerank_scopes:
                                continue
                            if not page.get("headings"):
                                continue

                            reranked_headings = []
                            for heading in page["headings"]:
                                semantic_score = heading.get("rerank_sim") or 0.0
                                if (
                                    semantic_score
                                    < self._reranker.config.min_score_threshold
                                ):
                                    continue
                                original_bm25_score = heading.get("bm25_sim") or 0.0
                                updated_heading = dict(heading)
                                updated_heading["bm25_sim"] = original_bm25_score
                                updated_heading["rerank_sim"] = semantic_score
                                updated_heading["is_basic"] = True
                                precision_threshold = (
                                    self._reranker.config.min_score_threshold + 0.2
                                )
                                updated_heading["is_precision"] = (
                                    semantic_score >= precision_threshold
                                )
                                reranked_headings.append(updated_heading)
                            reranked_headings.sort(
                                key=lambda h: h.get("rerank_sim") or 0.0, reverse=True
                            )
                            if (
                                self._reranker.config.top_k is not None
                                and self._reranker.config.top_k > 0
                            ):
                                reranked_headings = reranked_headings[
                                    : self._reranker.config.top_k
                                ]
                            if reranked_headings:
                                page["headings"] = reranked_headings
                            else:
                                page["headings"] = [
                                    {
                                        "text": page.get("heading", ""),
                                        "level": extract_heading_level(
                                            page.get("heading", "")
                                        ),
                                        "bm25_sim": page.get("bm25_sim"),
                                        "is_basic": True,
                                        "is_precision": page.get("is_precision", False),
                                        "related_context": page.get(
                                            "related_context", ""
                                        ),
                                    }
                                ]
                            page["heading_count"] = len(page.get("headings", []))
                            page["precision_count"] = sum(
                                1
                                for h in page.get("headings", [])
                                if h.get("is_precision", False)
                            )
                    else:
                        for page in context_results:
                            page["headings"] = [
                                {
                                    "text": page["heading"],
                                    "level": extract_heading_level(
                                        page["heading"]
                                    ),
                                    "bm25_sim": page.get("bm25_sim"),
                                    "is_basic": page.get("is_basic", True),
                                    "is_precision": page.get("is_precision", False),
                                    "related_context": page.get("related_context", ""),
                                }
                            ]
                            page["heading_count"] = 1
                            page["precision_count"] = (
                                1 if page.get("is_precision", False) else 0
                            )

                    # FALLBACK_2 本地向量化匹配（基于 related_context）
                    if (self.fallback_2_local_rerank and
                        self._fallback_2_local_matcher and
                        context_results):
                        from .reranker import fallback_2_local_rerank_headings
                        fallback_2_local_rerank_headings(
                            matcher=self._fallback_2_local_matcher,
                            pages=context_results,
                            queries=queries,
                            preprocess_func=self._preprocess_for_rerank if self.domain_nouns else None,
                            top_k_ratio=self.fallback_2_local_rerank_ratio,
                        )

                    # Merge FALLBACK_2 results with existing results
                    all_results.extend(context_results)
                    fallback_used = (
                        "FALLBACK_1+FALLBACK_2"
                        if fallback_used == "FALLBACK_1"
                        else "FALLBACK_2"
                    )

        # Calculate final success
        self._debug_print(f"DEBUG2: all_results count before loop = {len(all_results)}")
        success = len(all_results) >= self.min_page_titles

        results = []
        for page in all_results:
            self._debug_print(f"DEBUG2: processing page {page.get('page_title')}, bm25_sim={page.get('bm25_sim')}, headings={len(page.get('headings', []))}")

            # Check if this is a FALLBACK_2 page (FALLBACK_2 results should skip is_basic filter)
            page_source = page.get("source", "")
            is_fallback_2_page = page_source == "FALLBACK_2" or any(
                h.get("source") == "FALLBACK_2" for h in page.get("headings", [])
            )

            # FALLBACK_2 的 heading 保留原始结果（不检查 is_basic）
            if is_fallback_2_page:
                filtered_headings = page.get("headings", [])
            else:
                filtered_headings = [
                    h for h in page.get("headings", []) if h.get("is_basic", True)
                ]

            # Apply hierarchical filter only for non-FALLBACK_2 pages
            if self.hierarchical_filter and not is_fallback_2_page:
                from .heading_filter import filter_headings_hierarchically

                filtered_headings = filter_headings_hierarchically(
                    filtered_headings, page["page_title"]
                )

            if filtered_headings:
                # Check page-level BM25 threshold
                page_bm25_sim = page.get("bm25_sim") or 0
                # FALLBACK_2 精确匹配结果不经过 BM25 阈值检查
                self._debug_print(f"DEBUG2: page_bm25_sim={page_bm25_sim}, threshold={self.threshold_page_title}, is_fallback_2={is_fallback_2_page}")
                if is_fallback_2_page or page_bm25_sim >= self.threshold_page_title:
                    results.append(
                        {
                            "doc_set": page["doc_set"],
                            "page_title": page["page_title"],
                            "toc_path": page.get("toc_path", ""),
                            "headings": [
                                {
                                    "text": h.get("full_text", h["text"]),
                                    "level": h.get("level", 2),
                                    "rerank_sim": h.get("rerank_sim"),
                                    "bm25_sim": h.get("bm25_sim"),
                                    "related_context": h.get("related_context", ""),
                                    "is_basic": h.get("is_basic", True),
                                    "is_precision": h.get("is_precision", False),
                                    "source": h.get("source"),
                                }
                                for h in filtered_headings
                            ],
                            "bm25_sim": page_bm25_sim,
                            "rerank_sim": page.get("rerank_sim"),
                            "is_basic": page.get("is_basic", True),
                            "is_precision": page.get("is_precision", False),
                            "source": page.get("source"),
                        }
                    )
            elif (page.get("bm25_sim") or 0) >= self.threshold_page_title:
                rerank_sim = page.get("rerank_sim")
                if not self.reranker_enabled or (
                    rerank_sim is not None and rerank_sim >= self.reranker_threshold
                ):
                    results.append(
                        {
                            "doc_set": page["doc_set"],
                            "page_title": page["page_title"],
                            "toc_path": page.get("toc_path", ""),
                            "bm25_sim": page.get("bm25_sim"),
                            "rerank_sim": rerank_sim,
                            "is_basic": page.get("is_basic", True),
                            "is_precision": page.get("is_precision", False),
                            "source": page.get("source"),
                        }
                    )

        return {
            "success": success,
            "toc_fallback": toc_fallback,
            "grep_fallback": grep_fallback,
            "query": queries,
            "doc_sets_found": search_doc_sets,
            "results": results,
            "fallback_used": fallback_used,
            "message": "Search completed"
            if success
            else "No results found after all fallbacks",
            # Threshold configuration fields
            "threshold_page_title": self.threshold_page_title,
            "threshold_headings": self.threshold_headings,
            "threshold_precision": self.threshold_precision,
            "threshold_doc_set": self.threshold_doc_set,
            "reranker_threshold": self.reranker_threshold,
            "reranker_lang_threshold": self.reranker_lang_threshold,
            "bm25_k1": self.bm25_k1,
            "bm25_b": self.bm25_b,
            "min_page_titles": self.min_page_titles,
            "min_headings": self.min_headings,
            "reranker_enabled": self.reranker_enabled,
            "rerank_scopes": self.rerank_scopes,
        }

    def format_aop_output(self, result: Dict[str, Any]) -> str:
        """
        Format result as AOP output.

        Args:
            result: Search result from self.search()

        Returns:
            Formatted AOP markdown string
        """
        return OutputFormatter.format_aop(result)

    def format_structured_output(
        self,
        result: Dict[str, Any],
        queries: Optional[List[str]] = None,
        reranker_enabled: Optional[bool] = None,
    ) -> str:
        """
        Format result as structured JSON for machine parsing.

        Returns JSON metadata with doc_set, page_title, toc_path, and headings
        that can be parsed by downstream skills like md-doc-reader for
        section-level content extraction.

        Args:
            result: Search result from self.search()
            queries: Original query input list from --query parameter
            reranker_enabled: Whether reranker was enabled. If None, uses self.reranker_enabled

        Returns:
            JSON string with structured metadata
        """
        if reranker_enabled is None:
            reranker_enabled = self.reranker_enabled
        return OutputFormatter.format_structured(
            result, queries=queries, reranker_enabled=reranker_enabled
        )

    def rerank(
        self, pages: List[Dict[str, Any]], queries: Union[str, List[str]]
    ) -> Dict[str, Any]:
        """
        对页面执行独立的 transformer semantic reranking。

        可被 orchestrator 的 embedding_reranker 参数调用，用于 Phase 1.5 的
        独立重排序步骤。与 search() 内部的 reranking 逻辑独立。

        Args:
            pages: 页面列表（通常是 BM25 召回的原始结果）
            queries: 查询字符串或查询列表

        Returns:
            与 search() 返回格式相同的字典，包含 rerank_sim 和 is_basic。
            如果 reranker 未初始化或 pages 为空，返回原始结果。
        """
        if not pages:
            return {
                "success": False,
                "query": queries,
                "doc_sets_found": [],
                "results": [],
                "fallback_used": None,
                "message": "No pages to rerank",
            }

        if not self._reranker:
            self._debug_print("Reranker not initialized, skipping reranking")
            return {
                "success": True,
                "query": queries,
                "doc_sets_found": list(set(p.get("doc_set", "") for p in pages)),
                "results": pages,
                "fallback_used": None,
                "message": "Reranker not enabled, returning original results",
            }

        queries = [queries] if isinstance(queries, str) else queries
        self._debug_print(
            f"Executing transformer reranking on {len(pages)} pages with {len(queries)} queries"
        )

        batch_rerank_pages_and_headings(
            pages=pages,
            queries=queries,
            matcher=self._reranker.matcher,
            scopes=self.rerank_scopes,
            reranker_threshold=self.reranker_threshold,
            threshold_precision=self.threshold_precision,
            preprocess_func=self._preprocess_for_rerank if self.domain_nouns else None,
            preprocess_headings_func=self._preprocess_headings_for_rerank,
        )

        for page in pages:
            original_headings_len = len(page.get("headings", []))
            filtered_headings = [
                h for h in page.get("headings", []) if h.get("is_basic", True)
            ]

            if self.hierarchical_filter:
                from .heading_filter import filter_headings_hierarchically

                filtered_headings = filter_headings_hierarchically(
                    filtered_headings, page["page_title"]
                )

            page["headings"] = filtered_headings
            page["heading_count"] = len(filtered_headings)
            page["precision_count"] = sum(
                1 for h in filtered_headings if h.get("is_precision", False)
            )
            self._debug_print(
                f"  Page: {page['page_title']}, headings: {original_headings_len} -> {len(filtered_headings)}, rerank_sim: {page.get('rerank_sim')}"
            )

        return {
            "success": True,
            "query": queries,
            "doc_sets_found": list(set(p.get("doc_set", "") for p in pages)),
            "results": pages,
            "fallback_used": None,
            "message": "Transformer reranking completed",
        }
