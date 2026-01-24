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
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Import local modules
from bm25_recall import (
    BM25Recall,
    extract_keywords,
    extract_page_title_from_path,
)
from output_format import OutputFormatter
from reranker import HeadingReranker, RerankerConfig

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


@dataclass
class DocSearcherAPI:
    """
    Markdown Document Searcher API.

    Provides BM25-based document retrieval from docTOC.md files with optional
    transformer-based semantic re-ranking.

    Args:
        base_dir: Knowledge base root directory (loaded from knowledge_base.json)
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

    Attributes:
        base_dir: Knowledge base root directory
        config: Configuration dictionary
    """

    base_dir: Optional[str] = None
    bm25_k1: float = 1.2
    bm25_b: float = 0.75
    threshold_page_title: float = 0.6
    threshold_headings: float = 0.25
    threshold_precision: float = 0.7
    threshold_doc_set: float = 0.6
    min_page_titles: int = 2
    min_headings: int = 2
    debug: bool = False
    reranker_enabled: bool = False
    reranker_model_zh: str = "BAAI/bge-large-zh-v1.5"
    reranker_model_en: str = "BAAI/bge-large-en-v1.5"
    reranker_threshold: float = 0.5
    reranker_top_k: Optional[int] = None
    reranker_lang_threshold: float = 0.3
    hierarchical_filter: bool = True
    fallback_mode: str = "parallel"
    domain_nouns: List[str] = field(default_factory=list)
    predicate_verbs: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize configuration from knowledge_base.json."""
        # Search upward from current script to find .claude directory with knowledge_base.json
        current = Path(__file__).resolve()
        project_root = None
        for _ in range(6):  # Search up to 6 levels up
            if (current / "knowledge_base.json").exists():
                project_root = current / "knowledge_base.json"
                break
            current = current.parent
        if not project_root:
            raise ValueError(
                f"knowledge_base.json not found in parent directories of {__file__}"
            )
        try:
            with open(project_root, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in knowledge_base.json: {e}")
        kb_base_dir = config.get("knowledge_base", {}).get("base_dir")
        if not kb_base_dir:
            raise ValueError(
                "base_dir not found in knowledge_base.json['knowledge_base']"
            )

        # Use user-provided base_dir if specified, otherwise use config value
        if self.base_dir:
            path = Path(self.base_dir).expanduser()
            if not path.exists():
                raise ValueError(f"base_dir does not exist: '{self.base_dir}'")
            if not path.is_dir():
                raise ValueError(f"base_dir is not a directory: '{self.base_dir}'")
            self.base_dir = str(path.resolve())
        else:
            self.base_dir = str(Path(kb_base_dir).expanduser().resolve())
        self.config = {
            "bm25_k1": self.bm25_k1,
            "bm25_b": self.bm25_b,
            "threshold_page_title": self.threshold_page_title,
            "threshold_headings": self.threshold_headings,
            "threshold_precision": self.threshold_precision,
            "threshold_doc_set": self.threshold_doc_set,
            "min_page_titles": self.min_page_titles,
            "min_headings": self.min_headings,
            "debug": self.debug,
        }

        # Validate fallback_mode parameter
        if self.fallback_mode not in ("serial", "parallel"):
            raise ValueError(
                f"fallback_mode must be 'serial' or 'parallel', got: {self.fallback_mode}"
            )

        # Initialize reranker if enabled
        self._reranker: Optional[HeadingReranker] = None
        if self.reranker_enabled:
            transformer_config = TransformerConfig(
                model_zh=self.reranker_model_zh,
                model_en=self.reranker_model_en,
                lang_threshold=self.reranker_lang_threshold,
            )
            matcher = TransformerMatcher(transformer_config)
            reranker_config = RerankerConfig(
                enabled=True,
                min_score_threshold=self.reranker_threshold,
                top_k=self.reranker_top_k,
            )
            self._reranker = HeadingReranker(reranker_config, matcher)

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
        """从 heading 文本中移除 URL 链接，只保留纯文本用于 BM25 匹配。"""
        link_pattern = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
        anchor_pattern = re.compile(r"：https://[^\s]+|: https://[^\s]+")
        text = link_pattern.sub(r"\1", heading_text)
        text = anchor_pattern.sub("", text).strip()
        return text

    def _get_english_stem(self, word: str) -> str:
        """获取英文单词的词干（简单实现，处理常见复数形式）。"""
        # 常见的英文复数后缀
        suffixes = ['s', 'es', 'ied', 'ies', 'ves']
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                # 处理特殊情况：ies -> y, ves -> f
                if suffix == 'ies' and not word.endswith('aies') and not word.endswith('eies'):
                    return word[:-3] + 'y'
                elif suffix == 'ves':
                    return word[:-3] + 'f'
                elif suffix == 'ied' and not word.endswith('aied') and not word.endswith('eied'):
                    return word[:-3] + 'y'
                else:
                    return word[:-len(suffix)]
        return word

    def _contains_domain_noun(
        self,
        text: str,
        domain_nouns: List[str]
    ) -> bool:
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
            if re.search(r'[\u4e00-\u9fff]', noun_lower):
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
        self,
        text: str,
        domain_nouns: List[str],
        predicate_verbs: List[str]
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

        # 使用正则替换，移除所有 predicate_verbs（不区分大小写）
        processed_text = text
        for verb in predicate_verbs:
            # 检测是否为中文（包含中文字符）
            if re.search(r'[\u4e00-\u9fff]', verb):
                # 中文：直接子串匹配（不使用 word boundary）
                pattern = re.compile(re.escape(verb), re.IGNORECASE)
                processed_text = pattern.sub('', processed_text)
            else:
                # 英文：使用 word boundary 确保完整匹配
                pattern = re.compile(r'\b' + re.escape(verb) + r'\b', re.IGNORECASE)
                processed_text = pattern.sub('', processed_text)

        # 清理多余空格并 strip
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()

        return processed_text

    def _preprocess_headings_for_rerank(
        self,
        headings: List[Dict[str, Any]],
        domain_nouns: List[str],
        predicate_verbs: List[str]
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
            processed_text = self._preprocess_for_rerank(text, domain_nouns, predicate_verbs)
            processed_headings.append({**h, "text": processed_text})

        return processed_headings

    def _extract_heading_level(self, heading_text: str) -> int:
        """Extract heading level from markdown heading text.

        Args:
            heading_text: Heading text that may start with # characters

        Returns:
            Heading level (1-6), defaults to 2 if no # prefix found
        """
        # Match the heading pattern and count # characters
        match = re.match(r"^(#{1,6})\s+", heading_text.strip())
        if match:
            return len(match.group(1))
        return 2  # Default fallback level

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
        self, query: Union[str, List[str]], doc_sets: List[str]
    ) -> List[Dict[str, Any]]:
        """FALLBACK_1: grep TOC search. Supports single query or query list."""
        self._debug_print("Using FALLBACK_1: grep search")
        # Normalize query to list and extract keywords from all queries
        queries = [query] if isinstance(query, str) else query
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
                                "score": 0.0,
                                "is_basic": True,
                                "is_precision": False,
                                "source": "grep",
                            }
                        )

        return results

    def _fallback2_grep_context_bm25(
        self, query: Union[str, List[str]], doc_sets: List[str]
    ) -> List[Dict[str, Any]]:
        """FALLBACK_2: grep context + BM25 re-scoring. Supports single query or query list."""
        self._debug_print("Using FALLBACK_2: grep context + BM25")
        # Normalize query to list and extract keywords from all queries
        queries = [query] if isinstance(query, str) else query
        all_keywords = []
        for q in queries:
            all_keywords.extend(extract_keywords(q))
        # Remove duplicates
        keywords = list(dict.fromkeys(all_keywords))
        pattern = "|".join(keywords)
        # Combine queries for BM25 similarity
        combined_query = " ".join(queries)

        results = []
        for doc_set in doc_sets:
            cmd = [
                "grep",
                "-r",
                "-i",
                "-B",
                "5",
                "-E",
                pattern,
                f"{self.base_dir}/{doc_set}",
                "--include=docTOC.md",
            ]

            output = self._run_grep(cmd)

            if not output:
                cmd = [
                    "grep",
                    "-r",
                    "-i",
                    "-B",
                    "20",
                    "-E",
                    pattern,
                    f"{self.base_dir}/{doc_set}",
                    "--include=docTOC.md",
                ]
                output = self._run_grep(cmd)

            if not output:
                continue

            lines = output.split("\n")
            heading_candidates = []

            for line in lines:
                if line.strip().startswith("#"):
                    match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
                    if match:
                        heading_candidates.append(
                            {
                                "text": self._remove_url_from_heading(line.strip()),
                                "level": len(match.group(1)),
                                "context": "",
                            }
                        )

            nearest = heading_candidates[-1] if heading_candidates else None

            if nearest:
                from bm25_recall import calculate_bm25_similarity, BM25Config

                score = calculate_bm25_similarity(
                    combined_query,
                    nearest["text"],
                    BM25Config(k1=self.bm25_k1, b=self.bm25_b),
                )

                toc_path = ""
                for line in lines:
                    if "/" in line and "docTOC.md" in line:
                        toc_path = line.split(":")[0]
                        break

                page_title = (
                    extract_page_title_from_path(toc_path) if toc_path else "Unknown"
                )

                results.append(
                    {
                        "doc_set": doc_set,
                        "page_title": page_title,
                        "heading": nearest["text"],
                        "toc_path": toc_path,
                        "score": score,
                        "is_basic": score >= self.threshold_headings,
                        "is_precision": score >= self.threshold_precision,
                        "source": "grep_context_bm25",
                    }
                )

        return results

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
                # Create new page entry
                merged_pages[key] = {
                    "doc_set": result["doc_set"],
                    "page_title": result["page_title"],
                    "toc_path": result.get("toc_path", ""),
                    "headings": [],
                    "heading_count": 0,
                    "precision_count": 0,
                    "score": result.get("score", 0),
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
                    # If heading already exists, keep the higher scoring version
                    for idx, existing in enumerate(merged_pages[key]["headings"]):
                        if existing["text"] == heading["text"]:
                            if heading.get("bm25_sim", 0) > existing.get("bm25_sim", 0):
                                merged_pages[key]["headings"][idx] = heading
                            break

            # Update page-level statistics
            merged_pages[key]["heading_count"] = len(merged_pages[key]["headings"])
            merged_pages[key]["precision_count"] = sum(
                1 for h in merged_pages[key]["headings"] if h.get("is_precision", False)
            )

            # Update page score to highest heading score
            if merged_pages[key]["headings"]:
                merged_pages[key]["score"] = max(
                    h.get("bm25_sim", 0) for h in merged_pages[key]["headings"]
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
        self._debug_print(f"Searching queries: {queries}")
        self._debug_print(f"Base dir: {self.base_dir}")
        self._debug_print(f"Reranker enabled: {self.reranker_enabled}")

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

            # Transformer re-ranking for headings
            if self._reranker:
                self._debug_print("  Applying transformer re-ranking to headings")
                for page in scored_pages:
                    # 预处理 page_title
                    if self.domain_nouns:
                        page["page_title"] = self._preprocess_for_rerank(
                            page.get("page_title", ""),
                            self.domain_nouns,
                            self.predicate_verbs
                        )

                    original_headings = page["headings"]
                    if original_headings:
                        # 预处理 headings
                        processed_headings = self._preprocess_headings_for_rerank(
                            original_headings, self.domain_nouns, self.predicate_verbs
                        )
                        reranked_headings = self._reranker.rerank_headings(
                            combined_query, processed_headings
                        )
                        page["headings"] = reranked_headings
                        page["heading_count"] = len(reranked_headings)
                        page["precision_count"] = sum(
                            1 for h in reranked_headings if h.get("is_precision", False)
                        )
                        self._debug_print(
                            f"    Page: {page['page_title']}, headings: {len(original_headings)} -> {len(reranked_headings)}"
                        )

            for page in scored_pages:
                self._debug_print(
                    f"  Page: {page['page_title']}, score: {page['score']:.2f}, headings: {page['heading_count']}/{page.get('precision_count', 0)} precision"
                )
                if page["heading_count"] >= self.min_headings:
                    all_results.append(page)
                else:
                    self._debug_print(
                        f"    Skipped: heading_count ({page['heading_count']}) < min_headings ({self.min_headings})"
                    )

        self._debug_print(f"Total pages in all_results: {len(all_results)}")

        success = len(all_results) >= self.min_page_titles and any(
            r["score"] >= self.threshold_precision for r in all_results
        )
        fallback_used = None

        if not success:
            # ========== PARALLEL MODE (default) ==========
            if self.fallback_mode == "parallel":
                self._debug_print("Main flow failed, trying PARALLEL fallback mode")
                toc_fallback = True
                grep_fallback = True

                all_fallback_results = []
                fallback_strategies = []

                # Execute FALLBACK_1 (without applying reranker yet)
                grep_results = self._fallback1_grep_search(query, search_doc_sets)
                if grep_results:
                    from bm25_recall import calculate_bm25_similarity, BM25Config

                    for result in grep_results:
                        result["score"] = calculate_bm25_similarity(
                            combined_query,
                            result.get("heading", ""),
                            BM25Config(k1=self.bm25_k1, b=self.bm25_b),
                        )
                        result["is_basic"] = result["score"] >= self.threshold_headings
                        result["is_precision"] = result["score"] >= self.threshold_precision

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
                                "score": r["score"],
                                "is_basic": r["is_basic"],
                                "is_precision": r["is_precision"],
                            }
                        page_map[key]["headings"].append(
                            {
                                "text": r["heading"],
                                "level": self._extract_heading_level(r["heading"]),
                                "score": r["score"],
                                "bm25_sim": r["score"],
                                "is_basic": r["is_basic"],
                                "is_precision": r["is_precision"],
                            }
                        )
                        page_map[key]["heading_count"] += 1
                        if r["is_precision"]:
                            page_map[key]["precision_count"] += 1

                    all_fallback_results.extend(page_map.values())
                    fallback_strategies.append("FALLBACK_1")

                # Execute FALLBACK_2 (without applying reranker yet)
                context_results = self._fallback2_grep_context_bm25(query, search_doc_sets)
                if context_results:
                    # Convert "heading" to "headings" list for consistency
                    for page in context_results:
                        page["headings"] = [
                            {
                                "text": page["heading"],
                                "level": self._extract_heading_level(page["heading"]),
                                "score": page["score"],
                                "bm25_sim": page["score"],
                                "is_basic": page.get("is_basic", True),
                                "is_precision": page.get("is_precision", False),
                            }
                        ]
                        page["heading_count"] = 1
                        page["precision_count"] = 1 if page.get("is_precision", False) else 0

                    all_fallback_results.extend(context_results)
                    fallback_strategies.append("FALLBACK_2")

                # Merge results from both fallback strategies
                if all_fallback_results:
                    all_results = self._merge_fallback_results(all_fallback_results)

                    # Apply reranker once to merged results
                    if self._reranker:
                        self._debug_print("  Applying transformer re-ranking to merged PARALLEL fallback results")
                        for page in all_results:
                            # 预处理 page_title
                            if self.domain_nouns:
                                page["page_title"] = self._preprocess_for_rerank(
                                    page.get("page_title", ""),
                                    self.domain_nouns,
                                    self.predicate_verbs
                                )

                            original_headings = page["headings"]
                            if original_headings:
                                # 预处理 headings
                                processed_headings = self._preprocess_headings_for_rerank(
                                    original_headings, self.domain_nouns, self.predicate_verbs
                                )
                                reranked_headings = self._reranker.rerank_headings(
                                    combined_query, processed_headings
                                )
                                page["headings"] = reranked_headings
                                page["heading_count"] = len(reranked_headings)
                                page["precision_count"] = sum(
                                    1 for h in reranked_headings if h.get("is_precision", False)
                                )

                    success = len(all_results) >= self.min_page_titles
                    fallback_used = "+".join(fallback_strategies) if fallback_strategies else None

            # ========== SERIAL MODE (backward compatible) ==========
            else:  # self.fallback_mode == "serial"
                self._debug_print("Main flow failed, trying SERIAL fallback mode")

                # FALLBACK_1
                toc_fallback = True
                grep_results = self._fallback1_grep_search(query, search_doc_sets)

                if grep_results:
                    from bm25_recall import calculate_bm25_similarity, BM25Config

                    for result in grep_results:
                        result["score"] = calculate_bm25_similarity(
                            combined_query,
                            result.get("heading", ""),
                            BM25Config(k1=self.bm25_k1, b=self.bm25_b),
                        )
                        result["is_basic"] = result["score"] >= self.threshold_headings
                        result["is_precision"] = result["score"] >= self.threshold_precision

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
                                "score": r["score"],
                                "is_basic": r["is_basic"],
                                "is_precision": r["is_precision"],
                            }
                        page_map[key]["headings"].append(
                            {
                                "text": r["heading"],
                                "level": self._extract_heading_level(r["heading"]),
                                "score": r["score"],
                                "bm25_sim": r["score"],
                                "is_basic": r["is_basic"],
                                "is_precision": r["is_precision"],
                            }
                        )
                        page_map[key]["heading_count"] += 1
                        if r["is_precision"]:
                            page_map[key]["precision_count"] += 1

                    # Apply reranker if enabled for FALLBACK_1 (serial mode)
                    if self._reranker:
                        self._debug_print("  Applying transformer re-ranking to FALLBACK_1 results")
                        for page in page_map.values():
                            # 预处理 page_title
                            if self.domain_nouns:
                                page["page_title"] = self._preprocess_for_rerank(
                                    page.get("page_title", ""),
                                    self.domain_nouns,
                                    self.predicate_verbs
                                )

                            original_headings = page["headings"]
                            if original_headings:
                                # 预处理 headings
                                processed_headings = self._preprocess_headings_for_rerank(
                                    original_headings, self.domain_nouns, self.predicate_verbs
                                )
                                reranked_headings = self._reranker.rerank_headings(
                                    combined_query, processed_headings
                                )
                                page["headings"] = reranked_headings
                                page["heading_count"] = len(reranked_headings)
                                page["precision_count"] = sum(
                                    1 for h in reranked_headings if h.get("is_precision", False)
                                )

                    all_results = list(page_map.values())
                    success = (
                        len(all_results) >= self.min_page_titles and
                        any(page.get("heading_count", 0) > 0 for page in all_results)
                    )
                    fallback_used = "FALLBACK_1"

                # FALLBACK_2 (only if FALLBACK_1 failed)
                if not success:
                    grep_fallback = True
                    context_results = self._fallback2_grep_context_bm25(query, search_doc_sets)

                    if context_results:
                        # Apply reranker if enabled for FALLBACK_2 (serial mode)
                        if self._reranker:
                            self._debug_print("  Applying transformer re-ranking to FALLBACK_2 results")
                            for page in context_results:
                                # 预处理 page_title
                                if self.domain_nouns:
                                    page["page_title"] = self._preprocess_for_rerank(
                                        page.get("page_title", ""),
                                        self.domain_nouns,
                                        self.predicate_verbs
                                    )

                                original_headings = [
                                    {
                                        "text": page["heading"],
                                        "level": self._extract_heading_level(page["heading"]),
                                        "score": page["score"],
                                        "bm25_sim": page["score"],
                                        "is_basic": page.get("is_basic", True),
                                        "is_precision": page.get("is_precision", False),
                                    }
                                ]

                                # 预处理 headings
                                processed_headings = self._preprocess_headings_for_rerank(
                                    original_headings, self.domain_nouns, self.predicate_verbs
                                )
                                reranked_headings = self._reranker.rerank_headings(
                                    combined_query, processed_headings
                                )
                                if reranked_headings:
                                    page["headings"] = reranked_headings
                                else:
                                    page["headings"] = original_headings
                                page["heading_count"] = len(page.get("headings", []))
                                page["precision_count"] = sum(
                                    1 for h in page.get("headings", []) if h.get("is_precision", False)
                                )
                        else:
                            for page in context_results:
                                page["headings"] = [
                                    {
                                        "text": page["heading"],
                                        "level": self._extract_heading_level(page["heading"]),
                                        "score": page["score"],
                                        "bm25_sim": page["score"],
                                        "is_basic": page.get("is_basic", True),
                                        "is_precision": page.get("is_precision", False),
                                    }
                                ]
                                page["heading_count"] = 1
                                page["precision_count"] = 1 if page.get("is_precision", False) else 0

                        all_results = context_results
                        success = len(all_results) >= self.min_page_titles
                        fallback_used = "FALLBACK_2"

        results = []
        for page in all_results:
            filtered_headings = [
                h for h in page.get("headings", []) if h.get("is_basic", True)
            ]

            # Apply hierarchical filter if enabled
            if self.hierarchical_filter:
                from heading_filter import filter_headings_hierarchically
                filtered_headings = filter_headings_hierarchically(
                    filtered_headings,
                    page["page_title"]
                )

            if filtered_headings:
                results.append(
                    {
                        "doc_set": page["doc_set"],
                        "page_title": page["page_title"],
                        "toc_path": page.get("toc_path", ""),
                        "headings": [
                            {
                                "text": h["text"],
                                "level": h.get("level", 2),
                                "score": h.get("score"),  # This is rerank_sim after reranking
                                "bm25_sim": h.get("bm25_sim"),  # BM25 similarity
                            }
                            for h in filtered_headings
                        ],
                    }
                )

        return {
            "success": success,
            "toc_fallback": toc_fallback,
            "grep_fallback": grep_fallback,
            "doc_sets_found": search_doc_sets,
            "results": results,
            "fallback_used": fallback_used,
            "message": "Search completed"
            if success
            else "No results found after all fallbacks",
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

    def format_structured_output(self, result: Dict[str, Any], queries: Optional[List[str]] = None) -> str:
        """
        Format result as structured JSON for machine parsing.

        Returns JSON metadata with doc_set, page_title, toc_path, and headings
        that can be parsed by downstream skills like md-doc-reader for
        section-level content extraction.

        Args:
            result: Search result from self.search()
            queries: Original query input list from --query parameter

        Returns:
            JSON string with structured metadata
        """
        return OutputFormatter.format_structured(result, queries=queries)
