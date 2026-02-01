"""
Common Utilities - Shared utility functions for the searcher module.

This module consolidates duplicated utility functions from across the searcher
module to ensure code consistency and reduce maintenance overhead.

Functions provided:
- remove_url_from_heading: Remove URL links from heading text
- extract_page_title_from_path: Extract page title from file path
- extract_heading_level: Extract heading level from markdown heading
- filter_query_keywords: Filter out skiped keywords from query
- count_words: Count words in mixed Chinese/English text
- clean_context_from_urls: Clean URL information from context text
"""

import re
from pathlib import Path
from typing import List


def remove_url_from_heading(heading_text: str, preserve_hash: bool = False) -> str:
    """Remove URL links from heading text.

    Processing logic:
    1. Remove markdown link format [text](url) -> text
    2. Remove trailing anchor links (Chinese ：and English :)

    Args:
        heading_text: The heading text containing URL links
        preserve_hash: Whether to preserve original # level markers (default False)

    Returns:
        Cleaned heading text with URLs removed
    """
    # Remove markdown link format [text](url) -> text
    link_pattern = re.compile(r"\[([^\[\]]+)\]\([^)]+\)")
    # Remove trailing anchor links (Chinese ：and English :)
    anchor_pattern = re.compile(r"：https://[^\s]+|: https://[^\s]+")

    # First remove markdown links
    text = link_pattern.sub(r"\1", heading_text)
    # Then remove trailing anchor links
    text = anchor_pattern.sub("", text).strip()

    if preserve_hash:
        # Check if cleaned text starts with #
        if text.strip().startswith("#"):
            return text  # Already has # format, return directly

        # If original text starts with # but cleaned text doesn't, add #
        if heading_text.strip().startswith("#"):
            hash_match = re.match(r"^(#{1,6})\s+", heading_text.strip())
            if hash_match:
                hashes = hash_match.group(1)
                return f"{hashes} {text}"

    return text


def extract_page_title_from_path(file_path: str) -> str:
    """Extract page title from file path.

    Supports both docTOC.md and docContent.md file naming conventions.
    Falls back to reading the first line of the file if path-based extraction fails.

    Args:
        file_path: The file path (can be TOC or content file)

    Returns:
        The extracted page title or "Unknown" if extraction fails
    """
    path = Path(file_path)

    # From path extract, like "docSetName/pageTitle/docContent.md"
    parts = path.parts
    if len(parts) >= 2:
        potential_title = (
            parts[-2] if parts[-1] in ("docTOC.md", "docContent.md") else parts[-1]
        )
        if potential_title and not potential_title.endswith(".md"):
            return potential_title

    # Try reading file content as fallback
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line.startswith("#"):
                    title = first_line.lstrip("#").strip()
                    if title:
                        return title
    except Exception:
        pass

    return "Unknown"


def extract_heading_level(heading_text: str) -> int:
    """Extract heading level from markdown heading text.

    Args:
        heading_text: Heading text that may start with # characters

    Returns:
        Heading level (1-6), defaults to 1 if no # prefix found
    """
    match = re.match(r"^(#{1,6})\s+", heading_text.strip())
    if match:
        return len(match.group(1))
    return 1


def filter_query_keywords(query: str, skiped_keywords: List[str]) -> str:
    """Filter out skiped keywords from query string (case-insensitive).

    Args:
        query: Original query string
        skiped_keywords: List of keywords to remove

    Returns:
        Filtered query string with keywords removed
    """
    query_lower = query.strip()
    result = query_lower

    for keyword in skiped_keywords:
        keyword_lower = keyword.strip().lower()
        if not keyword_lower:
            continue
        pattern = keyword_lower
        result = re.sub(re.escape(pattern), "", result, flags=re.IGNORECASE)

    result = re.sub(r"\s+", " ", result).strip()
    return result


def count_words(text: str) -> int:
    """Count words/characters in mixed Chinese/English text.

    - Chinese: counts characters (each Chinese character counts as 1 unit)
    - English: counts space-separated words

    Args:
        text: Input text (can be mixed Chinese and English)

    Returns:
        Word/character count
    """
    if not text:
        return 0

    # Remove punctuation and extra whitespace
    cleaned = re.sub(r"[^\w\s\u4e00-\u9fff]", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return 0

    # Check if text contains Chinese characters
    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", cleaned))

    if has_chinese:
        # Chinese: count characters
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", cleaned)
        # Count English words separately
        english_words = re.findall(r"\b[a-zA-Z]+\b", cleaned)
        return len(chinese_chars) + len(english_words)
    else:
        # English: count words by space separation
        words = cleaned.split()
        return len(words)


def clean_context_from_urls(context: str) -> str:
    """Clean URL information from context text.

    Removes:
    1. Markdown link format [text](url) -> text
    2. Angle bracket links <url> -> url
    3. Trailing anchor links
    4. Pure URLs (standalone lines)
    5. URLs in code blocks
    6. URLs in inline code

    Args:
        context: Original context text

    Returns:
        Cleaned context text with URLs removed
    """
    # 1. Remove markdown link format [text](url) -> text
    link_pattern = re.compile(r"\[([^\[\]]+)\]\([^)]+\)")
    cleaned = link_pattern.sub(r"\1", context)

    # 2. Remove angle bracket links <url> -> url
    angle_bracket_pattern = re.compile(r"<(https?://[^\s<>]+)>")
    cleaned = angle_bracket_pattern.sub(r"\1", cleaned)

    # 3. Remove trailing anchor links
    anchor_pattern = re.compile(r"：https://[^\s]+|: https://[^\s]+")
    cleaned = anchor_pattern.sub("", cleaned)

    # 4. Remove standalone URL lines (only URL on the line)
    url_only_pattern = re.compile(r"^\s*https?://[^\s]*\s*$", re.MULTILINE)
    cleaned = url_only_pattern.sub("", cleaned)

    # 5. Remove code blocks containing URLs (entire block)
    # Match ``` ... ``` with any URL inside
    code_block_pattern = re.compile(r"```[^\n]*\n[^\n]*https?://[^\n]*\n```", re.DOTALL)
    cleaned = code_block_pattern.sub("", cleaned)

    # 6. Remove inline code URLs `url`
    inline_code_pattern = re.compile(r"`[^`]*?https?://[^\s]*?`")
    cleaned = inline_code_pattern.sub("", cleaned)

    # 7. Remove remaining pure URLs (with at least one space before)
    url_with_space_pattern = re.compile(r"\s+https?://[^\s<>]+")
    cleaned = url_with_space_pattern.sub("", cleaned)

    # 8. Remove remaining URL fragments at line start
    url_start_pattern = re.compile(r"^https?://[^\s]+", re.MULTILINE)
    cleaned = url_start_pattern.sub("", cleaned)

    # 9. Clean up empty code block markers
    cleaned = re.sub(r"```\s*```", "", cleaned)

    return cleaned.strip()


__all__ = [
    "remove_url_from_heading",
    "extract_page_title_from_path",
    "extract_heading_level",
    "filter_query_keywords",
    "count_words",
    "clean_context_from_urls",
]
