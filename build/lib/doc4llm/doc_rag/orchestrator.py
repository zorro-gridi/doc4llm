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
    - CLI Interface: python -m doc4llm.doc_rag.orchestrator "query"
    - Conditional Phase 1.5 invocation based on missing rerank_sim
    - Comprehensive error handling with fallbacks

Example:
    >>> from doc4llm.doc_rag.orchestrator import retrieve
    >>> result = retrieve("如何创建 ray cluster?")
    >>> print(result.output)
"""

import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from doc4llm.doc_rag.llm_reranker.llm_reranker import LLMReranker, RerankerResult
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
)
from doc4llm.doc_rag.query_router.query_router import QueryRouter, RoutingResult
from doc4llm.doc_rag.scene_output.scene_output import SceneOutput, SceneOutputResult
from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI
from doc4llm.doc_rag.reader.doc_reader_api import DocReaderAPI

# Type alias for stop_at_phase parameter
StopPhase = Literal["0a", "0b", "1", "1.5", "2"]


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
        debug: Enable debug mode
        skiped_keywords_path: Custom path for skiped_keywords.txt
        reader_config: Configuration dict for DocReaderAPI
        searcher_config: Configuration dict for DocSearcherAPI
    """
    base_dir: str
    default_threshold: int = 2100
    llm_reranker: bool = False
    embedding_reranker: bool = False
    searcher_reranker: bool = False
    reranker_threshold: float = 0.6
    debug: bool = False
    skiped_keywords_path: Optional[str] = None
    stop_at_phase: Optional[StopPhase] = None
    reader_config: Optional[Dict[str, Any]] = None
    searcher_config: Optional[Dict[str, Any]] = None


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

        # Build source URL if available
        source_url = ""
        if toc_path:
            # Convert local path to source URL format
            source_url = toc_path.replace("/docTOC.md", "").replace("doc4llm/md_docs/", "")

        headings = page.get("headings", [])
        heading_texts = [h.get("text", "") for h in headings if h.get("text")]

        doc_metas.append({
            "title": page_title,
            "doc_set": doc_set,
            "source_url": source_url,
            "local_path": toc_path,
            "headings": heading_texts,
        })

    return doc_metas


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
        warnings: List[str] = []
        timing: Dict[str, float] = {}

        print_pipeline_start(query)

        # -------------------------------------------------------------------------
        # Early return for stop_at_phase control
        # -------------------------------------------------------------------------
        # Only execute Phase 0a
        if self.config.stop_at_phase == "0a":
            optimizer = QueryOptimizer()
            start = time.perf_counter()
            opt_result = optimizer.optimize(query)
            timing["phase_0a"] = (time.perf_counter() - start) * 1000
            print(f"▶ [Phase 0a] Query Optimization 耗时: {timing['phase_0a']:.2f}ms")
            return DocRAGResult(
                success=True,
                output=json.dumps({
                    "phase": "0a",
                    "query_analysis": opt_result.query_analysis,
                    "optimized_queries": opt_result.optimized_queries,
                    "search_recommendation": opt_result.search_recommendation,
                }, ensure_ascii=False, indent=2),
                scene="",
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=[],
                timing=timing,
            )

        # Only execute Phase 0b
        if self.config.stop_at_phase == "0b":
            router = QueryRouter()
            start = time.perf_counter()
            router_result = router.route(query)
            timing["phase_0b"] = (time.perf_counter() - start) * 1000
            print(f"▶ [Phase 0b] Scene Routing 耗时: {timing['phase_0b']:.2f}ms")
            return DocRAGResult(
                success=True,
                output=json.dumps({
                    "phase": "0b",
                    "scene": router_result.scene,
                    "confidence": router_result.confidence,
                    "ambiguity": router_result.ambiguity,
                    "coverage_need": router_result.coverage_need,
                    "reranker_threshold": router_result.reranker_threshold,
                }, ensure_ascii=False, indent=2),
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
        def _run_phase_0a(query: str) -> OptimizationResult:
            optimizer = QueryOptimizer()
            return optimizer.optimize(query)

        def _run_phase_0b(query: str) -> RoutingResult:
            router = QueryRouter()
            return router.route(query)

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_0a = executor.submit(_run_phase_0a, query)
            future_0b = executor.submit(_run_phase_0b, query)

            start_0a = time.perf_counter()
            opt_result = future_0a.result()
            timing["phase_0a"] = (time.perf_counter() - start_0a) * 1000

            start_0b = time.perf_counter()
            router_result = future_0b.result()
            timing["phase_0b"] = (time.perf_counter() - start_0b) * 1000

        print(f"▶ [Phase 0a] Query Optimization 耗时: {timing['phase_0a']:.2f}ms")
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
        if not self.config.debug:
            print_phase_0a(
                query_analysis=opt_result.query_analysis,
                optimized_queries=optimized_queries,
                doc_sets=doc_sets,
                domain_nouns=domain_nouns,
                predicate_verbs=predicate_verbs,
                quiet=False
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
        if not self.config.debug:
            print_phase_0b(
                scene=scene,
                confidence=router_result.confidence,
                ambiguity=router_result.ambiguity,
                coverage_need=router_result.coverage_need,
                reranker_threshold=reranker_threshold,
                quiet=False
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
            {"phase": "0a", "output": _opt_result_to_dict(optimizer.last_result) if optimizer.last_result else {}},
            {"phase": "0b", "output": _router_result_to_dict(router.last_result) if router.last_result else {}},
        ]

        start_parser_0a_0b_to_1 = time.perf_counter()
        searcher_config_response = parser.parse_multi_phase(
            to_phase="1",
            phases=phases_output
        )
        timing["phase_0a_0b_to_1"] = (time.perf_counter() - start_parser_0a_0b_to_1) * 1000
        print(f"▶ [Phase 0a+0b -> Phase 1] 参数解析 耗时: {timing['phase_0a_0b_to_1']:.2f}ms")

        if searcher_config_response.status != "success":
            traceback.print_exc()
            raise Exception("当前本地文档检索流程出现错误，建议根据查询需求联网搜索相关线上文档")

        searcher_config = searcher_config_response.config or {}

        # Debug: 打印参数解析结果
        if self.config.debug:
            print_phase_0a_0b_to_1_debug(
                phases=phases_output,
                config=searcher_config,
                from_phase="0a+0b",
                to_phase="1",
                status=searcher_config_response.status,
                errors=searcher_config_response.errors
            )

        search_query = searcher_config.get("query", query)
        # API format: target_doc_sets is already a List[str]
        target_doc_sets = searcher_config.get("target_doc_sets", [])

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
        try:
            searcher = DocSearcherAPI(
                base_dir=base_dir,
                config=self.config.searcher_config,
                debug=False,
                domain_nouns=searcher_config.get("domain_nouns", []),
                predicate_verbs=searcher_config.get("predicate_verbs", []),
                reranker_enabled=self.config.searcher_reranker,
                reranker_threshold=self.config.reranker_threshold,
                skiped_keywords_path=self.config.skiped_keywords_path,
            )
            start_phase_1 = time.perf_counter()
            search_result = searcher.search(
                query=search_query,
                target_doc_sets=target_doc_sets if target_doc_sets else None
            )
            timing["phase_1"] = (time.perf_counter() - start_phase_1) * 1000
            print(f"▶ [Phase 1] Document Discovery 耗时: {timing['phase_1']:.2f}ms")
        except Exception as e:
            traceback.print_exc()
            raise Exception("当前本地文档检索流程出现错误，建议根据查询需求联网搜索相关线上文档")

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
            return DocRAGResult(
                success=True,
                output=json.dumps({
                    "phase": "1",
                    "query": search_query,
                    "target_doc_sets": target_doc_sets,
                    "results": search_result.get("results", []),
                }, ensure_ascii=False, indent=2),
                scene=scene,
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=doc_metas,
                timing=timing,
            )

        print_phase_1(
            results=search_result,
            query=search_query,
            quiet=True
        )

        if self.config.debug:
            print(f"\n{'─' * 60}")
            print(f"▶ Phase 1: 文档检索 (Document Search) [原始输出]")
            print(f"{'─' * 60}")
            json_output = json.dumps(search_result, ensure_ascii=False, indent=2)
            print(json_output)
            print(f"{'─' * 60}\n")

        # -------------------------------------------------------------------------
        # Phase 1.5: Re-ranking (LLM + Embedding, Optional Concurrent)
        # -------------------------------------------------------------------------
        start_phase_1_5 = time.perf_counter()
        current_results = search_result
        rerank_executed = False
        embedding_rerank_executed = False
        total_headings_before = 0
        total_headings_after = 0
        pages_before = len(search_result.get("results", []))
        pages_after = pages_before
        rerank_thinking = None

        total_headings_count = sum(
            len(r.get("headings", []))
            for r in search_result.get("results", [])
        )

        needs_rerank = any(
            h.get("rerank_sim") is None
            for r in search_result.get("results", [])
            for h in r.get("headings", [])
        )

        llm_result = None
        embedding_result = None

        if self.config.embedding_reranker and self.config.llm_reranker:
            with ThreadPoolExecutor(max_workers=2) as executor:
                def run_llm_rerank():
                    search_result_with_scene = {
                        **search_result,
                        "retrieval_scene": scene
                    }
                    reranker = LLMReranker()
                    return reranker.rerank(search_result_with_scene)

                def run_embedding_rerank():
                    return searcher.rerank(search_result.get("results", []), optimized_queries)

                future_llm = executor.submit(run_llm_rerank)
                future_embedding = executor.submit(run_embedding_rerank)

                llm_result = future_llm.result()
                embedding_result = future_embedding.result()

            if llm_result.success and llm_result.data.get("results"):
                current_results = llm_result.data
                rerank_executed = True
                total_headings_before = llm_result.total_headings_before
                total_headings_after = llm_result.total_headings_after
                pages_after = len(llm_result.data.get("results", []))
                rerank_thinking = llm_result.thinking
            elif embedding_result and embedding_result.get("results"):
                current_results = embedding_result
                embedding_rerank_executed = True
                embedding_pages = embedding_result.get("results", [])
                total_headings_before = sum(len(p.get("headings", [])) for p in search_result.get("results", []))
                total_headings_after = sum(len(p.get("headings", [])) for p in embedding_pages)
                pages_after = len(embedding_pages)
            else:
                warnings.append("Both rerankers returned empty results, using BM25 original results")

        elif self.config.embedding_reranker:
            embedding_result = searcher.rerank(search_result.get("results", []), optimized_queries)
            if embedding_result and embedding_result.get("results"):
                current_results = embedding_result
                embedding_rerank_executed = True
                embedding_pages = embedding_result.get("results", [])
                total_headings_before = sum(len(p.get("headings", [])) for p in search_result.get("results", []))
                total_headings_after = sum(len(p.get("headings", [])) for p in embedding_pages)
                pages_after = len(embedding_pages)
            else:
                warnings.append("Embedding reranker returned empty results, using BM25 original results")

        elif self.config.llm_reranker or needs_rerank:
            try:
                search_result_with_scene = {
                    **search_result,
                    "retrieval_scene": scene
                }
                reranker = LLMReranker()
                rerank_result = reranker.rerank(search_result_with_scene)
                rerank_thinking = rerank_result.thinking

                if rerank_result.success:
                    current_results = rerank_result.data
                    rerank_executed = True
                    total_headings_before = rerank_result.total_headings_before
                    total_headings_after = rerank_result.total_headings_after
                    pages_after = len(rerank_result.data.get("results", []))
                else:
                    warnings.append(f"Phase 1.5 (reranking) failed: {rerank_result.reason}, using BM25 results")
                    current_results = search_result
            except Exception as e:
                warnings.append(f"Phase 1.5 (reranking) error: {e}, using BM25 results")
                current_results = search_result
                rerank_thinking = None

        if not self.config.embedding_reranker and not self.config.llm_reranker and not needs_rerank:
            print_phase_1_5_skipped(
                reason="所有 reranker 均未启用",
                total_headings=total_headings_count,
                pages_count=pages_before
            )
        elif rerank_executed:
            print_phase_1_5(
                total_before=total_headings_before,
                total_after=total_headings_after,
                pages_before=pages_before,
                pages_after=pages_after,
                quiet=False
            )
            if self.config.debug:
                print_phase_1_5_debug(
                    total_before=total_headings_before,
                    total_after=total_headings_after,
                    pages_before=pages_before,
                    pages_after=pages_after,
                    raw_response=llm_result.raw_response if llm_result else None,
                    thinking=rerank_thinking,
                )
        elif embedding_rerank_executed:
            print_phase_1_5_embedding(
                total_before=total_headings_before,
                total_after=total_headings_after,
                pages_before=pages_before,
                pages_after=pages_after,
                quiet=False
            )
        elif not current_results.get("success", True) or not current_results.get("results"):
            fail_reason = warnings[-1] if warnings else "Reranker returned empty results"
            print_phase_1_5_failed(
                reason=fail_reason,
                total_headings=total_headings_count,
                pages_count=pages_before,
                thinking=rerank_thinking
            )
            if self.config.debug:
                print_phase_1_5_debug(
                    total_before=total_headings_count,
                    total_after=total_headings_count,
                    pages_before=pages_before,
                    pages_after=pages_before,
                    raw_response=llm_result.raw_response if llm_result else None,
                    thinking=rerank_thinking,
                )

        timing["phase_1_5"] = (time.perf_counter() - start_phase_1_5) * 1000
        rerank_type = "LLM" if rerank_executed else ("Embedding" if embedding_rerank_executed else "Skipped")
        print(f"▶ [Phase 1.5] Re-ranking ({rerank_type}) 耗时: {timing['phase_1_5']:.2f}ms")

        # Check if should stop at Phase 1.5
        if self.config.stop_at_phase == "1.5":
            doc_metas = _build_doc_metas(current_results)
            return DocRAGResult(
                success=True,
                output=json.dumps({
                    "phase": "1.5",
                    "rerank_type": rerank_type,
                    "rerank_executed": rerank_executed,
                    "embedding_rerank_executed": embedding_rerank_executed,
                    "results": current_results.get("results", []),
                }, ensure_ascii=False, indent=2),
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
        # 根据是否执行了 reranker 来确定 from_phase
        source_phase = "1.5" if (rerank_executed or embedding_rerank_executed) else "1"
        start_parser_1_5_to_2 = time.perf_counter()
        reader_config_response = parser.parse(
            from_phase=source_phase,
            to_phase="2",
            upstream_output=current_results
        )
        timing["phase_1_5_to_2"] = (time.perf_counter() - start_parser_1_5_to_2) * 1000
        print(f"▶ [Phase 1.5 -> Phase 2] 参数解析 ({source_phase} -> 2) 耗时: {timing['phase_1_5_to_2']:.2f}ms")

        if reader_config_response.status != "success":
            traceback.print_exc()
            raise Exception("当前本地文档检索流程出现错误，建议根据查询需求联网搜索相关线上文档")

        reader_config = reader_config_response.config or {}

        # Debug: 打印参数解析结果
        if self.config.debug:
            print_phase_1_to_2_debug(
                upstream_output=current_results,
                config=reader_config,
                from_phase=source_phase,
                to_phase="2",
                status=reader_config_response.status,
                errors=reader_config_response.errors
            )

        # -------------------------------------------------------------------------
        # Phase 2: Content Extraction
        # -------------------------------------------------------------------------
        try:
            reader_api = DocReaderAPI(
                base_dir=self.config.base_dir,
                config=self.config.reader_config
            )
            # API format: sections is a key in reader_config
            sections = reader_config.get("sections", [])
            start_phase_2 = time.perf_counter()
            extraction_result = reader_api.extract_multi_by_headings(
                sections=sections,
                threshold=self.config.default_threshold
            )
            timing["phase_2"] = (time.perf_counter() - start_phase_2) * 1000
            print(f"▶ [Phase 2] Content Extraction 耗时: {timing['phase_2']:.2f}ms")
        except Exception as e:
            traceback.print_exc()
            raise Exception("当前本地文档检索流程出现错误，建议根据查询需求联网搜索相关线上文档")

        print_phase_2_metadata(
            document_count=extraction_result.document_count,
            total_line_count=extraction_result.total_line_count,
            threshold=extraction_result.threshold,
            individual_counts=extraction_result.individual_counts,
            requires_processing=extraction_result.requires_processing,
            quiet=True
        )

        # Check if should stop at Phase 2
        if self.config.stop_at_phase == "2" or scene == "faithful_how_to":
            doc_metas = _build_doc_metas(current_results)
            raw_output = "\n\n".join(extraction_result.contents.values()) if extraction_result.contents else ""
            return DocRAGResult(
                success=True,
                output=raw_output,
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
            print(f"▶ [Phase 4] Scene-Based Output 耗时: {timing['phase_4']:.2f}ms")
        except Exception as e:
            # Return raw content if SceneOutput fails
            raw_output = "\n\n".join(extraction_result.contents.values()) if extraction_result.contents else ""
            result = DocRAGResult(
                success=True,
                output=raw_output or f"Error in Phase 4 (output): {e}",
                scene=scene,
                documents_extracted=extraction_result.document_count,
                total_lines=extraction_result.total_line_count,
                requires_processing=extraction_result.requires_processing,
                sources=doc_metas,
                raw_response=None,
                thinking=None,
                timing=timing,
            )
            print_pipeline_end(
                success=True,
                documents_extracted=result.documents_extracted,
                total_lines=result.total_lines
            )
            self.last_result = result
            return result

        # -------------------------------------------------------------------------
        # Build Final Result
        # -------------------------------------------------------------------------
        doc_metas = _build_doc_metas(current_results)

        # Print phase output (skip if debug mode, will use debug version instead)
        if not self.config.debug:
            print_phase_4(
                output_length=len(output_result.output),
                documents_used=len(doc_metas),
                scene=scene,
                quiet=False
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

        result = DocRAGResult(
            success=True,
            output=output_result.output,
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
        print(f"▶ [Pipeline] 总耗时: {total_time:.2f}ms")

        print_pipeline_end(
            success=True,
            documents_extracted=result.documents_extracted,
            total_lines=result.total_lines
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
    searcher_reranker: bool = False,
    reranker_threshold: float = 0.6,
    debug: bool = False,
    skiped_keywords_path: Optional[str] = None,
    stop_at_phase: Optional[StopPhase] = None,
    reader_config: Optional[Dict[str, Any]] = None,
    searcher_config: Optional[Dict[str, Any]] = None,
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
        stop_at_phase: Stop pipeline at specified phase ("0a", "0b", "1", "1.5", "2")
        reader_config: Configuration dict for DocReaderAPI (e.g., {"search_mode": "fuzzy"})
        searcher_config: Configuration dict for DocSearcherAPI (e.g., {"bm25_k1": 1.5})

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
    python -m doc4llm.doc_rag.orchestrator "如何创建 ray cluster?"

    # With JSON output
    python -m doc4llm.doc_rag.orchestrator "how to use api" --json

    # Skip LLM re-ranking
    python -m doc4llm.doc_rag.orchestrator "documentation" --skip-reranker

    # Save output to file
    python -m doc4llm.doc_rag.orchestrator "tutorial" --output result.md
        """,
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="User query (positional argument)",
    )

    parser.add_argument(
        "-k", "--kb", "--knowledge-base",
        dest="knowledge_base",
        help="Path to knowledge_base",
    )

    parser.add_argument(
        "-t", "--threshold",
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
        "-o", "--output",
        dest="output_file",
        help="Save output to file",
    )

    parser.add_argument(
        "--stop-at",
        dest="stop_at_phase",
        choices=["0a", "0b", "1", "1.5", "2"],
        help="Stop pipeline at specified phase (0a, 0b, 1, 1.5, or 2)",
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
        help="JSON config dict for DocReaderAPI (Python dict format, e.g., '{\"search_mode\": \"fuzzy\"}')",
    )

    parser.add_argument(
        "--searcher-config",
        dest="searcher_config",
        help="JSON config dict for DocSearcherAPI (Python dict format, e.g., '{\"bm25_k1\": 1.5}')",
    )

    return parser.parse_args()


def _main() -> int:
    """Main entry point for CLI."""
    start_cli = time.perf_counter()
    args = _parse_args()
    cli_parse_time = (time.perf_counter() - start_cli) * 1000
    print(f"▶ [CLI] 参数解析 耗时: {cli_parse_time:.2f}ms")

    if not args.query:
        print("Error: Query is required", file=sys.stderr)
        print("Usage: python -m doc4llm.doc_rag.orchestrator 'your query'", file=sys.stderr)
        return 1

    try:
        # Parse JSON config arguments
        reader_config = None
        searcher_config = None
        if args.reader_config:
            reader_config = json.loads(args.reader_config)
        if args.searcher_config:
            searcher_config = json.loads(args.searcher_config)

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
        )

        if args.json:
            # JSON output
            output_data = {
                "success": result.success,
                "output": result.output,
                "scene": result.scene,
                "documents_extracted": result.documents_extracted,
                "total_lines": result.total_lines,
                "requires_processing": result.requires_processing,
                "sources": result.sources,
            }
            print(json.dumps(output_data, ensure_ascii=False, indent=2))
        else:
            # Markdown output
            print(result.output)

        # Save to file if specified
        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(result.output)
            print(f"\n[Output saved to: {args.output_file}]", file=sys.stderr)

        return 0 if result.success else 1

    except Exception as e:
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
