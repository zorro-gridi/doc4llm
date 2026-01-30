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
from typing import Any, Dict, List, Optional


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
            # 显示分数信息
            bm25_sim = page.get("bm25_sim")
            if bm25_sim is not None:
                lines.append(f"   - BM25 分数: `{bm25_sim:.4f}`")
            heading_count = page.get("heading_count", 0)
            precision_count = page.get("precision_count", 0)
            lines.append(f"   - Heading 数量: {heading_count} ({precision_count} precision)")
            source = page.get("source", "bm25")
            lines.append(f"   - 来源: {source}")
            lines.append("   - **匹配Heading列表**:")

            for heading in page.get("headings", []):
                level_hash = "#" * heading.get("level", 1)
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
    def format_structured(result: Dict[str, Any], queries: Optional[List[str]] = None,
                          reranker_enabled: bool = True) -> str:
        """
        Format result as structured JSON for machine parsing.

        Returns JSON metadata with doc_set, page_title, toc_path, and headings
        that can be parsed by downstream skills like md-doc-reader for
        section-level content extraction. Results are not separated by relevance
        level (high/medium) - all matched pages are returned in a single list.

        Args:
            result: Search result from DocSearcherAPI.search()
            queries: Original query input list from --query parameter
            reranker_enabled: Whether reranker was enabled (affects rerank_sim output)

        Returns:
            JSON string with structured metadata
        """
        def _convert_to_json_serializable(obj):
            """Convert numpy types and other non-serializable objects to JSON-serializable types."""
            import numpy as np
            if isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        structured = {
            "success": result.get("success", False),
            "toc_fallback": result.get("toc_fallback", False),
            "grep_fallback": result.get("grep_fallback", False),
            "query": queries or [],
            "doc_sets_found": result.get("doc_sets_found", []),
            "results": [],
        }

        for page in result.get("results", []):
            page_data = {
                "doc_set": page["doc_set"],
                "page_title": page["page_title"],
                "toc_path": page["toc_path"],
            }

            # Add page-level scores (when headings is empty/fallback to page level)
            if "bm25_sim" in page:
                page_data["bm25_sim"] = _convert_to_json_serializable(page["bm25_sim"])
            if "rerank_sim" in page:
                page_data["rerank_sim"] = _convert_to_json_serializable(page["rerank_sim"]) if reranker_enabled else None

            # Add heading counts and source
            page_data["heading_count"] = page.get("heading_count", 0)
            page_data["precision_count"] = page.get("precision_count", 0)
            page_data["source"] = page.get("source", "bm25")

            # Only include headings if they exist and are non-empty
            if "headings" in page and page["headings"]:
                page_data["headings"] = [
                    {
                        "level": h.get("level", 1),
                        "text": h["text"],
                        "rerank_sim": _convert_to_json_serializable(h.get("rerank_sim")) if reranker_enabled else None,
                        "bm25_sim": _convert_to_json_serializable(h.get("bm25_sim")),
                    }
                    for h in page["headings"]
                ]

            structured["results"].append(page_data)

        return json.dumps(structured, ensure_ascii=False, indent=2)


__all__ = [
    "OutputFormatter",
]
