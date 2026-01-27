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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

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


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DocRAGConfig:
    """Orchestrator configuration for Doc-RAG retrieval workflow.

    Attributes:
        knowledge_base_path: Path to knowledge_base.json
        default_threshold: Line count threshold for requires_processing flag
        llm_reranker: Skip Phase 1.5 LLM re-ranking even if needed
        debug: Enable debug mode
        skiped_keywords_path: Custom path for skiped_keywords.txt
    """
    knowledge_base_path: str = "knowledge_base.json"
    default_threshold: int = 2100
    llm_reranker: bool = False
    debug: bool = False
    skiped_keywords_path: Optional[str] = None


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

        print_pipeline_start(query)

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

            opt_result = future_0a.result()
            router_result = future_0b.result()

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
        kb_path = self.config.knowledge_base_path

        parser = ParamsParserAPI(knowledge_base_path=kb_path)
        phases_output = [
            {"phase": "0a", "output": _opt_result_to_dict(optimizer.last_result) if optimizer.last_result else {}},
            {"phase": "0b", "output": _router_result_to_dict(router.last_result) if router.last_result else {}},
        ]

        searcher_config_response = parser.parse_multi_phase(
            to_phase="1",
            phases=phases_output
        )

        if searcher_config_response.status != "success":
            return DocRAGResult(
                success=False,
                output=f"Error in phase transition 0a+0b -> 1: {searcher_config_response.errors}",
                scene=scene,
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=[],
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
                errors=searcher_config_response.errors
            )

        search_query = searcher_config.get("query", query)
        # API format: target_doc_sets is already a List[str]
        target_doc_sets = searcher_config.get("target_doc_sets", [])

        # Use doc_sets from optimizer if not in config
        if not target_doc_sets and doc_sets:
            target_doc_sets = doc_sets

        base_dir = searcher_config.get("base_dir", "")

        # -------------------------------------------------------------------------
        # Phase 1: Document Discovery
        # -------------------------------------------------------------------------
        try:
            searcher = DocSearcherAPI(
                base_dir=base_dir,
                knowledge_base_path=kb_path,
                debug=False,
                domain_nouns=searcher_config.get("domain_nouns", []),
                predicate_verbs=searcher_config.get("predicate_verbs", []),
                reranker_threshold=searcher_config.get("reranker_threshold", 0.68),
                skiped_keywords_path=self.config.skiped_keywords_path,
            )
            search_result = searcher.search(
                query=search_query,
                target_doc_sets=target_doc_sets if target_doc_sets else None
            )
        except Exception as e:
            return DocRAGResult(
                success=False,
                output=f"Error in Phase 1 (search): {e}",
                scene=scene,
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=[],
            )

        if not search_result.get("success", False):
            return DocRAGResult(
                success=False,
                output=f"No documents found for query: {query}\n\nSearch message: {search_result.get('message', 'Unknown error')}",
                scene=scene,
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=[],
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
        # Phase 1.5: LLM Re-ranking (Conditional)
        # -------------------------------------------------------------------------
        current_results = search_result
        rerank_executed = False
        total_headings_before = 0
        total_headings_after = 0
        pages_before = len(search_result.get("results", []))
        pages_after = pages_before
        rerank_thinking = None

        # 统计所有 heading 总数用于显示
        total_headings_count = sum(
            len(r.get("headings", []))
            for r in search_result.get("results", [])
        )

        # Check if any heading has missing rerank_sim (needs LLM reranking)
        needs_rerank = any(
            h.get("rerank_sim") is None
            for r in search_result.get("results", [])
            for h in r.get("headings", [])
        )

        if self.config.llm_reranker or needs_rerank:
            try:
                reranker = LLMReranker()
                rerank_result = reranker.rerank(search_result)
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

        # 输出 Phase 1.5 结果
        if not self.config.llm_reranker and not needs_rerank:
            # llm_reranker 未启用且无需重排序
            print_phase_1_5_skipped(
                reason="LLM reranker 未启用 (llm_reranker=False)",
                total_headings=total_headings_count,
                pages_count=pages_before
            )
        elif rerank_executed:
            # 成功执行
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
                    raw_response=rerank_result.raw_response,
                    thinking=rerank_result.thinking,
                )
        else:
            # 执行失败
            fail_reason = warnings[-1] if warnings else "未知错误"
            print_phase_1_5_failed(
                reason=f"重排序失败: {fail_reason}",
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
                    raw_response=rerank_result.raw_response if 'rerank_result' in locals() else None,
                    thinking=rerank_thinking,
                )

        # -------------------------------------------------------------------------
        # Phase 1.5 -> Phase 2: Parse Parameters
        # -------------------------------------------------------------------------
        # 根据是否执行了 reranker 来确定 from_phase
        source_phase = "1.5" if rerank_executed else "1"
        reader_config_response = parser.parse(
            from_phase=source_phase,
            to_phase="2",
            upstream_output=current_results
        )

        if reader_config_response.status != "success":
            return DocRAGResult(
                success=False,
                output=f"Error in phase transition 1.5 -> 2: {reader_config_response.errors}",
                scene=scene,
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=[],
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
                errors=reader_config_response.errors
            )

        # -------------------------------------------------------------------------
        # Phase 2: Content Extraction
        # -------------------------------------------------------------------------
        try:
            reader_api = DocReaderAPI(
                knowledge_base_path=self.config.knowledge_base_path,
                base_dir=base_dir or None,  # 优先使用配置
            )
            # API format: sections is a key in reader_config
            sections = reader_config.get("sections", [])
            extraction_result = reader_api.extract_multi_by_headings(
                sections=sections,
                threshold=self.config.default_threshold
            )
        except Exception as e:
            return DocRAGResult(
                success=False,
                output=f"Error in Phase 2 (extraction): {e}",
                scene=scene,
                documents_extracted=0,
                total_lines=0,
                requires_processing=False,
                sources=[],
            )

        print_phase_2_metadata(
            document_count=extraction_result.document_count,
            total_line_count=extraction_result.total_line_count,
            threshold=extraction_result.threshold,
            individual_counts=extraction_result.individual_counts,
            requires_processing=extraction_result.requires_processing,
            quiet=True
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

            output_result = outputter.compose(output_input)
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
        )

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
    knowledge_base_path: Optional[str] = None,
    threshold: Optional[int] = None,
    llm_reranker: bool = False,
    debug: bool = False,
    skiped_keywords_path: Optional[str] = None,
) -> DocRAGResult:
    """Execute complete Doc-RAG retrieval workflow.

    This is the main entry point for the Python API.

    Args:
        query: User query text
        knowledge_base_path: Optional path to knowledge_base.json
        threshold: Optional line count threshold for requires_processing
        llm_reranker: Skip Phase 1.5 LLM re-ranking
        debug: Enable debug mode
        skiped_keywords_path: Custom path for skiped_keywords.txt file

    Returns:
        DocRAGResult with formatted output and metadata

    Example:
        >>> from doc4llm.doc_rag.orchestrator import retrieve
        >>> result = retrieve("如何创建 ray cluster?")
        >>> print(result.output)
    """
    config = DocRAGConfig(
        knowledge_base_path=knowledge_base_path or "knowledge_base.json",
        default_threshold=threshold or 2100,
        llm_reranker=llm_reranker,
        debug=debug,
        skiped_keywords_path=skiped_keywords_path,
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

    # Specify knowledge base path
    python -m doc4llm.doc_rag.orchestrator "agent skills" --kb /path/to/knowledge_base.json

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
        default="knowledge_base.json",
        help="Path to knowledge_base.json (default: knowledge_base.json)",
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
        "--json",
        action="store_true",
        help="Output result in JSON format",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )

    return parser.parse_args()


def _main() -> int:
    """Main entry point for CLI."""
    args = _parse_args()

    if not args.query:
        print("Error: Query is required", file=sys.stderr)
        print("Usage: python -m doc4llm.doc_rag.orchestrator 'your query'", file=sys.stderr)
        return 1

    try:
        result = retrieve(
            query=args.query,
            knowledge_base_path=args.knowledge_base,
            threshold=args.threshold,
            llm_reranker=args.llm_reranker,
            debug=args.debug,
            skiped_keywords_path=args.skip_keywords,
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
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "DocRAGConfig",
    "DocRAGResult",
    "DocRAGOrchestrator",
    "retrieve",
]


if __name__ == "__main__":
    sys.exit(_main())
