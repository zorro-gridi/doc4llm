"""
Test Phase 1.5 -> Phase 2.0 parameter parsing.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from doc4llm.doc_rag.params_parser.params_parser_api import ParamsParserAPI


class TestPhase1_5ToPhase2:
    """Test cases for phase 1.5 to phase 2 transition."""

    @pytest.fixture
    def api(self):
        """Create ParamsParserAPI instance."""
        return ParamsParserAPI()

    @pytest.fixture
    def sample_phase1_5_output(self):
        """Sample Phase 1.5 output from user."""
        return {
            "success": True,
            "toc_fallback": True,
            "grep_fallback": True,
            "query": [
                "opencode skills creation guide",
                "opencode skills setup tutorial",
                "how to create skills in opencode",
                "opencode skills configuration reference",
                "build skills opencode development guide"
            ],
            "doc_sets_found": ["OpenCode_Docs@latest"],
            "results": [
                {
                    "doc_set": "OpenCode_Docs@latest",
                    "page_title": "Agent Skills",
                    "toc_path": "/Users/zorro/project/md_docs_base/OpenCode_Docs@latest/Agent Skills/docTOC.md",
                    "headings": [
                        {
                            "text": "Agent Skills",
                            "level": 1,
                            "rerank_sim": 0.72,
                            "bm25_sim": None
                        }
                    ],
                    "bm25_sim": 6.345697232860008,
                    "rerank_sim": None
                },
                {
                    "doc_set": "OpenCode_Docs@latest",
                    "page_title": "Agents",
                    "toc_path": "/Users/zorro/project/md_docs_base/OpenCode_Docs@latest/Agents/docTOC.md",
                    "bm25_sim": 4.345697232860008,
                    "rerank_sim": None
                }
            ],
            "fallback_used": "FALLBACK_1",
            "message": "Search completed"
        }

    def test_basic_transition(self, api, sample_phase1_5_output):
        """Test basic phase 1.5 to phase 2 transition."""
        response = api.parse(
            from_phase="1.5",
            to_phase="2",
            upstream_output=sample_phase1_5_output
        )

        assert response.status == "success", f"Failed: {response.errors}"
        assert response.from_phase == "1.5"
        assert response.to_phase == "2"

    def test_page_titles_structure(self, api, sample_phase1_5_output):
        """Test page_titles array structure."""
        response = api.parse("1.5", "2", sample_phase1_5_output)
        assert response.status == "success"

        config = response.config
        assert "page_titles" in config
        assert isinstance(config["page_titles"], list)
        assert len(config["page_titles"]) == 2

    def test_page_title_extraction(self, api, sample_phase1_5_output):
        """Test page_title extraction."""
        response = api.parse("1.5", "2", sample_phase1_5_output)
        assert response.status == "success"

        page_titles = response.config["page_titles"]
        assert page_titles[0]["title"] == "Agent Skills"
        assert page_titles[1]["title"] == "Agents"

    def test_headings_extraction(self, api, sample_phase1_5_output):
        """Test headings array extraction and normalization."""
        response = api.parse("1.5", "2", sample_phase1_5_output)
        assert response.status == "success"

        page_titles = response.config["page_titles"]

        assert page_titles[0]["headings"] == ["Agent Skills"]
        assert page_titles[1]["headings"] == []

    def test_doc_set_preservation(self, api, sample_phase1_5_output):
        """Test doc_set field preservation."""
        response = api.parse("1.5", "2", sample_phase1_5_output)
        assert response.status == "success"

        page_titles = response.config["page_titles"]
        for item in page_titles:
            assert item["doc_set"] == "OpenCode_Docs@latest"

    def test_fixed_fields(self, api, sample_phase1_5_output):
        """Test fixed output fields."""
        response = api.parse("1.5", "2", sample_phase1_5_output)
        assert response.status == "success"

        config = response.config
        assert config["with_metadata"] is True
        assert config["format"] == "json"

    def test_empty_results(self, api):
        """Test edge case: empty results array."""
        upstream = {"success": True, "results": []}
        response = api.parse("1.5", "2", upstream)

        assert response.status == "success"
        assert response.config["page_titles"] == []

    def test_result_without_headings(self, api):
        """Test result without headings key."""
        upstream = {
            "success": True,
            "results": [
                {
                    "doc_set": "Test@latest",
                    "page_title": "Test Page"
                }
            ]
        }
        response = api.parse("1.5", "2", upstream)

        assert response.status == "success"
        assert response.config["page_titles"][0]["headings"] == []

    def test_multiple_headings(self, api):
        """Test result with multiple headings."""
        upstream = {
            "success": True,
            "results": [
                {
                    "doc_set": "Test@latest",
                    "page_title": "Test Page",
                    "headings": [
                        {"text": "## Heading 1"},
                        {"text": "Heading 2"},
                        {"text": "### Nested Heading"}
                    ]
                }
            ]
        }
        response = api.parse("1.5", "2", upstream)

        assert response.status == "success"
        headings = response.config["page_titles"][0]["headings"]
        assert headings == ["Heading 1", "Heading 2", "Nested Heading"]

    def test_heading_normalization(self, api):
        """Test heading text normalization (removes # prefix)."""
        upstream = {
            "success": True,
            "results": [
                {
                    "doc_set": "Test@latest",
                    "page_title": "Test Page",
                    "headings": [
                        {"text": "##  Introduction  "},
                        {"text": "###   Deep Dive   "}
                    ]
                }
            ]
        }
        response = api.parse("1.5", "2", upstream)

        assert response.status == "success"
        headings = response.config["page_titles"][0]["headings"]
        assert headings == ["Introduction", "Deep Dive"]

    def test_multiple_results(self, api):
        """Test multiple results processing."""
        upstream = {
            "success": True,
            "results": [
                {"doc_set": "Doc1@latest", "page_title": "Page 1", "headings": [{"text": "H1"}]},
                {"doc_set": "Doc2@latest", "page_title": "Page 2", "headings": []},
                {"doc_set": "Doc3@latest", "page_title": "Page 3", "headings": [{"text": "H3"}, {"text": "H4"}]}
            ]
        }
        response = api.parse("1.5", "2", upstream)

        assert response.status == "success"
        page_titles = response.config["page_titles"]
        assert len(page_titles) == 3

        assert page_titles[0]["title"] == "Page 1"
        assert page_titles[0]["headings"] == ["H1"]

        assert page_titles[1]["title"] == "Page 2"
        assert page_titles[1]["headings"] == []

        assert page_titles[2]["title"] == "Page 3"
        assert page_titles[2]["headings"] == ["H3", "H4"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
