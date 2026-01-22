"""
Markdown Document Searcher CLI + API Package.

This package provides CLI and API interfaces for searching markdown documents
in the doc4llm knowledge base using BM25-based retrieval.

Modules:
    doc_searcher_api: Core API for document retrieval
    doc_searcher_cli: Command-line interface

Usage:

API:
    >>> from doc_searcher_api import DocSearcherAPI
    >>> api = DocSearcherAPI(base_dir="/path/to/md_docs")
    >>> result = api.search(query="hooks configuration")
    >>> print(api.format_aop_output(result))

CLI:
    $ python doc_searcher_cli.py --base-dir /path/to/md_docs --query "hooks configuration"
    $ python doc_searcher_cli.py --base-dir /path/to/md_docs --query "api" --json
"""

from .doc_searcher_api import DocSearcherAPI
from .doc_searcher_cli import main

__all__ = [
    "DocSearcherAPI",
    "main",
]

__version__ = "1.0.0"
