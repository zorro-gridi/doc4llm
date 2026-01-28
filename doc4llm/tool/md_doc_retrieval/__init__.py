"""
Markdown document retrieval tool for doc4llm.

This is a sub-package providing tools for retrieving content from markdown documents
stored in the md_docs directory structure. Previously named md_doc_extractor.

The package has been renamed to md_doc_retrieval to better reflect its comprehensive
functionality including extraction, matching, and query optimization.

Example:
    >>> from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor
    >>> extractor = MarkdownDocExtractor()
    >>> content = extractor.extract_by_title("Agent Skills - Claude Code Docs")

Basic matching:
    >>> from doc4llm.tool.md_doc_retrieval import BasicDocMatcher
    >>> matcher = BasicDocMatcher(search_mode="exact")
    >>> result = matcher.match("Agent Skills", ["Agent Skills", "Slash Commands"])

Agentic matching:
    >>> from doc4llm.tool.md_doc_retrieval import AgenticDocMatcher
    >>> matcher = AgenticDocMatcher(extractor)
    >>> results = matcher.match("skills")

Transformer-based semantic matching:
    >>> from doc4llm.tool.md_doc_retrieval import TransformerMatcher
    >>> matcher = TransformerMatcher()
    >>> results = matcher.rerank("query text", ["candidate1", "candidate2"])
"""

from .basic_matcher import (
    BasicDocMatcher,
    MatchResult as BasicMatchResult,
)
from .doc_extractor import MarkdownDocExtractor, ExtractionResult
from .agentic_matcher import (
    AgenticDocMatcher,
    ProgressiveRetriever,
    ReflectiveReRanker,
    MatchResult,
    agentic_search,
)
from .exceptions import (
    BaseDirectoryNotFoundError,
    ConfigurationError,
    DocExtractorError,
    DocumentNotFoundError,
    InvalidTitleError,
    NoDocumentsFoundError,
    SingleFileNotFoundError,
)
from .utils import (
    build_doc_path,
    calculate_similarity,
    extract_doc_name_and_version,
    extract_section_by_title,
    extract_title_from_md_file,
    find_best_match,
    is_valid_doc_directory,
    normalize_title,
    parse_doc_structure,
    sanitize_filename,
)
from .bm25_matcher import (
    BM25Matcher,
    BM25Config,
    calculate_bm25_similarity,
    create_bm25_matcher_from_files,
    tokenize_text,
)
from .transformer_matcher import (
    TransformerMatcher,
    TransformerConfig,
)
from .modelscope_matcher import (
    ModelScopeMatcher,
    ModelScopeConfig,
)

__all__ = [
    # Main extractor class
    "MarkdownDocExtractor",
    "ExtractionResult",  # Multi-document extraction result with metadata (v2.5.0)
    # Basic matcher (v3.0.0)
    "BasicDocMatcher",
    "BasicMatchResult",
    # Agentic matcher (v2.0.0)
    "AgenticDocMatcher",
    "ProgressiveRetriever",
    "ReflectiveReRanker",
    "MatchResult",
    "agentic_search",
    # Exceptions
    "DocExtractorError",
    "DocumentNotFoundError",
    "InvalidTitleError",
    "BaseDirectoryNotFoundError",
    "NoDocumentsFoundError",
    "ConfigurationError",
    "SingleFileNotFoundError",
    # Utility functions
    "normalize_title",
    "calculate_similarity",
    "build_doc_path",
    "parse_doc_structure",
    "find_best_match",
    "sanitize_filename",
    "is_valid_doc_directory",
    "extract_doc_name_and_version",
    "extract_title_from_md_file",
    "extract_section_by_title",
    # BM25 matcher (v3.1.0)
    "BM25Matcher",
    "BM25Config",
    "calculate_bm25_similarity",
    "create_bm25_matcher_from_files",
    "tokenize_text",
    # Transformer matcher (v3.3.0)
    "TransformerMatcher",
    "TransformerConfig",
    # ModelScope matcher (v3.4.0)
    "ModelScopeMatcher",
    "ModelScopeConfig",
]

__version__ = "3.3.0"
