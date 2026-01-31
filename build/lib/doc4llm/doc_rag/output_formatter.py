"""
统一输出格式化模块 - Doc-RAG Pipeline

为 Doc-RAG 工作流的各个阶段提供统一的控制台输出格式化。

Features:
    - 阶段标题和分隔符统一样式
    - Phase 2 仅打印 metadata，不打印 content
    - 支持静默模式和调试模式
    - 清晰的视觉层次结构

Example:
    >>> from doc4llm.doc_rag.output_formatter import PhaseOutputFormatter
    >>> PhaseOutputFormatter.print_phase_1(search_result)
"""

from typing import Any, Dict, List, Optional

import json


PHASE_TITLES = {
    "0a": "查询优化 (Query Optimization)",
    "0b": "场景路由 (Scene Routing)",
    "1": "文档检索 (Document Search)",
    "1.5": "LLM 重排序 (LLM Re-ranking)",
    "2": "内容提取 (Content Extraction)",
    "4": "场景化输出 (Scene Output)",
}

PHASE_SEPARATOR = "─" * 60


def format_phase_header(phase: str) -> str:
    """生成阶段标题头"""
    title = PHASE_TITLES.get(phase, f"Phase {phase}")
    return f"\n{PHASE_SEPARATOR}\n▶ Phase {phase}: {title}\n{PHASE_SEPARATOR}\n"


def format_phase_footer(phase: str, status: str = "success") -> str:
    """生成阶段结尾"""
    symbol = "✓" if status == "success" else "✗"
    return f"\n{symbol} Phase {phase} completed\n{PHASE_SEPARATOR}\n"


def print_phase_0a(
    query_analysis: Dict[str, Any],
    optimized_queries: List[Dict[str, Any]],
    doc_sets: List[str],
    domain_nouns: List[str],
    predicate_verbs: List[str],
    quiet: bool = False,
) -> None:
    """Phase 0a: 查询优化结果打印"""
    if quiet:
        return

    print(format_phase_header("0a"))
    print(f"原始查询: {query_analysis.get('original', 'N/A')}")
    print(f"语言: {query_analysis.get('language', 'N/A')}")

    if doc_sets:
        print(f"\n目标文档集:")
        for ds in doc_sets:
            print(f"  • {ds}")

    if domain_nouns:
        print(f"\n领域名词: {', '.join(domain_nouns)}")

    if predicate_verbs:
        print(f"谓词动词: {', '.join(predicate_verbs)}")

    if optimized_queries:
        print(f"\n优化后的查询 ({len(optimized_queries)} 个):")
        for q in optimized_queries[:5]:
            rank = q.get("rank", "?")
            query_text = q.get("query", "")
            strategy = q.get("strategy", "")
            print(f"  [{rank}] {query_text} ({strategy})")

        if len(optimized_queries) > 5:
            print(f"  ... 还有 {len(optimized_queries) - 5} 个查询")

    print(format_phase_footer("0a"))


def print_phase_0a_debug(
    query_analysis: Dict[str, Any],
    optimized_queries: List[Dict[str, Any]],
    doc_sets: List[str],
    domain_nouns: List[str],
    predicate_verbs: List[str],
    raw_response: Optional[str] = None,
    thinking: Optional[str] = None,
) -> None:
    """Phase 0a: 查询优化结果打印（debug 版本，包含原始输出）"""
    print_phase_0a(
        query_analysis,
        optimized_queries,
        doc_sets,
        domain_nouns,
        predicate_verbs,
        quiet=False,
    )

    # 打印原始输出
    if thinking:
        print("\n[Thinking Process]")
        print(thinking)

    if raw_response:
        print("\n[Raw LLM Response]")
        print(raw_response)


def print_phase_0b(
    scene: str,
    confidence: float,
    ambiguity: float,
    coverage_need: float,
    reranker_threshold: float,
    quiet: bool = False,
) -> None:
    """Phase 0b: 场景路由结果打印"""
    if quiet:
        return

    print(format_phase_header("0b"))
    print(f"场景分类: {scene}")
    print(f"置信度: {confidence:.2f}")
    print(f"模糊度: {ambiguity:.2f}")
    print(f"覆盖需求: {coverage_need:.2f}")
    print(f"重排序阈值: {reranker_threshold:.2f}")
    print(format_phase_footer("0b"))


def print_phase_0b_debug(
    scene: str,
    confidence: float,
    ambiguity: float,
    coverage_need: float,
    reranker_threshold: float,
    raw_response: Optional[str] = None,
    thinking: Optional[str] = None,
) -> None:
    """Phase 0b: 场景路由结果打印（debug 版本，包含原始输出）"""
    print_phase_0b(
        scene, confidence, ambiguity, coverage_need, reranker_threshold, quiet=False
    )

    # 打印原始输出
    if thinking:
        print("\n[Thinking Process]")
        print(thinking)

    if raw_response:
        print("\n[Raw LLM Response]")
        print(raw_response)


def print_phase_1(
    results: Dict[str, Any],
    query: str,
    optimized_queries: Optional[List[Dict[str, Any]]] = None,
    quiet: bool = False,
) -> None:
    """Phase 1: 文档检索结果打印

    Args:
        results: 搜索结果
        query: 原始查询
        optimized_queries: 预处理后的查询列表（可选）
        quiet: 静默模式
    """
    if quiet:
        return

    print(format_phase_header("1"))

    # 使用 search_result 中的 query 字段（经过搜索器预处理后的查询）
    search_queries = results.get("query", [])
    if search_queries:
        print("检索查询:")
        for i, q in enumerate(search_queries[:5], 1):
            print(f"  [{i}] {q}")
        if len(search_queries) > 5:
            print(f"  ... 还有 {len(search_queries) - 5} 个查询")
    else:
        print(f"检索查询: {query}")

    doc_sets_found = results.get("doc_sets_found", [])
    print(f"文档集: {', '.join(doc_sets_found) if doc_sets_found else 'N/A'}")

    pages = results.get("results", [])
    print(f"检索到 {len(pages)} 个页面:")

    for i, page in enumerate(pages[:10], 1):
        page_title = page.get("page_title", "N/A")
        doc_set = page.get("doc_set", "N/A")
        headings_list = page.get("headings", [])
        heading_count = (
            len(headings_list) if headings_list else page.get("heading_count", 0)
        )
        precision_count = page.get("precision_count", 0)
        # Use bm25_sim for page-level BM25 score, fallback to score for backward compatibility
        score = page.get("bm25_sim", page.get("score", 0))

        print(f"  {i}. {page_title}")
        print(f"     📁 {doc_set}")
        # 如果 headings 列表为空，表示整页匹配（所有 heading 都会被提取）
        if not headings_list:
            print(f"     📊 整页匹配 (全部 heading)")
        else:
            print(
                f"     📊 标题: {heading_count} 个heading, {precision_count} 个精确匹配"
            )
        print(f"     📈 得分: {score:.4f}")
        # 显示来源
        source = page.get("source", "unknown")
        print(f"     📌 来源: {source}")

    if len(pages) > 10:
        print(f"  ... 还有 {len(pages) - 10} 个页面")

    print(format_phase_footer("1"))


def print_phase_1_5(
    total_before: int,
    total_after: int,
    pages_before: int,
    pages_after: int,
    quiet: bool = False,
) -> None:
    """Phase 1.5: LLM 重排序结果打印"""
    if quiet:
        return

    print(format_phase_header("1.5"))
    print(f"过滤统计:")
    print(
        f"  Headings: {total_before} → {total_after} (移除 {total_before - total_after})"
    )
    print(
        f"  Pages: {pages_before} → {pages_after} (移除 {pages_before - pages_after})"
    )

    retention_rate = total_after / total_before * 100 if total_before > 0 else 0
    print(f"  保留率: {retention_rate:.1f}%")
    print(format_phase_footer("1.5"))


def print_phase_1_5_debug(
    total_before: int,
    total_after: int,
    pages_before: int,
    pages_after: int,
    raw_response: Optional[str] = None,
    thinking: Optional[str] = None,
) -> None:
    """Phase 1.5: LLM 重排序结果打印（debug 版本，包含原始输出）"""
    print_phase_1_5(total_before, total_after, pages_before, pages_after, quiet=False)

    if thinking:
        print("\n[Thinking Process]")
        print(thinking)

    if raw_response:
        print("\n[Raw LLM Response]")
        print(raw_response)


def print_phase_1_debug(
    results: Dict[str, Any],
    query: str,
    raw_response: Optional[str] = None,
    thinking: Optional[str] = None,
) -> None:
    """Phase 1: 文档检索结果打印（debug 版本，仅原始输出）"""
    # debug 模式只打印原始 JSON 输出，不打印格式化结果（避免重复）
    print(f"\n{'─' * 60}")
    print(f"▶ Phase 1: 文档检索 (Document Search) [原始输出]")
    print(f"{'─' * 60}")
    json_output = json.dumps(results, ensure_ascii=False, indent=2)
    print(json_output)
    print(f"{'─' * 60}\n")

    if thinking:
        print("\n[Thinking Process]")
        print(thinking)

    if raw_response:
        print("\n[Raw LLM Response]")
        print(raw_response)


def print_phase_1_5_skipped(
    reason: str, total_headings: int = 0, pages_count: int = 0
) -> None:
    """Phase 1.5: 跳过重排序（所有 heading 已有 rerank_sim 或未启用）"""
    print(format_phase_header("1.5"))
    print(f"状态: 跳过")
    print(f"原因: {reason}")
    if total_headings > 0:
        print(f"Headings: {total_headings}")
        print(f"Pages: {pages_count}")
    print(format_phase_footer("1.5"))


def print_phase_1_5_failed(
    reason: str,
    total_headings: int = 0,
    pages_count: int = 0,
    thinking: Optional[str] = None,
) -> None:
    """Phase 1.5: 重排序失败"""
    print(format_phase_header("1.5"))
    print(f"状态: 失败")
    print(f"原因: {reason}")
    if thinking:
        print(
            f"\n=== LLM Think ===\n{thinking[:2000]}{'...' if len(thinking) > 2000 else ''}\n"
        )
    if total_headings > 0:
        print(f"保留原始结果")
        print(f"Headings: {total_headings}")
        print(f"Pages: {pages_count}")
    print(format_phase_footer("1.5"))


def print_phase_1_5_embedding(
    total_before: int,
    total_after: int,
    pages_before: int,
    pages_after: int,
    quiet: bool = False,
) -> None:
    """Phase 1.5: Transformer Embedding 重排序结果打印"""
    if quiet:
        return

    print(format_phase_header("1.5"))
    print(f"[Transformer Embedding Reranking]")
    print(f"过滤统计:")
    print(
        f"  Headings: {total_before} → {total_after} (移除 {total_before - total_after})"
    )
    print(
        f"  Pages: {pages_before} → {pages_after} (移除 {pages_before - pages_after})"
    )

    retention_rate = total_after / total_before * 100 if total_before > 0 else 0
    print(f"  保留率: {retention_rate:.1f}%")
    print(format_phase_footer("1.5"))


def print_phase_2_metadata(
    document_count: int,
    total_line_count: int,
    threshold: int,
    individual_counts: Dict[str, int],
    requires_processing: bool,
    quiet: bool = False,
) -> None:
    """Phase 2: 仅打印 metadata，不打印 content

    Args:
        document_count: 文档数量
        total_line_count: 总行数
        threshold: 阈值
        individual_counts: 各文档行数统计
        requires_processing: 是否超过阈值
        quiet: 静默模式
    """
    if quiet:
        return

    print(format_phase_header("2"))
    print(f"📄 内容提取完成")
    print(f"   文档数量: {document_count}")
    print(f"   总行数: {total_line_count}")
    print(f"   阈值: {threshold}")

    if requires_processing:
        excess = total_line_count - threshold
        print(f"   ⚠️  超限 {excess} 行，需要后处理")
    else:
        margin = threshold - total_line_count
        print(f"   ✓ 剩余 {margin} 行容量")

    print(f"\n📊 各文档行数统计:")
    for title, count in individual_counts.items():
        bar = "█" * min(count // 50, 30)
        print(f"   • {title[:40]:40s} | {count:5d} 行 | {bar}")

    print(format_phase_footer("2"))


def print_phase_2_debug(
    document_count: int,
    total_line_count: int,
    threshold: int,
    individual_counts: Dict[str, int],
    requires_processing: bool,
    contents: Dict[str, str],
    limit: int = 500,
    raw_response: Optional[str] = None,
    thinking: Optional[str] = None,
) -> None:
    """Phase 2: 内容提取结果打印（debug 版本，包含原始输出）"""
    print_phase_2_metadata(
        document_count,
        total_line_count,
        threshold,
        individual_counts,
        requires_processing,
        quiet=False,
    )

    if contents:
        print("\n[Extracted Document Contents]")
        print("=" * 60)
        for title, content in contents.items():
            print(f"\n▶ {title}")
            lines = content.split("\n")
            if len(lines) > limit:
                print("\n".join(lines[:limit]))
                print(f"... ({len(lines) - limit} more lines truncated)")
            else:
                print(content)
            print("-" * 60)

    if thinking:
        print("\n[Thinking Process]")
        print(thinking)

    if raw_response:
        print("\n[Raw LLM Response]")
        print(raw_response)


def print_phase_4(
    output_length: int, documents_used: int, scene: str, quiet: bool = False
) -> None:
    """Phase 4: 场景化输出结果打印"""
    if quiet:
        return

    print(format_phase_header("4"))
    print(f"场景: {scene}")
    print(f"使用的文档数: {documents_used}")
    print(f"输出长度: {output_length} 字符")
    print(format_phase_footer("4"))


def print_phase_4_debug(
    output_length: int,
    documents_used: int,
    scene: str,
    raw_response: Optional[str] = None,
    thinking: Optional[str] = None,
) -> None:
    """Phase 4: 场景化输出结果打印（debug 版本，包含原始输出）"""
    print_phase_4(output_length, documents_used, scene, quiet=False)

    # 打印原始输出
    if thinking:
        print("\n[Thinking Process]")
        print(thinking)

    if raw_response:
        print("\n[Raw LLM Response]")
        print(raw_response)


def print_phase_0a_0b_to_1_debug(
    phases: List[Dict[str, Any]],
    config: Dict[str, Any],
    from_phase: str = "0a+0b",
    to_phase: str = "1",
    status: str = "success",
    errors: Optional[List[str]] = None,
) -> None:
    """Phase 0a+0b -> 1: 参数解析结果打印（debug 版本）

    Args:
        phases: Phase 0a 和 0b 的输出列表
        config: 解析后的配置
        from_phase: 源阶段标识
        to_phase: 目标阶段标识
        status: 状态
        errors: 错误列表
    """
    print(f"\n{PHASE_SEPARATOR}")
    print(f"▶ Phase {from_phase} -> {to_phase}")
    print(f"{PHASE_SEPARATOR}\n")

    # 打印输入数据
    print("[输入数据 (Input)]")
    input_data = {"phases": phases, "to_phase": to_phase}
    print(json.dumps(input_data, ensure_ascii=False, indent=2))

    # 打印输出配置
    print("\n[输出配置 (Output)]")
    print(json.dumps(config, ensure_ascii=False, indent=2))

    # 打印状态信息
    print(f"\n[状态信息 (Status)]")
    print(f"  状态: {status}")
    if errors:
        print(f"  错误: {errors}")

    print(format_phase_footer(f"{from_phase} -> {to_phase}", status))


def print_phase_1_to_2_debug(
    upstream_output: Dict[str, Any],
    config: Dict[str, Any],
    from_phase: str,
    to_phase: str = "2",
    status: str = "success",
    errors: Optional[List[str]] = None,
) -> None:
    """Phase 1/1.5 -> 2: 参数解析结果打印（debug 版本）

    Args:
        upstream_output: 上游阶段的输出
        config: 解析后的配置
        from_phase: 源阶段标识
        to_phase: 目标阶段标识
        status: 状态
        errors: 错误列表
    """
    print(f"\n{PHASE_SEPARATOR}")
    print(f"▶ Phase {from_phase} -> {to_phase}")
    print(f"{PHASE_SEPARATOR}\n")

    # 打印输入数据
    print("[输入数据 (Input)]")
    input_data = {
        "from_phase": from_phase,
        "to_phase": to_phase,
        "upstream_output": upstream_output,
    }
    print(json.dumps(input_data, ensure_ascii=False, indent=2))

    # 打印输出配置
    print("\n[输出配置 (Output)]")
    print(json.dumps(config, ensure_ascii=False, indent=2))

    # 打印状态信息
    print(f"\n[状态信息 (Status)]")
    print(f"  状态: {status}")
    if errors:
        print(f"  错误: {errors}")

    print(format_phase_footer(f"{from_phase} -> {to_phase}", status))


def print_pipeline_start(query: str) -> None:
    """打印流水线开始信息"""
    print(f"\n{'═' * 60}")
    print(f"🚀 Doc-RAG 流水线开始")
    print(f"查询: {query[:80]}{'...' if len(query) > 80 else ''}")
    print(f"{'═' * 60}")


def print_pipeline_end(
    success: bool,
    documents_extracted: int,
    total_lines: int,
    duration: Optional[float] = None,
) -> None:
    """打印流水线结束信息"""
    status = "✓ 成功" if success else "✗ 失败"
    print(f"\n{'═' * 60}")
    print(f"🏁 Doc-RAG 流水线结束 | {status}")
    print(f"   提取文档: {documents_extracted} 个")
    print(f"   总行数: {total_lines}")
    if duration is not None:
        print(f"   耗时: {duration:.2f} 秒")
    print(f"{'═' * 60}\n")


__all__ = [
    "format_phase_header",
    "format_phase_footer",
    "print_phase_0a",
    "print_phase_0a_debug",
    "print_phase_0b",
    "print_phase_0b_debug",
    "print_phase_1",
    "print_phase_1_5",
    "print_phase_1_5_debug",
    "print_phase_1_5_skipped",
    "print_phase_1_5_failed",
    "print_phase_1_5_embedding",
    "print_phase_1_debug",
    "print_phase_2_metadata",
    "print_phase_2_debug",
    "print_phase_4",
    "print_phase_4_debug",
    "print_phase_0a_0b_to_1_debug",
    "print_phase_1_to_2_debug",
    "print_pipeline_start",
    "print_pipeline_end",
    "PHASE_TITLES",
    "PHASE_SEPARATOR",
]
