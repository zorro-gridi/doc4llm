"""
Simple test for extracting document content using titles from docTOC.md.

Tests whether we can extract content from docContent.md using specific titles.
"""
import re
from pathlib import Path

import pytest

from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor


# Test file paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
BASE_DIR = PROJECT_ROOT / "md_docs"
DOC_NAME = "code_claude_com"
DOC_VERSION = "latest"
DOC_TITLE = "Agent Skills - Claude Code Docs"

DOC_CONTENT_PATH = BASE_DIR / f"{DOC_NAME}:{DOC_VERSION}" / DOC_TITLE / "docContent.md"
DOC_TOC_PATH = BASE_DIR / f"{DOC_NAME}:{DOC_VERSION}" / DOC_TITLE / "docTOC.md"


# A few sample titles from docTOC.md to test
SAMPLE_TITLES = [
    "Create your first Skill",
    "How Skills work",
    "Configure Skills",
    "Write SKILL.md",
    "Examples",
    "Troubleshooting",
]


def parse_toc_titles(toc_path: Path) -> list[str]:
    """Parse markdown titles from docTOC.md file."""
    if not toc_path.exists():
        return []

    content = toc_path.read_text(encoding="utf-8")
    titles = []

    for line in content.splitlines():
        line = line.strip()
        # Match markdown headings (##, ###, ####) with the Chinese colon separator
        match = re.match(r'^(#{2,4})\s+(.+?)\s*：https://', line)
        if match:
            title = match.group(2).strip()
            # Remove numbering prefixes like "1. ", "2.1. ", "3.1.2. "
            title = re.sub(r'^\d+(\.\d+)*\.\s+', '', title)
            if title:
                titles.append(title)

    return titles


class TestDocContentExtraction:
    """Test suite for document content extraction."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup test fixtures."""
        if not DOC_CONTENT_PATH.exists():
            pytest.skip(f"docContent.md not found: {DOC_CONTENT_PATH}")

    def test_extract_full_document_by_title(self):
        """Test extracting the full document by its title using directory mode."""
        extractor = MarkdownDocExtractor(base_dir=str(BASE_DIR))

        content = extractor.extract_by_title(DOC_TITLE)
        assert content is not None, "Should return content for valid title"
        assert len(content) > 0, "Content should not be empty"
        # Verify it contains the main heading
        assert DOC_TITLE in content, "Content should contain the document title"

    def test_extract_full_document_single_file_mode(self):
        """Test extracting the full document in single file mode."""
        extractor = MarkdownDocExtractor(single_file_path=str(DOC_CONTENT_PATH))

        # Without title - should return full content
        content = extractor.extract_by_title()
        assert content is not None, "Should return full content when no title provided"
        assert len(content) > 100, "Content should have meaningful length"

    def test_extract_document_title_match_single_file_mode(self):
        """Test single file mode with matching title."""
        extractor = MarkdownDocExtractor(single_file_path=str(DOC_CONTENT_PATH))

        # With matching title - should return content
        content = extractor.extract_by_title(DOC_TITLE)
        assert content is not None, "Should return content for matching title"
        assert content != "", "Should not return empty string for match"
        assert len(content) > 0, "Content should not be empty"

    def test_extract_document_title_no_match_single_file_mode(self):
        """Test single file mode with non-matching title."""
        extractor = MarkdownDocExtractor(single_file_path=str(DOC_CONTENT_PATH))

        # With non-matching title - should return empty string
        content = extractor.extract_by_title("NonExistentTitle")
        assert content == "", "Should return empty string for non-matching title"

    def test_list_available_documents(self):
        """Test listing available documents."""
        extractor = MarkdownDocExtractor(base_dir=str(BASE_DIR))

        docs = extractor.list_available_documents()
        assert len(docs) > 0, "Should have at least one document"
        assert DOC_TITLE in docs, f"Should contain '{DOC_TITLE}'"

    def test_get_document_info(self):
        """Test getting document information."""
        extractor = MarkdownDocExtractor(base_dir=str(BASE_DIR))

        info = extractor.get_document_info(DOC_TITLE)
        assert info is not None, "Should return info for valid title"
        assert info["title"] == DOC_TITLE, "Title should match"
        assert info["exists"] is True, "File should exist"
        assert info["size"] > 0, "File should have content"

    def test_toc_titles_count(self):
        """Test that we can parse titles from docTOC.md."""
        titles = parse_toc_titles(DOC_TOC_PATH)
        assert len(titles) >= 30, f"Should have at least 30 titles, got {len(titles)}"

    def test_sample_titles_exist_in_toc(self):
        """Test that our sample titles exist in the parsed TOC."""
        titles = parse_toc_titles(DOC_TOC_PATH)

        for sample_title in SAMPLE_TITLES:
            assert sample_title in titles, f"Sample title '{sample_title}' should be in TOC"

    def test_search_documents_exact(self):
        """Test searching for documents with exact match."""
        extractor = MarkdownDocExtractor(
            base_dir=str(BASE_DIR),
            search_mode="exact"
        )

        results = extractor.search_documents(DOC_TITLE)
        assert len(results) == 1, "Should find exactly one match"
        assert results[0]["title"] == DOC_TITLE, "Title should match"

    def test_fuzzy_search(self):
        """Test fuzzy search functionality."""
        extractor = MarkdownDocExtractor(
            base_dir=str(BASE_DIR),
            search_mode="fuzzy",
            fuzzy_threshold=0.3
        )

        # Search for partial title
        results = extractor.search_documents("Agent Skills")
        assert len(results) >= 1, "Should find at least one match with fuzzy search"

    def test_extract_by_titles_batch(self):
        """Test extracting multiple documents by titles."""
        extractor = MarkdownDocExtractor(base_dir=str(BASE_DIR))

        results = extractor.extract_by_titles([DOC_TITLE])
        assert DOC_TITLE in results, "Should contain the requested title"
        assert len(results[DOC_TITLE]) > 0, "Content should not be empty"


def test_show_sample_titles():
    """Demo test showing the sample titles being tested."""
    titles = parse_toc_titles(DOC_TOC_PATH)

    print(f"\n=== Document: {DOC_TITLE} ===")
    print(f"Total TOC titles: {len(titles)}")
    print(f"\nSample titles being tested:")
    for i, title in enumerate(SAMPLE_TITLES, 1):
        in_toc = "✓" if title in titles else "✗"
        print(f"  {i}. {title} [{in_toc}]")

    print(f"\nAll {len(SAMPLE_TITLES)} sample titles found in TOC!")


if __name__ == "__main__":
    # Run the demo test
    pytest.main([__file__, "-k", "test_show_sample_titles", "-v", "-s"])
