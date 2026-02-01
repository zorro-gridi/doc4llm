"""
FALLBACK_1: Anchor/TOC Search Strategy (Pure Python Implementation).

This module provides a pure Python implementation of the FALLBACK_1 search strategy
for searching docTOC.md files. Uses pathlib + re instead of grep command.

This module is extracted from doc_searcher_api.py for better modularity.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from .common_utils import remove_url_from_heading, extract_heading_level
from .interfaces import BaseSearcher


@dataclass
class AnchorSearcherConfig:
    """Anchor/TOC searcher configuration for FALLBACK_1 strategy."""

    threshold_headings: float = 0.25
    threshold_precision: float = 0.7
    debug: bool = False


class AnchorSearcher(BaseSearcher):
    """FALLBACK_1: Grep/TOC Search Strategy (Pure Python Implementation).

    Uses pathlib + re to search docTOC.md files for keywords, supporting
    regular expression matching. This is a cross-platform implementation
    that doesn't depend on the system grep command.

    Attributes:
        base_dir: Knowledge base root directory
        config: Searcher configuration
    """

    def __init__(self, base_dir: str, config: Optional[AnchorSearcherConfig] = None):
        """Initialize AnchorSearcher.

        Args:
            base_dir: Knowledge base root directory
            config: Searcher configuration (uses defaults if not provided)
        """
        self.base_dir = base_dir
        self.config = config or AnchorSearcherConfig()

    @property
    def name(self) -> str:
        """Get the searcher name.

        Returns:
            Human-readable name identifying this searcher
        """
        return "FALLBACK_1"

    def _debug_print(self, message: str):
        """Print debug message."""
        if self.config.debug:
            print(f"[DEBUG] {message}")

    def _search_files(
        self, doc_sets: List[str], pattern: re.Pattern
    ) -> Generator[Tuple[Path, str], None, None]:
        """Search for pattern in docTOC.md files (pure Python implementation).

        Args:
            doc_sets: List of doc-set names to search
            pattern: Compiled regex pattern to search for

        Yields:
            Tuples of (toc_file_path, matched_line)
        """
        for doc_set in doc_sets:
            docset_path = Path(self.base_dir) / doc_set
            if not docset_path.exists():
                continue

            for toc_file in docset_path.rglob("docTOC.md"):
                try:
                    with open(toc_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if pattern.search(line):
                                yield toc_file, line  # noqa: F841
                except Exception as e:
                    self._debug_print(f"Error reading {toc_file}: {e}")

    def search(
        self, queries: Union[str, List[str]], doc_sets: List[str]
    ) -> List[Dict[str, Any]]:
        """Search docTOC.md files for keywords (FALLBACK_1 strategy).

        Args:
            queries: List of search query strings
            doc_sets: List of doc-set names to search

        Returns:
            List of search result dictionaries with fields:
                - doc_set: Document set name
                - page_title: Page title
                - heading: Heading text (with # format)
                - toc_path: TOC file path
                - bm25_sim: BM25 similarity score (initial value 0.0)
                - is_basic: Whether meets basic threshold
                - is_precision: Whether meets precision threshold
                - source: Strategy source identifier ("FALLBACK_1")
        """
        self._debug_print("Using FALLBACK_1: grep/TOC search (pure Python)")

        # Normalize queries to list
        if isinstance(queries, str):
            queries = [queries]

        # Import here to avoid circular imports
        from .bm25_recall import extract_keywords, extract_page_title_from_path

        # Extract and combine keywords from all queries
        all_keywords = []
        for q in queries:
            all_keywords.extend(extract_keywords(q))

        # Remove duplicates while preserving order
        keywords = list(dict.fromkeys(all_keywords))

        if not keywords:
            self._debug_print("No keywords extracted from queries")
            return []

        # Build regex pattern (OR logic for multiple keywords)
        pattern = "|".join(re.escape(kw) for kw in keywords)
        compiled_pattern = re.compile(pattern, re.IGNORECASE)

        results = []
        for toc_file, line in self._search_files(doc_sets, compiled_pattern):
            if not line.strip():
                continue

            # Parse grep-style output: path:matched_content
            if ":" in line:
                parts = line.split(":", 1)
                toc_path = parts[0].strip()
                match_content = parts[1] if len(parts) > 1 else ""

                page_title = extract_page_title_from_path(toc_path)

                heading_text = ""
                if "#" in match_content:
                    heading_match = re.search(r"(#{1,6}\s+[^\n]+)", match_content)
                    if heading_match:
                        # Preserve original # format heading text
                        heading_text = remove_url_from_heading(
                            heading_match.group(1), preserve_hash=True
                        )

                if heading_text:
                    results.append(
                        {
                            "doc_set": Path(toc_path).parent.parent.name,
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


__all__ = [
    "AnchorSearcherConfig",
    "AnchorSearcher",
]
