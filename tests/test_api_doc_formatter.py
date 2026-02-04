#!/usr/bin/env python3
"""
Unit tests for ApiDocTitleFormatter

Tests cover:
- API document detection
- Anchor parsing and hierarchy detection
- Title cleaning (Unicode artifacts removal)
- TOC and Content title formatting
"""

import pytest
from doc4llm.crawler.api_doc_formatter import ApiDocTitleFormatter, ApiDocItem


class TestApiDocTitleFormatter:
    """Test suite for ApiDocTitleFormatter"""

    # ==================== Setup ====================

    @pytest.fixture
    def formatter(self):
        """Create a formatter instance for testing"""
        return ApiDocTitleFormatter()

    @pytest.fixture
    def sphinx_formatter(self):
        """Create a Sphinx-specific formatter"""
        return ApiDocTitleFormatter.create_for_sphinx()

    @pytest.fixture
    def dolphin_formatter(self):
        """Create a DolphinScheduler-specific formatter"""
        return ApiDocTitleFormatter.create_for_dolphinscheduler()

    # ==================== Detection Tests ====================

    class TestIsApiDoc:
        """Tests for is_api_doc() method"""

        def test_sphinx_html_detection(self, formatter):
            """Test detection of Sphinx HTML patterns"""
            sphinx_html = '<dl class="py function"><dt class="sig sig-object py">'
            assert formatter.is_api_doc(sphinx_html) is True

        def test_sphinx_source_link(self, formatter):
            """Test detection of [[source]] links"""
            html = '<a class="reference internal" href="#">[[source]]</a>'
            assert formatter.is_api_doc(html) is True

        def test_pydolphinscheduler_pattern(self, formatter):
            """Test detection of pydolphinscheduler module paths"""
            html = "pydolphinscheduler.core.Engine"
            assert formatter.is_api_doc(html) is True

        def test_url_detection(self, formatter):
            """Test API doc detection via URL"""
            url = "https://dolphinscheduler.apache.org/python/main/api.html"
            assert formatter.is_api_doc("", url=url) is True

        def test_url_api_path(self, formatter):
            """Test detection via /api/ path"""
            assert formatter.is_api_doc("", url="/api/reference") is True
            assert formatter.is_api_doc("", url="/docs/api") is True

        def test_non_api_content(self, formatter):
            """Test that regular content is not detected as API"""
            regular_html = "<html><body><h1>Getting Started</h1><p>Welcome to our docs</p></body></html>"
            assert formatter.is_api_doc(regular_html) is False

    class TestDetectDocType:
        """Tests for detect_doc_type() method"""

        def test_module_detection(self, formatter):
            """Test module-level detection"""
            assert formatter.detect_doc_type("pydolphinscheduler.core") == "module"
            assert (
                formatter.detect_doc_type("module-pydolphinscheduler.core") == "module"
            )

        def test_class_detection(self, formatter):
            """Test class-level detection"""
            assert (
                formatter.detect_doc_type("pydolphinscheduler.core.Engine") == "class"
            )
            assert formatter.detect_doc_type("pydolphinscheduler.tasks.Task") == "class"

        def test_member_detection(self, formatter):
            """Test member (method/attribute) detection"""
            assert (
                formatter.detect_doc_type("pydolphinscheduler.core.Engine._get_attr")
                == "member"
            )
            assert (
                formatter.detect_doc_type("pydolphinscheduler.core.Task.add_in()")
                == "member"
            )

        def test_unknown_type(self, formatter):
            """Test unknown type detection"""
            assert formatter.detect_doc_type("random-text") == "unknown"

    # ==================== Parsing Tests ====================

    class TestParseAnchor:
        """Tests for parse_anchor() method"""

        def test_parse_module_anchor(self, formatter):
            """Test parsing a module anchor"""
            item = formatter.parse_anchor("pydolphinscheduler.core")
            assert item is not None
            assert item.level == 1
            assert item.doc_type == "module"

        def test_parse_class_anchor(self, formatter):
            """Test parsing a class anchor"""
            item = formatter.parse_anchor("pydolphinscheduler.core.Engine")
            assert item is not None
            assert item.level == 2
            assert item.doc_type == "class"

        def test_parse_member_anchor(self, formatter):
            """Test parsing a member anchor"""
            item = formatter.parse_anchor("pydolphinscheduler.core.Engine._get_attr")
            assert item is not None
            assert item.level == 3
            assert item.doc_type == "member"

        def test_empty_anchor_returns_none(self, formatter):
            """Test that empty anchor returns None"""
            assert formatter.parse_anchor("") is None
            assert formatter.parse_anchor("   ") is None

    class TestParseHierarchy:
        """Tests for parse_hierarchy() method"""

        def test_hierarchy_parsing(self, formatter):
            """Test parsing a list of anchors with hierarchy"""
            anchors = [
                "pydolphinscheduler.core",
                "pydolphinscheduler.core.Engine",
                "pydolphinscheduler.core.Engine._get_attr",
                "pydolphinscheduler.core.Engine._set_deps",
                "pydolphinscheduler.core.Task",
                "pydolphinscheduler.core.Task.add_in",
            ]
            items = formatter.parse_hierarchy(anchors)

            assert len(items) == 6

            # Verify hierarchy
            assert items[0].level == 1  # Module
            assert items[1].level == 2  # Class
            assert items[2].level == 3  # Method
            assert items[3].level == 3  # Method
            assert items[4].level == 2  # Class
            assert items[5].level == 3  # Method

        def test_numbering(self, formatter):
            """Test hierarchical numbering"""
            anchors = [
                "pydolphinscheduler.core",
                "pydolphinscheduler.core.Engine",
                "pydolphinscheduler.core.Engine._get_attr",
            ]
            items = formatter.parse_hierarchy(anchors)

            assert items[0].number == "1"
            assert items[1].number == "1.1"
            assert items[2].number == "1.1.1"

        def test_empty_list(self, formatter):
            """Test parsing empty list"""
            assert formatter.parse_hierarchy([]) == []

    # ==================== Title Cleaning Tests ====================

    class TestCleanTitle:
        """Tests for clean_title() method"""

        def test_remove_unicode_artifact(self, formatter):
            """Test removal of Unicode anchor symbol"""
            assert formatter.clean_title("Engine._get_attr()") == "Engine._get_attr()"

        def test_remove_source_link(self, formatter):
            """Test removal of [[source]] suffix"""
            assert (
                formatter.clean_title("Engine._get_attr()[[source]]")
                == "Engine._get_attr()"
            )

        def test_remove_return_type(self, formatter):
            """Test removal of return type arrow"""
            assert "→" not in formatter.clean_title("func() → str")

        def test_remove_method_signature(self, formatter):
            """Test removal of method parameters"""
            result = formatter.clean_title("func(arg1: str, arg2: int)")
            assert "(" not in result

        def test_preserve_method_name(self, formatter):
            """Test that method name is preserved"""
            assert "Engine._get_attr" in formatter.clean_title("Engine._get_attr()")

        def test_normalize_whitespace(self, formatter):
            """Test whitespace normalization"""
            assert "  " not in formatter.clean_title("Test   Title")

    # ==================== Formatting Tests ====================

    class TestFormatTocTitle:
        """Tests for format_toc_title() method"""

        def test_toc_title_with_number(self, formatter):
            """Test TOC title formatting with number"""
            item = ApiDocItem(
                level=2,
                anchor="test",
                raw_title="Engine",
                clean_title="Engine",
                number="1.1",
            )
            result = formatter.format_toc_title(item)
            assert result == "## 1.1 Engine"

        def test_toc_title_without_number(self, formatter):
            """Test TOC title formatting without number"""
            item = ApiDocItem(
                level=2,
                anchor="test",
                raw_title="Engine",
                clean_title="Engine",
                number="",
            )
            result = formatter.format_toc_title(item)
            assert result == "## Engine"

    class TestFormatContentTitle:
        """Tests for format_content_title() method"""

        def test_content_title_module_level(self, formatter):
            """Test content title at module level (##)"""
            item = ApiDocItem(
                level=1, anchor="test", raw_title="core", clean_title="core"
            )
            result = formatter.format_content_title(item)
            assert result == "## core"

        def test_content_title_class_level(self, formatter):
            """Test content title at class level (###)"""
            item = ApiDocItem(
                level=2, anchor="test", raw_title="Engine", clean_title="Engine"
            )
            result = formatter.format_content_title(item)
            assert result == "### Engine"

        def test_content_title_member_level(self, formatter):
            """Test content title at member level (####)"""
            item = ApiDocItem(
                level=3, anchor="test", raw_title="_get_attr", clean_title="_get_attr"
            )
            result = formatter.format_content_title(item)
            assert result == "#### _get_attr"

        def test_custom_base_level(self, formatter):
            """Test content title with custom base level"""
            item = ApiDocItem(
                level=2, anchor="test", raw_title="Engine", clean_title="Engine"
            )
            result = formatter.format_content_title(item, base_level=3)
            assert result == "#### Engine"

    class TestFormatHierarchy:
        """Tests for format_hierarchy() method"""

        def test_format_hierarchy_toc(self, formatter):
            """Test formatting hierarchy as TOC"""
            items = [
                ApiDocItem(
                    level=1,
                    anchor="a",
                    raw_title="Module",
                    clean_title="Module",
                    number="1",
                ),
                ApiDocItem(
                    level=2,
                    anchor="b",
                    raw_title="Class",
                    clean_title="Class",
                    number="1.1",
                ),
            ]
            lines = formatter.format_hierarchy(items, toc_format=True)

            assert lines[0] == "## 1 Module"
            assert lines[1] == "## 1.1 Class"

        def test_format_hierarchy_content(self, formatter):
            """Test formatting hierarchy as content"""
            items = [
                ApiDocItem(
                    level=1,
                    anchor="a",
                    raw_title="Module",
                    clean_title="Module",
                    number="",
                ),
                ApiDocItem(
                    level=2,
                    anchor="b",
                    raw_title="Class",
                    clean_title="Class",
                    number="",
                ),
            ]
            lines = formatter.format_hierarchy(items, toc_format=False)

            assert lines[0] == "## Module"
            assert lines[1] == "### Class"

    # ==================== Convenience Method Tests ====================

    class TestExtractMethodName:
        """Tests for extract_method_name() method"""

        def test_extract_from_toc_title(self, formatter):
            """Test extracting method name from TOC title"""
            assert (
                formatter.extract_method_name("1.1 Engine._get_attr")
                == "Engine._get_attr"
            )
            assert formatter.extract_method_name("2. Task.add_in()") == "Task.add_in()"

    class TestCreateForSphinx:
        """Tests for create_for_sphinx() class method"""

        def test_returns_formatter(self):
            """Test that it returns a formatter instance"""
            formatter = ApiDocTitleFormatter.create_for_sphinx()
            assert isinstance(formatter, ApiDocTitleFormatter)

        def test_default_settings(self):
            """Test that default settings are applied"""
            formatter = ApiDocTitleFormatter.create_for_sphinx()
            assert formatter.auto_number is True
            assert formatter.clean_unicode is True
            assert formatter.include_private is True

    class TestCreateForDolphinscheduler:
        """Tests for create_for_dolphinscheduler() class method"""

        def test_returns_formatter(self):
            """Test that it returns a formatter instance"""
            formatter = ApiDocTitleFormatter.create_for_dolphinscheduler()
            assert isinstance(formatter, ApiDocTitleFormatter)

        def test_dolphin_patterns_loaded(self):
            """Test that Dolphin-specific patterns are available"""
            formatter = ApiDocTitleFormatter.create_for_dolphinscheduler()
            assert len(formatter.DOLPHIN_PATTERNS) > 0


class TestApiDocItem:
    """Tests for ApiDocItem dataclass"""

    def test_default_values(self):
        """Test default values for optional fields"""
        item = ApiDocItem(
            level=2, anchor="test", raw_title="Engine", clean_title="Engine"
        )
        assert item.number == ""
        assert item.doc_type == "unknown"

    def test_level_validation_downgrade(self):
        """Test that invalid levels are downgraded"""
        item = ApiDocItem(level=99, anchor="test", raw_title="Test", clean_title="Test")
        # Invalid levels should be downgraded to 3 (member level)
        assert item.level == 3

    def test_custom_values(self):
        """Test setting custom values"""
        item = ApiDocItem(
            level=2,
            anchor="pydolphinscheduler.core.Engine",
            raw_title="Engine",
            clean_title="Engine",
            number="1.1",
            doc_type="class",
        )
        assert item.level == 2
        assert item.number == "1.1"
        assert item.doc_type == "class"


# ==================== Integration Tests ====================


class TestDolphinSchedulerIntegration:
    """Integration tests simulating DolphinScheduler API processing"""

    def test_full_processing_pipeline(self):
        """Test the complete pipeline for DolphinScheduler API"""
        formatter = ApiDocTitleFormatter.create_for_dolphinscheduler()

        # Simulated anchor list from DolphinScheduler API
        anchors = [
            "pydolphinscheduler.core",
            "pydolphinscheduler.core.Engine",
            "pydolphinscheduler.core.Engine._get_attr()",
            "pydolphinscheduler.core.Engine._set_deps()",
            "pydolphinscheduler.core.Task",
            "pydolphinscheduler.core.Task._get_attr()",
            "pydolphinscheduler.core.Workflow",
            "pydolphinscheduler.core.Workflow.run()",
            "pydolphinscheduler.models",
            "pydolphinscheduler.models.Base",
        ]

        # Parse hierarchy
        items = formatter.parse_hierarchy(anchors)

        # Verify structure
        assert len(items) == 10

        # Verify first module
        assert items[0].level == 1
        assert items[0].clean_title == "pydolphinscheduler.core"

        # Verify class under module
        assert items[1].level == 2
        assert items[1].number == "1.1"

        # Verify methods
        assert items[2].level == 3
        assert items[2].number == "1.1.1"

        # Verify TOC formatting
        toc_lines = formatter.format_hierarchy(items[:3], toc_format=True)
        assert "## 1 pydolphinscheduler.core" in toc_lines[0]
        assert "## 1.1 pydolphinscheduler.core.Engine" in toc_lines[1]

        # Verify Unicode is cleaned
        assert "" not in toc_lines[2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
