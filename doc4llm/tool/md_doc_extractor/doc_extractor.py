"""
Markdown document extractor for doc4llm documentation output.

This module provides the main MarkdownDocExtractor class for extracting content
from markdown documents stored in the md_docs directory structure.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from ...scanner.utils import DebugMixin
from . import utils
from .exceptions import (
    BaseDirectoryNotFoundError,
    ConfigurationError,
    DocumentNotFoundError,
    InvalidTitleError,
    NoDocumentsFoundError,
    SingleFileNotFoundError,
)


@dataclass
class ExtractionResult:
    """Result of multi-document extraction with metadata.

    Attributes:
        contents: Dictionary mapping document titles to their content
        total_line_count: Cumulative line count across all extracted documents
        individual_counts: Dictionary mapping document titles to their line counts
        requires_processing: Whether total line count exceeds threshold (default: > 2100)
        threshold: The threshold used for requires_processing check
        document_count: Number of successfully extracted documents
    """
    contents: Dict[str, str]
    total_line_count: int
    individual_counts: Dict[str, int] = field(default_factory=dict)
    requires_processing: bool = False
    threshold: int = 2100
    document_count: int = 0

    def __post_init__(self):
        """Calculate derived fields after initialization."""
        self.document_count = len(self.contents)
        # Update requires_processing based on threshold
        self.requires_processing = self.total_line_count > self.threshold

    def to_summary(self) -> str:
        """Return a human-readable summary of the extraction result."""
        lines = [
            f"📊 Extraction Result Summary:",
            f"   Documents extracted: {self.document_count}",
            f"   Total line count: {self.total_line_count}",
            f"   Threshold: {self.threshold}",
        ]
        if self.requires_processing:
            lines.append(f"   ⚠️  THRESHOLD EXCEEDED by {self.total_line_count - self.threshold} lines")
            lines.append(f"   → md-doc-processor SHOULD be invoked")
        else:
            margin = self.threshold - self.total_line_count
            lines.append(f"   ✓ Within threshold (margin: {margin} lines)")
            lines.append(f"   → Can return directly to user")

        lines.append("\n Individual document breakdown:")
        for title, count in self.individual_counts.items():
            lines.append(f"   - {title}: {count} lines")

        return "\n".join(lines)


class MarkdownDocExtractor(DebugMixin):
    """Extract content from markdown documents in md_docs directory.

    This class provides methods to extract content from markdown documents
    organized in the md_docs directory structure. It supports
    various search modes including exact match, case-insensitive, fuzzy matching,
    and partial matching.

    The expected directory structure is:
        md_docs/
        └── <doc_name>:<doc_version>/
            └── <PageTitle>/
                └── docContent.md

    Example:
        >>> extractor = MarkdownDocExtractor()
        >>> content = extractor.extract_by_title("Agent Skills - Claude Code Docs")
        >>> results = extractor.extract_by_titles(["Agent Skills", "Slash Commands"])
    """

    # Valid search modes
    VALID_SEARCH_MODES = {"exact", "case_insensitive", "fuzzy", "partial"}

    def __init__(
        self,
        base_dir: str | None = None,
        single_file_path: str | None = None,
        search_mode: str = "exact",
        case_sensitive: bool = False,
        max_results: int | None = None,
        fuzzy_threshold: float = 0.6,
        debug_mode: bool = False,
        enable_fallback: bool = False,
        fallback_modes: List[str] | None = None,
        compress_threshold: int = 1000,
        enable_compression: bool = False,
    ):
        """Initialize the extractor with configuration.

        Args:
            base_dir: Base documentation directory (defaults to "md_docs")
            single_file_path: Path to a single .md file for single-file mode
            search_mode: Search mode - "exact", "case_insensitive", "fuzzy", or "partial"
            case_sensitive: Whether exact matching should be case sensitive
            max_results: Maximum number of results to return for fuzzy/partial searches
            fuzzy_threshold: Minimum similarity ratio (0.0 to 1.0) for fuzzy matching
            debug_mode: Enable debug output
            enable_fallback: Enable automatic fallback to other search modes on failure
            fallback_modes: List of search modes to try as fallback (default: ["case_insensitive", "partial", "fuzzy"])
            compress_threshold: Line count threshold for content compression (default: 2000)
            enable_compression: Enable automatic content compression for large documents

        Raises:
            ConfigurationError: If search_mode or other configuration is invalid
            SingleFileNotFoundError: If single_file_path is provided but invalid
        """
        # Initialize DebugMixin
        DebugMixin.__init__(self, debug_mode=debug_mode)

        # Check for single file mode
        self._single_file_mode = False
        self._single_file_path = None
        self._single_file_title = None

        if single_file_path is not None:
            self._single_file_mode = True
            self._single_file_path = single_file_path
            path = Path(single_file_path)

            # Validate file exists
            if not path.exists() or not path.is_file():
                raise SingleFileNotFoundError(
                    single_file_path,
                    f"File does not exist or is not a file"
                )

            # Validate .md extension
            if not single_file_path.endswith('.md'):
                raise SingleFileNotFoundError(
                    single_file_path,
                    f"File must have .md extension"
                )

            # Extract and cache title from file
            try:
                self._single_file_title = utils.extract_title_from_md_file(single_file_path)
            except InvalidTitleError as e:
                raise SingleFileNotFoundError(
                    single_file_path,
                    f"Cannot extract title from file: {e}"
                )

            self._debug_print(f"Single file mode enabled: {single_file_path}")
            self._debug_print(f"Extracted title: '{self._single_file_title}'")

        # Set base directory (only used in directory mode)
        self.base_dir = base_dir or "md_docs"

        # Validate and set search mode
        if search_mode not in self.VALID_SEARCH_MODES:
            raise ConfigurationError(
                "search_mode",
                f"Must be one of {self.VALID_SEARCH_MODES}, got '{search_mode}'"
            )
        self.search_mode = search_mode

        # Set other configuration
        self.case_sensitive = case_sensitive
        self.max_results = max_results
        self.fuzzy_threshold = fuzzy_threshold

        # Validate fuzzy threshold
        if not 0.0 <= self.fuzzy_threshold <= 1.0:
            raise ConfigurationError(
                "fuzzy_threshold",
                f"Must be between 0.0 and 1.0, got {self.fuzzy_threshold}"
            )

        # New configuration parameters for fallback and compression
        self.enable_fallback = enable_fallback
        self.fallback_modes = fallback_modes or ["case_insensitive", "partial", "fuzzy"]
        self.compress_threshold = compress_threshold
        self.enable_compression = enable_compression

        # Validate fallback modes
        for mode in self.fallback_modes:
            if mode not in self.VALID_SEARCH_MODES:
                raise ConfigurationError(
                    "fallback_modes",
                    f"Invalid mode '{mode}'. Must be one of {self.VALID_SEARCH_MODES}"
                )

        # Validate compress threshold
        if self.compress_threshold < 0:
            raise ConfigurationError(
                "compress_threshold",
                f"Must be non-negative, got {self.compress_threshold}"
            )

        # Cache for document structure
        self._doc_structure: Dict[str, List[str]] | None = None

        if not self._single_file_mode:
            self._debug_print(f"Initialized with base_dir: {self.base_dir}")
            self._debug_print(f"Search mode: {self.search_mode}")
            if self.enable_fallback:
                self._debug_print(f"Fallback enabled: {self.fallback_modes}")

    def _get_doc_structure(self, force_refresh: bool = False) -> Dict[str, List[str]]:
        """Get the document structure, using cache if available.

        Args:
            force_refresh: Force re-parsing of the directory structure

        Returns:
            Dictionary mapping document names to lists of page titles

        Raises:
            BaseDirectoryNotFoundError: If base directory doesn't exist
            NoDocumentsFoundError: If no documents are found
        """
        # In single file mode, return a simple structure with just the single file
        if self._single_file_mode:
            if self._doc_structure is None or force_refresh:
                # Use a simple key for the single file structure
                self._doc_structure = {
                    "single_file": [self._single_file_title]
                }
                self._debug_print(f"Single file mode: title = '{self._single_file_title}'")
            return self._doc_structure

        if self._doc_structure is None or force_refresh:
            self._debug_print("Parsing document structure...")
            self._doc_structure = utils.parse_doc_structure(self.base_dir)
            total_docs = sum(len(titles) for titles in self._doc_structure.values())
            self._debug_print(f"Found {len(self._doc_structure)} doc sets with {total_docs} total pages")

        return self._doc_structure

    def _read_doc_content(self, doc_path: str) -> str:
        """Read content from a docContent.md file.

        Args:
            doc_path: Full path to the docContent.md file

        Returns:
            The content of the file as a string

        Raises:
            DocumentNotFoundError: If the file doesn't exist
        """
        path = Path(doc_path)

        if not path.exists() or not path.is_file():
            raise DocumentNotFoundError(
                path.parent.name,
                str(path)
            )

        try:
            content = path.read_text(encoding="utf-8")
            self._debug_print(f"Read {len(content)} characters from {doc_path}")
            return content
        except Exception as e:
            raise DocumentNotFoundError(
                path.parent.name,
                f"Failed to read file: {e}"
            )

    def _find_exact_match(
        self,
        title: str,
        titles: List[str]
    ) -> str | None:
        """Find an exact title match.

        Args:
            title: The title to search for
            titles: List of available titles

        Returns:
            The matched title or None if not found
        """
        normalized_query = utils.normalize_title(title)

        for available_title in titles:
            normalized_available = utils.normalize_title(available_title)

            if self.case_sensitive:
                if normalized_query == normalized_available:
                    return available_title
            else:
                if normalized_query.lower() == normalized_available.lower():
                    return available_title

        return None

    def _find_partial_match(
        self,
        title: str,
        titles: List[str]
    ) -> List[str]:
        """Find all partial (substring) matches.

        Args:
            title: The title to search for
            titles: List of available titles

        Returns:
            List of titles containing the query as a substring
        """
        normalized_query = utils.normalize_title(title).lower()
        matches = []

        for available_title in titles:
            normalized_available = utils.normalize_title(available_title).lower()
            if normalized_query in normalized_available:
                matches.append(available_title)

        return matches

    def extract_by_title(self, title: str | None = None) -> str | None:
        """Extract content for a single document title.

        Args:
            title: The document title to extract. In single file mode, if None,
                   returns the file content directly. Otherwise, performs title
                   matching.

        Returns:
            In single file mode:
                - If title is None: returns the file content
                - If title is provided and matches: returns the file content
                - If title is provided but doesn't match: returns empty string ""
            In directory mode:
                - The document content as a string, or None if not found

        Examples:
            >>> # Single file mode - direct read
            >>> extractor = MarkdownDocExtractor(single_file_path="/path/to/file.md")
            >>> content = extractor.extract_by_title()
            >>> # Single file mode - with title matching
            >>> content = extractor.extract_by_title("Agent Skills")
            >>> # Directory mode
            >>> extractor = MarkdownDocExtractor()
            >>> content = extractor.extract_by_title("Agent Skills - Claude Code Docs")
        """
        self._debug_print(f"Extracting document: '{title}'")

        # Single file mode handling
        if self._single_file_mode:
            # Type assertions for single file mode (guaranteed to be set after __init__)
            file_path = self._single_file_path
            file_title = self._single_file_title
            assert file_path is not None, "Single file path must be set in single file mode"
            assert file_title is not None, "Single file title must be set in single file mode"

            # If title is None, return the file content directly
            if title is None:
                self._debug_print("Single file mode: returning file content directly")
                return Path(file_path).read_text(encoding="utf-8")

            # Title is provided - validate and match
            if not title or not str(title).strip():
                raise InvalidTitleError(title, "Title cannot be empty")

            # Check if title matches the extracted file title
            matched_title = self._find_exact_match(title, [file_title])

            if matched_title:
                self._debug_print(f"Title matched in single file mode: '{matched_title}'")
                return Path(file_path).read_text(encoding="utf-8")
            else:
                self._debug_print(f"Title '{title}' did not match file title '{file_title}'")
                # Return empty string in single file mode (not None)
                return ""

        # Directory mode - title is required
        if not title or not str(title).strip():
            raise InvalidTitleError(title, "Title cannot be empty")

        # Get document structure
        try:
            doc_structure = self._get_doc_structure()
        except (BaseDirectoryNotFoundError, NoDocumentsFoundError) as e:
            self._debug_print(f"Error getting document structure: {e}")
            return None

        # Flatten all titles from all document sets
        all_titles = []
        for titles_list in doc_structure.values():
            all_titles.extend(titles_list)

        # Find the matching title based on search mode
        matched_title = None
        doc_name_version = None  # Initialize before fallback

        if self.search_mode in ("exact", "case_insensitive"):
            matched_title = self._find_exact_match(title, all_titles)

        elif self.search_mode == "partial":
            matches = self._find_partial_match(title, all_titles)
            if matches:
                matched_title = matches[0]  # Return first match

        elif self.search_mode == "fuzzy":
            result = utils.find_best_match(title, all_titles, self.fuzzy_threshold)
            if result:
                matched_title, score = result
                self._debug_print(f"Fuzzy match found with score: {score:.2f}")

        if matched_title is None:
            self._debug_print(f"No match found for '{title}'")
            # Try fallback modes if enabled
            if self.enable_fallback:
                self._debug_print("Fallback enabled, trying alternative search modes...")
                for fallback_mode in self.fallback_modes:
                    if fallback_mode == self.search_mode:
                        continue  # Skip the mode we already tried

                    self._debug_print(f"Trying fallback mode: {fallback_mode}")
                    fallback_result = self._extract_with_mode(title, fallback_mode, all_titles)
                    if fallback_result:
                        self._debug_print(f"Found match using {fallback_mode} mode")
                        matched_title = fallback_result["title"]
                        doc_name_version = fallback_result["doc_name_version"]
                        break

            if matched_title is None:
                return None

        # Find the document set that contains this title
        if doc_name_version is None:
            for doc_key, titles in doc_structure.items():
                if matched_title in titles:
                    doc_name_version = doc_key
                    break

        if doc_name_version is None:
            self._debug_print(f"Could not find document set for title: {matched_title}")
            return None

        # Parse doc name and version
        if ":" in doc_name_version:
            doc_name, doc_version = doc_name_version.split(":", 1)
        else:
            doc_name = doc_name_version
            doc_version = "latest"

        # Build the path and read content
        doc_path = utils.build_doc_path(self.base_dir, doc_name, doc_version, matched_title)

        try:
            content = self._read_doc_content(doc_path)
            return content
        except DocumentNotFoundError as e:
            self._debug_print(f"Error reading document: {e}")
            return None

    def extract_by_titles(self, titles: List[str]) -> Dict[str, str]:
        """Extract content for multiple document titles.

        Args:
            titles: List of document titles to extract

        Returns:
            Dictionary mapping title to content. Titles that cannot be found
            will not be included in the result.

            In single file mode: only returns entries for titles that match
            the single file's title.

        Examples:
            >>> extractor = MarkdownDocExtractor()
            >>> results = extractor.extract_by_titles([
            ...     "Agent Skills - Claude Code Docs",
            ...     "Slash Commands"
            ... ])
            >>> for title, content in results.items():
            ...     print(f"{title}: {len(content)} characters")
        """
        if not titles:
            return {}

        self._debug_print(f"Extracting {len(titles)} documents")

        results: Dict[str, str] = {}

        for title in titles:
            content = self.extract_by_title(title)
            # In single file mode, empty string means no match
            # In directory mode, None means not found
            if content and content != "":
                results[title] = content
            else:
                self._debug_print(f"Failed to extract: '{title}'")

        self._debug_print(f"Successfully extracted {len(results)}/{len(titles)} documents")

        return results

    def extract_by_titles_with_metadata(
        self,
        titles: List[str],
        threshold: int = 2100
    ) -> ExtractionResult:
        """Extract multiple documents with complete metadata including line counts.

        This method is designed for multi-document scenarios where cumulative
        line count tracking is critical for determining whether post-processing
        is required (e.g., invoking md-doc-processor for compression).

        Args:
            titles: List of document titles to extract
            threshold: Line count threshold for requiring post-processing (default: 2100)

        Returns:
            ExtractionResult containing:
                - contents: Dict mapping title to content
                - total_line_count: Cumulative line count across ALL documents
                - individual_counts: Dict mapping title to its line count
                - requires_processing: Whether total_line_count exceeds threshold
                - threshold: The threshold used for the check
                - document_count: Number of successfully extracted documents

        Examples:
            >>> extractor = MarkdownDocExtractor()
            >>> result = extractor.extract_by_titles_with_metadata([
            ...     "Hooks reference",
            ...     "Deployment guide",
            ...     "Best practices"
            ... ])
            >>>
            >>> # Check if processing is required
            >>> if result.requires_processing:
            ...     print(f"Need to process: {result.total_line_count} lines")
            ...     # Invoke md-doc-processor
            ... else:
            ...     print(f"Within threshold: {result.total_line_count} lines")
            ...     # Return directly
            >>>
            >>> # Print summary
            >>> print(result.to_summary())
        """
        if not titles:
            return ExtractionResult(
                contents={},
                total_line_count=0,
                individual_counts={},
                requires_processing=False,
                threshold=threshold,
                document_count=0
            )

        self._debug_print(f"Extracting {len(titles)} documents with metadata tracking")

        results: Dict[str, str] = {}
        individual_counts: Dict[str, int] = {}
        total_lines = 0

        for title in titles:
            content = self.extract_by_title(title)
            # In single file mode, empty string means no match
            # In directory mode, None means not found
            if content and content != "":
                results[title] = content
                line_count = len(content.split('\n'))
                individual_counts[title] = line_count
                total_lines += line_count
                self._debug_print(f"  ✓ '{title}': {line_count} lines")
            else:
                self._debug_print(f"  ✗ Failed to extract: '{title}'")

        # Determine if processing is required
        requires_processing = total_lines > threshold

        result = ExtractionResult(
            contents=results,
            total_line_count=total_lines,
            individual_counts=individual_counts,
            requires_processing=requires_processing,
            threshold=threshold,
            document_count=len(results)
        )

        self._debug_print(f"\n📊 Extraction Summary:")
        self._debug_print(f"   Extracted: {result.document_count}/{len(titles)} documents")
        self._debug_print(f"   Total lines: {total_lines}")
        self._debug_print(f"   Threshold: {threshold}")
        if requires_processing:
            self._debug_print(f"   ⚠️  THRESHOLD EXCEEDED by {total_lines - threshold} lines")
        else:
            margin = threshold - total_lines
            self._debug_print(f"   ✓ Within threshold (margin: {margin} lines)")

        return result

    def search_documents(self, title: str) -> List[Dict[str, Any]]:
        """Search for documents matching a title pattern.

        Returns detailed information about matching documents including
        similarity scores for fuzzy matching.

        Args:
            title: The title pattern to search for

        Returns:
            List of dictionaries containing:
                - title: The matched document title
                - similarity: Similarity score (for fuzzy search)
                - doc_name_version: Document name and version (e.g., "code_claude_com:latest")

            In single file mode: returns a single entry if the title matches,
            or an empty list if it doesn't match.

        Examples:
            >>> extractor = MarkdownDocExtractor(search_mode="fuzzy")
            >>> results = extractor.search_documents("agent skills")
            >>> for result in results:
            ...     print(f"{result['title']} (similarity: {result['similarity']:.2f})")
        """
        self._debug_print(f"Searching for: '{title}'")

        # Single file mode - just check if title matches the single file
        if self._single_file_mode:
            file_title = self._single_file_title
            assert file_title is not None, "Single file title must be set in single file mode"

            if self.search_mode in ("exact", "case_insensitive"):
                match = self._find_exact_match(title, [file_title])
                if match:
                    return [{
                        "title": file_title,
                        "similarity": 1.0,
                        "doc_name_version": "single_file",
                    }]
            elif self.search_mode == "partial":
                matches = self._find_partial_match(title, [file_title])
                if matches:
                    return [{
                        "title": file_title,
                        "similarity": 1.0,
                        "doc_name_version": "single_file",
                    }]
            elif self.search_mode == "fuzzy":
                similarity = utils.calculate_similarity(title, file_title)
                if similarity >= self.fuzzy_threshold:
                    return [{
                        "title": file_title,
                        "similarity": similarity,
                        "doc_name_version": "single_file",
                    }]

            return []

        # Get document structure
        try:
            doc_structure = self._get_doc_structure()
        except (BaseDirectoryNotFoundError, NoDocumentsFoundError) as e:
            self._debug_print(f"Error getting document structure: {e}")
            return []

        # Flatten all titles with their document set info
        all_titles_with_doc = []
        for doc_key, titles in doc_structure.items():
            for t in titles:
                all_titles_with_doc.append((t, doc_key))

        results: List[Dict[str, Any]] = []

        if self.search_mode in ("exact", "case_insensitive"):
            match = self._find_exact_match(title, [t for t, _ in all_titles_with_doc])
            if match:
                for t, doc_key in all_titles_with_doc:
                    if t == match:
                        results.append({
                            "title": t,
                            "similarity": 1.0,
                            "doc_name_version": doc_key,
                        })
                        break

        elif self.search_mode == "partial":
            matches = self._find_partial_match(title, [t for t, _ in all_titles_with_doc])
            for t, doc_key in all_titles_with_doc:
                if t in matches:
                    results.append({
                        "title": t,
                        "similarity": 1.0,
                        "doc_name_version": doc_key,
                    })

        elif self.search_mode == "fuzzy":
            for t, doc_key in all_titles_with_doc:
                similarity = utils.calculate_similarity(title, t)
                if similarity >= self.fuzzy_threshold:
                    results.append({
                        "title": t,
                        "similarity": similarity,
                        "doc_name_version": doc_key,
                    })

            # Sort by similarity descending
            results.sort(key=lambda x: x["similarity"], reverse=True)

        # Apply max_results limit
        if self.max_results and len(results) > self.max_results:
            results = results[:self.max_results]

        self._debug_print(f"Found {len(results)} matches")

        return results

    def list_available_documents(self, doc_name_version: str | None = None) -> List[str]:
        """List all available document titles.

        Args:
            doc_name_version: Optional document name and version filter
                             (e.g., "code_claude_com:latest"). If None,
                             lists all documents from all sets.

        Returns:
            List of available document titles

            In single file mode: returns a list with the single file's title,
            or an empty list if doc_name_version doesn't match "single_file".

        Examples:
            >>> extractor = MarkdownDocExtractor()
            >>> all_docs = extractor.list_available_documents()
            >>> claude_docs = extractor.list_available_documents("code_claude_com:latest")
        """
        self._debug_print("Listing available documents")

        # Single file mode
        if self._single_file_mode:
            file_title = self._single_file_title
            assert file_title is not None, "Single file title must be set in single file mode"

            if doc_name_version is None or doc_name_version == "single_file":
                return [file_title]
            return []

        try:
            doc_structure = self._get_doc_structure()
        except (BaseDirectoryNotFoundError, NoDocumentsFoundError) as e:
            self._debug_print(f"Error getting document structure: {e}")
            return []

        if doc_name_version is None:
            # Return all titles from all document sets
            all_titles = []
            for titles in doc_structure.values():
                all_titles.extend(titles)
            return sorted(all_titles)
        else:
            # Return titles for specific document set
            return doc_structure.get(doc_name_version, [])

    def get_document_info(self, title: str) -> Dict[str, Any] | None:
        """Get detailed information about a document.

        Args:
            title: The document title

        Returns:
            Dictionary containing document information including:
                - title: Document title
                - doc_name_version: Document name and version
                - path: Full path to docContent.md
                - exists: Whether the file exists
                - size: File size in bytes (if exists)

            In single file mode: returns info if title matches the file,
            otherwise returns None.

        Examples:
            >>> extractor = MarkdownDocExtractor()
            >>> info = extractor.get_document_info("Agent Skills - Claude Code Docs")
            >>> print(f"Size: {info['size']} bytes")
        """
        self._debug_print(f"Getting info for: '{title}'")

        # Single file mode
        if self._single_file_mode:
            file_path = self._single_file_path
            file_title = self._single_file_title
            assert file_path is not None, "Single file path must be set in single file mode"
            assert file_title is not None, "Single file title must be set in single file mode"

            # Check if title matches the single file title
            matched_title = self._find_exact_match(title, [file_title])
            if not matched_title:
                return None

            path = Path(file_path)
            return {
                "title": file_title,
                "doc_name_version": "single_file",
                "path": file_path,
                "exists": True,
                "size": path.stat().st_size,
            }

        try:
            doc_structure = self._get_doc_structure()
        except (BaseDirectoryNotFoundError, NoDocumentsFoundError):
            return None

        # Find the document set containing this title
        doc_name_version = None
        for doc_key, titles in doc_structure.items():
            if title in titles:
                doc_name_version = doc_key
                break

        if doc_name_version is None:
            return None

        # Parse doc name and version
        if ":" in doc_name_version:
            doc_name, doc_version = doc_name_version.split(":", 1)
        else:
            doc_name = doc_name_version
            doc_version = "latest"

        # Build the path
        doc_path = utils.build_doc_path(self.base_dir, doc_name, doc_version, title)
        path = Path(doc_path)

        info = {
            "title": title,
            "doc_name_version": doc_name_version,
            "path": doc_path,
            "exists": path.exists() and path.is_file(),
        }

        if info["exists"]:
            info["size"] = path.stat().st_size

        return info

    def _extract_with_mode(
        self,
        title: str,
        mode: str,
        all_titles: List[str] | None = None
    ) -> Dict[str, Any] | None:
        """Extract content using a specific search mode without modifying instance state.

        Args:
            title: The title to search for
            mode: The search mode to use
            all_titles: Optional list of all available titles (for efficiency)

        Returns:
            Dictionary with 'title' and 'doc_name_version' keys, or None if not found
        """
        # Get document structure if all_titles not provided
        if all_titles is None:
            try:
                doc_structure = self._get_doc_structure()
                all_titles = []
                for titles_list in doc_structure.values():
                    all_titles.extend(titles_list)
            except (BaseDirectoryNotFoundError, NoDocumentsFoundError):
                return None

        # Find the matching title based on the specified mode
        matched_title = None

        if mode in ("exact", "case_insensitive"):
            matched_title = self._find_exact_match(title, all_titles)

        elif mode == "partial":
            matches = self._find_partial_match(title, all_titles)
            if matches:
                matched_title = matches[0]

        elif mode == "fuzzy":
            result = utils.find_best_match(title, all_titles, self.fuzzy_threshold)
            if result:
                matched_title, score = result
                self._debug_print(f"Fuzzy match with score: {score:.2f}")

        if matched_title is None:
            return None

        # Find the document set that contains this title
        try:
            doc_structure = self._get_doc_structure()
        except (BaseDirectoryNotFoundError, NoDocumentsFoundError):
            return None

        doc_name_version = None
        for doc_key, titles in doc_structure.items():
            if matched_title in titles:
                doc_name_version = doc_key
                break

        if doc_name_version is None:
            return None

        return {
            "title": matched_title,
            "doc_name_version": doc_name_version
        }

    def extract_by_title_with_candidates(
        self,
        title: str,
        max_candidates: int = 5,
        min_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Extract multiple candidate documents matching the query.

        Returns multiple documents that match the query, sorted by similarity.
        This is useful when you want to present multiple options to the user.

        Args:
            title: The title query to search for
            max_candidates: Maximum number of candidates to return
            min_threshold: Minimum similarity threshold (0.0 to 1.0)

        Returns:
            List of dictionaries containing:
                - title: Document title
                - similarity: Similarity score (0.0 to 1.0)
                - doc_name_version: Document name and version
                - content_preview: First 200 characters of content

        Examples:
            >>> extractor = MarkdownDocExtractor()
            >>> candidates = extractor.extract_by_title_with_candidates("agent skills", max_candidates=3)
            >>> for c in candidates:
            ...     print(f"{c['title']} (similarity: {c['similarity']:.2f})")
        """
        self._debug_print(f"Extracting candidates for: '{title}'")

        # Get all available titles
        try:
            doc_structure = self._get_doc_structure()
        except (BaseDirectoryNotFoundError, NoDocumentsFoundError) as e:
            self._debug_print(f"Error getting document structure: {e}")
            return []

        # Flatten all titles with their document set info
        all_titles_with_doc = []
        for doc_key, titles in doc_structure.items():
            for t in titles:
                all_titles_with_doc.append((t, doc_key))

        # Calculate similarity for all titles
        candidates = []
        for t, doc_key in all_titles_with_doc:
            similarity = utils.calculate_similarity(title, t)

            if similarity >= min_threshold:
                # Try to get content preview
                content_preview = ""
                try:
                    if ":" in doc_key:
                        doc_name, doc_version = doc_key.split(":", 1)
                    else:
                        doc_name = doc_key
                        doc_version = "latest"

                    doc_path = utils.build_doc_path(self.base_dir, doc_name, doc_version, t)
                    content = self._read_doc_content(doc_path)
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                except Exception:
                    content_preview = ""

                candidates.append({
                    "title": t,
                    "similarity": similarity,
                    "doc_name_version": doc_key,
                    "content_preview": content_preview
                })

        # Sort by similarity descending
        candidates.sort(key=lambda x: x["similarity"], reverse=True)

        # Limit results
        if max_candidates and len(candidates) > max_candidates:
            candidates = candidates[:max_candidates]

        self._debug_print(f"Found {len(candidates)} candidates")

        return candidates

    def semantic_search_titles(
        self,
        query: str,
        doc_set: str | None = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Semantic search across document titles using multiple search strategies.

        Combines exact match, partial match, and fuzzy matching to find relevant documents.

        Args:
            query: The search query
            doc_set: Optional document set filter (e.g., "code_claude_com:latest")
            max_results: Maximum number of results to return

        Returns:
            List of dictionaries containing:
                - title: Document title
                - similarity: Similarity score (0.0 to 1.0)
                - match_type: Type of match ("exact", "partial", "fuzzy")
                - doc_name_version: Document name and version

        Examples:
            >>> extractor = MarkdownDocExtractor()
            >>> results = extractor.semantic_search_titles("skill", max_results=5)
        """
        self._debug_print(f"Semantic search for: '{query}'")

        # Get document structure
        try:
            doc_structure = self._get_doc_structure()
        except (BaseDirectoryNotFoundError, NoDocumentsFoundError) as e:
            self._debug_print(f"Error getting document structure: {e}")
            return []

        # Filter by doc_set if specified
        if doc_set:
            if doc_set not in doc_structure:
                return []
            titles_to_search = [(t, doc_set) for t in doc_structure[doc_set]]
        else:
            titles_to_search = []
            for doc_key, titles in doc_structure.items():
                for t in titles:
                    titles_to_search.append((t, doc_key))

        results: List[Dict[str, Any]] = []

        # Strategy 1: Exact match (weight 1.0)
        exact_match = self._find_exact_match(query, [t for t, _ in titles_to_search])
        if exact_match:
            for t, doc_key in titles_to_search:
                if t == exact_match:
                    results.append({
                        "title": t,
                        "similarity": 1.0,
                        "match_type": "exact",
                        "doc_name_version": doc_key
                    })
                    break

        # Strategy 2: Partial match (weight 0.8)
        partial_matches = self._find_partial_match(query, [t for t, _ in titles_to_search])
        for t, doc_key in titles_to_search:
            if t in partial_matches and t != exact_match:
                # Calculate similarity based on substring position
                if t.lower().startswith(query.lower()):
                    similarity = 0.9
                else:
                    similarity = 0.7

                results.append({
                    "title": t,
                    "similarity": similarity,
                    "match_type": "partial",
                    "doc_name_version": doc_key
                })

        # Strategy 3: Fuzzy match (weight 0.6)
        for t, doc_key in titles_to_search:
            if t == exact_match or t in partial_matches:
                continue  # Skip already matched

            similarity = utils.calculate_similarity(query, t)
            if similarity >= self.fuzzy_threshold:
                results.append({
                    "title": t,
                    "similarity": similarity,
                    "match_type": "fuzzy",
                    "doc_name_version": doc_key
                })

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # Limit results
        if max_results and len(results) > max_results:
            results = results[:max_results]

        self._debug_print(f"Semantic search found {len(results)} results")

        return results

    def extract_with_compression(
        self,
        title: str,
        query: str | None = None,
        summarize_prompt: str | None = None
    ) -> Dict[str, Any]:
        """Extract document content with automatic compression for large documents.

        For documents exceeding the compress_threshold, applies intelligent
        compression based on the query or smart truncation.

        Args:
            title: The document title to extract
            query: Optional query for relevance-based compression
            summarize_prompt: Optional custom prompt for summarization (future use)

        Returns:
            Dictionary containing:
                - title: Document title
                - content: Document content (compressed or original)
                - line_count: Number of lines in content
                - compressed: Whether compression was applied
                - compression_ratio: Compression ratio (0.0 to 1.0)
                - compression_method: Method used ("query_based", "smart_truncate", or None)

        Examples:
            >>> extractor = MarkdownDocExtractor(enable_compression=True, compress_threshold=100)
            >>> result = extractor.extract_with_compression("Large Doc", query="API reference")
            >>> if result['compressed']:
            ...     print(f"Compressed: {result['compression_ratio']:.0%}")
        """
        self._debug_print(f"Extracting with compression: '{title}'")

        # First, extract the content normally
        content = self.extract_by_title(title)

        if content is None:
            return {
                "title": title,
                "content": None,
                "line_count": 0,
                "compressed": False,
                "compression_ratio": 0.0,
                "compression_method": None
            }

        # Count lines
        line_count = len(content.split('\n'))

        # Check if compression is needed
        if self.enable_compression and line_count > self.compress_threshold:
            self._debug_print(f"Content ({line_count} lines) exceeds threshold ({self.compress_threshold}), compressing...")
            compressed_content = self._compress_content(content, query)

            compression_ratio = len(compressed_content) / len(content) if content else 0

            return {
                "title": title,
                "content": compressed_content,
                "line_count": line_count,
                "compressed": True,
                "compression_ratio": compression_ratio,
                "compression_method": "query_based" if query else "smart_truncate"
            }

        return {
            "title": title,
            "content": content,
            "line_count": line_count,
            "compressed": False,
            "compression_ratio": 0.0,
            "compression_method": None
        }

    def _compress_content(
        self,
        content: str,
        query: str | None = None
    ) -> str:
        """Compress long document content.

        Args:
            content: The content to compress
            query: Optional query for relevance-based compression

        Returns:
            Compressed content
        """
        lines = content.split('\n')

        if len(lines) <= self.compress_threshold:
            return content

        # Strategy 1: Query-based section extraction
        if query:
            return self._extract_relevant_sections(content, query)

        # Strategy 2: Smart truncation
        return self._smart_truncate(content)

    def _extract_relevant_sections(
        self,
        content: str,
        query: str
    ) -> str:
        """Extract sections relevant to the query.

        Parses markdown structure and extracts sections most relevant
        to the query, preserving code blocks intact.

        Args:
            content: Full markdown content
            query: Query string for relevance matching

        Returns:
            Extracted relevant sections
        """
        lines = content.split('\n')
        sections = []
        current_section = []
        current_heading = None
        current_level = 0

        for line in lines:
            # Check for heading
            if line.strip().startswith('#'):
                # Save previous section if it exists
                if current_heading is not None and current_section:
                    sections.append({
                        "level": current_level,
                        "heading": current_heading,
                        "content": '\n'.join(current_section)
                    })

                # Parse new heading
                match = re.match(r'^(#+)\s+(.+)$', line.strip())
                if match:
                    current_level = len(match.group(1))
                    current_heading = match.group(2).strip()
                    current_section = [line]
                else:
                    current_section.append(line)
            else:
                if current_section is not None:
                    current_section.append(line)

        # Add the last section
        if current_heading is not None and current_section:
            sections.append({
                "level": current_level,
                "heading": current_heading,
                "content": '\n'.join(current_section)
            })

        # Score sections by relevance
        scored_sections = []
        for section in sections:
            heading = section["heading"]
            content_text = section["content"]

            # Calculate relevance
            heading_score = utils.calculate_similarity(query, heading)
            content_score = 1.0 if query.lower() in content_text.lower() else 0.0

            # Combined score (heading is more important)
            combined_score = heading_score * 0.7 + content_score * 0.3

            # Boost score for code blocks
            if "```" in content_text:
                combined_score *= 1.2

            scored_sections.append({
                **section,
                "score": combined_score
            })

        # Sort by score
        scored_sections.sort(key=lambda x: x["score"], reverse=True)

        # Extract top sections (up to threshold)
        selected_sections = []
        total_lines = 0
        for section in scored_sections:
            section_lines = len(section["content"].split('\n'))
            if total_lines + section_lines <= self.compress_threshold * 1.5:
                selected_sections.append(section["content"])
                total_lines += section_lines
            elif not selected_sections:
                # Always include at least the top section
                selected_sections.append(section["content"])

        return '\n\n'.join(selected_sections)

    def _smart_truncate(self, content: str) -> str:
        """Intelligently truncate long content.

        Preserves:
        - Document header/overview
        - All code blocks
        - First paragraph of each section

        Args:
            content: Content to truncate

        Returns:
            Truncated content
        """
        lines = content.split('\n')

        if len(lines) <= self.compress_threshold:
            return content

        result = []
        line_count = 0
        in_code_block = False
        prev_heading_level = 0

        for line in lines:
            # Track code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                result.append(line)
                line_count += 1
                continue

            # Always include code blocks
            if in_code_block:
                result.append(line)
                line_count += 1
                continue

            # Check for heading
            if line.strip().startswith('#'):
                result.append(line)
                line_count += 1
                prev_heading_level = len(line.strip().split()[0])
                continue

            # Include content if under threshold
            if line_count < self.compress_threshold:
                # Skip empty lines after headings (but keep one)
                if not line.strip() and result and not result[-1].strip():
                    continue
                result.append(line)
                line_count += 1

        # Add truncation notice if needed
        if len(lines) > line_count:
            result.append(f"\n\n... ({len(lines) - line_count} more lines truncated)")

        return '\n'.join(result)

    @classmethod
    def from_config(cls, config_path: str | None = None) -> "MarkdownDocExtractor":
        """Create an extractor instance from a configuration file.

        Args:
            config_path: Path to config.json. If None, uses default location.

        Returns:
            A configured MarkdownDocExtractor instance

        Examples:
            >>> extractor = MarkdownDocExtractor.from_config()
        """
        # Default config path
        if config_path is None:
            config_path = "doc4llm/config/config.json"

        config_file = Path(config_path)

        if not config_file.exists():
            # Return with defaults if config doesn't exist
            return cls()

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Extract tool configuration if it exists
            tool_config = config.get("tool", {})
            extractor_config = tool_config.get("markdown_extractor", {})

            return cls(
                base_dir=extractor_config.get("base_dir", config.get("doc_dir", "md_docs")),
                search_mode=extractor_config.get("default_search_mode", "exact"),
                case_sensitive=extractor_config.get("case_sensitive", False),
                max_results=extractor_config.get("max_results", 10),
                fuzzy_threshold=extractor_config.get("fuzzy_threshold", 0.6),
                debug_mode=config.get("debug_mode", 0) == 1,
                enable_fallback=extractor_config.get("enable_fallback", False),
                fallback_modes=extractor_config.get("fallback_modes", None),
                compress_threshold=extractor_config.get("compress_threshold", 2000),
                enable_compression=extractor_config.get("enable_compression", False),
            )
        except (json.JSONDecodeError, IOError):
            # Return with defaults if config is invalid
            return cls()
