"""
Utility functions for the markdown document extraction tool.

This module provides helper functions for string normalization,
similarity calculation, path building, and documentation structure parsing.
"""
import difflib
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Regular expression for valid filename characters
VALID_FILENAME_PATTERN = re.compile(r'[^a-zA-Z0-9\s\-_\.,()\'"\[\]{}]')


def normalize_title(title: str) -> str:
    """Normalize a document title for consistent matching.

    This function performs the following normalizations:
    - Converts to string if not already
    - Strips leading/trailing whitespace
    - Replaces multiple spaces with single space
    - Removes special characters (keeps alphanumeric, spaces, hyphens, underscores)

    Args:
        title: The title string to normalize

    Returns:
        The normalized title string

    Raises:
        InvalidTitleError: If the title is None or empty after normalization

    Examples:
        >>> normalize_title("  Agent   Skills  ")
        'Agent Skills'
        >>> normalize_title("Skills/Tools")
        'SkillsTools'
    """
    from .exceptions import InvalidTitleError

    if title is None:
        raise InvalidTitleError(title, "Title cannot be None")

    title_str = str(title).strip()

    if not title_str:
        raise InvalidTitleError(title, "Title cannot be empty")

    # Replace multiple whitespace with single space
    title_str = re.sub(r'\s+', ' ', title_str)

    return title_str


def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate string similarity using difflib.SequenceMatcher.

    This function uses Python's built-in difflib.SequenceMatcher to calculate
    a similarity ratio between two strings. The ratio is a float between 0.0
    (no similarity) and 1.0 (identical strings).

    Args:
        str1: First string to compare
        str2: Second string to compare

    Returns:
        A float value between 0.0 and 1.0 representing similarity

    Examples:
        >>> calculate_similarity("hello", "hello")
        1.0
        >>> calculate_similarity("hello", "hallo")
        0.8
        >>> calculate_similarity("abc", "xyz")
        0.0
    """
    if not str1 or not str2:
        return 0.0

    # Normalize strings for comparison (case-insensitive)
    str1_normalized = str1.lower().strip()
    str2_normalized = str2.lower().strip()

    # Use SequenceMatcher for similarity calculation
    matcher = difflib.SequenceMatcher(None, str1_normalized, str2_normalized)
    return matcher.ratio()


def build_doc_path(
    base_dir: str,
    doc_name: str,
    doc_version: str,
    title: str
) -> str:
    """Build the full path to a document's docContent.md file.

    Constructs the path following the documentation structure:
    <base_dir>/<doc_name>@<doc_version>/<title>/docContent.md

    Args:
        base_dir: Base documentation directory (e.g., "md_docs")
        doc_name: Document name (e.g., "code_claude_com")
        doc_version: Document version (e.g., "latest")
        title: Page title (e.g., "Agent Skills - Claude Code Docs")

    Returns:
        The full path to the docContent.md file

    Raises:
        InvalidTitleError: If title is invalid

    Examples:
        >>> build_doc_path("md_docs", "code_claude_com", "latest", "Skills")
        'md_docs/code_claude_com@latest/Skills/docContent.md'
    """
    from .exceptions import InvalidTitleError

    if not title or not str(title).strip():
        raise InvalidTitleError(title, "Title cannot be empty")

    # Normalize the title
    normalized_title = normalize_title(title)

    # Build the document directory name with version
    doc_dir_name = f"{doc_name}@{doc_version}"

    # Construct the full path using pathlib for cross-platform compatibility
    path = Path(base_dir) / doc_dir_name / normalized_title / "docContent.md"

    return str(path)


def parse_doc_structure(base_dir: str) -> Dict[str, List[str]]:
    """Parse the documentation directory structure.

    Traverses the documentation directory and builds a dictionary mapping
    document names (with versions) to lists of available page titles.

    The expected structure is:
        <base_dir>/
        └── <doc_name>@<doc_version>/
            └── <PageTitle>/
                └── docContent.md

    Args:
        base_dir: Path to the documentation output directory

    Returns:
        A dictionary where keys are document names (e.g., "code_claude_com@latest")
        and values are lists of page titles (e.g., ["Agent Skills", "Slash Commands"])

    Raises:
        BaseDirectoryNotFoundError: If base_dir doesn't exist
        NoDocumentsFoundError: If no documents are found

    Examples:
        >>> parse_doc_structure("md_docs")
        {
            "code_claude_com@latest": ["Agent Skills - Claude Code Docs", "Slash Commands"],
            "other_docs@latest": ["Page 1", "Page 2"]
        }
    """
    from .exceptions import BaseDirectoryNotFoundError, NoDocumentsFoundError

    base_path = Path(base_dir)

    if not base_path.exists():
        raise BaseDirectoryNotFoundError(base_dir)

    if not base_path.is_dir():
        raise BaseDirectoryNotFoundError(f"{base_dir} is not a directory")

    result: Dict[str, List[str]] = {}

    # Iterate through all <doc_name>@<doc_version> directories
    for doc_dir in base_path.iterdir():
        if not doc_dir.is_dir():
            continue

        # Check if directory name matches the expected pattern (contains "@")
        if "@" not in doc_dir.name:
            continue

        doc_key = doc_dir.name
        titles: List[str] = []

        # Iterate through page title directories
        for title_dir in doc_dir.iterdir():
            if not title_dir.is_dir():
                continue

            # Check if docContent.md exists in this directory
            doc_content_file = title_dir / "docContent.md"
            if doc_content_file.exists() and doc_content_file.is_file():
                titles.append(title_dir.name)

        if titles:
            result[doc_key] = titles

    if not result:
        raise NoDocumentsFoundError(base_dir)

    return result


def find_best_match(
    query: str,
    candidates: List[str],
    threshold: float = 0.6
) -> Tuple[str, float] | None:
    """Find the best matching candidate for a query string.

    Uses fuzzy string matching to find the closest match from a list of candidates.

    Args:
        query: The query string to match
        candidates: List of candidate strings to search through
        threshold: Minimum similarity ratio (0.0 to 1.0) to consider a match valid

    Returns:
        A tuple of (best_match, similarity_score) if a match above threshold is found,
        None otherwise

    Examples:
        >>> find_best_match("agent skills", ["Agent Skills", "Slash Commands"], threshold=0.5)
        ("Agent Skills", 1.0)
        >>> find_best_match("unknown", ["Agent Skills"], threshold=0.8)
        None
    """
    if not candidates:
        return None

    best_match: str | None = None
    best_score = 0.0

    for candidate in candidates:
        score = calculate_similarity(query, candidate)
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_match is not None and best_score >= threshold:
        return best_match, best_score

    return None


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing or replacing invalid characters.

    Removes characters that are not typically allowed in filenames while
    preserving spaces, hyphens, underscores, and common punctuation.

    Args:
        filename: The filename to sanitize

    Returns:
        The sanitized filename

    Examples:
        >>> sanitize_filename("file/name?.txt")
        'filename.txt'
        >>> sanitize_title("My Document (final).md")
        'My Document (final).md'
    """
    # Replace invalid characters with empty string
    sanitized = VALID_FILENAME_PATTERN.sub('', filename)
    return sanitized.strip()


def is_valid_doc_directory(path: str) -> bool:
    """Check if a directory is a valid document directory.

    A valid document directory must:
    1. Exist and be a directory
    2. Contain a docContent.md file

    Args:
        path: Path to check

    Returns:
        True if the directory is a valid document directory, False otherwise
    """
    doc_path = Path(path)
    if not doc_path.exists() or not doc_path.is_dir():
        return False

    doc_content = doc_path / "docContent.md"
    return doc_content.exists() and doc_content.is_file()


def extract_doc_name_and_version(doc_dir: str) -> Tuple[str, str]:
    """Extract document name and version from a directory string.

    The directory name is expected to be in the format "name@version".

    Args:
        doc_dir: Directory name string (e.g., "code_claude_com@latest")

    Returns:
        A tuple of (doc_name, doc_version)

    Raises:
        InvalidTitleError: If the directory name format is invalid

    Examples:
        >>> extract_doc_name_and_version("code_claude_com@latest")
        ("code_claude_com", "latest")
        >>> extract_doc_name_and_version("docs@v1.0.0")
        ("docs", "v1.0.0")
    """
    from .exceptions import InvalidTitleError

    if "@" not in doc_dir:
        raise InvalidTitleError(
            doc_dir,
            "Directory name must contain '@' separator between name and version"
        )

    parts = doc_dir.split("@", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise InvalidTitleError(
            doc_dir,
            "Directory name must be in format 'name@version'"
        )

    return parts[0], parts[1]


def extract_title_from_md_file(file_path: str) -> str:
    """Extract title from a Markdown file.

    Reads the file content and extracts the first heading (one or more # characters).
    The heading markers (#) are stripped from the returned title.

    Args:
        file_path: Path to the Markdown file

    Returns:
        The extracted title with # markers and surrounding whitespace removed

    Raises:
        InvalidTitleError: If the file contains no heading

    Examples:
        >>> extract_title_from_md_file("/path/to/file.md")
        "Agent Skills - Claude Code Docs"
    """
    from .exceptions import InvalidTitleError

    path = Path(file_path)

    if not path.exists() or not path.is_file():
        raise InvalidTitleError(file_path, f"File not found: {file_path}")

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        raise InvalidTitleError(file_path, f"Failed to read file: {e}")

    # Look for the first line that starts with #
    for line in content.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("#"):
            # Remove the # markers and surrounding whitespace
            title = stripped_line.lstrip("#").strip()
            if title:
                return title

    raise InvalidTitleError(file_path, "No heading found in file")


def extract_core_title(heading: str) -> str:
    """Extract the core title text from a heading by removing prefixes and suffixes.

    This function:
    1. Removes numeric prefixes (e.g., "3.10. ", "1. ", "2) ")
    2. Removes URL suffixes (e.g., ": https://...", "：https://...")

    Args:
        heading: The heading text to process

    Returns:
        The core title text without prefixes and suffixes

    Examples:
        >>> extract_core_title("3.10. skill：https://opencode.ai/docs/tools#skill")
        'skill'
        >>> extract_core_title("1. Overview: https://example.com")
        'Overview'
        >>> extract_core_title("skill")
        'skill'
    """
    # Remove numeric prefixes: "3.10. skill" -> "skill"
    core = re.sub(r'^[\d\.]+[\)\-]?\s*', '', heading.strip())
    # Handle remaining patterns like "3.10." (no space after)
    core = re.sub(r'^[\d\.]+\s*', '', core)
    # Remove URL suffixes: "skill：https://..." or "skill: https://..."
    core = re.sub(r'[\：:]\s*https?://\S*$', '', core)
    return core.strip()


def extract_section_by_title(content: str, title: str) -> str | None:
    """Extract a section from markdown content by its heading title.

    This function searches for a heading matching the given title and returns
    the complete section content until the next heading of the same or higher level.
    Supports matching titles with or without numeric prefixes (e.g., "1. Title")
    and with or without URL suffixes (e.g., "Title: https://...").

    Args:
        content: Full markdown document content
        title: Section heading title to extract (without # prefix)

    Returns:
        The extracted section content including the heading, or None if not found

    Examples:
        >>> content = "# Doc\\n\\n## Section 1\\nContent\\n## Section 2\\nMore"
        >>> extract_section_by_title(content, "Section 1")
        "## Section 1\\nContent"
        >>> content = "## 1. Create your first Skill\\nContent"
        >>> extract_section_by_title(content, "Create your first Skill")
        "## 1. Create your first Skill\\nContent"
        >>> content = "### skill\\nContent"
        >>> extract_section_by_title(content, "3.10. skill：https://opencode.ai/docs/tools#skill")
        "### skill\\nContent"
    """
    lines = content.splitlines()
    start_idx = None
    heading_level = None

    # Extract core title by removing numeric prefixes and URL suffixes
    # This handles patterns like: "3.10. skill：https://..." -> "skill"
    core_title = extract_core_title(title)

    # Build list of title variants to try (in order of preference)
    # Prefer exact match first, then core title, then normalized variants
    title_variants = [title, core_title]

    # Also create normalized variants without numeric prefixes
    for tv in [title, core_title]:
        normalized = re.sub(r'^[\d\.]+[\)\-]?\s*', '', tv.strip())
        normalized = re.sub(r'^[\d\.]+\s*', '', normalized)
        if normalized and normalized not in title_variants:
            title_variants.append(normalized)

    # Remove duplicates while preserving order
    seen = set()
    title_variants = [x for x in title_variants if not (x in seen or seen.add(x))]

    # Find the heading
    for i, line in enumerate(lines):
        # Try each title variant
        for title_variant in title_variants:
            # Match the title as a heading (case-insensitive)
            # Also allow optional numeric prefix in the document
            pattern = r'^(#+)\s+(?:[\d\.]+[\)\-]?\s*)?' + re.escape(title_variant) + r'\s*$'
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                start_idx = i
                heading_level = len(match.group(1))
                break
        if start_idx is not None:
            break

    if start_idx is None:
        return None

    # heading_level is guaranteed to be set when start_idx is not None
    assert heading_level is not None

    # Find the end of the section (next heading at same or higher level)
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        match = re.match(r'^(#+)\s+', line)
        if match:
            current_level = len(match.group(1))
            if current_level <= heading_level:
                end_idx = i
                break

    # Extract the section
    section_lines = lines[start_idx:end_idx]
    return '\n'.join(section_lines)


def extract_toc_sections(
    toc_content: str,
    query: str | None = None,
    max_sections: int = 20
) -> List[Dict[str, Any]]:
    """Extract section headings from docTOC.md content.

    This function parses a docTOC.md file and extracts all section headings
    with their metadata including level, title, anchor, and line number.

    Args:
        toc_content: The content of docTOC.md file
        query: Optional query string to filter sections by title relevance
        max_sections: Maximum number of sections to return

    Returns:
        List of dictionaries containing:
            - level: Heading level (1-6, number of # characters)
            - title: Section title without # markers
            - anchor: URL-friendly anchor text (lowercase, hyphenated)
            - line_number: Line number in the original file

    Examples:
        >>> toc = "## Create your first Skill\\n### Configure hooks"
        >>> extract_toc_sections(toc)
        [
            {'level': 2, 'title': 'Create your first Skill', 'anchor': 'create-your-first-skill', 'line_number': 0},
            {'level': 3, 'title': 'Configure hooks', 'anchor': 'configure-hooks', 'line_number': 1}
        ]
    """
    sections: List[Dict[str, Any]] = []
    lines = toc_content.splitlines()

    for line_number, line in enumerate(lines):
        stripped = line.strip()

        # Match markdown heading pattern
        match = re.match(r'^(#+)\s+(.+)$', stripped)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()

            # Generate anchor (URL-friendly version)
            # Convert to lowercase, replace spaces with hyphens, remove special chars
            anchor = re.sub(r'[^\w\s-]', '', title.lower())
            anchor = re.sub(r'[-\s]+', '-', anchor).strip('-')

            sections.append({
                "level": level,
                "title": title,
                "anchor": anchor,
                "line_number": line_number
            })

    # Apply query filter if provided
    if query and sections:
        sections = semantic_match_toc_sections(sections, query)

    # Limit results
    if max_sections and len(sections) > max_sections:
        sections = sections[:max_sections]

    return sections


def semantic_match_toc_sections(
    toc_sections: List[Dict[str, Any]],
    query: str
) -> List[Dict[str, Any]]:
    """Sort and filter TOC sections by semantic relevance to a query.

    This function calculates similarity scores between each section title
    and the query, then sorts the sections by relevance.

    Args:
        toc_sections: List of section dictionaries from extract_toc_sections
        query: Query string to match against section titles

    Returns:
        List of sections sorted by relevance (highest first),
        with an added 'relevance_score' key for each section.

    Examples:
        >>> sections = [
        ...     {'title': 'Agent Skills', 'level': 2},
        ...     {'title': 'API Reference', 'level': 2}
        ... ]
        >>> semantic_match_toc_sections(sections, 'skill')
        [{'title': 'Agent Skills', 'level': 2, 'relevance_score': 1.0}, ...]
    """
    if not toc_sections or not query:
        return toc_sections

    # Calculate relevance for each section
    sections_with_scores = []
    for section in toc_sections:
        title = section.get("title", "")

        # Primary: exact/partial title match
        if query.lower() in title.lower():
            # Higher score for starts-with, lower for contains
            if title.lower().startswith(query.lower()):
                title_score = 1.0
            else:
                title_score = 0.7
        else:
            # Fallback: fuzzy similarity
            title_score = calculate_similarity(query, title)

        sections_with_scores.append({
            **section,
            "relevance_score": title_score
        })

    # Filter out sections with very low relevance
    filtered = [s for s in sections_with_scores if s["relevance_score"] >= 0.3]

    # Sort by relevance score descending
    filtered.sort(key=lambda x: x["relevance_score"], reverse=True)

    return filtered
