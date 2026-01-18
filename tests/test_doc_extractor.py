"""
Unit tests for the MarkdownDocExtractor module.

Tests the new functionality added in v2.0:
- Fallback mechanism
- Content compression
- Multi-candidate extraction
- Semantic search
- TOC processing utilities
"""
import json
import os
import tempfile
from pathlib import Path
from unittest import TestCase

from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor
from doc4llm.tool.md_doc_retrieval.utils import (
    calculate_similarity,
    extract_toc_sections,
    semantic_match_toc_sections,
)


class TestMarkdownDocExtractorV2(TestCase):
    """Test cases for MarkdownDocExtractor v2.0 features."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.doc_set = f"{self.test_dir}/test_docs:latest"
        os.makedirs(self.doc_set, exist_ok=True)

        # Create test documents
        self._create_test_document("Agent Skills - Claude Code Docs", "# Agent Skills\n\nThis is a test document about agent skills.")
        self._create_test_document("Slash Commands", "# Slash Commands\n\nDocumentation for slash commands.")
        self._create_test_document("Settings", "# Settings\n\nConfiguration and settings documentation.")

    def _create_test_document(self, title: str, content: str):
        """Helper to create a test document."""
        doc_dir = Path(self.doc_set) / title
        doc_dir.mkdir(parents=True, exist_ok=True)
        (doc_dir / "docContent.md").write_text(content)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_fallback_mechanism_enabled(self):
        """Test that fallback mechanism works when enabled."""
        extractor = MarkdownDocExtractor(
            base_dir=self.test_dir,
            search_mode="exact",
            enable_fallback=True,
            fallback_modes=["partial", "fuzzy"]
        )

        # Test with partial match - should fallback to partial mode
        content = extractor.extract_by_title("skill")
        self.assertIsNotNone(content)
        # Content should be a string
        self.assertIsInstance(content, str)

    def test_fallback_mechanism_disabled(self):
        """Test that fallback is not used when disabled."""
        extractor = MarkdownDocExtractor(
            base_dir=self.test_dir,
            search_mode="exact",
            enable_fallback=False
        )

        # With exact mode and partial query, should not find anything
        content = extractor.extract_by_title("skill")
        self.assertIsNone(content)

    def test_extract_by_title_with_candidates(self):
        """Test extracting multiple candidate documents."""
        extractor = MarkdownDocExtractor(base_dir=self.test_dir)

        candidates = extractor.extract_by_title_with_candidates("agent", max_candidates=3, min_threshold=0.2)

        self.assertGreater(len(candidates), 0)
        self.assertIn("title", candidates[0])
        self.assertIn("similarity", candidates[0])
        self.assertIn("content_preview", candidates[0])

        # Check that results are sorted by similarity
        for i in range(len(candidates) - 1):
            self.assertGreaterEqual(candidates[i]["similarity"], candidates[i+1]["similarity"])

    def test_semantic_search_titles(self):
        """Test semantic search across document titles."""
        extractor = MarkdownDocExtractor(base_dir=self.test_dir)

        results = extractor.semantic_search_titles("skill")

        self.assertGreater(len(results), 0)
        self.assertIn("title", results[0])
        self.assertIn("similarity", results[0])
        self.assertIn("match_type", results[0])

        # Check valid match types
        for result in results:
            self.assertIn(result["match_type"], ["exact", "partial", "fuzzy"])

    def test_semantic_search_with_doc_set_filter(self):
        """Test semantic search with document set filtering."""
        extractor = MarkdownDocExtractor(base_dir=self.test_dir)

        # Search with doc set filter
        results = extractor.semantic_search_titles("skill", doc_set="test_docs:latest")

        self.assertGreater(len(results), 0)

        # Search with non-existent doc set
        results = extractor.semantic_search_titles("skill", doc_set="nonexistent:latest")
        self.assertEqual(len(results), 0)

    def test_extract_with_compression_enabled(self):
        """Test content compression for large documents."""
        # Create a large document
        large_content = "# Large Document\n\n" + "\n".join([f"Line {i}" for i in range(2000)])
        self._create_test_document("Large Doc", large_content)

        extractor = MarkdownDocExtractor(
            base_dir=self.test_dir,
            enable_compression=True,
            compress_threshold=500
        )

        result = extractor.extract_with_compression("Large Doc")

        self.assertTrue(result["compressed"])
        self.assertLess(result["compression_ratio"], 1.0)
        self.assertIn("compression_method", result)

    def test_extract_with_compression_disabled(self):
        """Test that compression is not applied when disabled."""
        large_content = "# Large Document\n\n" + "\n".join([f"Line {i}" for i in range(2000)])
        self._create_test_document("Large Doc", large_content)

        extractor = MarkdownDocExtractor(
            base_dir=self.test_dir,
            enable_compression=False
        )

        result = extractor.extract_with_compression("Large Doc")

        self.assertFalse(result["compressed"])
        self.assertEqual(result["compression_ratio"], 0.0)

    def test_extract_with_compression_query_based(self):
        """Test query-based content compression."""
        # Create a document with multiple sections
        content = """# API Reference

## Authentication
This section covers authentication.

## Endpoints
This section covers API endpoints.

## Data Models
This section covers data models.
"""
        self._create_test_document("API Doc", content)

        extractor = MarkdownDocExtractor(
            base_dir=self.test_dir,
            enable_compression=True,
            compress_threshold=5
        )

        result = extractor.extract_with_compression("API Doc", query="authentication")

        self.assertTrue(result["compressed"])
        self.assertIn("authentication", result["content"].lower())


class TestTOCProcessingUtilities(TestCase):
    """Test cases for TOC processing utilities."""

    def test_extract_toc_sections_basic(self):
        """Test basic TOC section extraction."""
        toc_content = """# Main Title

## Section 1
Content here

### Subsection 1.1
More content

## Section 2
Final content
"""

        sections = extract_toc_sections(toc_content)

        self.assertEqual(len(sections), 4)
        self.assertEqual(sections[0]["level"], 1)
        self.assertEqual(sections[0]["title"], "Main Title")
        self.assertEqual(sections[1]["title"], "Section 1")
        self.assertEqual(sections[2]["title"], "Subsection 1.1")
        self.assertEqual(sections[3]["title"], "Section 2")

    def test_extract_toc_sections_with_query(self):
        """Test TOC extraction with query filtering."""
        toc_content = """# Main

## Agent Skills
Content about skills

## Settings
Configuration settings

## API Reference
API documentation
"""

        sections = extract_toc_sections(toc_content, query="skills", max_sections=20)

        # Should return sections, with Agent Skills being most relevant
        self.assertGreater(len(sections), 0)
        # Check that relevance scores are present
        self.assertIn("relevance_score", sections[0])

    def test_extract_toc_sections_max_limit(self):
        """Test TOC extraction with max_sections limit."""
        toc_content = "\n".join([f"## Section {i}" for i in range(30)])

        sections = extract_toc_sections(toc_content, max_sections=10)

        self.assertLessEqual(len(sections), 10)

    def test_extract_toc_sections_anchor_generation(self):
        """Test that anchor links are generated correctly."""
        toc_content = "## Create Your First Skill"

        sections = extract_toc_sections(toc_content)

        self.assertEqual(sections[0]["anchor"], "create-your-first-skill")

    def test_semantic_match_toc_sections(self):
        """Test semantic matching of TOC sections."""
        sections = [
            {"level": 2, "title": "Agent Skills", "anchor": "agent-skills", "line_number": 1},
            {"level": 2, "title": "API Reference", "anchor": "api-reference", "line_number": 10},
            {"level": 2, "title": "Settings", "anchor": "settings", "line_number": 20},
        ]

        matched = semantic_match_toc_sections(sections, "skill")

        self.assertGreater(len(matched), 0)
        # Agent Skills should be first (highest relevance)
        self.assertEqual(matched[0]["title"], "Agent Skills")

        # Check relevance scores
        for section in matched:
            self.assertIn("relevance_score", section)
            self.assertGreaterEqual(section["relevance_score"], 0.0)
            self.assertLessEqual(section["relevance_score"], 1.0)

    def test_calculate_similarity(self):
        """Test similarity calculation."""
        # Exact match
        self.assertEqual(calculate_similarity("hello", "hello"), 1.0)

        # Case insensitive
        self.assertEqual(calculate_similarity("Hello", "hello"), 1.0)

        # Partial match
        similarity = calculate_similarity("hello", "hallo")
        self.assertGreater(similarity, 0.5)
        self.assertLess(similarity, 1.0)

        # No match
        self.assertEqual(calculate_similarity("abc", "xyz"), 0.0)

        # Empty strings
        self.assertEqual(calculate_similarity("", "test"), 0.0)
        self.assertEqual(calculate_similarity("test", ""), 0.0)


class TestFromConfig(TestCase):
    """Test configuration loading."""

    def test_from_config_default(self):
        """Test loading with default config (no config file)."""
        extractor = MarkdownDocExtractor.from_config("/nonexistent/path/config.json")

        # Should have default values
        self.assertEqual(extractor.search_mode, "exact")
        self.assertFalse(extractor.enable_fallback)
        self.assertFalse(extractor.enable_compression)

    def test_from_config_with_file(self):
        """Test loading from actual config file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "tool": {
                    "markdown_extractor": {
                        "default_search_mode": "fuzzy",
                        "enable_fallback": True,
                        "enable_compression": True,
                        "compress_threshold": 500
                    }
                }
            }
            json.dump(config, f)
            config_path = f.name

        try:
            extractor = MarkdownDocExtractor.from_config(config_path)

            self.assertEqual(extractor.search_mode, "fuzzy")
            self.assertTrue(extractor.enable_fallback)
            self.assertTrue(extractor.enable_compression)
            self.assertEqual(extractor.compress_threshold, 500)
        finally:
            os.unlink(config_path)


if __name__ == "__main__":
    import unittest
    unittest.main()
