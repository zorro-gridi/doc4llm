"""
Markdown Document Searcher CLI + API Package.

This package provides CLI and API interfaces for searching markdown documents
in the doc4llm knowledge base using BM25-based retrieval.

Modules:
    doc_searcher_api: Core API for document retrieval
    doc_searcher_cli: Command-line interface
    content_searcher: Pythonic content searcher (FALLBACK_SEARCHER)

Usage:

API:
    >>> from doc_searcher_api import DocSearcherAPI
    >>> api = DocSearcherAPI(base_dir="/path/to/md_docs")
    >>> result = api.search(query="hooks configuration")
    >>> print(api.format_aop_output(result))

    # Or use the Pythonic content searcher directly:
    >>> from content_searcher import ContentSearcher
    >>> searcher = ContentSearcher(base_dir="/path/to/md_docs", domain_nouns=["hook"])
    >>> results = searcher.search(["hooks"], ["Claude_Code_Docs@latest"])

CLI:
    $ python doc_searcher_cli.py --base-dir /path/to/md_docs --query "hooks configuration"
    $ python doc_searcher_cli.py --base-dir /path/to/md_docs --query "api" --json
"""

from .bm25_recall import BM25Recall, BM25Config
from .content_searcher import ContentSearcher
from .doc_searcher_api import DocSearcherAPI
from .doc_searcher_cli import main
from .anchor_searcher import AnchorSearcher, AnchorSearcherConfig
from .text_preprocessor import TextPreprocessor, LanguageDetector
from .fallback_merger import FallbackMerger
from .search_utils import debug_print
from .common_utils import (
    extract_heading_level,
    filter_query_keywords,
    remove_url_from_heading,
    extract_page_title_from_path,
    count_words,
    clean_context_from_urls,
)
from .config import (
    BM25Config,
    ThresholdConfig,
    RerankerConfig,
    FallbackConfig,
    AnchorSearcherConfig,
    ContentSearcherConfig,
    SearchConfig,
)
from .config_manager import ConfigManager
from .interfaces import BaseSearcher, SearchResult
from .searcher_registry import SearcherRegistry, get_registry, reset_registry

__all__ = [
    # Core classes
    "BM25Recall",
    "BM25Config",
    "ContentSearcher",
    "DocSearcherAPI",
    "AnchorSearcher",
    "AnchorSearcherConfig",
    "TextPreprocessor",
    "LanguageDetector",
    "FallbackMerger",
    "ConfigManager",
    # Searcher registry
    "SearcherRegistry",
    "get_registry",
    "reset_registry",
    # Interfaces
    "BaseSearcher",
    "SearchResult",
    # Configuration
    "BM25Config",
    "ThresholdConfig",
    "RerankerConfig",
    "FallbackConfig",
    "AnchorSearcherConfig",
    "ContentSearcherConfig",
    "SearchConfig",
    # Utility functions
    "debug_print",
    "extract_heading_level",
    "filter_query_keywords",
    "remove_url_from_heading",
    "extract_page_title_from_path",
    "count_words",
    "clean_context_from_urls",
    # CLI
    "main",
]

__version__ = "1.1.0"
