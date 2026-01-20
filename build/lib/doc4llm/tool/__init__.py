"""
Markdown document retrieval tool for doc4llm.

This package provides tools for retrieving content from markdown documents
stored in the md_docs directory structure.

The main tool is organized as a sub-package: md_doc_retrieval
(previously named md_doc_extractor - a compatibility layer is available).

Example:
    >>> from doc4llm.tool import MarkdownDocExtractor
    >>> extractor = MarkdownDocExtractor()
    >>> content = extractor.extract_by_title("Agent Skills - Claude Code Docs")

Or use the sub-package directly:
    >>> from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor
    >>> extractor = MarkdownDocExtractor()
"""

# Re-export from the md_doc_retrieval sub-package
from .md_doc_retrieval import (
    BaseDirectoryNotFoundError,
    BasicDocMatcher,
    ConfigurationError,
    DocExtractorError,
    DocumentNotFoundError,
    ExtractionResult,
    InvalidTitleError,
    MarkdownDocExtractor,
    NoDocumentsFoundError,
    build_doc_path,
    calculate_similarity,
    extract_doc_name_and_version,
    find_best_match,
    is_valid_doc_directory,
    normalize_title,
    parse_doc_structure,
    sanitize_filename,
)

__all__ = [
    # Main extractor class
    "MarkdownDocExtractor",
    "ExtractionResult",
    # Basic matcher (v3.0.0)
    "BasicDocMatcher",
    # Exceptions
    "DocExtractorError",
    "DocumentNotFoundError",
    "InvalidTitleError",
    "BaseDirectoryNotFoundError",
    "NoDocumentsFoundError",
    "ConfigurationError",
    # Utility functions
    "normalize_title",
    "calculate_similarity",
    "build_doc_path",
    "parse_doc_structure",
    "find_best_match",
    "sanitize_filename",
    "is_valid_doc_directory",
    "extract_doc_name_and_version",
]

__version__ = "3.0.0"
