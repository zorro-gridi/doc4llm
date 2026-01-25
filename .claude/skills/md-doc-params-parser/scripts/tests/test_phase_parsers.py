"""Unit tests for md-doc-params-parser."""

import json
import pytest
from pathlib import Path

# Add scripts directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from parser_factory import ParserFactory
from config_schema import validate_schema, get_schema


class TestPhase0aToPhase1Parser:
    """Tests for Phase 0a → Phase 1 parser."""

    def test_basic_conversion(self):
        """Test basic query optimizer to searcher conversion."""
        optimizer_output = {
            "query_analysis": {
                "doc_set": ["OpenCode_Docs@latest"],
                "domain_nouns": ["hooks"],
                "predicate_verbs": ["create"]
            },
            "optimized_queries": [
                {"rank": 1, "query": "create hooks", "strategy": "translation"}
            ]
        }

        result = ParserFactory.parse("0a", "1", optimizer_output)

        assert "query" in result
        assert result["query"] == ["create hooks"]
        assert result["doc_sets"] == "OpenCode_Docs@latest"
        assert result["domain_nouns"] == ["hooks"]
        assert result["predicate_verbs"] == ["create"]

    def test_multiple_queries_sorted_by_rank(self):
        """Test that queries are sorted by rank."""
        optimizer_output = {
            "query_analysis": {
                "doc_set": ["API_Reference@latest"],
                "domain_nouns": [],
                "predicate_verbs": []
            },
            "optimized_queries": [
                {"rank": 3, "query": "third query", "strategy": "original"},
                {"rank": 1, "query": "first query", "strategy": "translation"},
                {"rank": 2, "query": "second query", "strategy": "expansion"}
            ]
        }

        result = ParserFactory.parse("0a", "1", optimizer_output)

        # Result should have queries in rank order
        assert result["query"] == ["first query", "second query", "third query"]

    def test_multiple_doc_sets(self):
        """Test conversion with multiple doc sets."""
        optimizer_output = {
            "query_analysis": {
                "doc_set": ["OpenCode_Docs@latest", "API_Reference@latest"],
                "domain_nouns": [],
                "predicate_verbs": []
            },
            "optimized_queries": []
        }

        result = ParserFactory.parse("0a", "1", optimizer_output)

        assert result["doc_sets"] == "OpenCode_Docs@latest,API_Reference@latest"

    def test_empty_optional_fields(self):
        """Test handling of empty optional fields."""
        optimizer_output = {
            "query_analysis": {
                "doc_set": ["OpenCode_Docs@latest"]
            },
            "optimized_queries": []
        }

        result = ParserFactory.parse("0a", "1", optimizer_output)

        assert result["query"] == []
        assert result["doc_sets"] == "OpenCode_Docs@latest"
        assert result["domain_nouns"] == []
        assert result["predicate_verbs"] == []


class TestPhase0bToPhase1Parser:
    """Tests for Phase 0b → Phase 1 parser."""

    def test_basic_conversion(self):
        """Test basic query router to searcher conversion."""
        router_output = {
            "scene": "api_reference",
            "reranker_threshold": 0.75
        }

        result = ParserFactory.parse("0b", "1", router_output)

        assert result["reranker_threshold"] == 0.75
        assert result["scene"] == "api_reference"

    def test_default_values(self):
        """Test default values when fields are missing."""
        router_output = {}

        result = ParserFactory.parse("0b", "1", router_output)

        assert result["reranker_threshold"] == 0.63
        assert result["scene"] == "fact_lookup"


class TestPhase1ToPhase1_5Parser:
    """Tests for Phase 1 → Phase 1.5 parser."""

    def test_needs_rerank_when_missing_rerank_sim(self):
        """Test that reranking is needed when rerank_sim is null."""
        searcher_output = {
            "success": True,
            "results": [
                {
                    "doc_set": "OpenCode_Docs@latest",
                    "headings": [
                        {"text": "## Create Skills", "rerank_sim": None}
                    ]
                }
            ]
        }

        result = ParserFactory.parse("1", "1.5", searcher_output)

        assert result["needs_rerank"] is True

    def test_no_rerank_when_all_have_rerank_sim(self):
        """Test that reranking is not needed when all have rerank_sim."""
        searcher_output = {
            "success": True,
            "results": [
                {
                    "doc_set": "OpenCode_Docs@latest",
                    "headings": [
                        {"text": "## Create Skills", "rerank_sim": 0.85}
                    ]
                }
            ]
        }

        result = ParserFactory.parse("1", "1.5", searcher_output)

        assert result["needs_rerank"] is False

    def test_no_rerank_when_no_headings(self):
        """Test handling of results with no headings."""
        searcher_output = {
            "success": True,
            "results": []
        }

        result = ParserFactory.parse("1", "1.5", searcher_output)

        assert result["needs_rerank"] is False


class TestPhase1_5ToPhase2Parser:
    """Tests for Phase 1.5 → Phase 2 parser."""

    def test_basic_conversion(self):
        """Test basic reranker to reader conversion."""
        reranker_output = {
            "success": True,
            "reranked_count": 2,
            "results": [
                {
                    "doc_set": "OpenCode_Docs@latest",
                    "page_title": "Agent Skills",
                    "headings": [
                        {"text": "## Create Skills", "rerank_sim": 0.92},
                        {"text": "## Delete Skills", "rerank_sim": 0.85}
                    ]
                }
            ]
        }

        result = ParserFactory.parse("1.5", "2", reranker_output)

        assert len(result["page_titles"]) == 1
        assert result["page_titles"][0]["title"] == "Agent Skills"
        assert result["page_titles"][0]["doc_set"] == "OpenCode_Docs@latest"
        assert result["page_titles"][0]["headings"] == ["## Create Skills", "## Delete Skills"]
        assert result["with_metadata"] is True
        assert result["format"] == "json"

    def test_multiple_results(self):
        """Test conversion with multiple results."""
        reranker_output = {
            "success": True,
            "results": [
                {
                    "doc_set": "OpenCode_Docs@latest",
                    "page_title": "Page 1",
                    "headings": [{"text": "## Heading 1"}]
                },
                {
                    "doc_set": "API_Reference@latest",
                    "page_title": "Page 2",
                    "headings": [{"text": "## Heading 2"}]
                }
            ]
        }

        result = ParserFactory.parse("1.5", "2", reranker_output)

        assert len(result["page_titles"]) == 2


class TestPhase2ToPhase3Parser:
    """Tests for Phase 2 → Phase 3 parser."""

    def test_basic_conversion(self):
        """Test basic reader to processor conversion."""
        reader_output = {
            "success": True,
            "contents": {"OpenCode_Docs@latest": []},
            "total_line_count": 100,
            "requires_processing": True,
            "metadata": {"source": "OpenCode_Docs@latest"}
        }

        result = ParserFactory.parse("2", "3", reader_output)

        assert result["contents"] == reader_output["contents"]
        assert result["line_count"] == 100
        assert result["requires_processing"] is True


class TestPhase3ToPhase4Parser:
    """Tests for Phase 3 → Phase 4 parser."""

    def test_basic_conversion(self):
        """Test basic processor to sence-output conversion."""
        processor_output = {
            "success": True,
            "processed_doc": "# Processed content",
            "compression_applied": True,
            "original_line_count": 100,
            "output_line_count": 30,
            "doc_meta": {"source": "OpenCode_Docs@latest"}
        }

        result = ParserFactory.parse("3", "4", processor_output)

        assert result["processed_doc"] == "# Processed content"
        assert result["compression_meta"]["compression_applied"] is True
        assert result["compression_meta"]["original_line_count"] == 100
        assert result["compression_meta"]["output_line_count"] == 30


class TestParserFactory:
    """Tests for ParserFactory class."""

    def test_valid_transition(self):
        """Test that valid transitions are recognized."""
        assert ParserFactory.is_valid_transition("0a", "1") is True
        assert ParserFactory.is_valid_transition("1", "1.5") is True
        assert ParserFactory.is_valid_transition("1.5", "2") is True

    def test_invalid_transition(self):
        """Test that invalid transitions raise ValueError."""
        with pytest.raises(ValueError):
            ParserFactory.get_parser("1", "3")

    def test_get_available_transitions(self):
        """Test getting available transitions."""
        transitions = ParserFactory.get_available_transitions()
        assert ("0a", "1") in transitions
        assert ("0b", "1") in transitions

    def test_get_available_transitions_filtered(self):
        """Test getting transitions filtered by source phase."""
        transitions = ParserFactory.get_available_transitions("1")
        for t in transitions:
            assert t[0] == "1"

    def test_validate_output_valid(self):
        """Test validation of valid output."""
        optimizer_output = {
            "query_analysis": {"doc_set": ["test"]},
            "optimized_queries": []
        }
        is_valid, errors = ParserFactory.validate_output("0a", "1", optimizer_output)
        assert is_valid is True
        assert len(errors) == 0


class TestConfigSchema:
    """Tests for config schema validation."""

    def test_get_schema(self):
        """Test getting schemas by phase and I/O type."""
        schema = get_schema("0a", "output")
        assert schema is not None
        assert schema["type"] == "object"

    def test_validate_schema_valid(self):
        """Test validation of valid data."""
        schema = get_schema("0a", "output")
        data = {
            "query_analysis": {"doc_set": ["test"]},
            "optimized_queries": []
        }
        is_valid, errors = validate_schema(data, schema)
        assert is_valid is True

    def test_validate_schema_invalid(self):
        """Test validation of invalid data."""
        schema = get_schema("0a", "output")
        # Missing required field
        data = {"optimized_queries": []}
        is_valid, errors = validate_schema(data, schema)
        assert is_valid is False
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
