"""
Doc-RAG Orchestrator - Complete RAG Pipeline for Documentation Retrieval

Integrates seven modules to execute complete Doc-RAG retrieval workflow:
- Phase 0a: Query Optimization (QueryOptimizer)
- Phase 0b: Scene Routing (QueryRouter)
- Phase 1: Document Discovery (DocSearcherAPI)
- Phase 1.5: LLM Re-ranking (LLMReranker, conditional)
- Phase 2: Content Extraction (MarkdownDocExtractor)
- Phase 4: Scene-Based Output (SceneOutput)

Phase 3 (content compression) is skipped - direct Phase 2 → Phase 4 transition.

Workflow:
    Phase 0a+0b -> Phase 1: Parse Parameters
    Phase 1: Document Discovery -> Search Results
    Phase 1.5: LLM Re-ranking (conditional) -> Reranked Results
    Phase 1.5 -> Phase 2: Parse Parameters
    Phase 2: Content Extraction -> ExtractionResult
    Phase 4: Scene-Based Output -> Final Result

Features:
    - Python API: retrieve(query, config) -> DocRAGResult
    - CLI Interface: docrag "query"
    - Conditional Phase 1.5 invocation based on missing rerank_sim
    - Comprehensive error handling with fallbacks

Example:
    >>> from doc4llm.doc_rag.orchestrator import retrieve
    >>> result = retrieve("如何创建 ray cluster?")
    >>> print(result.output)
"""

import argparse
import io
import json
import os
import sys
import time
import traceback
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from doc4llm.doc_rag.llm_reranker.llm_reranker import (
    LLMReranker,
    LLMRerankerConfig,
    RerankerResult,
)
from doc4llm.doc_rag.output_formatter import (
    print_phase_0a,
    print_phase_0a_debug,
    print_phase_0b,
    print_phase_0b_debug,
    print_phase_1,
    print_phase_1_5,
    print_phase_1_5_debug,
    print_phase_1_5_failed,
    print_phase_1_5_skipped,
    print_phase_1_5_embedding,
    print_phase_1_debug,
    print_phase_2_metadata,
    print_phase_2_debug,
    print_phase_4,
    print_phase_4_debug,
    print_phase_0a_0b_to_1_debug,
    print_phase_1_to_2_debug,
    print_pipeline_start,
    print_pipeline_end,
)
from doc4llm.doc_rag.params_parser.params_parser_api import ParamsParserAPI
from doc4llm.doc_rag.query_optimizer.query_optimizer import (
    OptimizationResult,
    QueryOptimizer,
    QueryOptimizerConfig,
)
from doc4llm.doc_rag.query_router.query_router import (
    QueryRouter,
    QueryRouterConfig,
    RoutingResult,
)
from doc4llm.doc_rag.scene_output.scene_output import SceneOutput, SceneOutputResult
from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI
from doc4llm.doc_rag.reader.doc_reader_api import DocReaderAPI
from doc4llm.doc_rag.utils.reranker_utils import (
    adjust_threshold,
    filter_reranker_output,
)

# Type alias for stop_at_phase parameter
StopPhase = Literal["0a", "0b", "1", "1.5", "2", "4"]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class DocRAGConfig:
    """Orchestrator configuration for Doc-RAG retrieval workflow.

    Attributes:
        base_dir: Path to knowledge_base
        default_threshold: Line count threshold for requires_processing flag
        llm_reranker: Enable Phase 1.5 LLM re-ranking
        embedding_reranker: Enable Phase 1.5 transformer embedding re-ranking
        reranker_threshold: Threshold for transformer embedding reranker (default 0.6)
        reranker_threshold_adjustment: Threshold adjustment for LLM reranker input (default 0.1)
        debug: Enable debug mode
        skiped_keywords_path: Custom path for skiped_keywords.txt
        reader_config: Configuration dict for DocReaderAPI
        searcher_config: Configuration dict for DocSearcherAPI
        silent: Silent mode, suppress all output (used by CLI for hook injection)
    """

    base_dir: str
    default_threshold: int = 2100
    llm_reranker: bool = True
    embedding_reranker: bool = False
    searcher_reranker: bool = True
    reranker_threshold: float = 0.6
    reranker_threshold_adjustment: float = 0.1
    debug: bool = False
    skiped_keywords_path: Optional[str] = None
    stop_at_phase: Optional[StopPhase] = None
    reader_config: Optional[Dict[str, Any]] = None
    searcher_config: Optional[Dict[str, Any]] = None
    silent: bool = True  # 静默模式，不打印任何输出


@dataclass
class DocRAGResult:
    """Final result returned to user from Doc-RAG retrieval workflow.

    Attributes:
        success: Whether the retrieval was successful
        output: Final formatted Markdown output
        scene: Classification from Phase 0b (QueryRouter)
        documents_extracted: Number of documents/sections extracted
        total_lines: Total line count of extracted content
        requires_processing: Whether threshold was exceeded (metadata)
        sources: List of source document metadata
        raw_response: Raw LLM response from SceneOutput (if available)
        thinking: LLM thinking process from SceneOutput (if available)
        timing: Dictionary containing timing information for each phase
    """

    success: bool
    output: str
    scene: str
    documents_extracted: int
    total_lines: int
    requires_processing: bool
    sources: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: Optional[str] = None
    thinking: Optional[str] = None
    timing: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# Helper Functions
# =============================================================================


def _opt_result_to_dict(result: OptimizationResult) -> Dict[str, Any]:
    """Convert OptimizationResult to dictionary for ParamsParserAPI."""
    return {
        "query_analysis": result.query_analysis,
        "optimized_queries": result.optimized_queries,
        "search_recommendation": result.search_recommendation,
    }


def _router_result_to_dict(result: RoutingResult) -> Dict[str, Any]:
    """Convert RoutingResult to dictionary for ParamsParserAPI."""
    return {
        "scene": result.scene,
        "confidence": result.confidence,
        "ambiguity": result.ambiguity,
        "coverage_need": result.coverage_need,
        "reranker_threshold": result.reranker_threshold,
    }


def _build_doc_metas(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build document metadata list from search/rerank results.

    Args:
        results: Search results from DocSearcherAPI or reranked results

    Returns:
        List of document metadata dictionaries
    """
    doc_metas = []
    for page in results.get("results", []):
        doc_set = page.get("doc_set", "")
        page_title = page.get("page_title", "")

        # Extract toc_path for source tracking
        toc_path = page.get("toc_path", "")

        # Build local_path and source_url
        local_path = ""
        source_url = ""
        if toc_path:
            # local_path points to docContent.md
            local_path = toc_path.replace("/docTOC.md", "/docContent.md")
            # Extract original URL from docContent.md
            # Format: "> **原文链接**: https://..." or "原文链接: https://..."
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "> **原文链接**:" in line or "原文链接:" in line:
                            # Remove markdown blockquote and formatting
                            source_url = (
                                line.replace("> **原文链接**:", "")
                                .replace("原文链接:", "")
                                .strip()
                            )
                            break
            except Exception:
                pass

        headings = page.get("headings", [])
        heading_texts = [h.get("text", "") for h in headings if h.get("text")]

        doc_metas.append(
            {
                "title": page_title,
                "doc_set": doc_set,
                "source_url": source_url,
                "local_path": local_path,
                "headings": heading_texts,
            }
        )

    return doc_metas


def _restore_toc_paths(
    results: Dict[str, Any], toc_path_map: Dict[tuple, str]
) -> Dict[str, Any]:
    """从映射表回溯还原 toc_path 字段。

    Phase 1.5 LLM Reranking 会过滤掉 toc_path 字段，
    此函数用于从 Phase 1 保存的映射表中回溯还原。

    Args:
        results: Phase 1.5 结果（可能不含 toc_path）
        toc_path_map: (doc_set, page_title) → toc_path 映射表

    Returns:
        还原 toc_path 后的结果
    """
    if not toc_path_map:
        return results

    results_copy = {
        "query": results.get("query", []),
        "doc_sets_found": results.get("doc_sets_found", []),
        "results": [],
    }

    for page in results.get("results", []):
        page_copy = page.copy()
        key = (page.get("doc_set", ""), page.get("page_title", ""))

        # 如果 toc_path 缺失，从映射表回溯
        if not page_copy.get("toc_path") and key in toc_path_map:
            page_copy["toc_path"] = toc_path_map[key]

        results_copy["results"].append(page_copy)

    return results_copy


def _build_output_with_wrapper_and_sources(
    raw_content: str, doc_metas: List[Dict[str, Any]], doc_sets: List[str]
) -> str:
    """Build output with AOP-FINAL wrapper and Sources section.

    Args:
        raw_content: Raw extracted content from Phase 2
        doc_metas: List of document metadata from _build_doc_metas
        doc_sets: List of doc-set names for source field

    Returns:
        Formatted output with wrapper and sources
    """
    # Count actual lines in content
    actual_line_count = len(raw_content.strip().split("\n"))

    # Build sources section
    sources_section = "\n---\n\n### 文档来源 (Sources)\n\n"
    for i, doc_meta in enumerate(doc_metas, 1):
        sources_section += f"{i}. **{doc_meta.get('title', '')}**\n"
        sources_section += f"   - 原文链接: {doc_meta.get('source_url', '')}\n"
        sources_section += f"   - 本地文档: `{doc_meta.get('local_path', '')}`\n\n"

    # Build source field value (comma-separated doc_sets)
    source_field = ", ".join(doc_sets) if doc_sets else "unknown"

    # Combine wrapper + content + sources
    return f"""=== AOP-FINAL | agent=rag | format=markdown | lines={actual_line_count} | source={source_field} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

{raw_content}
{sources_section}=== END-AOP-FINAL ===
"""


# =============================================================================
# Search Result Field Filtering Constants
# =============================================================================

# Search result 顶层保留字段（其他配置/元数据字段会被过滤掉）
SEARCH_RESULT_KEEP_FIELDS = frozenset(
    {
        "query",  # 搜索查询（优化后的）
        "doc_sets_found",  # 找到的 doc-sets 列表
        "results",  # 搜索结果（详细内容在下方处理）
    }
)

# Page 级别保留字段
PAGE_KEEP_FIELDS = frozenset(
    {
        "doc_set",  # 必须 - 文档集标识
        "page_title",  # 必须 - 页面标题
        "rerank_sim",  # 必须 - 页面级别的 rerank 结果
        "headings",  # 必须 - heading 列表
        "toc_path",  # 必须 - source_url 回溯必须字段
    }
)

# Heading 级别保留字段
HEADING_KEEP_FIELDS = frozenset(
    {
        "text",  # 必须 - 核心内容
        "rerank_sim",  # 必须 - 用于 LLM reranker 判断
        "related_context",
    }
)


def _filter_page_fields(page: Dict[str, Any]) -> Dict[str, Any]:
    """Filter page to keep only essential fields."""
    filtered_page = {k: v for k, v in page.items() if k in PAGE_KEEP_FIELDS}
    # 过滤 headings
    filtered_page["headings"] = [
        {h_k: h_v for h_k, h_v in heading.items() if h_k in HEADING_KEEP_FIELDS}
        for heading in page.get("headings", [])
    ]
    return filtered_page


def _filter_search_result_fields(search_result: Dict[str, Any]) -> Dict[str, Any]:
    """Filter search result to keep only essential fields.

    Args:
        search_result: Raw search result from DocSearcherAPI

    Returns:
        Filtered search result with only essential fields
    """
    # 1. 过滤 search_result 顶层字段，只保留核心字段
    filtered = {
        k: v for k, v in search_result.items() if k in SEARCH_RESULT_KEEP_FIELDS
    }
    # 2. 过滤 results 中的每个 page
    filtered["results"] = [
        _filter_page_fields(page) for page in search_result.get("results", [])
    ]
    return filtered


def _clear_rerank_sim_fields(data: Any) -> Any:
    """递归清除 rerank_sim 字段，返回新对象（不修改原数据）.

    Args:
        data: 任意数据（dict/list/其他）

    Returns:
        清除 rerank_sim 后的新对象
    """
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k == "rerank_sim":
                result[k] = None  # 置为 null
            else:
                result[k] = _clear_rerank_sim_fields(v)
        return result
    elif isinstance(data, list):
        return [_clear_rerank_sim_fields(item) for item in data]
    else:
        return data


# =============================================================================
# Main Orchestrator Class
# =============================================================================


class DocRAGOrchestrator:
    """Main orchestrator for Doc-RAG retrieval workflow.

    Coordinates all seven modules to execute complete documentation retrieval
    and output generation pipeline.

    Attributes:
        config: Current configuration
        last_result: Last retrieval result
    """

    config: DocRAGConfig
    last_result: Optional[DocRAGResult]

    def __init__(self, config: Optional[DocRAGConfig] = None) -> None:
        """Initialize the orchestrator with optional configuration.

        Args:
            config: DocRAGConfig instance, uses defaults if None
        """
        self.config = config or DocRAGConfig()
        self.last_result = None

    def _save_reranker_input(self, data: Dict[str, Any]) -> None:
        """保存 Phase 1.5 LLM Re-ranker 输入数据到 JSON 文件。

        Args:
            data: 输入数据 (search_result_with_scene)
        """
        filename = "phase1_5_input.json"
        filepath = os.path.join(os.getcwd(), filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"▶ [Debug] Phase 1.5 输入数据已保存: {filepath}")
        except Exception as e:
            print(f"▶ [Debug] 保存 Phase 1.5 输入数据失败: {e}")

    def retrieve(self, query: str) -> DocRAGResult:
        """Execute complete Doc-RAG retrieval workflow.

        Workflow:
            Phase 0a: Query Optimization -> OptimizationResult
            Phase 0b: Scene Routing -> RoutingResult
            Phase 0a+0b -> Phase 1: Parse Parameters
            Phase 1: Document Discovery -> Search Results
            Phase 1.5: LLM Re-ranking (conditional) -> Reranked Results
            Phase 1.5 -> Phase 2: Parse Parameters
            Phase 2: Content Extraction -> ExtractionResult
            Phase 4: Scene-Based Output -> Final Result

        Args:
            query: User query text

        Returns:
            DocRAGResult with formatted output and metadata
        """
        original_query = query
        timing: Dict[str, float] = {}

        if not self.config.silent:
            print_pipeline_start(query)

        # -------------------------------------------------------------------------
        # Early return for stop_at_phase control
        # -------------------------------------------------------------------------
        # Only execute Phase 0a
        if self.config.stop_at_phase == "0a":
            optimizer = QueryOptimizer(QueryOptimizerConfig(silent=self.config.silent))
            start = time.perf_counter()
            opt_result = optimizer.optimize(query)
            timing["phase_0a"] = (time.perf_counter() - start) * 1000
            if not self.config.silent:
                print(
                    f"▶ [Phase 0a] Query Optimization 耗时: {timing['phase_0a']:.2f}ms"
                )
            if self.config.debug:
                print(f"\n{'─' * 60}")
                print(f"▶ Phase 0a: Query Optimization [原始输出]")
                print(f"{'─' * 60}")
                json_output = json.dumps(
                    {
                        "phase": "0a",
                        "query_analysis": opt_result.query_analysis,
                        "optimized_queries": opt_result.optimized_queries,
                        "search_recommendation": opt_result.search_recommendation,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                print(json_output)
                print(f"{'─' * 60}\n")
            return DocRAGResult(
                success=True,
                output=json.dumps(
                    {
                        "phase": "0a",
                        "query_analysis": opt_result.query_analysis,
                        "optimized_queries": opt_result.optimized_queries,
                        "search_recommendation": opt_result.search_recommendation,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                scene="",
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=[],
                timing=timing,
            )

        # Only execute Phase 0b
        if self.config.stop_at_phase == "0b":
            router = QueryRouter(QueryRouterConfig(silent=self.config.silent))
            start = time.perf_counter()
            router_result = router.route(query)
            timing["phase_0b"] = (time.perf_counter() - start) * 1000
            if not self.config.silent:
                print(f"▶ [Phase 0b] Scene Routing 耗时: {timing['phase_0b']:.2f}ms")
            if self.config.debug:
                print(f"\n{'─' * 60}")
                print(f"▶ Phase 0b: Scene Routing [原始输出]")
                print(f"{'─' * 60}")
                json_output = json.dumps(
                    {
                        "phase": "0b",
                        "scene": router_result.scene,
                        "confidence": router_result.confidence,
                        "ambiguity": router_result.ambiguity,
                        "coverage_need": router_result.coverage_need,
                        "reranker_threshold": router_result.reranker_threshold,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                print(json_output)
                print(f"{'─' * 60}\n")
            return DocRAGResult(
                success=True,
                output=json.dumps(
                    {
                        "phase": "0b",
                        "scene": router_result.scene,
                        "confidence": router_result.confidence,
                        "ambiguity": router_result.ambiguity,
                        "coverage_need": router_result.coverage_need,
                        "reranker_threshold": router_result.reranker_threshold,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                scene=router_result.scene,
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=[],
                timing=timing,
            )

        # -------------------------------------------------------------------------
        # Phase 0a: Query Optimization & Phase 0b: Scene Routing (Concurrent)
        # -------------------------------------------------------------------------
        def _run_phase_0a(query: str, silent: bool) -> OptimizationResult:
            optimizer = QueryOptimizer(QueryOptimizerConfig(silent=silent))
            return optimizer.optimize(query)

        def _run_phase_0b(query: str, silent: bool) -> RoutingResult:
            router = QueryRouter(QueryRouterConfig(silent=silent))
            return router.route(query)

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_0a = executor.submit(_run_phase_0a, query, self.config.silent)
            future_0b = executor.submit(_run_phase_0b, query, self.config.silent)

            try:
                start_0a = time.perf_counter()
                opt_result = future_0a.result()
                timing["phase_0a"] = (time.perf_counter() - start_0a) * 1000

                start_0b = time.perf_counter()
                router_result = future_0b.result()
                timing["phase_0b"] = (time.perf_counter() - start_0b) * 1000
            except Exception as e:
                traceback.print_exc()
                raise Exception(
                    f"▶ [Phase 0a/0b] Query Optimization/Routing 流程出现异常: {e}，请重试或改为在线搜索"
                )

        if not self.config.silent:
            print(f"▶ [Phase 0a] Query Optimization 耗时: {timing['phase_0a']:.2f}ms")
        if not self.config.silent:
            print(f"▶ [Phase 0b] Scene Routing 耗时: {timing['phase_0b']:.2f}ms")

        optimizer = QueryOptimizer()
        optimizer.last_result = opt_result
        optimized_queries = opt_result.optimized_queries
        doc_sets = opt_result.query_analysis.get("doc_set", [])
        domain_nouns = opt_result.query_analysis.get("domain_nouns", [])
        predicate_verbs = opt_result.query_analysis.get("predicate_verbs", [])

        router = QueryRouter()
        router.last_result = router_result
        scene = router_result.scene
        reranker_threshold = router_result.reranker_threshold

        # Print phase output (skip if debug mode, will use debug version instead)
        # Also skip if silent mode
        if not self.config.debug and not self.config.silent:
            print_phase_0a(
                query_analysis=opt_result.query_analysis,
                optimized_queries=optimized_queries,
                doc_sets=doc_sets,
                domain_nouns=domain_nouns,
                predicate_verbs=predicate_verbs,
                quiet=False,
            )

        # Debug: 打印原始输出
        if self.config.debug:
            print_phase_0a_debug(
                query_analysis=opt_result.query_analysis,
                optimized_queries=optimized_queries,
                doc_sets=doc_sets,
                domain_nouns=domain_nouns,
                predicate_verbs=predicate_verbs,
                raw_response=opt_result.raw_response,
                thinking=opt_result.thinking,
            )

        # -------------------------------------------------------------------------
        # Phase 0b: Scene Routing (already executed concurrently above)
        # -------------------------------------------------------------------------

        # Print phase output (skip if debug mode, will use debug version instead)
        # Also skip if silent mode
        if not self.config.debug and not self.config.silent:
            print_phase_0b(
                scene=scene,
                confidence=router_result.confidence,
                ambiguity=router_result.ambiguity,
                coverage_need=router_result.coverage_need,
                reranker_threshold=reranker_threshold,
                quiet=False,
            )

        # Debug: 打印原始输出
        if self.config.debug and router_result:
            print_phase_0b_debug(
                scene=scene,
                confidence=router_result.confidence,
                ambiguity=router_result.ambiguity,
                coverage_need=router_result.coverage_need,
                reranker_threshold=reranker_threshold,
                raw_response=router_result.raw_response,
                thinking=router_result.thinking,
            )

        # -------------------------------------------------------------------------
        # Phase 0a+0b -> Phase 1: Parse Parameters
        # -------------------------------------------------------------------------

        parser = ParamsParserAPI()
        phases_output = [
            {
                "phase": "0a",
                "output": _opt_result_to_dict(optimizer.last_result)
                if optimizer.last_result
                else {},
            },
            {
                "phase": "0b",
                "output": _router_result_to_dict(router.last_result)
                if router.last_result
                else {},
            },
        ]

        start_parser_0a_0b_to_1 = time.perf_counter()
        searcher_config_response = parser.parse_multi_phase(
            to_phase="1",
            phases=phases_output,
        )
        timing["phase_0a_0b_to_1"] = (
            time.perf_counter() - start_parser_0a_0b_to_1
        ) * 1000
        if not self.config.silent:
            print(
                f"▶ [Phase 0a+0b -> Phase 1] 参数解析 耗时: {timing['phase_0a_0b_to_1']:.2f}ms"
            )

        if searcher_config_response.status != "success":
            traceback.print_exc()
            raise Exception(
                f"▶ [Phase 0a+0b -> Phase 1] Params Parser 流程出现异常: 参数解析失败，请重试或改为在线搜索"
            )

        searcher_config = searcher_config_response.config or {}

        # Debug: 打印参数解析结果
        if self.config.debug:
            print_phase_0a_0b_to_1_debug(
                phases=phases_output,
                config=searcher_config,
                from_phase="0a+0b",
                to_phase="1",
                status=searcher_config_response.status,
                errors=searcher_config_response.errors,
            )

        search_query = (
            searcher_config_response.config.get("query", query)
            if searcher_config_response.config
            else query
        )
        # API format: target_doc_sets is already a List[str]
        target_doc_sets = (
            searcher_config_response.config.get("target_doc_sets", [])
            if searcher_config_response.config
            else []
        )

        # Use doc_sets from optimizer if not in config
        if not target_doc_sets and doc_sets:
            target_doc_sets = doc_sets

        # Use base_dir from user-provided config
        base_dir = self.config.base_dir

        # 验证 base_dir 不为空
        if not base_dir:
            raise ValueError(
                "base_dir is not set. Please provide base_dir via "
                "retrieve(base_dir='path/to/knowledge_base') parameter"
            )

        # -------------------------------------------------------------------------
        # Phase 1: Document Discovery
        # -------------------------------------------------------------------------
        # Merge searcher_config from ParamsParserAPI with user-provided config
        # Priority: user config > parsed config (user can override specific settings)
        merged_searcher_config = {
            **(searcher_config_response.config or {}),
            **(self.config.searcher_config or {}),
        }

        try:
            searcher = DocSearcherAPI(
                base_dir=base_dir,
                config=merged_searcher_config,
                debug=False,
                reranker_enabled=self.config.searcher_reranker,
                reranker_threshold=self.config.reranker_threshold,
                skiped_keywords_path=self.config.skiped_keywords_path,
                domain_nouns=domain_nouns,
            )
            start_phase_1 = time.perf_counter()
            search_result = searcher.search(
                query=search_query,
                target_doc_sets=target_doc_sets if target_doc_sets else None,
            )
            timing["phase_1"] = (time.perf_counter() - start_phase_1) * 1000
        except Exception as e:
            traceback.print_exc()
            raise Exception(
                f"▶ [Phase 1] DocSearcher 流程出现异常: {e}，请重试或改为在线搜索"
            )

        if not self.config.silent:
            print(f"▶ [Phase 1] Document Discovery 耗时: {timing['phase_1']:.2f}ms")

        if not search_result.get("success", False):
            return DocRAGResult(
                success=False,
                output=f"No documents found for query: {query}\n\nSearch message: {search_result.get('message', 'Unknown error')}",
                scene=scene,
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=[],
                timing=timing,
            )

        # Check if should stop at Phase 1
        if self.config.stop_at_phase == "1":
            doc_metas = _build_doc_metas(search_result)
            if not self.config.silent:
                print(f"▶ [Phase 1] Document Search 耗时: {timing['phase_1']:.2f}ms")
            if self.config.debug:
                print(f"\n{'─' * 60}")
                print(f"▶ Phase 1: 文档检索 (Document Search) [原始输出]")
                print(f"{'─' * 60}")
                json_output = json.dumps(search_result, ensure_ascii=False, indent=2)
                print(json_output)
                print(f"{'─' * 60}\n")
            return DocRAGResult(
                success=True,
                output=json.dumps(
                    {
                        "phase": "1",
                        "query": search_result.get(
                            "query", search_query
                        ),  # 使用过滤后的 query
                        "target_doc_sets": target_doc_sets,
                        "results": search_result.get("results", []),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                scene=scene,
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=doc_metas,
                timing=timing,
            )

        # 非 debug 模式：静默打印 Phase 1 结果
        # debug 模式：由 print_phase_1_debug 内部调用 print_phase_1，避免重复输出
        # silent 模式下也跳过
        if not self.config.debug and not self.config.silent:
            print_phase_1(
                results=search_result,
                query=search_query,
                optimized_queries=optimized_queries,
                quiet=True,
            )

        # Debug: 打印 Phase 1 结果（仅原始 JSON 输出）
        if self.config.debug:
            print_phase_1_debug(
                results=search_result,
                query=search_query,
            )

        # -------------------------------------------------------------------------
        # Phase 1.5: Re-ranking (LLM + Embedding, Optional Concurrent)
        # -------------------------------------------------------------------------
        start_phase_1_5 = time.perf_counter()

        # 保存 Phase 1 结果的 toc_path 映射（用于 Phase 1.5 后回溯）
        toc_path_map = {
            (page.get("doc_set", ""), page.get("page_title", "")): page.get(
                "toc_path", ""
            )
            for page in search_result.get("results", [])
        }

        # 清理 search_result，移除多余字段，只保留核心字段
        search_result_cleaned = _filter_search_result_fields(search_result)
        # 创建清除 rerank_sim 的副本（不修改原始数据）
        search_result_for_rerank = _clear_rerank_sim_fields(search_result_cleaned)

        current_results = search_result
        rerank_executed = False
        embedding_rerank_executed = False
        total_headings_before = 0
        total_headings_after = 0
        pages_before = len(search_result.get("results", []))
        pages_after = pages_before
        rerank_thinking = None

        total_headings_count = sum(
            len(r.get("headings", [])) for r in search_result.get("results", [])
        )

        needs_rerank = any(
            h.get("rerank_sim") is None
            for r in search_result.get("results", [])
            for h in r.get("headings", [])
        )

        llm_result = None
        embedding_result = None

        if self.config.embedding_reranker and self.config.llm_reranker:
            # 计算调整后的阈值（输入到 LLM reranker 时减 0.1）
            adjusted_threshold = adjust_threshold(
                reranker_threshold, self.config.reranker_threshold_adjustment
            )
            # 构造 Phase 1.5 LLM Re-ranker 输入数据
            search_result_with_scene = {
                **search_result_for_rerank,
                "retrieval_scene": scene,
                "reranker_threshold": adjusted_threshold,  # 使用调整后的阈值
            }
            # 分离记录：截留 headings=[] 或 headings>=10 的记录
            original_results = search_result_with_scene.get("results", [])
            skipped_pages = []  # 截留的页面（headings=[] 或 headings>=10）
            rerank_input_pages = []  # 送入 LLM reranker 的页面 (0 < len(headings) < 10)

            for page in original_results:
                headings = page.get("headings", [])
                if len(headings) == 0 or len(headings) >= 10:
                    # 截留：直接转为 sections（整页提取）
                    skipped_pages.append(page)
                else:
                    # 送入 LLM reranker 处理
                    rerank_input_pages.append(page)

            # 更新 LLM reranker 输入（只包含 0 < len(headings) < 10 的记录）
            search_result_with_scene["results"] = rerank_input_pages

            # Debug: 打印截留信息
            if self.config.debug:
                skipped_empty = sum(
                    1 for p in skipped_pages if len(p.get("headings", [])) == 0
                )
                skipped_many = sum(
                    1 for p in skipped_pages if len(p.get("headings", [])) >= 10
                )
                print(f"\n{'─' * 60}")
                print(f"▶ Phase 1.5: 记录分离 [Debug]")
                print(f"{'─' * 60}")
                print(f"  总页面数: {len(original_results)}")
                print(
                    f"  截留页面: {len(skipped_pages)} (空 headings: {skipped_empty}, headings>=10: {skipped_many})"
                )
                print(f"  送入 LLM reranker: {len(rerank_input_pages)}")
                print(f"{'─' * 60}\n")

            # 保存 Phase 1.5 输入数据（调试用途）
            if self.config.debug:
                self._save_reranker_input(search_result_with_scene)

            with ThreadPoolExecutor(max_workers=2) as executor:

                def run_llm_rerank(
                    input_data: Dict[str, Any], silent: bool
                ) -> RerankerResult:
                    reranker = LLMReranker(LLMRerankerConfig(silent=silent))
                    return reranker.rerank(input_data)

                def run_embedding_rerank():
                    return searcher.rerank(
                        search_result_for_rerank.get("results", []), optimized_queries
                    )

                future_llm = executor.submit(
                    run_llm_rerank, search_result_with_scene, self.config.silent
                )
                future_embedding = executor.submit(run_embedding_rerank)

                try:
                    llm_result = future_llm.result()
                    embedding_result = future_embedding.result()
                except Exception as e:
                    traceback.print_exc()
                    raise Exception(
                        f"▶ [Phase 1.5] Reranker (LLM + Embedding 并发) 流程出现异常: {e}，请重试或改为在线搜索"
                    )

            if llm_result.success and llm_result.data.get("results"):
                current_results = llm_result.data
                rerank_executed = True
                total_headings_before = llm_result.total_headings_before
                total_headings_after = llm_result.total_headings_after
                pages_after = len(llm_result.data.get("results", []))
                rerank_thinking = llm_result.thinking
                # 按原阈值二次过滤 LLM 输出结果
                current_results = filter_reranker_output(
                    current_results, reranker_threshold
                )
                # 合并：截留记录 + 过滤后 LLM 输出记录 → 形成完整 results
                reranker_output_results = current_results.get("results", [])
                self._merged_results_for_parser = (
                    skipped_pages + reranker_output_results
                )
            elif embedding_result and embedding_result.get("results"):
                current_results = embedding_result
                embedding_rerank_executed = True
                embedding_pages = embedding_result.get("results", [])
                # 确保每个 page 都有 toc_path（从 toc_path_map 回溯）
                for page in embedding_pages:
                    key = (page.get("doc_set", ""), page.get("page_title", ""))
                    if not page.get("toc_path") and key in toc_path_map:
                        page["toc_path"] = toc_path_map[key]
                total_headings_before = sum(
                    len(p.get("headings", [])) for p in search_result.get("results", [])
                )
                total_headings_after = sum(
                    len(p.get("headings", [])) for p in embedding_pages
                )
                pages_after = len(embedding_pages)
                # 合并：截留记录 + Embedding 输出记录 → 形成完整 results
                self._merged_results_for_parser = skipped_pages + embedding_pages
            else:
                traceback.print_exc()
                llm_empty = not (llm_result and llm_result.data.get("results"))
                embedding_empty = not (
                    embedding_result and embedding_result.get("results")
                )
                if llm_empty and embedding_empty:
                    raise Exception(
                        f"▶ [Phase 1.5] LLM Reranker 和 Embedding Reranker 均返回空结果，请重试或改为在线搜索"
                    )
                elif llm_empty:
                    raise Exception(
                        f"▶ [Phase 1.5] LLM Reranker 返回空结果，Embedding Reranker 也无可用结果，请重试或改为在线搜索"
                    )
                else:
                    raise Exception(
                        f"▶ [Phase 1.5] Embedding Reranker 返回空结果，请重试或改为在线搜索"
                    )

        elif self.config.embedding_reranker:
            try:
                embedding_result = searcher.rerank(
                    search_result_for_rerank.get("results", []), optimized_queries
                )
            except Exception as e:
                traceback.print_exc()
                raise Exception(
                    f"▶ [Phase 1.5] Embedding Reranker 流程出现异常: {e}，请重试或改为在线搜索"
                )

            if embedding_result and embedding_result.get("results"):
                current_results = embedding_result
                embedding_rerank_executed = True
                embedding_pages = embedding_result.get("results", [])
                # 确保每个 page 都有 toc_path（从 toc_path_map 回溯）
                for page in embedding_pages:
                    key = (page.get("doc_set", ""), page.get("page_title", ""))
                    if not page.get("toc_path") and key in toc_path_map:
                        page["toc_path"] = toc_path_map[key]
                total_headings_before = sum(
                    len(p.get("headings", [])) for p in search_result.get("results", [])
                )
                total_headings_after = sum(
                    len(p.get("headings", [])) for p in embedding_pages
                )
                pages_after = len(embedding_pages)
            else:
                traceback.print_exc()
                raise Exception(
                    f"▶ [Phase 1.5] Embedding Reranker 返回空结果，请重试或改为在线搜索"
                )

        elif self.config.llm_reranker or needs_rerank:
            try:
                # 1. 分离记录：截留 headings=[] 或 headings>=10 的记录
                original_results = search_result_for_rerank.get("results", [])
                skipped_pages = []  # 截留的页面（headings=[] 或 headings>=10）
                rerank_input_pages = []  # 送入 LLM reranker 的页面 (0 < len(headings) < 10)

                for page in original_results:
                    headings = page.get("headings", [])
                    if len(headings) == 0 or len(headings) >= 10:
                        # 截留：直接转为 sections（整页提取）
                        skipped_pages.append(page)
                    else:
                        # 送入 LLM reranker 处理
                        rerank_input_pages.append(page)

                # 2. 计算调整后的阈值（输入到 LLM reranker 时减 0.1）
                adjusted_threshold = adjust_threshold(
                    reranker_threshold, self.config.reranker_threshold_adjustment
                )
                # 构造 LLM reranker 输入（只包含 0 < len(headings) < 10 的记录）
                search_result_with_scene = {
                    **search_result_for_rerank,
                    "retrieval_scene": scene,
                    "reranker_threshold": adjusted_threshold,  # 使用调整后的阈值
                    "results": rerank_input_pages,
                }

                # Debug: 打印截留信息
                if self.config.debug:
                    skipped_empty = sum(
                        1 for p in skipped_pages if len(p.get("headings", [])) == 0
                    )
                    skipped_many = sum(
                        1 for p in skipped_pages if len(p.get("headings", [])) >= 10
                    )
                    print(f"\n{'─' * 60}")
                    print(f"▶ Phase 1.5: 记录分离 [Debug]")
                    print(f"{'─' * 60}")
                    print(f"  总页面数: {len(original_results)}")
                    print(
                        f"  截留页面: {len(skipped_pages)} (空 headings: {skipped_empty}, headings>=10: {skipped_many})"
                    )
                    print(f"  送入 LLM reranker: {len(rerank_input_pages)}")
                    print(f"{'─' * 60}\n")

                # 保存 Phase 1.5 输入数据（调试用途）
                if self.config.debug:
                    self._save_reranker_input(search_result_with_scene)

                reranker = LLMReranker(LLMRerankerConfig(silent=self.config.silent))
                rerank_result = reranker.rerank(search_result_with_scene)
                rerank_thinking = rerank_result.thinking

                if rerank_result.success:
                    current_results = rerank_result.data
                    rerank_executed = True
                    total_headings_before = rerank_result.total_headings_before
                    total_headings_after = rerank_result.total_headings_after
                    pages_after = len(rerank_result.data.get("results", []))

                    # 按原阈值二次过滤 LLM 输出结果
                    current_results = filter_reranker_output(
                        current_results, reranker_threshold
                    )
                    # 合并：截留记录 + 过滤后 LLM 输出记录 → 形成完整 results
                    reranker_output_results = current_results.get("results", [])
                    self._merged_results_for_parser = (
                        skipped_pages + reranker_output_results
                    )
                else:
                    traceback.print_exc()
                    raise Exception(
                        f"▶ [Phase 1.5] LLM Reranker 流程失败: {rerank_result.reason}，请重试或改为在线搜索"
                    )
            except Exception as e:
                traceback.print_exc()
                raise Exception(
                    f"▶ [Phase 1.5] LLM Reranker 流程出现异常: {e}，请重试或改为在线搜索"
                )

        if (
            not self.config.embedding_reranker
            and not self.config.llm_reranker
            and not needs_rerank
        ):
            if not self.config.silent:
                print_phase_1_5_skipped(
                    reason="所有 reranker 均未启用",
                    total_headings=total_headings_count,
                    pages_count=pages_before,
                )
        elif rerank_executed:
            # debug 模式下调用 print_phase_1_5_debug（内部会调用 print_phase_1_5 打印统计）
            # 非 debug 模式下单独调用 print_phase_1_5 打印统计
            if self.config.debug:
                print_phase_1_5_debug(
                    total_before=total_headings_before,
                    total_after=total_headings_after,
                    pages_before=pages_before,
                    pages_after=pages_after,
                    raw_response=llm_result.raw_response if llm_result else None,
                    thinking=rerank_thinking,
                )
            elif not self.config.silent:
                print_phase_1_5(
                    total_before=total_headings_before,
                    total_after=total_headings_after,
                    pages_before=pages_before,
                    pages_after=pages_after,
                    quiet=False,
                )
        elif embedding_rerank_executed:
            # debug 模式下调用 print_phase_1_5_debug（内部会调用 print_phase_1_5 打印统计）
            # 非 debug 模式下调用 print_phase_1_5_embedding（显示 embedding 特有标签）
            if self.config.debug:
                print_phase_1_5_debug(
                    total_before=total_headings_before,
                    total_after=total_headings_after,
                    pages_before=pages_before,
                    pages_after=pages_after,
                    raw_response=None,
                    thinking=None,
                )
            elif not self.config.silent:
                print_phase_1_5_embedding(
                    total_before=total_headings_before,
                    total_after=total_headings_after,
                    pages_before=pages_before,
                    pages_after=pages_after,
                    quiet=False,
                )
        elif not current_results.get("success", True) or not current_results.get(
            "results"
        ):
            fail_reason = "Reranker 返回空结果"
            # debug 模式下调用 print_phase_1_5_debug（内部会调用 print_phase_1_5 打印统计）
            # 非 debug 模式下单独调用 print_phase_1_5_failed 打印失败信息
            if self.config.debug:
                print_phase_1_5_debug(
                    total_before=total_headings_count,
                    total_after=total_headings_count,
                    pages_before=pages_before,
                    pages_after=pages_before,
                    raw_response=llm_result.raw_response if llm_result else None,
                    thinking=rerank_thinking,
                )
            elif not self.config.silent:
                print_phase_1_5_failed(
                    reason=fail_reason,
                    total_headings=total_headings_count,
                    pages_count=pages_before,
                    thinking=rerank_thinking,
                )

        timing["phase_1_5"] = (time.perf_counter() - start_phase_1_5) * 1000
        rerank_type = (
            "LLM"
            if rerank_executed
            else ("Embedding" if embedding_rerank_executed else "Skipped")
        )
        if not self.config.silent:
            print(
                f"▶ [Phase 1.5] Re-ranking ({rerank_type}) 耗时: {timing['phase_1_5']:.2f}ms"
            )

        # 回溯还原 toc_path 字段（Phase 1.5 可能会过滤掉此字段）
        current_results = _restore_toc_paths(current_results, toc_path_map)

        # Check if should stop at Phase 1.5
        if self.config.stop_at_phase == "1.5":
            doc_metas = _build_doc_metas(current_results)
            if not self.config.silent:
                print(
                    f"▶ [Phase 1.5] Re-ranking ({rerank_type}) 耗时: {timing['phase_1_5']:.2f}ms"
                )
            if self.config.debug:
                print(f"\n{'─' * 60}")
                print(f"▶ Phase 1.5: LLM Re-ranking [原始输出]")
                print(f"{'─' * 60}")
                json_output = json.dumps(
                    {
                        "phase": "1.5",
                        "rerank_type": rerank_type,
                        "rerank_executed": rerank_executed,
                        "embedding_rerank_executed": embedding_rerank_executed,
                        "results": current_results.get("results", []),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                print(json_output)
                print(f"{'─' * 60}\n")
            return DocRAGResult(
                success=True,
                output=json.dumps(
                    {
                        "phase": "1.5",
                        "rerank_type": rerank_type,
                        "rerank_executed": rerank_executed,
                        "embedding_rerank_executed": embedding_rerank_executed,
                        "results": current_results.get("results", []),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                scene=scene,
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=doc_metas,
                timing=timing,
            )

        # -------------------------------------------------------------------------
        # Phase 1.5 -> Phase 2: Parse Parameters
        # -------------------------------------------------------------------------
        # 如果有合并后的 results（截留记录 + LLM 输出），使用合并结果
        # 否则使用 params parser 从 reranker 结果解析

        if (
            hasattr(self, "_merged_results_for_parser")
            and self._merged_results_for_parser
        ):
            # 使用合并后的 results 构造 parser 输入
            merged_results = self._merged_results_for_parser
            parser_input = {
                "query": current_results.get("query", []),
                "doc_sets_found": current_results.get("doc_sets_found", []),
                "results": merged_results,
            }
            delattr(self, "_merged_results_for_parser")
        else:
            parser_input = current_results

        # 根据是否执行了 reranker 来确定 from_phase
        source_phase = "1.5" if (rerank_executed or embedding_rerank_executed) else "1"
        start_parser_1_5_to_2 = time.perf_counter()
        reader_config_response = parser.parse(
            from_phase=source_phase, to_phase="2", upstream_output=parser_input
        )
        timing["phase_1_5_to_2"] = (time.perf_counter() - start_parser_1_5_to_2) * 1000
        if not self.config.silent:
            print(
                f"▶ [Phase 1.5 -> Phase 2] 参数解析 ({source_phase} -> 2) 耗时: {timing['phase_1_5_to_2']:.2f}ms"
            )

        if reader_config_response.status != "success":
            traceback.print_exc()
            raise Exception(
                f"▶ [Phase 1.5 -> Phase 2] Params Parser 流程出现异常: 参数解析失败，请重试或改为在线搜索"
            )

        reader_config = reader_config_response.config or {}

        # Debug: 打印参数解析结果
        if self.config.debug:
            print_phase_1_to_2_debug(
                upstream_output=current_results,
                config=reader_config,
                from_phase=source_phase,
                to_phase="2",
                status=reader_config_response.status,
                errors=reader_config_response.errors,
            )

        # -------------------------------------------------------------------------
        # Phase 2: Content Extraction
        # -------------------------------------------------------------------------
        try:
            reader_api = DocReaderAPI(
                base_dir=self.config.base_dir, config=self.config.reader_config
            )
            # API format: sections is a key in reader_config
            sections = reader_config.get("sections", [])
            start_phase_2 = time.perf_counter()
            extraction_result = reader_api.extract_multi_by_headings(
                sections=sections, threshold=self.config.default_threshold
            )
            timing["phase_2"] = (time.perf_counter() - start_phase_2) * 1000
        except Exception as e:
            traceback.print_exc()
            raise Exception(
                f"▶ [Phase 2] DocReader 流程出现异常: {e}，请重试或改为在线搜索"
            )

        if not self.config.silent:
            print(f"▶ [Phase 2] Content Extraction 耗时: {timing['phase_2']:.2f}ms")

        if not self.config.silent:
            print_phase_2_metadata(
                document_count=extraction_result.document_count,
                total_line_count=extraction_result.total_line_count,
                threshold=extraction_result.threshold,
                individual_counts=extraction_result.individual_counts,
                requires_processing=extraction_result.requires_processing,
                quiet=True,
            )

        # Check if should stop at Phase 2
        if self.config.stop_at_phase == "2" or scene in (
            "faithful_how_to",
            "faithful_reference",
            "how_to",
        ):
            doc_metas = _build_doc_metas(current_results)
            raw_output = (
                "\n\n".join(extraction_result.contents.values())
                if extraction_result.contents
                else ""
            )

            # Build wrapped output for faithful_* and how_to scenes
            if scene in ("faithful_how_to", "faithful_reference", "how_to"):
                wrapped_output = _build_output_with_wrapper_and_sources(
                    raw_output, doc_metas, target_doc_sets
                )
            else:
                wrapped_output = raw_output

            # Debug: 打印统计信息
            if self.config.debug:
                total_chars = sum(
                    len(content) for content in extraction_result.contents.values()
                )
                usage_rate = (
                    extraction_result.total_line_count
                    / extraction_result.threshold
                    * 100
                )

                print(f"\n{'─' * 60}")
                print(f"▶ Phase 2: Content Extraction [Debug Info]")
                print(f"{'─' * 60}")
                print(f"  文档数量: {extraction_result.document_count} 个 section")
                print(f"  总行数: {extraction_result.total_line_count:,} 行")
                print(f"  总字符数: {total_chars:,} 字")
                print(
                    f"  阈值: {extraction_result.threshold:,} 行 ({usage_rate:.1f}% 使用率)"
                )
                print(f"{'─' * 60}\n")

            return DocRAGResult(
                success=True,
                output=wrapped_output,
                scene=scene,
                documents_extracted=extraction_result.document_count,
                total_lines=extraction_result.total_line_count,
                requires_processing=extraction_result.requires_processing,
                sources=doc_metas,
                timing=timing,
            )

        if self.config.debug:
            print_phase_2_debug(
                document_count=extraction_result.document_count,
                total_line_count=extraction_result.total_line_count,
                threshold=extraction_result.threshold,
                individual_counts=extraction_result.individual_counts,
                requires_processing=extraction_result.requires_processing,
                contents=extraction_result.contents,
                limit=50,
            )

        # -------------------------------------------------------------------------
        # Phase 4: Scene-Based Output
        # -------------------------------------------------------------------------
        try:
            outputter = SceneOutput()

            # Build doc_metas from current_results
            doc_metas = _build_doc_metas(current_results)

            # Build compression metadata (Phase 3 is skipped)
            compression_meta = {
                "compression_applied": False,  # Phase 3 skipped
                "original_line_count": extraction_result.total_line_count,
                "output_line_count": extraction_result.total_line_count,
            }

            output_input = {
                "query": original_query,
                "scene": scene,
                "contents": extraction_result.contents,
                "doc_metas": doc_metas,
                "compression_meta": compression_meta,
            }

            start_phase_4 = time.perf_counter()
            output_result = outputter.compose(output_input)
            timing["phase_4"] = (time.perf_counter() - start_phase_4) * 1000
        except Exception as e:
            traceback.print_exc()
            raise Exception(
                f"▶ [Phase 4] Scene Output 流程出现异常: {e}，请重试或改为在线搜索"
            )

        # -------------------------------------------------------------------------
        # Build Final Result
        # -------------------------------------------------------------------------
        # doc_metas 已在 Phase 4 开始时构建，此处复用，无需重复构建
        # doc_metas = _build_doc_metas(current_results)  # 已存在，无需重复构建

        # Print phase output (skip if debug mode, will use debug version instead)
        # Also skip if silent mode
        if not self.config.silent:
            print(f"▶ [Phase 4] Scene-Based Output 耗时: {timing['phase_4']:.2f}ms")

        if not self.config.debug and not self.config.silent:
            print_phase_4(
                output_length=len(output_result.output),
                documents_used=len(doc_metas),
                scene=scene,
                quiet=False,
            )

        # Debug: 打印原始输出
        if self.config.debug:
            print_phase_4_debug(
                output_length=len(output_result.output),
                documents_used=len(doc_metas),
                scene=scene,
                raw_response=output_result.raw_response,
                thinking=output_result.thinking,
            )

        # Wrap output with AOP format and sources for Phase 4
        wrapped_output = _build_output_with_wrapper_and_sources(
            output_result.output, doc_metas, target_doc_sets
        )

        result = DocRAGResult(
            success=True,
            output=wrapped_output,
            scene=scene,
            documents_extracted=extraction_result.document_count,
            total_lines=extraction_result.total_line_count,
            requires_processing=extraction_result.requires_processing,
            sources=doc_metas,
            raw_response=output_result.raw_response,
            thinking=output_result.thinking,
            timing=timing,
        )

        total_time = sum(timing.values())
        if not self.config.silent:
            print(f"▶ [Pipeline] 总耗时: {total_time:.2f}ms")

        if not self.config.silent:
            print_pipeline_end(
                success=True,
                documents_extracted=result.documents_extracted,
                total_lines=result.total_lines,
            )

        self.last_result = result
        return result

    def __call__(self, query: str) -> DocRAGResult:
        """Make orchestrator callable for convenience.

        Args:
            query: User query text

        Returns:
            DocRAGResult with formatted output
        """
        return self.retrieve(query)


# =============================================================================
# Public API Functions
# =============================================================================


def retrieve(
    query: str,
    base_dir: str,
    threshold: Optional[int] = None,
    llm_reranker: bool = False,
    embedding_reranker: bool = False,
    searcher_reranker: bool = True,
    reranker_threshold: float = 0.6,
    debug: bool = False,
    skiped_keywords_path: Optional[str] = None,
    stop_at_phase: Optional[StopPhase] = None,
    reader_config: Optional[Dict[str, Any]] = None,
    searcher_config: Optional[Dict[str, Any]] = None,
    silent: bool = True,
) -> DocRAGResult:
    """Execute complete Doc-RAG retrieval workflow.

    This is the main entry point for the Python API.

    Args:
        query: User query text
        threshold: Optional line count threshold for requires_processing
        llm_reranker: Enable Phase 1.5 LLM re-ranking
        embedding_reranker: Enable Phase 1.5 transformer embedding re-ranking
        reranker_threshold: Threshold for transformer embedding reranker (default 0.6)
        debug: Enable debug mode
        skiped_keywords_path: Custom path for skiped_keywords.txt file
        stop_at_phase: Stop pipeline at specified phase ("0a", "0b", "1", "1.5", "2", "4")
        reader_config: Configuration dict for DocReaderAPI (e.g., {"search_mode": "fuzzy"})
        searcher_config: Configuration dict for DocSearcherAPI (e.g., {"bm25_k1": 1.5})
        silent: Silent mode, suppress all output (used by CLI for hook injection)

    Returns:
        DocRAGResult with formatted output and metadata

    Example:
        >>> from doc4llm.doc_rag.orchestrator import retrieve
        >>> result = retrieve("如何创建 ray cluster?")
        >>> print(result.output)
    """
    config = DocRAGConfig(
        base_dir=base_dir,
        default_threshold=threshold or 2100,
        llm_reranker=llm_reranker,
        embedding_reranker=embedding_reranker,
        searcher_reranker=searcher_reranker,
        reranker_threshold=reranker_threshold,
        debug=debug,
        skiped_keywords_path=skiped_keywords_path,
        stop_at_phase=stop_at_phase,
        reader_config=reader_config,
        searcher_config=searcher_config,
        silent=silent,
    )

    orchestrator = DocRAGOrchestrator(config)
    return orchestrator.retrieve(query)


# =============================================================================
# CLI Interface
# =============================================================================


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Doc-RAG Orchestrator - Documentation Retrieval for LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic query
    docrag "如何创建 ray cluster?"

    # With JSON output
    docrag "how to use api" --json

    # Skip LLM re-ranking
    docrag "documentation" --skip-reranker

    # Save output to file
    docrag "tutorial" --output result.md
        """,
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="User query (positional argument)",
    )

    parser.add_argument(
        "-k",
        "--kb",
        "--knowledge-base",
        dest="knowledge_base",
        help="Path to knowledge_base",
    )

    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        default=2100,
        help="Line count threshold for requires_processing flag (default: 2100)",
    )

    parser.add_argument(
        "--llm-reranker",
        dest="llm_reranker",
        action="store_true",
        help="Enable Phase 1.5 LLM re-ranking",
    )

    parser.add_argument(
        "--embedding-reranker",
        dest="embedding_reranker",
        action="store_true",
        help="Enable Phase 1.5 transformer embedding re-ranking",
    )

    parser.add_argument(
        "--searcher-reranker",
        dest="searcher_reranker",
        action="store_true",
        help="Enable Phase 1 transformer re-ranking in DocSearcherAPI",
    )

    parser.add_argument(
        "--reranker-threshold",
        dest="reranker_threshold",
        type=float,
        default=0.6,
        help="Threshold for transformer embedding reranker (default: 0.6)",
    )

    parser.add_argument(
        "--skip-keywords",
        dest="skip_keywords",
        help="Custom path for skiped_keywords.txt file",
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        help="Save output to file",
    )

    parser.add_argument(
        "--stop-at",
        dest="stop_at_phase",
        choices=["0a", "0b", "1", "1.5", "2", "4"],
        help="Stop pipeline at specified phase (0a, 0b, 1, 1.5, 2, or 4)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON format",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )

    parser.add_argument(
        "--reader-config",
        dest="reader_config",
        help='JSON config dict for DocReaderAPI (Python dict format, e.g., \'{"search_mode": "fuzzy"}\')',
    )

    parser.add_argument(
        "--searcher-config",
        dest="searcher_config",
        help="JSON config dict for DocSearcherAPI (Python dict format, e.g., '{\"bm25_k1\": 1.5}')",
    )

    parser.add_argument(
        "--silent",
        action="store_true",
        default=True,
        help="Enable silent mode, suppress all output (default: true)",
    )

    return parser.parse_args()


def _main() -> int:
    """Main entry point for CLI."""
    start_cli = time.perf_counter()
    args = _parse_args()
    silent = getattr(args, "silent", True)

    if not silent:
        cli_parse_time = (time.perf_counter() - start_cli) * 1000
        print(f"▶ [CLI] 参数解析 耗时: {cli_parse_time:.2f}ms")

    if not args.query:
        if not silent:
            print("Error: Query is required", file=sys.stderr)
            print(
                "Usage: docrag 'your query'",
                file=sys.stderr,
            )
        return 1

    try:
        # Parse JSON config arguments
        reader_config = None
        searcher_config = None
        if args.reader_config:
            reader_config = json.loads(args.reader_config)
        if args.searcher_config:
            searcher_config = json.loads(args.searcher_config)

        # Use silent mode for hook injection (Claude reads from /tmp/doc4llm_result.txt only)
        result = retrieve(
            query=args.query,
            base_dir=args.knowledge_base,
            threshold=args.threshold,
            llm_reranker=args.llm_reranker,
            embedding_reranker=args.embedding_reranker,
            searcher_reranker=args.searcher_reranker,
            reranker_threshold=args.reranker_threshold,
            debug=args.debug,
            skiped_keywords_path=args.skip_keywords,
            stop_at_phase=args.stop_at_phase,
            reader_config=reader_config,
            searcher_config=searcher_config,
            silent=True,  # CLI 模式静默输出，结果写入文件供 hook 读取
        )

        # Write to temp file for hook injection (Claude context only, user invisible)
        result_file = os.environ.get("DOC4LLM_RESULT_FILE", "/tmp/doc4llm_result.txt")
        with open(result_file, "w", encoding="utf-8") as f:
            f.write(result.output)

        # Save to file if specified (only show message in non-silent mode)
        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(result.output)
            if not silent:
                print(f"\n[Output saved to: {args.output_file}]", file=sys.stderr)

        return 0 if result.success else 1

    except Exception as e:
        if not silent:
            print(f"Error: {e}", file=sys.stderr)
        return 1


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "DocRAGConfig",
    "DocRAGResult",
    "DocRAGOrchestrator",
    "retrieve",
    "StopPhase",
]


if __name__ == "__main__":
    sys.exit(_main())
