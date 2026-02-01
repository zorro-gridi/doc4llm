"""
Searcher Interfaces - Abstract base classes for searcher implementations.

This module defines the interfaces that all searchers must implement,
ensuring consistent behavior and return formats across different search strategies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseSearcher(ABC):
    """Abstract base class for all searcher implementations.

    Searchers are responsible for finding relevant documents/pages/headings
    based on given queries. All searchers must implement the search() method
    and return results in a consistent format.

    Attributes:
        name: Human-readable name of the searcher
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the searcher name.

        Returns:
            Human-readable name identifying this searcher
        """
        pass

    @abstractmethod
    def search(
        self, queries: List[str], doc_sets: List[str]
    ) -> List[Dict[str, Any]]:
        """Execute search for the given queries.

        Args:
            queries: List of search query strings
            doc_sets: List of doc-set names to search within

        Returns:
            List of search result dictionaries. Each result must contain:
            - doc_set: Document set name
            - page_title: Page title
            - heading: Heading text (if applicable)
            - toc_path: Path to TOC file
            - bm25_sim: BM25 similarity score
            - is_basic: Whether meets basic threshold
            - is_precision: Whether meets precision threshold
            - source: Strategy/source identifier
        """
        pass

    def health_check(self) -> Dict[str, Any]:
        """Check if the searcher is healthy and ready.

        Returns:
            Dictionary with 'status' and optional 'message' fields.
            Default implementation returns {'status': 'ok'}.
        """
        return {"status": "ok"}


class SearchResult:
    """Standardized search result container.

    Provides a structured way to represent search results with
    type hints and validation.
    """

    def __init__(
        self,
        doc_set: str,
        page_title: str,
        heading: Optional[str] = None,
        toc_path: str = "",
        bm25_sim: float = 0.0,
        is_basic: bool = True,
        is_precision: bool = False,
        source: str = "unknown",
        **kwargs,
    ):
        """Initialize a search result.

        Args:
            doc_set: Document set name
            page_title: Page title
            heading: Heading text (optional)
            toc_path: Path to TOC file
            bm25_sim: BM25 similarity score
            is_basic: Whether meets basic threshold
            is_precision: Whether meets precision threshold
            source: Strategy/source identifier
            **kwargs: Additional fields
        """
        self.doc_set = doc_set
        self.page_title = page_title
        self.heading = heading
        self.toc_path = toc_path
        self.bm25_sim = bm25_sim
        self.is_basic = is_basic
        self.is_precision = is_precision
        self.source = source
        self.extra = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format.

        Returns:
            Dictionary representation of the result
        """
        result = {
            "doc_set": self.doc_set,
            "page_title": self.page_title,
            "heading": self.heading,
            "toc_path": self.toc_path,
            "bm25_sim": self.bm25_sim,
            "is_basic": self.is_basic,
            "is_precision": self.is_precision,
            "source": self.source,
        }
        result.update(self.extra)
        return result


__all__ = [
    "BaseSearcher",
    "SearchResult",
]
