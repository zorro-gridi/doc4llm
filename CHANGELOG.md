# Changelog

All notable changes to WhiteURLScan will be documented in this file.

## [2.2.0] - 2026-01-16

### Inline Content/TOC Extraction Optimization

This release introduces inline extraction optimization that eliminates duplicate HTTP requests by performing content and TOC extraction during the URL scan phase, reducing network traffic by ~66% for mode 3 operations.

### Added

#### ContentExtractor Module (`scanner/content_extractor.py`)
- New `ContentExtractor` class with in-memory content/TOC extraction capabilities:
  - `extract_inline(result, response, mode)` - Main entry point for inline extraction
  - `_extract_content_inline(url, title, html_content)` - Content extraction without additional HTTP requests
  - `_extract_toc_inline(url, title, html_content)` - TOC extraction using existing HTML response
  - `_is_in_toc(a_tag)` - TOC detection logic (from DocUrlCrawler)
  - `_add_hierarchy_numbers(anchor_links)` - Hierarchy numbering for TOC links
  - `_filter_toc_end_markers(anchor_links)` - TOC end marker filtering
- Thread-safe operations with `threading.Lock()` for file operations
- Atomic statistics updates with thread-safe counters
- Bloom filter for URL deduplication

#### Scanner Integration (`scanner/scanner.py`)
- New `_inline_extract_content(result, response)` method in `UltimateURLScanner`
- Integrated extraction into `scan_url()` method after realtime output
- Lazy initialization of ContentExtractor (created on first use)
- Only processes successful (200 status code) responses

#### Configuration Enhancement (`scanner/config.py`)
- New `enable_inline_extraction` parameter (default: `1`)
- Added to `ScannerConfig.__init__()` signature
- Supported in both config.json and command-line arguments

#### Main Entry Point Updates (`main.py`)
- Mode 1: Skip DocContentCrawler when inline extraction is enabled
- Mode 2: Skip DocUrlCrawler when inline extraction is enabled
- Mode 3: New combined mode that extracts both content and TOC inline
- User-friendly messaging when traditional crawlers are skipped

#### Configuration File (`config/config.json`)
- New `enable_inline_extraction: 1` configuration entry
- Default enabled for optimal performance

### Performance Improvements

| Metric | Before (mode 3) | After (inline) | Improvement |
|--------|-----------------|----------------|-------------|
| HTTP requests (100 URLs) | 300 | 100 | **66% reduction** |
| Total execution time | ~3x | ~1x | **66% faster** |
| Target server load | 3x | 1x | **66% reduction** |

### Changed

#### Mode Enhancement
- `mode` parameter now supports `3` (combined mode):
  - mode `0`: CSV scanning only
  - mode `1`: Content extraction
  - mode `2`: TOC extraction
  - mode `3`: Both content and TOC extraction (NEW)

#### Backward Compatibility
- Traditional crawler flow preserved when `enable_inline_extraction=0`
- Full fallback to DocContentCrawler and DocUrlCrawler available
- Legacy command-line arguments still supported

### Documentation

#### Updated Files
- `CONFIG_GUIDE.md`:
  - Added `enable_inline_extraction` parameter documentation
  - Updated `mode` section to include mode 3
  - Added "内联提取优化" section with performance comparison
  - Added working principle diagrams
  - Updated version log to v1.4
- `CHANGELOG.md`:
  - This file

### Usage Examples

```bash
# Default: inline extraction enabled
python main.py -u https://docs.example.com -mode 3

# Legacy mode: use traditional crawlers
python main.py -u https://docs.example.com -mode 3 -enable-inline-extraction 0
```

### Technical Details

#### Architecture
```
Traditional flow (mode 3):
UltimateURLScanner → DocContentCrawler → DocUrlCrawler
    (HTTP req 1)      (HTTP req 2)        (HTTP req 3)

Inline extraction flow:
UltimateURLScanner + ContentExtractor
    (1 HTTP req for scanning + extraction in memory)
```

#### Thread Safety
- Uses `threading.Lock()` for all file operations
- Atomic statistics updates with lock protection
- `os.makedirs(exist_ok=True)` for directory creation

---

## [2.1.0] - 2026-01-16

### Content Post-Processing Template

This release introduces a unified content post-processing template that automatically converts plain text end markers into flexible regex patterns for content filtering.

### Added

#### Unified Post-Processing Template (`filter/base.py`)
- New `filter_by_end_markers()` function with the following features:
  - **Plain text to regex conversion**: Users input plain text, system automatically converts to flexible regex patterns
  - **Smart pattern matching**: Supports variable whitespace, Markdown heading prefixes, and numbered sections
  - **Case-sensitive matching**: Precise matching (does NOT ignore case)
  - **Dual data type support**: Works with both strings (Markdown content) and lists (TOC anchor links)
- New `_compile_flexible_pattern()` helper function for pattern generation

#### Pattern Conversion Features
- **Whitespace flexibility**: `"Next steps"` can match `"Next  steps"` (multiple spaces)
- **Markdown heading support**: Automatically supports `##`, `###` heading prefixes
- **Numbered sections**: Automatically supports `"6. Next steps"` format
- **Special character escaping**: Automatically escapes regex special characters (`.`, `*`, `?`, etc.)
- **Case-sensitive**: Precise matching ("Next steps" won't match "next steps")

#### Configuration Parameters
- `toc_end_markers` in `toc_url_filter` configuration (for `DocUrlCrawler.py`)
  - Filters TOC markdown files generated by `DocUrlCrawler`
  - Default markers: "See also", "Related articles", "Further reading", "Next steps", etc.
- `content_end_markers` in `content_filter` configuration (for `DocContentCrawler.py`)
  - Filters content markdown files generated by `DocContentCrawler`
  - Now uses plain text input instead of raw regex patterns

#### ScannerConfig Enhancement
- Added `toc_url_filter` parameter to `ScannerConfig.__init__()` in `scanner/config.py`
- `main.py` now passes `toc_url_filter` configuration from `config.json` to `ScannerConfig`
- `DocUrlCrawler.py` updated to read `toc_url_filter` from `config.toc_url_filter`

### Changed

#### Filter Module Updates
- `filter/base.py`:
  - `BaseContentFilter.filter_content_end_markers()` now uses the unified `filter_by_end_markers()` utility
- `filter/standard.py`:
  - Added `content_end_markers` attribute import from `config.py`
  - Implemented `filter_content_end_markers()` method using the unified utility
- `filter/enhanced.py`:
  - Simplified `filter_content_end_markers()` to use the unified utility
  - Debug mode enabled for enhanced filtering
- `filter/__init__.py`:
  - Added export for `filter_by_end_markers` function

#### DocUrlCrawler Updates
- `DocUrlCrawler.py`:
  - `_filter_toc_end_markers()` now uses the unified `filter_by_end_markers()` utility
  - Fixed configuration loading from `ScannerConfig.toc_url_filter`

### Documentation

#### Updated Files
- `filter/FILTER_CONFIG.md`:
  - Added "文档内容后处理模板" section
  - Added automatic conversion rules table
  - Added `content_end_markers` and `toc_end_markers` configuration documentation
  - Added case sensitivity warnings
- `CONFIG_GUIDE.md`:
  - Added `toc_end_markers` field to `toc_url_filter` configuration table
  - Added default values and configuration examples
- `CHANGELOG.md`:
  - This file

### Technical Details

#### Pattern Generation
```
User Input: "Next steps"
Markdown Mode: ^(##+\s*)?(?:\d+\.\s*)?Next\s+steps
TOC Mode: ^\s*Next\s+steps
```

#### Matching Examples
- `"Next steps"` matches:
  - `## Next steps`
  - `## 6. Next steps：https://code.claude.com/docs/en/skills#next-steps`
  - `### Next steps`

- `"See also"` matches:
  - `## See also`
  - `### See also`
  - `See also`

### Fixed

- **Config not passed to ScannerConfig**: `toc_url_filter` configuration is now properly passed from `config.json` to `ScannerConfig` and `DocUrlCrawler`
- **Case sensitivity removed**: Matching is now case-sensitive (does NOT ignore case)

---

## [2.0.0] - 2025-01-16

### Content Filter Major Update

This release represents a comprehensive overhaul of the content filter system with improved configuration management, bug fixes, and enhanced documentation.

### Added

#### Unified Configuration Module (`filter/config.py`)
- Centralized all predefined tag lists with standardized naming conventions:
  - `SEMANTIC_NON_CONTENT_SELECTORS` - HTML5 semantic tags and ARIA roles (high priority)
  - `GENERAL_NON_CONTENT_SELECTORS` - Common ID/Class patterns for most websites
  - `FUZZY_KEYWORDS` - Keywords for fuzzy matching class/id attributes
  - `LOG_LEVELS` - Python logging level patterns for filtering code blocks
  - `MEANINGLESS_CONTENT` - Text patterns to remove from output
  - `CONTENT_PRESERVE_SELECTORS` - Content selectors to prioritize keeping
  - `CONTENT_END_MARKERS` - Regex patterns marking content end
  - `CODE_CONTAINER_SELECTORS` - Code block container selectors
- New utility functions:
  - `merge_selectors()` - Merge selector lists with extend or replace mode
  - `get_filter_config()` - Get complete filter configuration
- `FilterConfigLoader` class for loading config from `config.json`

#### Configuration File Support (`config.json`)
- New `content_filter` configuration section with the following options:
  - `merge_mode` - "extend" (default) or "replace" for configuration merging
  - `documentation_preset` - Framework presets: mintlify/docusaurus/vitepress/gitbook
  - `non_content_selectors` - Custom CSS selectors for non-content elements
  - `fuzzy_keywords` - Custom keywords for fuzzy matching
  - `log_levels` - Custom logging level patterns
  - `meaningless_content` - Custom text to remove
  - `content_end_markers` - Custom content end markers
  - `content_preserve_selectors` - Custom content preservation selectors
  - `code_container_selectors` - Custom code container selectors

#### HTML to Markdown Conversion Fixes (`MarkdownConverter.py`)
- New `_clean_markdown()` method that fixes:
  - Zero-width spaces and invisible Unicode characters (U+200B, U+200C, U+200D, U+2060, U+00AD, U+FEFF)
  - Extra newlines between header symbols and text (e.g., `## \n\nHeading` → `## Heading`)
  - Extra spaces in headers (e.g., `##   Heading` → `## Heading`)
  - Consecutive empty lines compression

### Changed

#### Filter Module Refactoring
- `filter/standard.py`:
  - Now uses `extend` mode instead of override
  - Imports and uses unified configuration from `filter/config.py`
  - Custom selectors are appended to defaults instead of replacing them

- `filter/enhanced.py`:
  - Refactored to use unified configuration from `filter/config.py`
  - Improved framework detection with standardized presets
  - Better configuration loading from `config.json`

- `filter/__init__.py`:
  - Added exports for all configuration constants
  - Added exports for utility functions and classes
  - Updated version to `2.0.0`

#### Crawler Updates
- `DocContentCrawler.py`:
  - Added `_load_content_filter()` method to load config from `config.json`
  - Now calls `filter_content_end_markers()` in the conversion pipeline
  - Automatically uses `EnhancedContentFilter` when advanced config is detected

- `WebContentExtractor.py`:
  - Added `_load_filter_config()` method for config file loading
  - Improved filter initialization with config support
  - Better handling of `content_end_markers` and other advanced options

- `WebTextCrawler.py`:
  - Added config loading support from `config.json`
  - Improved filter selection logic

### Fixed

- **content_end_markers not working**: Content after "Next steps" and similar markers is now properly removed from output
- **Malformed Markdown headers**: Headers like `## \n\nHeading` are now correctly formatted as `## Heading`
- **Zero-width space pollution**: Invisible Unicode characters from HTML anchor links are now removed
- **Config not being applied**: Multiple crawler classes now properly read and apply `config.json` settings

### Documentation

#### New Files
- `filter/FILTER_CONFIG.md` - Comprehensive configuration guide with:
  - Configuration structure and parameter descriptions
  - Selector type explanations with examples
  - config.json configuration examples
  - Documentation framework presets
  - Programming configuration examples
  - Best practices and FAQs
  - Version history

#### Updated Files
- `CLAUDE.md` - Added filter package architecture and content_filter configuration docs
- `config.json` - Added complete `content_filter` configuration section
- `CHANGELOG.md` - This file

## [1.0.0] - Initial Release

### Features
- URL scanning with recursive crawling
- Intelligent path concatenation
- Sensitive information detection
- External URL collection
- Multi-threaded concurrent execution
- Content filtering for web scraping
- HTML to Markdown conversion
- Documentation framework detection (Mintlify, Docusaurus, VitePress, GitBook)
