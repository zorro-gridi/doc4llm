"""
Markdown document extraction tool for doc4llm.

This is a sub-package providing tools for extracting content from markdown documents
stored in the md_docs directory structure.

Example:
    >>> from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor
    >>> extractor = MarkdownDocExtractor()
    >>> content = extractor.extract_by_title("Agent Skills - Claude Code Docs")

Agentic matching:
    >>> from doc4llm.tool.md_doc_extractor import AgenticDocMatcher
    >>> matcher = AgenticDocMatcher(extractor)
    >>> results = matcher.match("skills")
"""

from .doc_extractor import MarkdownDocExtractor
from .agentic_matcher import (
    AgenticDocMatcher,
    ProgressiveRetriever,
    ReflectiveReRanker,
    MatchResult,
    agentic_search,
)
from .query_optimizer import (
    QueryOptimizer,
    OptimizedQuery,
    QueryAnalysis,
    optimize_query,
)
from .chain_reasoner import (
    ChainReasoner,
    ReasoningStep,
    ReasoningResult,
    chain_reason,
)
from .conversation_memory import (
    ConversationMemory,
    ConversationTurn,
    ConversationSession,
    create_memory,
)
from .hybrid_matcher import (
    HybridMatcher,
    LLMEnhancement,
    hybrid_search,
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

__all__ = [
    # Main extractor class
    "MarkdownDocExtractor",
    # Agentic matcher (v2.0.0)
    "AgenticDocMatcher",
    "ProgressiveRetriever",
    "ReflectiveReRanker",
    "MatchResult",
    "agentic_search",
    # Query optimizer (v2.2.0)
    "QueryOptimizer",
    "OptimizedQuery",
    "QueryAnalysis",
    "optimize_query",
    # Chain reasoner (v2.3.0)
    "ChainReasoner",
    "ReasoningStep",
    "ReasoningResult",
    "chain_reason",
    # Conversation memory (v2.4.0)
    "ConversationMemory",
    "ConversationTurn",
    "ConversationSession",
    "create_memory",
    # Hybrid matcher (v2.1.0) - LLM-enhanced
    "HybridMatcher",
    "LLMEnhancement",
    "hybrid_search",
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
]

__version__ = "2.1.0"
