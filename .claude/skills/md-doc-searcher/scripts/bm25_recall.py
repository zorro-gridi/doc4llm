"""
BM25 recall module for page title and heading matching.

Extracted from doc_searcher_api.py to provide modular BM25-based
retrieval functionality.

Example:
    >>> from bm25_recall import BM25Recall, BM25Config
    >>> recall = BM25Recall(k1=1.2, b=0.75)
    >>> scored_pages = recall.recall_pages(doc_set, query, threshold=0.6)
    >>> for page in scored_pages:
    ...     print(f"{page['page_title']}: {page['score']}")
"""

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# Constants for tokenization
STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "is",
    "are",
    "was",
    "were",
    "to",
    "for",
    "with",
    "by",
    "from",
    "at",
    "on",
    "in",
    "about",
    "how",
    "what",
    "where",
    "when",
    "why",
    "which",
    "that",
    "this",
    "these",
    "those",
    "use",
    "using",
    "can",
    "will",
    "would",
}

TECHNICAL_TERMS = {
    "api",
    "cli",
    "sdk",
    "http",
    "https",
    "jwt",
    "oauth",
    "ssh",
    "webhook",
    "middleware",
    "endpoint",
    "token",
    "auth",
    "config",
    "deploy",
    "hooks",
    "async",
    "sync",
    "json",
    "xml",
    "yaml",
    "yml",
}


@dataclass
class BM25Config:
    """Configuration for BM25 ranking parameters."""

    k1: float = 1.2
    b: float = 0.75
    min_token_length: int = 2
    max_token_length: int = 30
    lowercase: bool = True
    stop_words: Optional[set] = None


class BM25Matcher:
    """BM25-based matcher for content search."""

    DEFAULT_STOP_WORDS = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "is",
        "are",
        "was",
        "were",
        "to",
        "for",
        "with",
        "by",
        "from",
        "at",
        "on",
        "in",
        "about",
        "as",
        "of",
        "it",
        "this",
        "that",
        "be",
        "have",
        "has",
        "had",
    }

    def __init__(self, config: Optional[BM25Config] = None):
        self.config = config or BM25Config()
        if self.config.stop_words is None:
            self.config.stop_words = self.DEFAULT_STOP_WORDS
        self._doc_ids: List[str] = []
        self._doc_lengths: List[int] = []
        self._doc_vectors: List[Dict[str, int]] = []
        self._idf_cache: Dict[str, float] = {}
        self._avg_doc_length: float = 0.0
        self._total_docs: int = 0

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"\b\w+\b", text)
        filtered = []
        for token in tokens:
            if self.config.lowercase:
                token = token.lower()
            if token in self.config.stop_words:
                continue
            if len(token) < self.config.min_token_length:
                continue
            if len(token) > self.config.max_token_length:
                continue
            filtered.append(token)
        return filtered

    def build_index(
        self, documents: Dict[str, str], pre_tokenized: bool = False
    ) -> None:
        self._doc_ids = []
        self._doc_lengths = []
        self._doc_vectors = []
        self._idf_cache = {}
        total_length = 0

        for doc_id, content in documents.items():
            self._doc_ids.append(doc_id)
            if pre_tokenized:
                tokens = content if isinstance(content, list) else content.split()
            else:
                tokens = self._tokenize(content)
            term_freq = Counter(tokens)
            self._doc_vectors.append(dict(term_freq))
            self._doc_lengths.append(len(tokens))
            total_length += len(tokens)

        self._total_docs = len(self._doc_ids)
        self._avg_doc_length = (
            total_length / self._total_docs if self._total_docs > 0 else 0
        )
        self._compute_idf()

    def _compute_idf(self) -> None:
        doc_freq = Counter()
        for doc_vector in self._doc_vectors:
            for term in doc_vector:
                doc_freq[term] += 1
        for term, df in doc_freq.items():
            self._idf_cache[term] = math.log(
                (self._total_docs - df + 0.5) / (df + 0.5) + 1.0
            )

    def _get_idf(self, term: str) -> float:
        if self.config.lowercase:
            term = term.lower()
        return self._idf_cache.get(term, 0.0)

    def _score_document(self, query_tokens: List[str], doc_idx: int) -> float:
        doc_vector = self._doc_vectors[doc_idx]
        doc_length = self._doc_lengths[doc_idx]
        score = 0.0
        for token in query_tokens:
            if token not in doc_vector:
                continue
            tf = doc_vector[token]
            idf = self._get_idf(token)
            numerator = tf * (self.config.k1 + 1)
            denominator = tf + self.config.k1 * (
                1 - self.config.b + self.config.b * (doc_length / self._avg_doc_length)
            )
            score += idf * (numerator / denominator)
        return score

    def search(
        self, query: str, top_k: int = 10, min_score: float = 0.0
    ) -> List[Tuple[str, float]]:
        if not self._doc_ids:
            return []
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        scores = []
        for doc_idx in range(self._total_docs):
            score = self._score_document(query_tokens, doc_idx)
            if score >= min_score:
                scores.append((self._doc_ids[doc_idx], score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


def calculate_bm25_similarity(
    query: str, content: str, config: Optional[BM25Config] = None
) -> float:
    """Quick BM25 similarity calculation for a single document."""
    if not query or not content:
        return 0.0
    matcher = BM25Matcher(config)
    matcher.build_index({"doc": content})
    results = matcher.search(query, top_k=1)
    return results[0][1] if results else 0.0


def extract_keywords(query: str) -> List[str]:
    """Extract keywords from query string."""
    words = re.findall(r"[\w\u4e00-\u9fff]+", query.lower())
    keywords = []
    for word in words:
        if re.search(r"[\u4e00-\u9fff]", word):
            keywords.append(word)
        elif word in TECHNICAL_TERMS:
            keywords.append(word)
        elif word not in STOP_WORDS:
            keywords.append(word)
    seen = set()
    result = []
    for word in keywords:
        if word not in seen:
            seen.add(word)
            result.append(word)
    return result


def extract_page_title_from_path(toc_path: str) -> str:
    """Extract page title from toc file path."""
    parts = toc_path.split("/")
    for i, part in enumerate(parts):
        if part == "docTOC.md":
            if i > 0:
                return parts[i - 1]
    return "Unknown"


def parse_headings(toc_content: str) -> List[Dict[str, Any]]:
    """Parse headings from TOC content."""
    if not toc_content:
        return []
    lines = toc_content.split("\n")
    headings = []
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
    link_pattern = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
    anchor_pattern = re.compile(r"：https://[^\s]+|: https://[^\s]+")

    for line in lines:
        match = heading_pattern.match(line.strip())
        if match:
            level = len(match.group(1))
            full_text = match.group(2).strip()
            anchor = None
            anchor_match = anchor_pattern.search(full_text)
            if anchor_match:
                anchor = (
                    anchor_match.group(0).replace("：", "").replace(": ", "").strip()
                )
            text = anchor_pattern.sub("", full_text).strip()
            link_match = link_pattern.search(text)
            if link_match:
                text = link_match.group(1)
            headings.append(
                {
                    "level": level,
                    "text": text,
                    "full_text": f"{'#' * level} {text}",
                    "anchor": anchor,
                }
            )
    return headings


@dataclass
class ScoredPage:
    """A scored page result from BM25 recall.

    Attributes:
        doc_set: Document set name
        page_title: Page title
        score: BM25 score
        is_basic: Whether score meets basic threshold
        is_precision: Whether score meets precision threshold
        toc_path: Path to TOC file
        headings: List of scored headings
        heading_count: Number of valid headings
        precision_count: Number of precision-level headings
    """
    doc_set: str
    page_title: str
    score: float
    is_basic: bool
    is_precision: bool
    toc_path: str
    headings: List[Dict[str, Any]]
    heading_count: int
    precision_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "doc_set": self.doc_set,
            "page_title": self.page_title,
            "score": self.score,
            "is_basic": self.is_basic,
            "is_precision": self.is_precision,
            "toc_path": self.toc_path,
            "headings": self.headings,
            "heading_count": self.heading_count,
            "precision_count": self.precision_count,
        }


@dataclass
class ScoredHeading:
    """A scored heading result from BM25 recall.

    Attributes:
        level: Heading level (1-6)
        text: Heading text
        full_text: Full heading text with level markers
        anchor: Optional anchor URL
        score: BM25 similarity score
        is_basic: Whether score meets basic threshold
        is_precision: Whether score meets precision threshold
    """
    level: int
    text: str
    full_text: str
    anchor: Optional[str]
    score: float
    is_basic: bool
    is_precision: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level,
            "text": self.text,
            "full_text": self.full_text,
            "anchor": self.anchor,
            "score": self.score,
            "is_basic": self.is_basic,
            "is_precision": self.is_precision,
        }


class BM25Recall:
    """BM25-based recall for page titles and headings.

    This class provides methods to recall relevant pages and headings
    from a doc-set using BM25 scoring.
    """

    def __init__(
        self,
        base_dir: str,
        k1: float = 1.2,
        b: float = 0.75,
        threshold_page_title: float = 0.6,
        threshold_headings: float = 0.25,
        threshold_precision: float = 0.7,
        debug: bool = False
    ):
        """Initialize BM25 recall module.

        Args:
            base_dir: Knowledge base root directory
            k1: BM25 k1 parameter (default 1.2)
            b: BM25 b parameter (default 0.75)
            threshold_page_title: Page title matching threshold (default 0.6)
            threshold_headings: Heading matching threshold (default 0.25)
            threshold_precision: Precision matching threshold (default 0.7)
            debug: Enable debug mode (default False)
        """
        self.base_dir = base_dir
        self.k1 = k1
        self.b = b
        self.threshold_page_title = threshold_page_title
        self.threshold_headings = threshold_headings
        self.threshold_precision = threshold_precision
        self.debug = debug

    def _debug_print(self, message: str):
        """Print debug message."""
        if self.debug:
            print(f"[DEBUG] {message}")

    def _find_toc_files(self, doc_set: str) -> List[str]:
        """Find all TOC files in a doc-set."""
        base = Path(self.base_dir) / doc_set
        if not base.exists():
            return []
        toc_files = []
        for item in base.iterdir():
            if item.is_dir():
                toc_path = item / "docTOC.md"
                if toc_path.exists():
                    toc_files.append(str(toc_path))
        return sorted(toc_files)

    def _read_toc_content(self, toc_path: str) -> str:
        """Read TOC file content."""
        try:
            return Path(toc_path).read_text(encoding="utf-8")
        except Exception:
            return ""

    def recall_pages(
        self,
        doc_set: str,
        query: Union[str, List[str]],
        min_headings: int = 2
    ) -> List[Dict[str, Any]]:
        """Recall pages using BM25 scoring.

        Args:
            doc_set: Document set name
            query: Search query string or list of query strings
            min_headings: Minimum headings required per page (default 2)

        Returns:
            List of scored page dictionaries
        """
        # Normalize query to list
        queries = [query] if isinstance(query, str) else query
        combined_query = " ".join(queries)

        toc_files = self._find_toc_files(doc_set)
        matcher = BM25Matcher(BM25Config(k1=self.k1, b=self.b))

        documents = {}
        for toc_path in toc_files:
            page_title = extract_page_title_from_path(toc_path)
            content = self._read_toc_content(toc_path)
            documents[page_title] = content

        if not documents:
            return []

        matcher.build_index(documents)
        results = matcher.search(combined_query, top_k=100)

        scored_pages = []
        for page_title, score in results:
            is_basic = score >= self.threshold_page_title

            if is_basic:
                toc_path = str(Path(self.base_dir) / doc_set / page_title / "docTOC.md")
                toc_content = self._read_toc_content(toc_path)
                headings = parse_headings(toc_content)

                scored_headings = []
                for heading in headings:
                    h_score = calculate_bm25_similarity(
                        combined_query,
                        heading["text"],
                        BM25Config(k1=self.k1, b=self.b),
                    )
                    self._debug_print(
                        f"    Heading: {heading['text'][:50]}, score: {h_score:.2f}"
                    )
                    scored_headings.append(
                        {
                            **heading,
                            "score": h_score,
                            "is_basic": h_score >= self.threshold_headings,
                            "is_precision": h_score >= self.threshold_precision,
                        }
                    )

                self._debug_print(
                    f"    threshold_headings: {self.threshold_headings}, valid count before filter: {len(scored_headings)}"
                )
                valid_headings = [h for h in scored_headings if h["is_basic"]]
                self._debug_print(f"    valid_headings count: {len(valid_headings)}")

                precision_count = sum(1 for h in valid_headings if h["is_precision"])

                scored_pages.append(
                    {
                        "doc_set": doc_set,
                        "page_title": page_title,
                        "score": score,
                        "is_basic": is_basic,
                        "is_precision": False,
                        "toc_path": toc_path,
                        "headings": valid_headings,
                        "heading_count": len(valid_headings),
                        "precision_count": precision_count,
                    }
                )

        # Filter by min_headings
        return [p for p in scored_pages if p["heading_count"] >= min_headings]


__all__ = [
    "BM25Config",
    "BM25Matcher",
    "BM25Recall",
    "ScoredPage",
    "ScoredHeading",
    "calculate_bm25_similarity",
    "extract_keywords",
    "extract_page_title_from_path",
    "parse_headings",
]
