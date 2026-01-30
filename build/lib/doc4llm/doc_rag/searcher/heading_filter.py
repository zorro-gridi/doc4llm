"""
Hierarchical heading filter for doc searcher results.

Filters headings recursively: if a higher-level heading exists,
all lower-level sub-headings are filtered out.
"""

from typing import Any, Dict, List


def filter_headings_hierarchically(
    headings: List[Dict[str, Any]],
    page_title: str = ""
) -> List[Dict[str, Any]]:
    """
    Filter headings using recursive hierarchical logic.

    If a higher-level heading exists (e.g., level=1), all lower-level
    sub-headings (level > 1) under the same page_title are filtered out.

    Args:
        headings: List of heading dicts with keys: text, level, bm25_sim, rerank_sim
        page_title: Page title for logging/debugging purposes

    Returns:
        Filtered list of headings preserving all metadata

    Examples:
        >>> headings = [
        ...     {"level": 1, "text": "# Agent Skills", "bm25_sim": 0.72},
        ...     {"level": 2, "text": "## Disable", "bm25_sim": 0.64},
        ...     {"level": 2, "text": "## Recognize", "bm25_sim": 0.62}
        ... ]
        >>> filter_headings_hierarchically(headings, "Test")
        [{'level': 1, 'text': '# Agent Skills', 'bm25_sim': 0.72}]
    """
    # Edge cases: empty or single heading
    if not headings or len(headings) <= 1:
        return headings

    # Find minimum heading level
    levels = [h.get("level", 1) for h in headings]
    min_level = min(levels)

    # Filter: keep only headings at minimum level
    filtered = [h for h in headings if h.get("level", 1) == min_level]

    return filtered
