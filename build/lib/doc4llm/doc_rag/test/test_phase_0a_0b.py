"""
Test Phase 0a (QueryOptimizer) and Phase 0b (QueryRouter)

Tests for data input/output parsing results of QueryOptimizer and QueryRouter.

IMPORTANT: These tests will actually call LLM API and require valid API key configuration.
"""

import pytest
from typing import Dict, Any, List

from doc4llm.doc_rag.query_optimizer import QueryOptimizer, QueryOptimizerConfig, OptimizationResult
from doc4llm.doc_rag.query_router import QueryRouter, QueryRouterConfig, RoutingResult
from doc4llm.doc_rag.params_parser import ParamsParserAPI


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def optimizer() -> QueryOptimizer:
    """Create a QueryOptimizer instance for testing."""
    config = QueryOptimizerConfig(
        model="MiniMax-M2.1",
        max_tokens=20000,
        temperature=0.1
    )
    return QueryOptimizer(config)


@pytest.fixture
def router() -> QueryRouter:
    """Create a QueryRouter instance for testing."""
    config = QueryRouterConfig(
        model="MiniMax-M2.1",
        max_tokens=20000,
        temperature=0.1
    )
    return QueryRouter(config)


@pytest.fixture
def params_parser() -> ParamsParserAPI:
    """Create a ParamsParserAPI instance for testing."""
    return ParamsParserAPI(validate=True)


@pytest.fixture
def sample_optimizer_output() -> Dict[str, Any]:
    """Sample optimizer output for testing parser."""
    return {
        "query_analysis": {
            "original": "如何创建 opencode skills?",
            "language": "zh",
            "doc_set": ["opencode"],
            "domain_nouns": ["opencode", "skills", "skill"],
            "predicate_verbs": ["创建", "create", "make", "develop"]
        },
        "optimized_queries": [
            {
                "rank": 1,
                "query": "如何创建 OpenCode skills",
                "strategy": "direct_translation"
            },
            {
                "rank": 2,
                "query": "how to create OpenCode skills step by step",
                "strategy": "translation_expansion"
            },
            {
                "rank": 3,
                "query": "OpenCode skill development tutorial",
                "strategy": "concept_expansion"
            }
        ],
        "search_recommendation": {
            "online_suggested": False,
            "reason": "Local documentation is sufficient"
        }
    }


# =============================================================================
# QueryOptimizer (Phase 0a) Tests
# =============================================================================

class TestQueryOptimizer:
    """Test cases for QueryOptimizer (Phase 0a)."""

    def test_query_optimizer_basic(self, optimizer: QueryOptimizer):
        """Test basic query optimization functionality (actual LLM API call)."""
        query = "如何创建 opencode skills?"

        result = optimizer.optimize(query)

        # Verify result structure
        assert isinstance(result, OptimizationResult)
        assert hasattr(result, 'query_analysis')
        assert hasattr(result, 'optimized_queries')
        assert hasattr(result, 'search_recommendation')

        # Verify query_analysis contains required fields
        query_analysis = result.query_analysis
        assert 'original' in query_analysis
        assert 'language' in query_analysis
        assert 'doc_set' in query_analysis
        assert 'domain_nouns' in query_analysis
        assert 'predicate_verbs' in query_analysis

        # Verify optimized_queries is non-empty
        assert len(result.optimized_queries) > 0

        # Verify queries are sorted by rank
        ranks = [q.get('rank', 999) for q in result.optimized_queries]
        assert ranks == sorted(ranks), "Optimized queries should be sorted by rank"

        print(f"Original Query: {query_analysis.get('original')}")
        print(f"Language: {query_analysis.get('language')}")
        print(f"Doc Set: {query_analysis.get('doc_set', [])}")
        print(f"Domain Nouns: {query_analysis.get('domain_nouns', [])}")
        print(f"Predicate Verbs: {query_analysis.get('predicate_verbs', [])}")

    def test_query_optimizer_english_query(self, optimizer: QueryOptimizer):
        """Test query optimization with English query (actual LLM API call)."""
        query = "how to install doc4llm"

        result = optimizer.optimize(query)

        assert isinstance(result, OptimizationResult)
        assert len(result.optimized_queries) > 0
        assert 'original' in result.query_analysis

        # English query should have language 'en'
        assert result.query_analysis.get('language') in ['en', 'EN', 'english']

    def test_query_optimizer_comparison_query(self, optimizer: QueryOptimizer):
        """Test query optimization with comparison query (actual LLM API call)."""
        query = "Claude Code vs OpenCode comparison"

        result = optimizer.optimize(query)

        assert isinstance(result, OptimizationResult)
        assert len(result.optimized_queries) > 0

    def test_entity_extraction(self, optimizer: QueryOptimizer):
        """Test domain_nouns and predicate_verbs extraction (actual LLM API call)."""
        query = "如何创建 opencode skills?"

        result = optimizer.optimize(query)

        # Verify entity extraction
        domain_nouns = result.query_analysis.get('domain_nouns', [])
        predicate_verbs = result.query_analysis.get('predicate_verbs', [])

        # Should extract domain nouns (technical terms, product names)
        assert len(domain_nouns) > 0, "Should extract domain nouns"

        # Should extract predicate verbs (action words)
        assert len(predicate_verbs) > 0, "Should extract predicate verbs"

        # Check for expected entities based on query
        nouns_text = ' '.join(domain_nouns).lower()
        assert 'opencode' in nouns_text or 'skill' in nouns_text, \
            "Should extract 'opencode' or 'skill' as domain noun"

    def test_query_optimizer_async(self, optimizer: QueryOptimizer):
        """Test async optimize_async interface (actual LLM API call)."""
        import asyncio

        query = "how to install doc4llm"

        # Run async function
        result = asyncio.run(optimizer.optimize_async(query))

        assert isinstance(result, OptimizationResult)
        assert len(result.optimized_queries) > 0

    def test_query_optimizer_callable(self, optimizer: QueryOptimizer):
        """Test that optimizer is callable (actual LLM API call)."""
        query = "doc4llm 支持哪些平台?"

        # Use __call__ method
        result = optimizer(query)

        assert isinstance(result, OptimizationResult)
        assert len(result.optimized_queries) > 0


# =============================================================================
# QueryRouter (Phase 0b) Tests
# =============================================================================

class TestQueryRouter:
    """Test cases for QueryRouter (Phase 0b)."""

    # Valid scene types
    VALID_SCENES = [
        'fact_lookup',
        'faithful_reference',
        'faithful_how_to',
        'concept_learning',
        'how_to',
        'comparison',
        'exploration'
    ]

    def test_query_router_fact_lookup(self, router: QueryRouter):
        """Test fact_lookup scene classification (actual LLM API call)."""
        query = "What is the version number?"

        result = router.route(query)

        assert isinstance(result, RoutingResult)
        assert hasattr(result, 'scene')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'ambiguity')
        assert hasattr(result, 'coverage_need')
        assert hasattr(result, 'reranker_threshold')

        # Verify scene is valid
        assert result.scene in self.VALID_SCENES, \
            f"Scene should be one of {self.VALID_SCENES}, got '{result.scene}'"

        # Verify confidence, ambiguity, coverage_need are in [0.0, 1.0]
        assert 0.0 <= result.confidence <= 1.0
        assert 0.0 <= result.ambiguity <= 1.0
        assert 0.0 <= result.coverage_need <= 1.0

        # Verify reranker_threshold is in [0.30, 0.80]
        assert 0.30 <= result.reranker_threshold <= 0.80

    def test_query_router_faithful_reference(self, router: QueryRouter):
        """Test faithful_reference scene classification (actual LLM API call)."""
        query = "According to the docs, how to configure API key?"

        result = router.route(query)

        assert isinstance(result, RoutingResult)
        assert result.scene in self.VALID_SCENES

    def test_query_router_how_to(self, router: QueryRouter):
        """Test how_to scene classification (actual LLM API call)."""
        query = "How to install doc4llm step by step?"

        result = router.route(query)

        assert isinstance(result, RoutingResult)
        assert result.scene in self.VALID_SCENES
        assert 0.0 <= result.confidence <= 1.0

    def test_query_router_concept_learning(self, router: QueryRouter):
        """Test concept_learning scene classification (actual LLM API call)."""
        query = "Explain what is Claude Code architecture"

        result = router.route(query)

        assert isinstance(result, RoutingResult)
        assert result.scene in self.VALID_SCENES

    def test_query_router_comparison(self, router: QueryRouter):
        """Test comparison scene classification (actual LLM API call)."""
        query = "Compare OpenCode vs Claude Code features"

        result = router.route(query)

        assert isinstance(result, RoutingResult)
        assert result.scene in self.VALID_SCENES

    def test_query_router_exploration(self, router: QueryRouter):
        """Test exploration scene classification (actual LLM API call)."""
        query = "Research the latest AI coding tools trends"

        result = router.route(query)

        assert isinstance(result, RoutingResult)
        assert result.scene in self.VALID_SCENES

    def test_query_router_all_scenes_covered(self, router: QueryRouter):
        """Test that all seven scenes can be classified (actual LLM API call)."""
        test_cases = [
            ("What is the version number?", 'fact_lookup'),
            ("According to the docs, how to configure API key?", 'faithful_reference'),
            ("How to install doc4llm step by step?", 'how_to'),
            ("Explain what is Claude Code architecture", 'concept_learning'),
            ("Compare OpenCode vs Claude Code features", 'comparison'),
            ("Research the latest AI coding tools trends", 'exploration'),
        ]

        covered_scenes = set()

        for query, expected_hint in test_cases:
            result = router.route(query)
            covered_scenes.add(result.scene)

        # Verify we can classify different scene types
        assert len(covered_scenes) >= 3, \
            f"Should be able to classify multiple scene types, got: {covered_scenes}"

    def test_query_router_async(self, router: QueryRouter):
        """Test async route_async interface (actual LLM API call)."""
        import asyncio

        query = "how to install doc4llm"

        # Run async function
        result = asyncio.run(router.route_async(query))

        assert isinstance(result, RoutingResult)
        assert result.scene in self.VALID_SCENES

    def test_query_router_callable(self, router: QueryRouter):
        """Test that router is callable (actual LLM API call)."""
        query = "doc4llm 支持哪些平台?"

        # Use __call__ method
        result = router(query)

        assert isinstance(result, RoutingResult)
        assert result.scene in self.VALID_SCENES


# =============================================================================
# ParamsParserAPI Tests - Using Real Phase Outputs
# =============================================================================

class TestParamsParserAPI:
    """Test cases for ParamsParserAPI with real phase outputs."""

    def test_phase_0a_to_phase1_parsing(
        self,
        optimizer: QueryOptimizer,
        params_parser: ParamsParserAPI
    ):
        """Use real optimizer output to test Phase 1 config conversion."""
        query = "如何创建 opencode skills?"

        # Get real optimizer output
        optimizer_result = optimizer.optimize(query)

        # Convert to dict format for parser
        output = {
            "query_analysis": optimizer_result.query_analysis,
            "optimized_queries": optimizer_result.optimized_queries,
            "search_recommendation": optimizer_result.search_recommendation
        }

        # Parse Phase 0a -> Phase 1
        response = params_parser.parse("0a", "1", output)

        assert response.status == "success", f"Parsing failed: {response.errors}"
        assert response.config is not None

        # Verify config contains expected fields
        config = response.config
        assert "query" in config
        assert "doc_sets" in config
        assert "domain_nouns" in config
        assert "predicate_verbs" in config

        # Verify query is a list
        assert isinstance(config["query"], list)
        assert len(config["query"]) > 0

    def test_phase_0b_to_phase1_parsing(
        self,
        router: QueryRouter,
        params_parser: ParamsParserAPI
    ):
        """Use real router output to test Phase 1 config conversion."""
        query = "How to install doc4llm step by step?"

        # Get real router output
        router_result = router.route(query)

        # Convert to dict format for parser
        output = {
            "scene": router_result.scene,
            "confidence": router_result.confidence,
            "ambiguity": router_result.ambiguity,
            "coverage_need": router_result.coverage_need,
            "reranker_threshold": router_result.reranker_threshold
        }

        # Parse Phase 0b -> Phase 1
        response = params_parser.parse("0b", "1", output)

        assert response.status == "success", f"Parsing failed: {response.errors}"
        assert response.config is not None

        # Verify config contains expected fields
        config = response.config
        assert "reranker_threshold" in config
        assert "scene" in config

    def test_phase_0a_plus_0b_merge(
        self,
        optimizer: QueryOptimizer,
        router: QueryRouter,
        params_parser: ParamsParserAPI
    ):
        """Test 0a+0b merge output."""
        query = "如何创建 opencode skills?"

        # Get outputs from both phases
        optimizer_result = optimizer.optimize(query)
        router_result = router.route(query)

        # Prepare multi-phase input
        phases = [
            {
                "phase": "0a",
                "output": {
                    "query_analysis": optimizer_result.query_analysis,
                    "optimized_queries": optimizer_result.optimized_queries,
                    "search_recommendation": optimizer_result.search_recommendation
                }
            },
            {
                "phase": "0b",
                "output": {
                    "scene": router_result.scene,
                    "confidence": router_result.confidence,
                    "ambiguity": router_result.ambiguity,
                    "coverage_need": router_result.coverage_need,
                    "reranker_threshold": router_result.reranker_threshold
                }
            }
        ]

        # Parse 0a+0b -> Phase 1
        response = params_parser.parse_multi_phase("1", phases)

        assert response.status == "success", f"Parsing failed: {response.errors}"
        assert response.config is not None

        # Verify merged config contains all expected fields
        config = response.config
        assert "query" in config  # From 0a
        assert "doc_sets" in config  # From 0a
        assert "domain_nouns" in config  # From 0a
        assert "predicate_verbs" in config  # From 0a
        assert "reranker_threshold" in config  # From 0b
        assert "scene" in config  # From 0b

    def test_invalid_phase_transition(
        self,
        params_parser: ParamsParserAPI,
        sample_optimizer_output: Dict[str, Any]
    ):
        """Test invalid phase transition."""
        # Invalid: 0a -> 3 (not a valid transition)
        response = params_parser.parse("0a", "3", sample_optimizer_output)

        assert response.status == "failed"
        assert response.errors is not None
        assert len(response.errors) > 0

    def test_0a_0b_merge_missing_phase(
        self,
        params_parser: ParamsParserAPI,
        sample_optimizer_output: Dict[str, Any]
    ):
        """Test 0a+0b merge with missing phase."""
        # Missing 0b output
        phases = [
            {"phase": "0a", "output": sample_optimizer_output}
        ]

        response = params_parser.parse("0a+0b", "1", phases)

        assert response.status == "failed"
        assert response.errors is not None

    def test_0a_0b_merge_invalid_phase(
        self,
        params_parser: ParamsParserAPI,
        sample_optimizer_output: Dict[str, Any]
    ):
        """Test 0a+0b merge with invalid phase in list."""
        phases = [
            {"phase": "0a", "output": sample_optimizer_output},
            {"phase": "invalid", "output": {}}
        ]

        response = params_parser.parse("0a+0b", "1", phases)

        assert response.status == "failed"
        assert response.errors is not None


# =============================================================================
# Parser Factory Tests
# =============================================================================

class TestParserFactory:
    """Test cases for ParserFactory."""

    def test_parser_factory_get_parser_0a_to_1(self):
        """Test getting correct parser for 0a -> 1 transition."""
        from doc4llm.doc_rag.params_parser.parser_factory import ParserFactory
        from doc4llm.doc_rag.params_parser.phase_parser import Phase0aToPhase1Parser

        parser = ParserFactory.get_parser("0a", "1")
        assert isinstance(parser, Phase0aToPhase1Parser)

    def test_parser_factory_get_parser_0b_to_1(self):
        """Test getting correct parser for 0b -> 1 transition."""
        from doc4llm.doc_rag.params_parser.parser_factory import ParserFactory
        from doc4llm.doc_rag.params_parser.phase_parser import Phase0bToPhase1Parser

        parser = ParserFactory.get_parser("0b", "1")
        assert isinstance(parser, Phase0bToPhase1Parser)

    def test_parser_factory_get_parser_0a_0b_to_1(self):
        """Test getting correct parser for 0a+0b -> 1 transition."""
        from doc4llm.doc_rag.params_parser.parser_factory import ParserFactory
        from doc4llm.doc_rag.params_parser.phase_parser import MultiPhaseToPhase1Parser

        parser = ParserFactory.get_parser("0a+0b", "1")
        assert isinstance(parser, MultiPhaseToPhase1Parser)

    def test_parser_factory_invalid_transition(self):
        """Test getting parser for invalid transition."""
        from doc4llm.doc_rag.params_parser.parser_factory import ParserFactory

        with pytest.raises(ValueError) as exc_info:
            ParserFactory.get_parser("0a", "3")

        assert "No parser available" in str(exc_info.value)

    def test_parser_factory_valid_transitions(self):
        """Test valid transitions list."""
        from doc4llm.doc_rag.params_parser.parser_factory import ParserFactory

        valid_transitions = ParserFactory.VALID_TRANSITIONS

        # Should contain expected transitions
        assert ("0a", "1") in valid_transitions
        assert ("0b", "1") in valid_transitions
        assert ("0a+0b", "1") in valid_transitions

    def test_parser_factory_is_valid_transition(self):
        """Test is_valid_transition method."""
        from doc4llm.doc_rag.params_parser.parser_factory import ParserFactory

        assert ParserFactory.is_valid_transition("0a", "1") is True
        assert ParserFactory.is_valid_transition("0b", "1") is True
        assert ParserFactory.is_valid_transition("0a", "3") is False
        assert ParserFactory.is_valid_transition("1", "0a") is False

    def test_parser_factory_get_available_transitions(self):
        """Test get_available_transitions method."""
        from doc4llm.doc_rag.params_parser.parser_factory import ParserFactory

        # Get all transitions
        all_transitions = ParserFactory.get_available_transitions()
        assert len(all_transitions) > 0

        # Get transitions from 0a
        transitions_from_0a = ParserFactory.get_available_transitions("0a")
        assert len(transitions_from_0a) > 0
        assert all(t[0] == "0a" for t in transitions_from_0a)


# =============================================================================
# End-to-End Integration Tests
# =============================================================================

class TestEndToEnd:
    """End-to-end integration tests for Phase 0a + 0b workflow."""

    def test_end_to_end_phase_0a_0b(
        self,
        optimizer: QueryOptimizer,
        router: QueryRouter,
        params_parser: ParamsParserAPI
    ):
        """End-to-end test: complete workflow verification."""
        query = "如何创建 opencode skills?"

        # Step 1: QueryOptimizer -> OptimizationResult
        optimizer_result = optimizer.optimize(query)

        # Step 2: QueryRouter -> RoutingResult
        router_result = router.route(query)

        # Step 3: Merge and parse -> Phase 1 config
        phases = [
            {
                "phase": "0a",
                "output": {
                    "query_analysis": optimizer_result.query_analysis,
                    "optimized_queries": optimizer_result.optimized_queries,
                    "search_recommendation": optimizer_result.search_recommendation
                }
            },
            {
                "phase": "0b",
                "output": {
                    "scene": router_result.scene,
                    "confidence": router_result.confidence,
                    "ambiguity": router_result.ambiguity,
                    "coverage_need": router_result.coverage_need,
                    "reranker_threshold": router_result.reranker_threshold
                }
            }
        ]

        # Parse and get Phase 1 config
        response = params_parser.parse_multi_phase("1", phases)

        assert response.status == "success", f"End-to-end test failed: {response.errors}"
        assert response.config is not None

        # Verify all fields are correctly passed through
        config = response.config

        # From Phase 0a (QueryOptimizer)
        assert "query" in config
        assert "doc_sets" in config
        assert "domain_nouns" in config
        assert "predicate_verbs" in config

        # From Phase 0b (QueryRouter)
        assert "reranker_threshold" in config
        assert "scene" in config

        # Print results for debugging
        print("\n=== End-to-End Test Results ===")
        print(f"Query: {query}")
        print(f"Scene: {router_result.scene}")
        print(f"Confidence: {router_result.confidence}")
        print(f"Optimized Queries: {len(optimizer_result.optimized_queries)}")
        print(f"Doc Sets: {optimizer_result.query_analysis.get('doc_set', [])}")
        print(f"Domain Nouns: {optimizer_result.query_analysis.get('domain_nouns', [])}")

    def test_end_to_end_different_queries(
        self,
        optimizer: QueryOptimizer,
        router: QueryRouter,
        params_parser: ParamsParserAPI
    ):
        """Test end-to-end workflow with different query types."""
        test_queries = [
            "how to install doc4llm",
            "Compare OpenCode vs Claude Code features",
            "What is the version number?",
        ]

        for query in test_queries:
            optimizer_result = optimizer.optimize(query)
            router_result = router.route(query)

            # Quick validation
            assert len(optimizer_result.optimized_queries) > 0
            assert router_result.scene in [
                'fact_lookup', 'faithful_reference', 'faithful_how_to',
                'concept_learning', 'how_to', 'comparison', 'exploration'
            ]


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
