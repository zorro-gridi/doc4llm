"""
Markdown Document Searcher API - BM25 based retrieval.

This module provides CLI + API interface for searching markdown documents
in the doc4llm knowledge base. Uses BM25 scoring for doc-set, page_title,
and heading matching. Fallback strategies use grep-based search.

Core BM25 Parameters:
    k1: Term frequency saturation parameter (default 1.2)
    b: Length normalization parameter (default 0.75)

Matching Thresholds:
    threshold_page_title: Page title match threshold, uses full TOC (default 0.6)
    threshold_headings: Heading match threshold, single heading text (default 0.25)
    threshold_precision: Precision match threshold for headings (default 0.7)
"""

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


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
class DocSearcherAPI:
    """
    Markdown Document Searcher API.

    Provides BM25-based document retrieval from docTOC.md files.
    Supports main flow with full-text BM25 and grep-based fallback strategies.

    Args:
        base_dir: Knowledge base root directory
        bm25_k1: BM25 k1 parameter (default 1.2)
        bm25_b: BM25 b parameter (default 0.75)
        threshold_page_title: Page title matching threshold, uses full TOC content (default 0.6)
        threshold_headings: Heading matching threshold, single heading text (default 0.25)
        threshold_precision: Precision matching threshold for headings only (default 0.7)
        threshold_doc_set: Doc-set matching threshold, keyword Jaccard (default 0.6)
        min_page_titles: Minimum page titles per doc-set (default 1)
        min_headings: Minimum headings per doc-set (default 2)
        debug: Enable debug mode (default False)

    Attributes:
        base_dir: Knowledge base root directory
        config: Configuration dictionary
    """

    base_dir: str  # Required, loaded from knowledge_base.json
    bm25_k1: float = 1.2
    bm25_b: float = 0.75
    threshold_page_title: float = 0.6
    threshold_headings: float = 0.25
    threshold_precision: float = 0.7
    threshold_doc_set: float = 0.6
    min_page_titles: int = 1
    min_headings: int = 2
    debug: bool = False

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
            raise ValueError(f"knowledge_base.json not found in parent directories of {__file__}")
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
        self.base_dir = str(Path(kb_base_dir).expanduser())
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

    def _debug_print(self, message: str):
        """Print debug message."""
        if self.debug:
            print(f"[DEBUG] {message}")

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text (保留版本号作为独立词)。"""
        return re.findall(r"[a-zA-Z]+", text.lower())

    def _calculate_jaccard(self, set1: List[str], set2: List[str]) -> float:
        """Calculate Jaccard similarity coefficient."""
        s1, s2 = set(set1), set(set2)
        if not s1 or not s2:
            return 0.0
        return len(s1 & s2) / len(s1 | s2)

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
            if item.is_dir() and ":" in item.name:
                doc_sets.append(item.name)
        return sorted(doc_sets)

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

    def _search_page_titles_bm25(
        self, doc_set: str, query: Union[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """Search page titles using BM25. Supports single query or query list."""
        # Normalize query to list
        queries = [query] if isinstance(query, str) else query
        # Combine queries with space for BM25 search
        combined_query = " ".join(queries)

        toc_files = self._find_toc_files(doc_set)
        matcher = BM25Matcher(BM25Config(k1=self.bm25_k1, b=self.bm25_b))

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
            # Page Title 使用 threshold_page_title
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
                        BM25Config(k1=self.bm25_k1, b=self.bm25_b),
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

                # 只返回 basic 级别以上的 headings (使用 threshold_headings)
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
                        "is_precision": False,  # Page title 不使用 precision
                        "toc_path": toc_path,
                        "headings": valid_headings,
                        "heading_count": len(valid_headings),
                        "precision_count": precision_count,
                    }
                )

        return scored_pages

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
                            heading_text = heading_match.group(1).strip()

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
                                "text": line.strip(),
                                "level": len(match.group(1)),
                                "context": "",
                            }
                        )

            nearest = heading_candidates[-1] if heading_candidates else None

            if nearest:
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

    def search(
        self, query: Union[str, List[str]], doc_sets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute document search.

        Main flow:
            STATE 1: Identify doc-set using keyword matching (Jaccard)
            STATE 2: Identify page-titles using BM25
            STATE 3: Identify headings using BM25
            STATE 4: Return results

        Fallback strategies:
            FALLBACK_1: grep TOC search
            FALLBACK_2: grep context + BM25 re-scoring

        Args:
            query: Search query string or list of query strings
            doc_sets: Optional list of doc-sets to search (default: all)

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

        available_doc_sets = self._find_doc_sets()
        if not available_doc_sets:
            return {
                "success": False,
                "doc_sets_found": [],
                "results": [],
                "fallback_used": None,
                "message": "No doc-sets found",
            }

        if doc_sets:
            target_doc_sets = [ds for ds in doc_sets if ds in available_doc_sets]
        else:
            target_doc_sets = available_doc_sets

        if not target_doc_sets:
            return {
                "success": False,
                "doc_sets_found": [],
                "results": [],
                "fallback_used": None,
                "message": "No matching doc-sets found",
            }

        self._debug_print(f"Available doc-sets: {target_doc_sets}")

        matched_doc_set = self._match_doc_sets(query, target_doc_sets)
        if matched_doc_set is None:
            self._debug_print(
                "No doc-set matched with threshold >= {self.threshold_doc_set}"
            )
            return {
                "success": False,
                "doc_sets_found": target_doc_sets,
                "results": [],
                "fallback_used": None,
                "message": "No doc-set matched",
            }

        self._debug_print(f"Matched doc-set: {matched_doc_set}")

        all_results = []
        self._debug_print(f"Processing {matched_doc_set}")

        scored_pages = self._search_page_titles_bm25(matched_doc_set, query)
        self._debug_print(f"Found {len(scored_pages)} scored pages")

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
            self._debug_print("Main flow failed, trying FALLBACK_1")
            grep_results = self._fallback1_grep_search(query, [matched_doc_set])

            if grep_results:
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
                            "level": 2,
                            "score": r["score"],
                            "is_basic": r["is_basic"],
                            "is_precision": r["is_precision"],
                        }
                    )
                    page_map[key]["heading_count"] += 1
                    if r["is_precision"]:
                        page_map[key]["precision_count"] += 1

                all_results = list(page_map.values())
                success = len(all_results) >= self.min_page_titles
                fallback_used = "FALLBACK_1"

        if not success:
            self._debug_print("FALLBACK_1 failed, trying FALLBACK_2")
            context_results = self._fallback2_grep_context_bm25(
                query, [matched_doc_set]
            )

            if context_results:
                all_results = context_results
                success = len(all_results) >= self.min_page_titles
                fallback_used = "FALLBACK_2"

        results = []
        for page in all_results:
            filtered_headings = [
                h for h in page.get("headings", []) if h.get("is_basic", True)
            ]
            if filtered_headings:
                results.append(
                    {
                        "doc_set": page["doc_set"],
                        "page_title": page["page_title"],
                        "toc_path": page.get("toc_path", ""),
                        "headings": [
                            {"text": h["text"], "level": h.get("level", 2)}
                            for h in filtered_headings
                        ],
                    }
                )

        return {
            "success": success,
            "doc_sets_found": target_doc_sets,
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
        doc_sets_str = ",".join(result.get("doc_sets_found", []))
        results = result.get("results", [])
        count = len(results)

        lines = []
        lines.append(
            f"=== AOP-FINAL | agent=md-doc-searcher | results={count} | doc_sets={doc_sets_str} ==="
        )
        lines.append(
            "**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary"
        )

        for page in results:
            lines.append(f"**{page['doc_set']}**")
            lines.append("")
            lines.append(f"**{page['page_title']}**")
            lines.append(f"   - TOC 路径: `{page['toc_path']}`")
            lines.append("   - **匹配Heading列表**:")

            for heading in page.get("headings", []):
                level_hash = "#" * heading.get("level", 2)
                lines.append(f"     - {level_hash} {heading['text']}")

                lines.append("")

        lines.append("=== END-AOP-FINAL ===")

        if count == 0:
            lines.clear()
            lines.append(
                f"=== AOP-FINAL | agent=md-doc-searcher | results={count} | doc_sets={doc_sets_str} ==="
            )
            lines.append(
                "**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary"
            )
            lines.append("")
            lines.append("No matched headings found!")
            lines.append("")
            lines.append("=== END-AOP-FINAL ===")

        return "\n".join(lines)

    def format_structured_output(self, result: Dict[str, Any]) -> str:
        """
        Format result as structured JSON for machine parsing.

        Returns JSON metadata with doc_set, page_title, toc_path, and headings
        that can be parsed by downstream skills like md-doc-reader for
        section-level content extraction. Results are not separated by relevance
        level (high/medium) - all matched pages are returned in a single list.

        Args:
            result: Search result from self.search()

        Returns:
            JSON string with structured metadata
        """
        structured = {
            "success": result.get("success", False),
            "doc_sets_found": result.get("doc_sets_found", []),
            "results": [
                {
                    "doc_set": page["doc_set"],
                    "page_title": page["page_title"],
                    "toc_path": page["toc_path"],
                    "headings": [
                        {"level": h.get("level", 2), "text": h["text"]}
                        for h in page.get("headings", [])
                    ],
                }
                for page in result.get("results", [])
            ],
        }
        return json.dumps(structured, ensure_ascii=False, indent=2)
