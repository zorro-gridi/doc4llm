"""
Fallback Merger - Merge results from different fallback strategies.

This module provides the FallbackMerger class for combining results
from FALLBACK_1 (grep TOC search) and FALLBACK_2 (grep context + BM25).
"""

from typing import Any, Dict, List

from .common_utils import normalize_heading_text


class FallbackMerger:
    """Fallback 结果合并器"""

    def merge(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并多个 fallback 策略的结果。

        合并策略：
        1. 按 (doc_set, page_title) 去重
        2. 合并 headings（使用规范化文本去重，保留最高 BM25 分数和 related_context）
        3. 聚合 heading_count 和 precision_count
        4. 更新 page 分数为最高 heading 分数

        Args:
            results: List of page results from fallback strategies

        Returns:
            Merged list of page results with deduplicated headings
        """
        merged_pages = {}

        for result in results:
            key = (result["doc_set"], result["page_title"])

            if key not in merged_pages:
                merged_pages[key] = {
                    "doc_set": result["doc_set"],
                    "page_title": result["page_title"],
                    "toc_path": result.get("toc_path", ""),
                    "headings": [],
                    "heading_count": 0,
                    "precision_count": 0,
                    "bm25_sim": result.get("bm25_sim"),
                    "is_basic": result.get("is_basic", True),
                    "is_precision": result.get("is_precision", False),
                }

            # Aggregate headings (deduplicate by normalized heading_text)
            # Mapping: normalized_text -> index in headings list
            existing_headings_map = {}  # {normalized_text: index}

            for idx, existing in enumerate(merged_pages[key]["headings"]):
                normalized = normalize_heading_text(existing.get("text", ""))
                if normalized:
                    existing_headings_map[normalized] = idx

            for heading in result.get("headings", []):
                heading_text = heading.get("text", "")
                normalized = normalize_heading_text(heading_text)

                if not normalized:
                    # If normalized text is empty, add directly
                    merged_pages[key]["headings"].append(heading)
                    continue

                if normalized not in existing_headings_map:
                    # New heading, add it
                    merged_pages[key]["headings"].append(heading)
                    existing_headings_map[normalized] = len(merged_pages[key]["headings"]) - 1
                else:
                    # Heading exists, decide whether to update based on bm25_sim and related_context
                    idx = existing_headings_map[normalized]
                    existing = merged_pages[key]["headings"][idx]
                    existing_rc = existing.get("related_context", "")
                    new_rc = heading.get("related_context", "")
                    existing_bm25 = existing.get("bm25_sim") or 0
                    new_bm25 = heading.get("bm25_sim") or 0

                    # Merge strategy:
                    # 1. Keep heading with higher BM25 score
                    # 2. If BM25 equal, prefer to keep the one with non-empty related_context
                    # 3. Preserve original text field
                    if new_bm25 > existing_bm25:
                        merged_pages[key]["headings"][idx] = heading
                    elif new_rc and not existing_rc:
                        # Preserve related_context from FALLBACK_2
                        existing["related_context"] = new_rc
                        # Also update source if it comes from FALLBACK_2
                        if heading.get("source") == "FALLBACK_2":
                            existing["source"] = "FALLBACK_2"

            # Update page-level statistics
            merged_pages[key]["heading_count"] = len(merged_pages[key]["headings"])
            merged_pages[key]["precision_count"] = sum(
                1 for h in merged_pages[key]["headings"] if h.get("is_precision", False)
            )

            # Update page score to highest heading score
            if merged_pages[key]["headings"]:
                merged_pages[key]["bm25_sim"] = max(
                    (h.get("bm25_sim") or 0) for h in merged_pages[key]["headings"]
                )
                merged_pages[key]["is_basic"] = any(
                    h.get("is_basic", True) for h in merged_pages[key]["headings"]
                )
                merged_pages[key]["is_precision"] = any(
                    h.get("is_precision", False) for h in merged_pages[key]["headings"]
                )

        return list(merged_pages.values())
