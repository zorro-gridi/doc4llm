"""
Search Utilities - Helper functions for document search.

This module provides small utility functions used across the searcher module.
"""

import re
from typing import Any

from .common_utils import extract_heading_level


def debug_print(message: str, debug: bool = False) -> None:
    """Conditionally print debug message.

    Args:
        message: Debug message to print
        debug: Whether debug mode is enabled
    """
    if debug:
        print(f"[DEBUG] {message}")


def filter_headings_by_level(
    headings: list[dict[str, Any]], max_level: int = 6
) -> list[dict[str, Any]]:
    """Filter headings to only include those at or below max_level.

    Args:
        headings: List of heading dictionaries
        max_level: Maximum heading level to include (default 6)

    Returns:
        Filtered list of headings
    """
    return [h for h in headings if h.get("level", 6) <= max_level]


def normalize_text(text: str) -> str:
    """Normalize text for comparison.

    Args:
        text: Text to normalize

    Returns:
        Normalized text with extra whitespace removed
    """
    return re.sub(r"\s+", " ", text.strip())
