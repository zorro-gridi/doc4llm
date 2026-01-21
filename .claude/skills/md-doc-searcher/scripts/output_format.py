"""
Output formatting module for doc searcher results.

Provides methods to format search results in AOP markdown format
or structured JSON format.

Example:
    >>> from output_format import OutputFormatter
    >>> result = {"success": True, "results": [...]}
    >>> aop_output = OutputFormatter.format_aop(result)
    >>> json_output = OutputFormatter.format_structured(result)
"""

import json
from typing import Any, Dict


class OutputFormatter:
    """Formatter for doc searcher search results.

    Provides static methods for formatting results in different output formats.
    """

    @staticmethod
    def format_aop(result: Dict[str, Any]) -> str:
        """
        Format result as AOP output.

        Args:
            result: Search result from DocSearcherAPI.search()

        Returns:
            Formatted AOP markdown string
        """
        doc_sets_str = ",".join(result.get("doc_sets_found", []))
        results = result.get("results", [])
        count = len(results)

        lines = []
        lines.append(
            f"=== AOP-FINAL | agent=md-doc-searcher | results={count} | doc_sets={doc_sets_str} ==="
        )
        lines.append(
            "**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary"
        )

        for page in results:
            lines.append(f"**{page['doc_set']}**")
            lines.append("")
            lines.append(f"**{page['page_title']}**")
            lines.append(f"   - TOC 路径: `{page['toc_path']}`")
            lines.append("   - **匹配Heading列表**:")

            for heading in page.get("headings", []):
                level_hash = "#" * heading.get("level", 2)
                lines.append(f"     - {level_hash} {heading['text']}")

                lines.append("")

        lines.append("=== END-AOP-FINAL ===")

        if count == 0:
            lines.clear()
            lines.append(
                f"=== AOP-FINAL | agent=md-doc-searcher | results={count} | doc_sets={doc_sets_str} ==="
            )
            lines.append(
                "**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary"
            )
            lines.append("")
            lines.append("No matched headings found!")
            lines.append("")
            lines.append("=== END-AOP-FINAL ===")

        return "\n".join(lines)

    @staticmethod
    def format_structured(result: Dict[str, Any]) -> str:
        """
        Format result as structured JSON for machine parsing.

        Returns JSON metadata with doc_set, page_title, toc_path, and headings
        that can be parsed by downstream skills like md-doc-reader for
        section-level content extraction. Results are not separated by relevance
        level (high/medium) - all matched pages are returned in a single list.

        Args:
            result: Search result from DocSearcherAPI.search()

        Returns:
            JSON string with structured metadata
        """
        structured = {
            "success": result.get("success", False),
            "doc_sets_found": result.get("doc_sets_found", []),
            "results": [
                {
                    "doc_set": page["doc_set"],
                    "page_title": page["page_title"],
                    "toc_path": page["toc_path"],
                    "headings": [
                        {"level": h.get("level", 2), "text": h["text"]}
                        for h in page.get("headings", [])
                    ],
                }
                for page in result.get("results", [])
            ],
        }
        return json.dumps(structured, ensure_ascii=False, indent=2)


__all__ = [
    "OutputFormatter",
]
