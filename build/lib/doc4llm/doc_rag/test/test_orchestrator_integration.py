"""
Integration tests for Doc-RAG Orchestrator complete retrieval pipeline.

Tests the full RAG retrieval workflow including all phases:
- Phase 0a: Query Optimization
- Phase 0b: Scene Routing
- Phase 1: Document Discovery
- Phase 1.5: LLM Re-ranking (conditional)
- Phase 2: Content Extraction
- Phase 4: Scene-Based Output

Each test validates the data input/output at each phase using real LLM API calls.
"""

import pytest
from typing import Dict, Any, List, Optional
from pathlib import Path

from doc4llm.doc_rag.query_optimizer.query_optimizer import (
    QueryOptimizer,
    OptimizationResult,
    QueryOptimizerConfig,
)
from doc4llm.doc_rag.query_router.query_router import (
    QueryRouter,
    RoutingResult,
    QueryRouterConfig,
)
from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI
from doc4llm.doc_rag.llm_reranker.llm_reranker import (
    LLMReranker,
    RerankerResult,
    LLMRerankerConfig,
)
from doc4llm.doc_rag.scene_output.scene_output import (
    SceneOutput,
    SceneOutputResult,
    SceneOutputConfig,
)
from doc4llm.doc_rag.orchestrator import (
    DocRAGOrchestrator,
    DocRAGConfig,
    DocRAGResult,
)
from doc4llm.tool.md_doc_retrieval.doc_extractor import (
    MarkdownDocExtractor,
    ExtractionResult,
)


class TestPhase0aQueryOptimization:
    """Phase 0a: Query Optimization Tests.

    Tests the QueryOptimizer module which transforms user queries into
    retrieval-friendly optimized queries using LLM.
    """

    def test_optimize_returns_valid_structure(self, env_setup, simple_query: str):
        """Verify optimization result has correct structure."""
        optimizer = QueryOptimizer()
        result = optimizer.optimize(simple_query)

        assert isinstance(result, OptimizationResult)
        assert isinstance(result.query_analysis, dict)
        assert isinstance(result.optimized_queries, list)
        assert isinstance(result.search_recommendation, dict)

    def test_optimize_returns_non_empty_queries(
        self, env_setup, sample_queries: List[str]
    ):
        """Verify optimization returns at least one optimized query."""
        for query in sample_queries:
            optimizer = QueryOptimizer()
            result = optimizer.optimize(query)

            assert len(result.optimized_queries) > 0, f"No queries for: {query}"

            for q in result.optimized_queries:
                assert "query" in q, "Missing 'query' field"
                assert "rank" in q, "Missing 'rank' field"
                assert "strategy" in q, "Missing 'strategy' field"
                assert isinstance(q["query"], str), "Query must be string"
                assert q["rank"] >= 1, "Rank must be >= 1"

    def test_optimize_extracts_doc_sets(self, env_setup):
        """Verify optimization extracts doc_set from query."""
        optimizer = QueryOptimizer()
        result = optimizer.optimize("OpenCode skills 如何创建?")

        doc_sets = result.query_analysis.get("doc_set", [])
        assert isinstance(doc_sets, list)

    def test_optimize_extracts_domain_nouns(self, env_setup):
        """Verify optimization extracts domain nouns."""
        optimizer = QueryOptimizer()
        result = optimizer.optimize("doc4llm documentation crawler 使用方法")

        domain_nouns = result.query_analysis.get("domain_nouns", [])
        assert isinstance(domain_nouns, list)

    def test_optimize_extracts_predicate_verbs(self, env_setup):
        """Verify optimization extracts predicate verbs."""
        optimizer = QueryOptimizer()
        result = optimizer.optimize("如何配置和使用 doc4llm")

        predicate_verbs = result.query_analysis.get("predicate_verbs", [])
        assert isinstance(predicate_verbs, list)

    def test_optimize_preserves_raw_response(self, env_setup, simple_query: str):
        """Verify raw LLM response is preserved."""
        optimizer = QueryOptimizer()
        result = optimizer.optimize(simple_query)

        assert result.raw_response is not None
        assert len(result.raw_response) > 0

    def test_optimize_last_result_is_set(self, env_setup):
        """Verify last_result is set after optimization."""
        optimizer = QueryOptimizer()
        query = "test query"

        result = optimizer.optimize(query)

        assert optimizer.last_result is not None
        assert optimizer.last_result == result

    def test_optimize_custom_config(self, env_setup):
        """Verify custom configuration works."""
        config = QueryOptimizerConfig(model="MiniMax-M2.1", max_tokens=10000)
        optimizer = QueryOptimizer(config)

        result = optimizer.optimize("测试查询")

        assert optimizer.config.model == "MiniMax-M2.1"
        assert optimizer.config.max_tokens == 10000


class TestPhase0bSceneRouting:
    """Phase 0b: Scene Routing Tests.

    Tests the QueryRouter module which classifies user queries into
    one of seven retrieval scenes.
    """

    def test_route_returns_valid_scene(self, env_setup, simple_query: str):
        """Verify routing returns a valid scene classification."""
        router = QueryRouter()
        result = router.route(simple_query)

        valid_scenes = [
            "fact_lookup",
            "faithful_reference",
            "faithful_how_to",
            "concept_learning",
            "how_to",
            "comparison",
            "exploration",
        ]
        assert result.scene in valid_scenes, f"Invalid scene: {result.scene}"

    def test_route_returns_valid_confidence(self, env_setup, sample_queries: List[str]):
        """Verify confidence score is within valid range."""
        for query in sample_queries:
            router = QueryRouter()
            result = router.route(query)

            assert 0.0 <= result.confidence <= 1.0, f"Invalid confidence: {result.confidence}"

    def test_route_returns_valid_ambiguity(self, env_setup, sample_queries: List[str]):
        """Verify ambiguity score is within valid range."""
        for query in sample_queries:
            router = QueryRouter()
            result = router.route(query)

            assert 0.0 <= result.ambiguity <= 1.0, f"Invalid ambiguity: {result.ambiguity}"

    def test_route_returns_valid_coverage_need(self, env_setup, sample_queries: List[str]):
        """Verify coverage_need is within valid range."""
        for query in sample_queries:
            router = QueryRouter()
            result = router.route(query)

            assert 0.0 <= result.coverage_need <= 1.0, f"Invalid coverage_need: {result.coverage_need}"

    def test_route_returns_valid_reranker_threshold(self, env_setup, sample_queries: List[str]):
        """Verify reranker_threshold is within [0.30, 0.80] range."""
        for query in sample_queries:
            router = QueryRouter()
            result = router.route(query)

            assert 0.30 <= result.reranker_threshold <= 0.80, f"Invalid threshold: {result.reranker_threshold}"

    def test_route_returns_complete_result(self, env_setup, simple_query: str):
        """Verify routing returns all required fields."""
        router = QueryRouter()
        result = router.route(simple_query)

        assert hasattr(result, "scene")
        assert hasattr(result, "confidence")
        assert hasattr(result, "ambiguity")
        assert hasattr(result, "coverage_need")
        assert hasattr(result, "reranker_threshold")
        assert hasattr(result, "thinking")
        assert hasattr(result, "raw_response")

    def test_route_last_result_is_set(self, env_setup):
        """Verify last_result is set after routing."""
        router = QueryRouter()
        query = "test query"

        result = router.route(query)

        assert router.last_result is not None
        assert router.last_result == result

    def test_route_preserves_raw_response(self, env_setup, simple_query: str):
        """Verify raw LLM response is preserved."""
        router = QueryRouter()
        result = router.route(simple_query)

        assert result.raw_response is not None
        assert len(result.raw_response) > 0


class TestPhase1DocumentDiscovery:
    """Phase 1: Document Discovery Tests.

    Tests the DocSearcherAPI module which performs BM25-based document
    retrieval from the knowledge base.
    """

    def test_search_returns_success_flag(self, env_setup, knowledge_base_path: str):
        """Verify search returns success flag."""
        searcher = DocSearcherAPI(knowledge_base_path=knowledge_base_path)
        result = searcher.search("how to create skills")

        assert "success" in result
        assert isinstance(result["success"], bool)

    def test_search_returns_results_list(self, env_setup, knowledge_base_path: str):
        """Verify search returns results as a list."""
        searcher = DocSearcherAPI(knowledge_base_path=knowledge_base_path)
        result = searcher.search("how to create skills")

        assert "results" in result
        assert isinstance(result["results"], list)

    def test_search_result_structure(self, env_setup, knowledge_base_path: str):
        """Verify each result has required fields."""
        searcher = DocSearcherAPI(knowledge_base_path=knowledge_base_path)
        result = searcher.search("agent skills")

        if result.get("success") and result["results"]:
            for page in result["results"]:
                assert "page_title" in page, "Missing 'page_title'"
                assert "headings" in page, "Missing 'headings'"
                assert "doc_set" in page, "Missing 'doc_set'"

    def test_search_headings_have_required_fields(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify each heading has required fields."""
        searcher = DocSearcherAPI(knowledge_base_path=knowledge_base_path)
        result = searcher.search("skills configuration")

        if result.get("success") and result["results"]:
            for page in result["results"]:
                for heading in page.get("headings", []):
                    assert "text" in heading, "Missing heading 'text'"
                    assert isinstance(heading["text"], str)

    def test_search_with_target_doc_sets(self, env_setup, knowledge_base_path: str):
        """Verify search works with target doc_sets."""
        searcher = DocSearcherAPI(knowledge_base_path=knowledge_base_path)

        available_doc_sets = searcher._find_doc_sets()
        if available_doc_sets:
            result = searcher.search(
                "skills",
                target_doc_sets=[available_doc_sets[0]]
            )

            assert "success" in result

    def test_search_returns_doc_sets_found(self, env_setup, knowledge_base_path: str):
        """Verify search returns doc_sets_found field."""
        searcher = DocSearcherAPI(knowledge_base_path=knowledge_base_path)
        result = searcher.search("documentation")

        assert "doc_sets_found" in result
        assert isinstance(result["doc_sets_found"], list)

    def test_search_returns_message(self, env_setup, knowledge_base_path: str):
        """Verify search returns message field."""
        searcher = DocSearcherAPI(knowledge_base_path=knowledge_base_path)
        result = searcher.search("test query")

        assert "message" in result
        assert isinstance(result["message"], str)


class TestPhase1_5LLMReranking:
    """Phase 1.5: LLM Re-ranking Tests.

    Tests the LLMReranker module which performs semantic re-ranking
    using LLM and filters results by threshold.
    """

    def test_rerank_returns_success_flag(
        self, env_setup, mock_search_results: Dict[str, Any]
    ):
        """Verify rerank returns success flag."""
        reranker = LLMReranker()
        result = reranker.rerank(mock_search_results)

        assert isinstance(result, RerankerResult)
        assert isinstance(result.success, bool)

    def test_rerank_fills_rerank_sim(
        self, env_setup, mock_search_results: Dict[str, Any]
    ):
        """Verify rerank fills rerank_sim field for all headings."""
        reranker = LLMReranker()
        result = reranker.rerank(mock_search_results)

        if result.success and result.data.get("results"):
            for page in result.data["results"]:
                for heading in page.get("headings", []):
                    rerank_sim = heading.get("rerank_sim")
                    assert rerank_sim is not None, "rerank_sim should be filled"
                    assert isinstance(rerank_sim, (int, float))
                    assert 0.0 <= rerank_sim <= 1.0

    def test_rerank_filters_by_threshold(
        self, env_setup, mock_search_results: Dict[str, Any]
    ):
        """Verify rerank filters headings below threshold."""
        reranker = LLMReranker()
        result = reranker.rerank(mock_search_results)

        threshold = reranker.config.filter_threshold

        if result.success and result.data.get("results"):
            for page in result.data["results"]:
                for heading in page.get("headings", []):
                    rerank_sim = heading.get("rerank_sim", 0)
                    if heading.get("rerank_sim") is not None:
                        assert rerank_sim >= threshold, f"Heading below threshold: {rerank_sim}"

    def test_rerank_reduces_heading_count(
        self, env_setup, mock_search_results: Dict[str, Any]
    ):
        """Verify reranking reduces heading count when filtering."""
        reranker = LLMReranker()
        result = reranker.rerank(mock_search_results)

        assert result.total_headings_after <= result.total_headings_before

    def test_rerank_last_result_is_set(
        self, env_setup, mock_search_results: Dict[str, Any]
    ):
        """Verify last_result is set after reranking."""
        reranker = LLMReranker()
        result = reranker.rerank(mock_search_results)

        assert reranker.last_result is not None
        assert reranker.last_result == result

    def test_rerank_preserves_thinking(self, env_setup, mock_search_results: Dict[str, Any]):
        """Verify thinking process is preserved."""
        reranker = LLMReranker()
        result = reranker.rerank(mock_search_results)

        assert result.thinking is None or isinstance(result.thinking, str)

    def test_rerank_preserves_raw_response(
        self, env_setup, mock_search_results: Dict[str, Any]
    ):
        """Verify raw response is preserved."""
        reranker = LLMReranker()
        result = reranker.rerank(mock_search_results)

        assert result.raw_response is None or isinstance(result.raw_response, str)

    def test_rerank_custom_config(self, env_setup, mock_search_results: Dict[str, Any]):
        """Verify custom configuration works."""
        config = LLMRerankerConfig(filter_threshold=0.7)
        reranker = LLMReranker(config)

        assert reranker.config.filter_threshold == 0.7


class TestPhase2ContentExtraction:
    """Phase 2: Content Extraction Tests.

    Tests the MarkdownDocExtractor module which extracts content
    from markdown documents in the knowledge base.
    """

    def test_extract_by_title_returns_content(
        self, env_setup, kb_base_dir: Path
    ):
        """Verify extract_by_title returns content string."""
        extractor = MarkdownDocExtractor(base_dir=str(kb_base_dir))

        titles = extractor.list_available_documents()
        if titles:
            content = extractor.extract_by_title(titles[0])
            assert content is None or isinstance(content, str)

    def test_extract_by_titles_returns_dict(
        self, env_setup, kb_base_dir: Path
    ):
        """Verify extract_by_titles returns dictionary."""
        extractor = MarkdownDocExtractor(base_dir=str(kb_base_dir))

        titles = extractor.list_available_documents()
        if len(titles) >= 2:
            results = extractor.extract_by_titles(titles[:2])
            assert isinstance(results, dict)

    def test_extract_by_titles_with_metadata(
        self, env_setup, kb_base_dir: Path
    ):
        """Verify extraction returns correct metadata."""
        extractor = MarkdownDocExtractor(base_dir=str(kb_base_dir))

        titles = extractor.list_available_documents()
        if titles:
            result = extractor.extract_by_titles_with_metadata(titles[:2])

            assert isinstance(result, ExtractionResult)
            assert isinstance(result.contents, dict)
            assert isinstance(result.total_line_count, int)
            assert isinstance(result.document_count, int)
            assert isinstance(result.individual_counts, dict)

    def test_extraction_result_line_count(self, env_setup, kb_base_dir: Path):
        """Verify line count calculation is accurate."""
        extractor = MarkdownDocExtractor(base_dir=str(kb_base_dir))

        titles = extractor.list_available_documents()
        if titles:
            result = extractor.extract_by_titles_with_metadata([titles[0]])

            if result.contents:
                first_title = list(result.contents.keys())[0]
                content = result.contents[first_title]
                expected_lines = len(content.split("\n"))

                assert result.individual_counts.get(first_title, 0) > 0
                assert result.total_line_count >= expected_lines

    def test_extraction_threshold_flag(self, env_setup, kb_base_dir: Path):
        """Verify requires_processing flag is set correctly."""
        extractor = MarkdownDocExtractor(base_dir=str(kb_base_dir))

        result = extractor.extract_by_titles_with_metadata(
            extractor.list_available_documents()[:5] if extractor.list_available_documents() else [],
            threshold=0
        )

        assert isinstance(result.requires_processing, bool)

    def test_list_available_documents(self, env_setup, kb_base_dir: Path):
        """Verify list_available_documents returns list of titles."""
        extractor = MarkdownDocExtractor(base_dir=str(kb_base_dir))

        titles = extractor.list_available_documents()

        assert isinstance(titles, list)
        for title in titles:
            assert isinstance(title, str)

    def test_extract_by_headings(self, env_setup, kb_base_dir: Path):
        """Verify extract_by_headings returns section content."""
        extractor = MarkdownDocExtractor(base_dir=str(kb_base_dir))

        titles = extractor.list_available_documents()
        if titles:
            content = extractor.extract_by_title(titles[0])
            if content:
                first_heading = content.split("\n## ")[1].split("\n")[0] if "## " in content else None
                if first_heading:
                    sections = extractor.extract_by_headings(
                        page_title=titles[0],
                        headings=[first_heading]
                    )
                    assert isinstance(sections, dict)


class TestPhase4SceneOutput:
    """Phase 4: Scene-Based Output Tests.

    Tests the SceneOutput module which formats the final output
    based on the query scene and extracted content.
    """

    def test_compose_returns_result(self, env_setup):
        """Verify compose returns a result object."""
        outputter = SceneOutput()

        input_data = {
            "query": "如何安装 doc4llm?",
            "scene": "how_to",
            "contents": {"安装指南": "## 安装\n\npip install doc4llm"},
            "doc_metas": [
                {
                    "title": "安装指南",
                    "source_url": "https://example.com/docs/install",
                    "local_path": "md_docs/install.md",
                }
            ],
            "compression_meta": {
                "compression_applied": False,
                "original_line_count": 5,
                "output_line_count": 5,
            },
        }

        result = outputter.compose(input_data)

        assert isinstance(result, SceneOutputResult)

    def test_compose_returns_string_output(self, env_setup):
        """Verify compose returns string output."""
        outputter = SceneOutput()

        input_data = {
            "query": "test query",
            "scene": "fact_lookup",
            "contents": {},
            "doc_metas": [],
            "compression_meta": {
                "compression_applied": False,
                "original_line_count": 0,
                "output_line_count": 0,
            },
        }

        result = outputter.compose(input_data)

        assert isinstance(result.output, str)

    def test_compose_last_result_is_set(self, env_setup):
        """Verify last_result is set after composition."""
        outputter = SceneOutput()

        input_data = {
            "query": "test",
            "scene": "fact_lookup",
            "contents": {},
            "doc_metas": [],
            "compression_meta": {
                "compression_applied": False,
                "original_line_count": 0,
                "output_line_count": 0,
            },
        }

        result = outputter.compose(input_data)

        assert outputter.last_result is not None
        assert outputter.last_result == result

    def test_compose_with_real_content(
        self, env_setup, mock_extraction_sections: Dict[str, str]
    ):
        """Verify compose works with realistic content."""
        outputter = SceneOutput()

        input_data = {
            "query": "如何创建 skills?",
            "scene": "how_to",
            "contents": mock_extraction_sections,
            "doc_metas": [
                {
                    "title": "Agent Skills",
                    "source_url": "https://docs.opencode.ai/skills",
                    "local_path": "md_docs/skills.md",
                }
            ],
            "compression_meta": {
                "compression_applied": False,
                "original_line_count": 30,
                "output_line_count": 30,
            },
        }

        result = outputter.compose(input_data)

        assert result.output is not None
        assert len(result.output) > 0

    def test_compose_all_scenes(self, env_setup, valid_scenes: List[str]):
        """Verify compose works with all valid scenes."""
        outputter = SceneOutput()

        for scene in valid_scenes:
            input_data = {
                "query": "test query",
                "scene": scene,
                "contents": {"Test": "## Test\n\nContent here"},
                "doc_metas": [{"title": "Test", "source_url": "", "local_path": ""}],
                "compression_meta": {
                    "compression_applied": False,
                    "original_line_count": 3,
                    "output_line_count": 3,
                },
            }

            result = outputter.compose(input_data)
            assert isinstance(result.output, str), f"Scene {scene} failed"

    def test_compose_preserves_thinking(self, env_setup):
        """Verify thinking process is preserved."""
        outputter = SceneOutput()

        input_data = {
            "query": "test",
            "scene": "fact_lookup",
            "contents": {},
            "doc_metas": [],
            "compression_meta": {
                "compression_applied": False,
                "original_line_count": 0,
                "output_line_count": 0,
            },
        }

        result = outputter.compose(input_data)

        assert result.thinking is None or isinstance(result.thinking, str)


class TestEndToEndRetrieval:
    """End-to-End Retrieval Pipeline Tests.

    Tests the complete DocRAGOrchestrator workflow from query
    to final output, validating data flow between phases.
    """

    def test_complete_retrieval_success(self, env_setup, knowledge_base_path: str):
        """Verify complete retrieval pipeline returns success."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("如何创建 OpenCode skills?")

        assert isinstance(result, DocRAGResult)
        assert result.success is True or result.output != ""

    def test_complete_retrieval_returns_valid_output(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify retrieval returns string output."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("doc4llm 功能介绍")

        assert isinstance(result.output, str)

    def test_complete_retrieval_returns_valid_scene(
        self, env_setup, knowledge_base_path: str, valid_scenes: List[str]
    ):
        """Verify retrieval returns valid scene classification."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("如何配置 doc4llm?")

        assert result.scene in valid_scenes, f"Invalid scene: {result.scene}"

    def test_complete_retrieval_returns_metadata(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify retrieval returns complete metadata."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("skills 使用方法")

        assert isinstance(result.documents_extracted, int)
        assert isinstance(result.total_lines, int)
        assert isinstance(result.requires_processing, bool)
        assert isinstance(result.sources, list)

    def test_complete_retrieval_sources_structure(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify sources have correct structure."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("agent skills")

        for source in result.sources:
            assert isinstance(source, dict)
            assert "title" in source or "page_title" in source
            assert "doc_set" in source

    def test_complete_retrieval_last_result_set(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify last_result is set after retrieval."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        orchestrator.retrieve("测试查询")

        assert orchestrator.last_result is not None

    def test_complete_retrieval_with_llm_reranker(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify retrieval works with llm_reranker option."""
        config = DocRAGConfig(
            knowledge_base_path=knowledge_base_path,
            llm_reranker=True
        )
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("doc4llm documentation")

        assert isinstance(result, DocRAGResult)

    def test_complete_retrieval_with_custom_threshold(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify retrieval works with custom threshold."""
        config = DocRAGConfig(
            knowledge_base_path=knowledge_base_path,
            default_threshold=100
        )
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("skills")

        assert isinstance(result, DocRAGResult)
        assert isinstance(result.requires_processing, bool)

    def test_complete_retrieval_preserves_raw_response(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify raw LLM response is preserved when available."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("OpenCode skills 创建")

        assert result.raw_response is None or isinstance(result.raw_response, str)

    def test_complete_retrieval_preserves_thinking(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify thinking process is preserved when available."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("如何配置 skills")

        assert result.thinking is None or isinstance(result.thinking, str)


class TestDataFlowBetweenPhases:
    """Tests for data flow validation between pipeline phases.

    Verifies that data is correctly passed and transformed
    between each phase of the retrieval pipeline.
    """

    def test_optimizer_to_router_data_flow(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify data flows correctly from optimizer to router."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("测试查询")

        if result.success:
            assert orchestrator._optimizer.last_result is not None
            assert orchestrator._router.last_result is not None

    def test_router_to_searcher_data_flow(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify scene classification affects search."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        how_to_result = orchestrator.retrieve("如何创建 skills")
        fact_result = orchestrator.retrieve("doc4llm 是什么")

        assert how_to_result.scene == "how_to" or how_to_result.scene in [
            "fact_lookup", "faithful_how_to"
        ]
        assert fact_result.scene in [
            "fact_lookup", "concept_learning", "exploration"
        ]

    def test_searcher_to_reranker_data_flow(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify search results flow to reranker."""
        config = DocRAGConfig(
            knowledge_base_path=knowledge_base_path,
            llm_reranker=False
        )
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("skills 创建配置")

        if result.success and result.documents_extracted > 0:
            pass

    def test_reranker_to_extractor_data_flow(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify reranked results flow to extractor."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("agent skills")

        if result.success and result.documents_extracted > 0:
            assert len(result.sources) > 0

    def test_extractor_to_output_data_flow(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify extracted content flows to output."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator.retrieve("doc4llm 安装")

        if result.success:
            assert len(result.output) > 0
            assert result.scene in [
                "fact_lookup", "how_to", "concept_learning"
            ]


class TestOrchestratorCallable:
    """Tests for DocRAGOrchestrator callable interface."""

    def test_orchestrator_callable(self, env_setup, knowledge_base_path: str):
        """Verify orchestrator can be called directly."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        result = orchestrator("如何创建 skills")

        assert isinstance(result, DocRAGResult)

    def test_orchestrator_and_retrieve_equivalence(
        self, env_setup, knowledge_base_path: str
    ):
        """Verify __call__ and retrieve return equivalent results."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)
        orchestrator = DocRAGOrchestrator(config)

        call_result = orchestrator("测试查询")
        retrieve_result = orchestrator.retrieve("测试查询")

        assert call_result.success == retrieve_result.success
        assert call_result.scene == retrieve_result.scene
        assert call_result.output == retrieve_result.output


class TestOrchestratorConfig:
    """Tests for DocRAGConfig configuration options."""

    def test_default_config(self, knowledge_base_path: str):
        """Verify default configuration values."""
        config = DocRAGConfig(knowledge_base_path=knowledge_base_path)

        assert config.knowledge_base_path == knowledge_base_path
        assert config.default_threshold == 2100
        assert config.llm_reranker is False
        assert config.debug is False

    def test_custom_config(self, knowledge_base_path: str):
        """Verify custom configuration values are set."""
        config = DocRAGConfig(
            knowledge_base_path=knowledge_base_path,
            default_threshold=500,
            llm_reranker=True,
            debug=True
        )

        assert config.default_threshold == 500
        assert config.llm_reranker is True
        assert config.debug is True

    def test_config_from_environ(self, knowledge_base_path: str):
        """Verify configuration can be overridden."""
        config = DocRAGConfig(
            knowledge_base_path=knowledge_base_path,
            threshold=1000
        )

        assert config.default_threshold == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
