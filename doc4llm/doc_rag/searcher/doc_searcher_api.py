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

import numpy as np

# Import local modules
from .bm25_recall import (
    BM25Recall,
    BM25Config,
    calculate_bm25_similarity,
    extract_keywords,
    extract_page_title_from_path,
)
from .output_format import OutputFormatter
from .reranker import HeadingReranker, RerankerConfig

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

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        return re.findall(r"[a-zA-Z]+", text.lower())

    def _calculate_jaccard(self, set1: List[str], set2: List[str]) -> float:
        """Calculate Jaccard similarity coefficient."""
        s1, s2 = set(set1), set(set2)
        if not s1 or not s2:
            return 0.0
        return len(s1 & s2) / len(s1 | s2)

    def _detect_language(self, text: str) -> str:
        """
        Detect text language based on Chinese character ratio.

        Args:
            text: Input text to analyze

        Returns:
            "zh" if Chinese character ratio >= threshold, "en" otherwise
        """
        # Count Chinese characters (Unicode range for CJK Unified Ideographs)
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(text.strip())

        if total_chars == 0:
            return "en"

        ratio = chinese_chars / total_chars
        return "zh" if ratio >= self.reranker_lang_threshold else "en"

    def _remove_url_from_heading(self, heading_text: str) -> str:
        """从 heading 文本中移除 URL 链接，保留原始 # 层级格式。

        处理逻辑：
        1. 移除 markdown 链接格式 [text](url) -> text
        2. 移除行尾锚点链接
        3. 保留原始 # 层级符号
        """
        # 移除 markdown 链接格式 [text](url) -> text
        link_pattern = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
        # 移除行尾锚点链接（中文：和英文 :）
        anchor_pattern = re.compile(r"：https://[^\s]+|: https://[^\s]+")

        # 先移除 markdown 链接
        text = link_pattern.sub(r"\1", heading_text)
        # 再移除行尾锚点链接
        text = anchor_pattern.sub("", text).strip()

        # 检查清理后的文本是否以 # 开头
        if text.strip().startswith("#"):
            return text  # 已经包含 # 格式，直接返回

        # 如果原始文本以 # 开头，但清理后的文本没有 #，需要添加
        if heading_text.strip().startswith("#"):
            hash_match = re.match(r"^(#{1,6})\s+", heading_text.strip())
            if hash_match:
                hashes = hash_match.group(1)
                return f"{hashes} {text}"

        return text

    def _get_english_stem(self, word: str) -> str:
        """获取英文单词的词干（简单实现，处理常见复数形式）。"""
        # 常见的英文复数后缀
        suffixes = ["s", "es", "ied", "ies", "ves"]
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                # 处理特殊情况：ies -> y, ves -> f
                if (
                    suffix == "ies"
                    and not word.endswith("aies")
                    and not word.endswith("eies")
                ):
                    return word[:-3] + "y"
                elif suffix == "ves":
                    return word[:-3] + "f"
                elif (
                    suffix == "ied"
                    and not word.endswith("aied")
                    and not word.endswith("eied")
                ):
                    return word[:-3] + "y"
                else:
                    return word[: -len(suffix)]
        return word

    def _contains_domain_noun(self, text: str, domain_nouns: List[str]) -> bool:
        """
        检查 text 是否包含 domain_nouns 中至少一个名词（支持中英文和词干匹配）。

        规则：
        - 英文：使用词干匹配（"hook" 匹配 "hooks"）
        - 中文：直接子串匹配

        Args:
            text: 待检查的文本
            domain_nouns: 领域名词列表

        Returns:
            True 如果包含至少一个 domain_nouns，否则 False
        """
        if not text or not domain_nouns:
            return False

        text_lower = text.lower()

        for noun in domain_nouns:
            noun_lower = noun.lower()

            # 检测是否为中文（包含中文字符）
            if re.search(r"[\u4e00-\u9fff]", noun_lower):
                # 中文：直接子串匹配
                if noun_lower in text_lower:
                    return True
            else:
                # 英文：词干匹配
                # 使用简单的后缀处理：移除常见的英文复数后缀
                stem = self._get_english_stem(noun_lower)
                if stem in text_lower or noun_lower in text_lower:
                    return True

        return False

    def _preprocess_for_rerank(
        self, text: str, domain_nouns: List[str], predicate_verbs: List[str]
    ) -> str:
        """
        预处理文本用于 rerank 计算。

        规则：
        1. 检查 text 是否包含 domain_nouns 中至少一个名词
        2. 如果不包含任何 domain_nouns，则剔除 text 中的 predicate_verbs
        3. 返回处理后的文本

        Args:
            text: 原始 heading 或 page_title 文本
            domain_nouns: 领域名词列表
            predicate_verbs: 谓词动词列表

        Returns:
            处理后的文本（如果包含 domain_nouns 则返回原文本，否则剔除 predicate_verbs）
        """
        if not text:
            return text

        # 如果 domain_nouns 为空或 None，直接返回原文本
        if not domain_nouns:
            return text

        # 检查是否包含至少一个 domain_nouns
        if self._contains_domain_noun(text, domain_nouns):
            return text

        # 如果不包含任何 domain_nouns，剔除 predicate_verbs
        if not predicate_verbs:
            return text

        # 获取受保护的关键词（skiped_keywords 与 domain_nouns 的交集）
        protected_keywords = self._get_protected_keywords()

        # 使用正则替换，移除所有 predicate_verbs（不区分大小写）
        # 但跳过受保护的关键词
        processed_text = text
        for verb in predicate_verbs:
            # 跳过受保护的关键词
            if protected_keywords and verb.lower() in {
                kw.lower() for kw in protected_keywords
            }:
                continue
            # 检测是否为中文（包含中文字符）
            if re.search(r"[\u4e00-\u9fff]", verb):
                # 中文：直接子串匹配（不使用 word boundary）
                pattern = re.compile(re.escape(verb), re.IGNORECASE)
                processed_text = pattern.sub("", processed_text)
            else:
                # 英文：使用 word boundary 确保完整匹配
                pattern = re.compile(r"\b" + re.escape(verb) + r"\b", re.IGNORECASE)
                processed_text = pattern.sub("", processed_text)

        # 清理多余空格并 strip
        processed_text = re.sub(r"\s+", " ", processed_text).strip()

        return processed_text

    def _preprocess_headings_for_rerank(
        self,
        headings: List[Dict[str, Any]],
        domain_nouns: List[str],
        predicate_verbs: List[str],
    ) -> List[Dict[str, Any]]:
        """
        预处理 headings 列表用于 rerank 计算。

        Args:
            headings: heading 字典列表
            domain_nouns: 领域名词列表
            predicate_verbs: 谓词动词列表

        Returns:
            处理后的 heading 字典列表
        """
        if not domain_nouns:
            return headings

        processed_headings = []
        for h in headings:
            text = h.get("text", "")
            processed_text = self._preprocess_for_rerank(
                text, domain_nouns, predicate_verbs
            )
            processed_headings.append({**h, "text": processed_text})

        return processed_headings

    def _get_protected_keywords(self) -> set:
        """
        获取受保护的关键词集合（skiped_keywords 与 domain_nouns 的交集）。

        这些关键词在预处理时不会被剔除。

        Returns:
            受保护的关键词集合
        """
        if not self.domain_nouns or not self.skiped_keywords:
            return set()
        return set(self.domain_nouns) & set(self.skiped_keywords)

    def _filter_query_keywords(self, query: str, skiped_keywords: List[str]) -> str:
        """Filter out skiped keywords from query string (case-insensitive)."""
        query_lower = query.strip()
        result = query_lower

        for keyword in skiped_keywords:
            keyword_lower = keyword.strip().lower()
            if not keyword_lower:
                continue
            pattern = keyword_lower
            result = re.sub(re.escape(pattern), "", result, flags=re.IGNORECASE)

        result = re.sub(r"\s+", " ", result).strip()
        return result

    def _batch_rerank_pages_and_headings(
        self, pages: List[Dict[str, Any]], queries: List[str], scopes: List[str]
    ) -> None:
        """
        批量计算多个 page 和 heading 与多个 query 的语义相似度。

        使用 batch reranking 替代循环调用，大幅减少 API 调用次数。

        Args:
            pages: Page 字典列表，每个 page 包含 page_title 和 headings
            queries: Query 字符串列表
            scopes: Rerank 范围列表，支持 ["page_title"], ["headings"], ["page_title", "headings"]
        """
        if not pages or not queries or not self._reranker:
            return

        # Step 1: 收集 page_titles（始终执行预处理，但仅在 scopes 包含 "page_title" 时计算相似度）
        page_titles = []
        page_indices = []  # (page_idx, processed_title)
        for page_idx, page in enumerate(pages):
            title = page.get("page_title", "")
            if self.domain_nouns:
                title = self._preprocess_for_rerank(
                    title, self.domain_nouns, self.predicate_verbs
                )
                page["page_title"] = title
            page_titles.append(title)
            page_indices.append((page_idx, title))

        # Step 2: 批量计算 page_title 相似度（如果 scopes 包含 "page_title"）
        if "page_title" in scopes and page_titles:
            sim_matrix, _ = self._reranker.matcher.rerank_batch(queries, page_titles)
            # 对于每个 page，取所有 query 中的最大相似度
            for page_idx, _ in enumerate(page_titles):
                max_score = float(np.max(sim_matrix[:, page_idx]))
                pages[page_idx]["rerank_sim"] = max_score
                pages[page_idx]["source"] = (
                    "RERANKER"  # 实际执行了 page_title rerank 才添加
                )
                # 如果只匹配 page_title，检查阈值并清空 headings
                if scopes == ["page_title"]:
                    # 需要同时满足 reranker_threshold (默认 0.68) 和 threshold_precision (默认 0.7)
                    cond1 = max_score >= self.reranker_threshold
                    cond2 = max_score >= self.threshold_precision
                    if cond1 and cond2:
                        pages[page_idx]["headings"] = []

        # Step 3: 收集 headings（如果 scopes 包含 "headings"）
        if "headings" in scopes:
            headings = []  # [(page_idx, heading_idx, text), ...]
            for page_idx, page in enumerate(pages):
                original_headings = page.get("headings", [])
                if not original_headings:
                    continue
                processed_headings = self._preprocess_headings_for_rerank(
                    original_headings, self.domain_nouns, self.predicate_verbs
                )
                # 更新 page 中的 headings
                for h_idx, heading in enumerate(processed_headings):
                    headings.append((page_idx, h_idx, heading["text"]))
                # 保存处理后的 headings
                page["headings"] = processed_headings

            # 批量计算 headings 相似度
            if headings:
                heading_texts = [h[2] for h in headings]
                sim_matrix, _ = self._reranker.matcher.rerank_batch(
                    queries, heading_texts
                )
                # 对于每个 heading，取所有 query 中的最大相似度
                for heading_idx, (page_idx, h_idx, _) in enumerate(headings):
                    max_score = float(np.max(sim_matrix[:, heading_idx]))
                    if h_idx < len(pages[page_idx]["headings"]):
                        pages[page_idx]["headings"][h_idx]["rerank_sim"] = max_score
                        # 根据 reranker_threshold 过滤 headings
                        pages[page_idx]["headings"][h_idx]["is_basic"] = (
                            max_score >= self.reranker_threshold
                        )
                        pages[page_idx]["headings"][h_idx]["source"] = (
                            "RERANKER"  # 实际执行了 heading rerank 才添加
                        )

    def _extract_heading_level(self, heading_text: str) -> int:
        """Extract heading level from markdown heading text.

        Args:
            heading_text: Heading text that may start with # characters

        Returns:
            Heading level (1-6), defaults to 1 if no # prefix found
        """
        # Match the heading pattern and count # characters
        match = re.match(r"^(#{1,6})\s+", heading_text.strip())
        if match:
            return len(match.group(1))
        return 1  # Default fallback level

    def _detect_docset_language(self, doc_set: str, sample_size: int = 5) -> str:
        """
        Detect the primary language of a doc-set by sampling docTOC.md files.

        Args:
            doc_set: Name of the doc-set to analyze
            sample_size: Maximum number of TOC files to sample

        Returns:
            "zh" if Chinese is dominant, "en" otherwise
        """
        docset_path = Path(self.base_dir) / doc_set
        if not docset_path.exists():
            self._debug_print(f"Doc-set path not found: {docset_path}")
            return "en"  # Default to English

        # Find all docTOC.md files
        toc_files = list(docset_path.rglob("docTOC.md"))
        if not toc_files:
            self._debug_print(f"No docTOC.md files found in {doc_set}")
            return "en"  # Default to English

        # Sample files
        sample_files = toc_files[:sample_size]
        self._debug_print(
            f"Sampling {len(sample_files)} TOC files for language detection"
        )

        # Collect all text from sampled files
        all_text = []
        for toc_file in sample_files:
            try:
                with open(toc_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Extract headings (lines starting with #)
                    headings = [
                        line
                        for line in content.split("\n")
                        if line.strip().startswith("#")
                    ]
                    all_text.extend(headings)
            except Exception as e:
                self._debug_print(f"Error reading {toc_file}: {e}")

        if not all_text:
            return "en"

        # Combine all headings for language detection
        combined_text = " ".join(all_text)
        detected_lang = self._detect_language(combined_text)
        self._debug_print(f"Detected doc-set language: {detected_lang}")

        return detected_lang

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

    def _match_doc_sets(
        self, query: Union[str, List[str]], doc_sets: List[str]
    ) -> Optional[str]:
        """
        Use keyword matching (Jaccard) to find the best matching doc-set.

        Args:
            query: Search query string or list of query strings
            doc_sets: List of available doc-set names

        Returns:
            Best matching doc-set name, or None if no match >= threshold
        """
        if not doc_sets:
            return None

        # If only one doc-set is provided, skip matching and return it directly
        if len(doc_sets) == 1:
            self._debug_print(
                f"Single doc-set provided, skipping matching: {doc_sets[0]}"
            )
            return doc_sets[0]

        # Normalize query to list and extract keywords from all queries
        queries = [query] if isinstance(query, str) else query
        query_keywords = []
        for q in queries:
            query_keywords.extend(self._extract_keywords(q))
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in query_keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        query_keywords = unique_keywords

        self._debug_print(f"Query keywords: {query_keywords}")

        best_doc_set = None
        best_score = 0.0

        for doc_set in doc_sets:
            doc_keywords = self._extract_keywords(doc_set)
            score = self._calculate_jaccard(query_keywords, doc_keywords)
            self._debug_print(
                f"  Doc-set: {doc_set}, keywords: {doc_keywords}, Jaccard: {score:.2f}"
            )

            if score > best_score and score >= self.threshold_doc_set:
                best_score = score
                best_doc_set = doc_set

        if best_doc_set:
            self._debug_print(
                f"Best matched doc-set: {best_doc_set} (score: {best_score:.2f})"
            )
        else:
            # Fallback: return the first doc-set if no match found
            self._debug_print(
                f"No doc-set matched with threshold >= {self.threshold_doc_set}, using first: {doc_sets[0]}"
            )
            return doc_sets[0]

        return best_doc_set

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

    def _run_grep(self, cmd: List[str]) -> str:
        """Run grep command and return output."""
        try:
            import subprocess

            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return proc.stdout.strip()
        except Exception as e:
            self._debug_print(f"grep error: {e}")
            return ""

    def _fallback1_grep_search(
        self, queries: List[str], doc_sets: List[str]
    ) -> List[Dict[str, Any]]:
        """FALLBACK_1: grep TOC search. Supports single query or query list."""
        self._debug_print("Using FALLBACK_1: grep search")
        all_keywords = []
        for q in queries:
            all_keywords.extend(extract_keywords(q))
        # Remove duplicates
        keywords = list(dict.fromkeys(all_keywords))
        pattern = "|".join(keywords)

        results = []
        for doc_set in doc_sets:
            cmd = [
                "grep",
                "-r",
                "-i",
                "-E",
                pattern,
                f"{self.base_dir}/{doc_set}",
                "--include=docTOC.md",
            ]

            output = self._run_grep(cmd)
            if not output:
                continue

            for line in output.split("\n"):
                if not line.strip():
                    continue

                if ":" in line:
                    parts = line.split(":", 1)
                    toc_path = parts[0]
                    match_content = parts[1] if len(parts) > 1 else ""

                    page_title = extract_page_title_from_path(toc_path)

                    heading_text = ""
                    if "#" in match_content:
                        heading_match = re.search(r"(#{1,6}\s+[^\n]+)", match_content)
                        if heading_match:
                            # 保留原始 # 格式的 heading 文本
                            heading_text = self._remove_url_from_heading(
                                heading_match.group(1)
                            )

                    if heading_text:
                        results.append(
                            {
                                "doc_set": doc_set,
                                "page_title": page_title,
                                "heading": heading_text,
                                "toc_path": toc_path,
                                "bm25_sim": 0.0,
                                "is_basic": True,
                                "is_precision": False,
                                "source": "FALLBACK_1",
                            }
                        )

        return results

    def _fallback2_grep_context_bm25(
        self, queries: List[str], doc_sets: List[str]
    ) -> List[Dict[str, Any]]:
        """FALLBACK_2: grep context + BM25 re-scoring. Supports single query or query list.

        Features:
        - Keyword priority: domain_nouns -> predicate_verbs -> query keywords (fallback)
        - Separate heading search and related_context extraction:
          * Heading search: Progressive grep with -B 15 -> 30 -> 50... on docTOC.md
          * Related_context: Fixed -B 1 -A 1 on docContent.md (match line + 1 before + 1 after)
        - Multiple results returned (all with score >= threshold_headings)
        - Filter URL-only matches
        - Extract context with URL info removed
        """
        self._debug_print("Using FALLBACK_2: grep context + BM25")

        # Step 1: Determine keywords with priority
        if self.domain_nouns:
            keywords = self.domain_nouns
        elif self.predicate_verbs:
            keywords = self.predicate_verbs
        else:
            # Both domain_nouns and predicate_verbs are empty, extract from queries
            self._debug_print(
                "No domain_nouns or predicate_verbs, extracting from queries"
            )
            all_keywords = []
            for q in queries:
                all_keywords.extend(extract_keywords(q))
            # Remove duplicates while preserving order
            keywords = list(dict.fromkeys(all_keywords))

        if not keywords:
            self._debug_print("No keywords available, skipping FALLBACK_2")
            return []

        pattern = "|".join(keywords)
        combined_query = " ".join(queries)

        results = []
        for doc_set in doc_sets:
            doc_set_path = f"{self.base_dir}/{doc_set}"

            # === 正确的流程: 在 docContent.md 中搜索关键词，然后回溯 heading ===
            # Step 1: 在 docContent.md 中搜索 (包含足够的上文回溯 heading)
            heading_context_sizes = ["15", "30", "50"]  # Progressive -B sizes
            matched_files = set()  # Avoid duplicate processing of same file

            for before_ctx in heading_context_sizes:
                cmd = [
                    "grep",
                    "-r",
                    "-i",
                    "-B",
                    before_ctx,  # 足够的上文用于回溯 heading
                    "-A",
                    "1",  # 匹配行本身
                    "-E",
                    pattern,
                    doc_set_path,
                    "--include=docContent.md",  # 直接搜索 docContent.md
                ]

                output = self._run_grep(cmd)
                if not output:
                    continue  # No results, try larger context

                # 处理 grep 输出：提取 heading 和 context
                for result in self._process_content_grep_output(
                    output, keywords, combined_query, doc_set, pattern
                ):
                    # 使用 file_path 作为去重键（避免同一文件的重复结果）
                    if result["source_file"] not in matched_files:
                        matched_files.add(result["source_file"])

                        related_context = result.get("related_context", "")
                        if related_context:
                            # Calculate BM25 score
                            score = calculate_bm25_similarity(
                                combined_query,
                                related_context,
                                BM25Config(k1=self.bm25_k1, b=self.bm25_b),
                            )

                            # Check threshold
                            if score < self.threshold_headings:
                                self._debug_print(
                                    f"  Score below threshold: {score:.4f} < {self.threshold_headings}"
                                )
                                continue

                            result["bm25_sim"] = score
                            result["is_basic"] = score >= self.threshold_headings
                            result["is_precision"] = score >= self.threshold_precision
                            results.append(result)

                # If enough results found, break early
                if len(results) >= 10:
                    break

        return results

    def _process_content_grep_output(
        self,
        output: str,
        keywords: List[str],
        combined_query: str,
        doc_set: str,
        pattern: str,
    ) -> List[Dict[str, Any]]:
        """Process grep output from docContent.md, extract heading and context.

        This method implements the correct logic:
        1. Find keyword matches in docContent.md
        2. Backtrack to find the nearest heading in the grep context
        3. Extract the match line as related_context

        Returns list of match results with heading and context.
        """
        results = []

        if not output:
            return results

        # Split grep output by file (grep -A/-B outputs -- separator)
        file_blocks = output.split("\n--\n")

        for block in file_blocks:
            if not block.strip():
                continue

            # Parse block to get: file path, line number, heading content
            file_path, line_num, match_content = self._parse_grep_block(block, pattern)

            if not file_path:
                continue

            # 在 grep 输出块中回溯找到最近的 heading
            nearest_heading = self._find_nearest_heading_in_block(block)

            if (
                not nearest_heading["text"]
                or nearest_heading["text"] == "Unknown Section"
            ):
                continue

            # 提取 page title
            page_title = self._extract_page_title_from_path(file_path)

            # 构建 related_context: 使用匹配行的内容
            # 清理 URL 信息
            context_cleaned = self._clean_context_from_urls(match_content)

            if not context_cleaned.strip():
                continue

            results.append(
                {
                    "doc_set": doc_set,
                    "page_title": page_title,
                    "heading": nearest_heading[
                        "text"
                    ],  # _find_nearest_heading_in_block 已经返回带 # 的文本
                    "toc_path": "",
                    "bm25_sim": 0.0,
                    "is_basic": True,
                    "is_precision": False,
                    "related_context": context_cleaned.strip(),
                    "source_file": file_path,
                    "match_line_num": line_num,
                    "source": "FALLBACK_2",
                }
            )

        return results

    def _process_heading_grep_output(
        self,
        output: str,
        keywords: List[str],
        combined_query: str,
        doc_set: str,
        pattern: str,
    ) -> List[Dict[str, Any]]:
        """Process grep output from docTOC.md, extract heading information.

        Returns list of match results with heading info.
        """
        results = []

        if not output:
            return results

        # Split grep output by file (grep -A/-B outputs -- separator)
        file_blocks = output.split("\n--\n")

        for block in file_blocks:
            if not block.strip():
                continue

            # Parse block to get: file path, line number, heading content
            file_path, line_num, heading_content = self._parse_grep_block(
                block, pattern
            )

            if not file_path:
                continue

            # Extract heading text (remove # prefix)
            heading_text = ""
            match = re.match(r"^(#{1,6})\s+(.+)$", heading_content.strip())
            if match:
                heading_text = self._remove_url_from_heading(match.group(2).strip())
            else:
                # If no # prefix, still try to clean the content
                heading_text = self._remove_url_from_heading(heading_content.strip())

            if not heading_text:
                continue

            # Extract page title from the file path
            page_title = self._extract_page_title_from_path(file_path)

            # Construct docContent.md path from docTOC.md path
            doc_content_path = file_path.replace("docTOC.md", "docContent.md")

            results.append(
                {
                    "doc_set": doc_set,
                    "page_title": page_title,
                    "heading": f"# {heading_text}",
                    "toc_path": file_path,
                    "bm25_sim": 0.0,
                    "is_basic": True,
                    "is_precision": False,
                    "related_context": "",
                    "source_file": doc_content_path,
                    "match_line_num": line_num,
                    "source": "FALLBACK_2",
                }
            )

        return results

    def _extract_fixed_context(
        self,
        doc_set_path: str,
        source_file: str,
        pattern: str,
        heading_text: Optional[str] = None,
    ) -> str:
        """Extract fixed context from docContent.md using heading text matching.

        This extracts: match line + 1 line before + 1 line after the heading match.
        Uses heading text matching to locate the relevant section in docContent.md,
        avoiding the accumulation of context from all pattern matches.

        Args:
            doc_set_path: Base path to doc-set
            source_file: Full path to the source file (docContent.md)
            pattern: Search pattern for grep (used for fallback if heading_text fails)
            heading_text: Heading text to match for precise context extraction

        Returns:
            Extracted context text with URL info removed, or empty string if no match
        """
        if heading_text and Path(source_file).exists():
            # 方案 B: 使用 heading 文本精确匹配定位上下文
            # 1. 使用 grep -F 找到 heading 文本的行号
            cmd_find = [
                "grep",
                "-i",
                "-n",
                "-F",
                "-m",
                "1",  # 只取第一个匹配
                heading_text,
                source_file,
            ]

            output_find = self._run_grep(cmd_find)
            if not output_find:
                # Fallback: 如果 heading 匹配失败，使用 pattern 搜索第一个匹配
                self._debug_print(
                    f"Heading '{heading_text}' not found, falling back to first pattern match"
                )
                # 使用 grep -n -m 1 找到 pattern 的第一个匹配行号
                cmd_find_fallback = [
                    "grep",
                    "-i",
                    "-n",
                    "-m",
                    "1",
                    "-E",
                    pattern,
                    source_file,
                ]
                output_find = self._run_grep(cmd_find_fallback)
                if not output_find:
                    return ""

            # 解析行号
            match = re.match(r"^(\d+):(.+)$", output_find.strip())
            if not match:
                return ""

            line_num = int(match.group(1))
            # 2. 使用 sed 提取该行附近的上下文 (-1 到 +1 行)
            start = max(1, line_num - 1)
            end = line_num + 1
            cmd_sed = ["sed", "-n", f"{start},{end}p", source_file]
            output = self._run_grep(cmd_sed)
            if not output:
                return ""
        else:
            # Fallback: 原始实现 (向后兼容)
            cmd_context = [
                "grep",
                "-i",
                "-B",
                "1",
                "-A",
                "1",
                "-E",
                pattern,
                source_file,
            ]
            output = self._run_grep(cmd_context)
            if not output:
                return ""

        # Process the grep output to extract context
        context_lines = []
        for line in output.split("\n"):
            if line.strip() == "--":
                continue

            # Remove line number and file path prefix
            content = line
            # Standard format: /path/to/file.md:123:content
            if re.match(r"^(.+?):\d+:", line):
                content = re.sub(r"^(.+?):\d+:", "", line)
            # Space-separated format: /path/to/file.md- content
            elif re.match(r"^(.+\.md[a-zA-Z0-9_-]*)\s*-\s*(.+)$", line):
                content = re.sub(r"^(.+\.md[a-zA-Z0-9_-]*)\s*-\s*", "", line)

            # Remove URL info from context
            content = self._clean_context_from_urls(content)

            if content.strip():
                context_lines.append(content.strip())

        return "\n".join(context_lines)

    def _process_grep_output_with_context(
        self,
        output: str,
        keywords: List[str],
        combined_query: str,
        doc_set: str,
        pattern: str,
    ) -> List[Dict[str, Any]]:
        """Process grep output, return list of match results with URL filtering and BM25 scoring."""
        results = []

        if not output:
            return results

        # Split grep output by file (grep -A/-B outputs -- separator)
        file_blocks = output.split("\n--\n")

        for block in file_blocks:
            if not block.strip():
                continue

            # Parse block to get: file path, line number, match content
            file_path, line_num, match_content = self._parse_grep_block(block, pattern)

            if not file_path:
                continue

            # === Extract context first ===
            context_text = self._extract_context_from_block(block, pattern)

            if not context_text:
                continue

            # === Filter URL-only matches (check entire context, not just match line) ===
            # Keywords might be in context lines, not just the grep match line
            if self._is_keyword_in_url_only(context_text, keywords):
                self._debug_print(f"  Filtered URL-only match: {file_path}:{line_num}")
                continue  # Skip URL-only matches

            # === Calculate BM25 score ===
            score = calculate_bm25_similarity(
                combined_query,
                context_text,
                BM25Config(k1=self.bm25_k1, b=self.bm25_b),
            )

            # === Threshold check ===
            if score < self.threshold_headings:
                self._debug_print(
                    f"  Score below threshold: {score:.4f} < {self.threshold_headings}"
                )
                continue

            # === Find nearest chapter heading from block ===
            nearest_heading = self._find_nearest_heading_in_block(block)

            results.append(
                {
                    "doc_set": doc_set,
                    "page_title": self._extract_page_title_from_path(file_path),
                    "heading": nearest_heading[
                        "text"
                    ],  # _find_nearest_heading_in_block 已经返回带 # 的文本
                    "toc_path": "",
                    "bm25_sim": score,
                    "is_basic": score >= self.threshold_headings,
                    "is_precision": score >= self.threshold_precision,
                    "related_context": context_text,
                    "source_file": file_path,
                    "match_line_num": line_num,
                }
            )

        return results

    def _parse_grep_block(self, block: str, pattern: str) -> tuple:
        """Parse grep block, extract file path, line number, and match content.

        Handles two grep output formats:
        1. Standard: /path/to/file.md:123:line content with keyword
        2. Space-separated: /path/to/file.md- line content (when path contains spaces)
        """
        lines = block.split("\n")
        if not lines:
            return None, None, None

        # First line typically contains file path and line number
        first_line = lines[0]

        # Try standard format: /path/to/file.md:123:content
        match = re.match(r"^(.+?):(\d+):(.+)$", first_line)
        if match:
            file_path = match.group(1)
            line_num = int(match.group(2))
            match_content = match.group(3)
            return file_path, line_num, match_content

        # Try space-separated format: /path/to/file.md- content
        # Look for the pattern where path ends with .md or .md-XXX and is followed by -
        match = re.match(r"^(.+(?:\.md[a-zA-Z0-9_-]*))\s*-\s*(.+)$", first_line)
        if match:
            file_path = match.group(1)
            match_content = match.group(2)
            # Try to extract line number from content (may not always be present)
            line_match = re.match(r"^(\d+)-(.+)$", match_content)
            if line_match:
                line_num = int(line_match.group(1))
                match_content = line_match.group(2)
            else:
                line_num = 0  # Unknown line number
            return file_path, line_num, match_content

        return None, None, None

    def _is_keyword_in_url_only(self, content: str, keywords: List[str]) -> bool:
        """Check if keywords only appear in URL links.

        - Remove markdown link format [text](url)
        - Remove bare URLs (https://..., www....)
        - Check if keywords still exist in plain text
        """
        if not content or not keywords:
            return False

        # Extract plain text part (remove URLs)
        text_only = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)
        text_only = re.sub(r"https?://[^\s]+", "", text_only)
        text_only = re.sub(r"www\.[^\s]+", "", text_only)

        # Check if keywords appear in plain text
        for keyword in keywords:
            if keyword.lower() in text_only.lower():
                return False  # Keyword in plain text, keep

        return True  # Keywords only in URLs, filter

    def _extract_context_from_block(self, block: str, pattern: str) -> str:
        """Extract context from grep block (match line + 1 line before + 1 line after).

        Also removes URL information from context.
        Handles both standard and space-separated grep output formats.
        """
        lines = block.split("\n")
        context_parts = []

        for line in lines:
            # Skip grep separator
            if line.strip() == "--":
                continue

            # Remove line number and file path prefix
            content = line
            # Standard format: /path/to/file.md:123:content
            if re.match(r"^(.+?):\d+:", line):
                content = re.sub(r"^(.+?):\d+:", "", line)
            # Space-separated format: /path/to/file.md- content or /path/to/file.md-123-content
            elif re.match(r"^(.+\.md[a-zA-Z0-9_-]*)\s*-\s*(.+)$", line):
                content = re.sub(r"^(.+\.md[a-zA-Z0-9_-]*)\s*-\s*", "", line)

            # Remove URL info from context
            content = self._clean_context_from_urls(content)

            if content.strip():
                context_parts.append(content.strip())

        return "\n".join(context_parts)

    def _clean_context_from_urls(self, text: str) -> str:
        """Remove URL link information from context."""
        # Remove markdown link format [text](url) -> text
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # Remove bare URLs
        text = re.sub(r"https?://[^\s]+", "", text)
        # Remove www. links
        text = re.sub(r"www\.[^\s]+", "", text)
        return text.strip()

    def _find_nearest_heading_in_block(self, block: str) -> Dict[str, Any]:
        """Find the nearest chapter heading from grep block (# or ##开头).

        Handles both standard and space-separated grep output formats.
        """
        lines = block.split("\n")

        for line in lines:
            # Skip grep separator
            if line.strip() == "--":
                continue

            # Remove line number and file path prefix
            content = line
            # Standard format: /path/to/file.md:123:content
            if re.match(r"^(.+?):\d+:", line):
                content = re.sub(r"^(.+?):\d+:", "", content)
            # Space-separated format: /path/to/file.md- content
            elif re.match(r"^(.+\.md[a-zA-Z0-9_-]*)\s*-\s*(.+)$", line):
                content = re.sub(r"^(.+\.md[a-zA-Z0-9_-]*)\s*-\s*", "", content)

            # Detect heading (#开头)
            match = re.match(r"^(#{1,6})\s+(.+)$", content.strip())
            if match:
                heading_text = self._remove_url_from_heading(content.strip())
                return {
                    "text": heading_text,
                    "level": len(match.group(1)),
                }

        # No heading found, return default
        return {"text": "Unknown Section", "level": 2}

    def _extract_page_title_from_path(self, file_path: str) -> str:
        """Extract page title from file path.

        Handles two grep output formats:
        1. Standard: /path/to/file.md:123:content (with line number)
        2. Space-separated: /path/to/file.md- content (when grep uses -B/-A)

        Falls back to reading first line of docContent.md if path extraction fails.
        """
        # Skip if file_path is None or empty
        if not file_path:
            return "Unknown"

        # Check if file_path looks like it's from grep space-separated format
        # e.g., "docContent.md-" instead of actual path
        if file_path.endswith(".md-") or file_path.endswith(".md:"):
            # This is a malformed path from grep parsing, will fallback to file read
            pass
        else:
            # Try to extract from path normally
            # Remove base_dir prefix if present
            if self.base_dir and file_path.startswith(self.base_dir):
                relative_path = file_path[len(self.base_dir) :].lstrip("/")
            else:
                relative_path = file_path

            # Extract page title from path like "docSetName/pageTitle/docContent.md"
            parts = relative_path.split("/")
            if len(parts) >= 2:
                # Check if this looks like a valid page title (not a file path artifact)
                potential_title = (
                    parts[-2]
                    if parts[-1] in ("docTOC.md", "docContent.md")
                    else parts[-1]
                )
                # Valid page title should not be empty and should not look like a file artifact
                if (
                    potential_title
                    and not potential_title.endswith(".md")
                    and len(potential_title) > 1
                ):
                    return potential_title

        # Fallback: try to read the actual file to get page title from first line
        actual_path = file_path
        # If the path looks malformed, try to construct the correct path
        if not Path(actual_path).exists():
            # Try to find the file by looking for docContent.md in the parent directory
            potential_dir = (
                Path(file_path).parent if Path(file_path).parent.exists() else None
            )
            if potential_dir:
                doc_content = potential_dir / "docContent.md"
                if doc_content.exists():
                    actual_path = str(doc_content)

        # Read first line of the file for page title
        try:
            if Path(actual_path).exists():
                with open(actual_path, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    # First line is typically "# Page Title\n" or just "# Page Title"
                    if first_line.startswith("#"):
                        title = first_line.lstrip("#").strip()
                        if title:
                            return title
        except Exception as e:
            self._debug_print(f"Error reading page title from file: {e}")

        return "Unknown"

    def _merge_fallback_results(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge results from different fallback strategies.

        Combines results from FALLBACK_1 and FALLBACK_2 by:
        1. Merging pages with the same (doc_set, page_title) key
        2. Deduplicating headings within each page
        3. Keeping the highest BM25 score for duplicate headings
        4. Aggregating heading_count and precision_count

        Args:
            results: List of page results from fallback strategies

        Returns:
            Merged list of page results with deduplicated headings
        """
        merged_pages = {}

        for result in results:
            key = (result["doc_set"], result["page_title"])

            if key not in merged_pages:
                merged_pages[key] = {
                    "doc_set": result["doc_set"],
                    "page_title": result["page_title"],
                    "toc_path": result.get("toc_path", ""),
                    "headings": [],
                    "heading_count": 0,
                    "precision_count": 0,
                    "bm25_sim": result.get("bm25_sim"),
                    "is_basic": result.get("is_basic", True),
                    "is_precision": result.get("is_precision", False),
                }

            # Aggregate headings (deduplicate by heading_text)
            existing_headings = {h["text"] for h in merged_pages[key]["headings"]}

            for heading in result.get("headings", []):
                if heading["text"] not in existing_headings:
                    merged_pages[key]["headings"].append(heading)
                    existing_headings.add(heading["text"])
                else:
                    for idx, existing in enumerate(merged_pages[key]["headings"]):
                        if existing["text"] == heading["text"]:
                            existing_score = existing.get("bm25_sim") or 0
                            new_score = heading.get("bm25_sim") or 0
                            if new_score > existing_score:
                                merged_pages[key]["headings"][idx] = heading
                            break

            # Update page-level statistics
            merged_pages[key]["heading_count"] = len(merged_pages[key]["headings"])
            merged_pages[key]["precision_count"] = sum(
                1 for h in merged_pages[key]["headings"] if h.get("is_precision", False)
            )

            # Update page score to highest heading score
            if merged_pages[key]["headings"]:
                merged_pages[key]["bm25_sim"] = max(
                    (h.get("bm25_sim") or 0) for h in merged_pages[key]["headings"]
                )
                merged_pages[key]["is_basic"] = any(
                    h.get("is_basic", True) for h in merged_pages[key]["headings"]
                )
                merged_pages[key]["is_precision"] = any(
                    h.get("is_precision", False) for h in merged_pages[key]["headings"]
                )

        return list(merged_pages.values())

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
                self._batch_rerank_pages_and_headings(
                    scored_pages, queries, self.rerank_scopes
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
            grep_results = self._fallback1_grep_search(queries, search_doc_sets)
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
                            "level": self._extract_heading_level(r["heading"]),
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

                # Execute FALLBACK_2 (without applying reranker yet)
                context_results = self._fallback2_grep_context_bm25(
                    queries, search_doc_sets
                )
                if context_results:
                    # Convert "heading" to "headings" list for consistency
                    for page in context_results:
                        page["headings"] = [
                            {
                                "text": page["heading"],
                                "level": self._extract_heading_level(page["heading"]),
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

                # Merge results from both fallback strategies
                if all_fallback_results:
                    merged_fallback = self._merge_fallback_results(all_fallback_results)

                    # 去重：BM25 召回结果与 fallback 结果合并
                    seen_pages = {}
                    deduped_results = []
                    for page in scored_pages + merged_fallback:
                        key = (page["doc_set"], page["page_title"])
                        if key not in seen_pages:
                            seen_pages[key] = page
                            deduped_results.append(page)
                        else:
                            existing = seen_pages[key]
                            if (page.get("bm25_sim") or 0) > (
                                existing.get("bm25_sim") or 0
                            ):
                                seen_pages[key] = page

                    all_results = deduped_results

                    # Apply reranker once to merged results
                    if self.reranker_enabled and self._reranker:
                        self._debug_print(
                            "  Applying transformer re-ranking to merged PARALLEL fallback results"
                        )
                        # 使用批量 reranking
                        self._batch_rerank_pages_and_headings(
                            all_results, queries, self.rerank_scopes
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

                    fallback_used = (
                        "+".join(fallback_strategies) if fallback_strategies else None
                    )
                else:
                    all_results = scored_pages

            # ========== SERIAL MODE (backward compatible) ==========
            if self.fallback_mode == "serial":
                self._debug_print(
                    "Executing SERIAL fallback mode (always when reranker disabled)"
                )

                # FALLBACK_1
                toc_fallback = True
                grep_results = self._fallback1_grep_search(query, search_doc_sets)

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
                                "level": self._extract_heading_level(r["heading"]),
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
                        self._batch_rerank_pages_and_headings(
                            list(page_map.values()), queries, self.rerank_scopes
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

                # FALLBACK_2 (always execute in serial mode when reranker disabled)
                grep_fallback = True
                context_results = self._fallback2_grep_context_bm25(
                    query, search_doc_sets
                )

                if context_results:
                    # Apply reranker if enabled for FALLBACK_2 (serial mode)
                    if self.reranker_enabled and self._reranker:
                        self._debug_print(
                            "  Applying transformer re-ranking to FALLBACK_2 results"
                        )
                        # 使用批量 reranking
                        self._batch_rerank_pages_and_headings(
                            context_results, queries, self.rerank_scopes
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
                                        "level": self._extract_heading_level(
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
                                    "level": self._extract_heading_level(
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

                    # Merge FALLBACK_2 results with existing results
                    all_results.extend(context_results)
                    fallback_used = (
                        "FALLBACK_1+FALLBACK_2"
                        if fallback_used == "FALLBACK_1"
                        else "FALLBACK_2"
                    )

        # Calculate final success
        success = len(all_results) >= self.min_page_titles

        results = []
        for page in all_results:
            filtered_headings = [
                h for h in page.get("headings", []) if h.get("is_basic", True)
            ]

            # Apply hierarchical filter if enabled
            if self.hierarchical_filter:
                from .heading_filter import filter_headings_hierarchically

                filtered_headings = filter_headings_hierarchically(
                    filtered_headings, page["page_title"]
                )

            if filtered_headings:
                # Check page-level BM25 threshold
                page_bm25_sim = page.get("bm25_sim") or 0
                if page_bm25_sim >= self.threshold_page_title:
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

        self._batch_rerank_pages_and_headings(pages, queries, self.rerank_scopes)

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
