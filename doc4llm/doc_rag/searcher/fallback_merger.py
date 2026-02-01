"""
Fallback Merger - Merge results from different fallback strategies.

This module provides the FallbackMerger class for combining results
from FALLBACK_1 (grep TOC search) and FALLBACK_2 (grep context + BM25).
"""

from typing import Any, Dict, List


class FallbackMerger:
    """Fallback 结果合并器"""

    def merge(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并多个 fallback 策略的结果。

        合并策略：
        1. 按 (doc_set, page_title) 去重
        2. 合并 headings（去重，保留最高 BM25 分数）
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

            # Aggregate headings (deduplicate by heading_text)
            existing_headings = {h["text"] for h in merged_pages[key]["headings"]}

            for heading in result.get("headings", []):
                if heading["text"] not in existing_headings:
                    merged_pages[key]["headings"].append(heading)
                    existing_headings.add(heading["text"])
                else:
                    # If heading already exists, keep the one with higher BM25 score
                    for idx, existing in enumerate(merged_pages[key]["headings"]):
                        if existing["text"] == heading["text"]:
                            existing_score = existing.get("bm25_sim") or 0
                            new_score = heading.get("bm25_sim") or 0
                            if new_score > existing_score:
                                merged_pages[key]["headings"][idx] = heading
                            break

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
