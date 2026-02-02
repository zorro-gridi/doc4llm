"""
Reranker Utils - Phase 1.5 阈值调整与输出过滤工具模块

Features:
    - 阈值调整函数
    - 输出二次过滤函数
    - 最低保障机制
"""

from typing import Any, Dict, List

# 默认阈值调降值
DEFAULT_THRESHOLD_ADJUSTMENT = 0.1


def adjust_threshold(threshold: float, adjustment: float = DEFAULT_THRESHOLD_ADJUSTMENT) -> float:
    """调整 reranker_threshold 阈值。

    Args:
        threshold: 原始阈值
        adjustment: 调整值（默认减 0.1）

    Returns:
        调整后的阈值（不低于 0.0，保留两位小数）
    """
    adjusted = max(0.0, threshold - adjustment)
    return round(adjusted, 2)


def filter_reranker_output(
    data: Dict[str, Any],
    original_threshold: float,
    min_headings_count: int = 1,
) -> Dict[str, Any]:
    """按照原阈值对 LLM reranker 输出结果进行二次过滤。

    过滤规则：
    1. 如果 page_title.rerank_sim >= original_threshold → headings 设为 []
    2. 如果 page_title.rerank_sim < original_threshold → 过滤 headings[].rerank_sim < original_threshold
    3. 如果 page_title.rerank_sim < original_threshold 且 headings 过滤后为 [] → 删除这个 result
    4. 最后至少保留 N 条 rerank_sim 最高的 heading（避免空结果）

    Args:
        data: LLM reranker 输出结果
        original_threshold: 原阈值（用于二次过滤）
        min_headings_count: 最少保留的高分 heading 数量（默认 1）

    Returns:
        过滤后的结果
    """
    filtered_results = []
    all_filtered_headings: List[Dict[str, Any]] = []

    for result in data.get("results", []):
        page_rerank_sim = result.get("rerank_sim")
        headings = result.get("headings", [])

        if page_rerank_sim is not None and page_rerank_sim >= original_threshold:
            # 规则1: page_title 达标，整个 headings 设为 []
            result_copy = result.copy()
            result_copy["headings"] = []
            filtered_results.append(result_copy)
        else:
            # 规则2: 过滤低评分 headings
            filtered_headings = [
                h for h in headings
                if h.get("rerank_sim") is not None and h.get("rerank_sim") >= original_threshold
            ]

            if filtered_headings:
                # 规则3: 有 headings，保留整个 result
                result_copy = result.copy()
                result_copy["headings"] = filtered_headings
                filtered_results.append(result_copy)
                all_filtered_headings.extend(filtered_headings)

    # 规则4: 至少保留 N 条最高分的 heading
    if len(filtered_results) < min_headings_count and all_filtered_headings:
        # 找出得分最高的 N 条 headings
        sorted_headings = sorted(
            all_filtered_headings,
            key=lambda h: h.get("rerank_sim", 0),
            reverse=True
        )
        top_headings = sorted_headings[:min_headings_count]

        for heading in top_headings:
            # 找到对应的原始 page
            for result in data.get("results", []):
                if any(h.get("text") == heading.get("text") for h in result.get("headings", [])):
                    result_copy = result.copy()
                    result_copy["headings"] = [heading]
                    if result_copy not in filtered_results:
                        filtered_results.append(result_copy)
                    break

    return {
        **data,
        "results": filtered_results
    }


__all__ = [
    "adjust_threshold",
    "filter_reranker_output",
    "DEFAULT_THRESHOLD_ADJUSTMENT",
]
