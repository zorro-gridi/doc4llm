---
name: md-doc-reader
description: Extract content from markdown documents by title in the doc4llm md_docs directory structure. Use this skill when Claude needs to read documentation pages that were previously scraped and converted to markdown, query specific titles within documentation sets, extract content from doc4llm's md_docs/ directory or individual .md files, or search and list available documentation titles. Supports exact, case-insensitive, fuzzy, and partial matching modes.
allowed-tools:
  - Read
  - Glob
  - Bash
context: fork
---

# Markdown Document Reader

Extract content from markdown documents in the doc4llm md_docs directory structure using the `MarkdownDocExtractor`.

## Output Language Requirement

**CRITICAL: When extracting content, maintain the original language of the document.**

- **Preserve original content language** - Do not translate document content
- **Chinese documents** - Return in Chinese as stored
- **English documents** - Return in English as stored
- **Technical terms** - Keep original terminology in parentheses when helpful
- **Code examples** - Always preserve original language (don't translate code)

**When this skill is invoked independently (not through doc-retriever agent):**
- Default to returning content in the **original document language**
- If user requests translation or explanation, respond in **Chinese by default**

**Example:**
```markdown
# Input Document (English)
## Hooks Configuration
Hooks are automation scripts...

# Output (preserve English)
## Hooks Configuration
Hooks are automation scripts...
```

## Quick Start

```python
from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor, ExtractionResult

# Directory mode (default: md_docs)
extractor = MarkdownDocExtractor()
content = extractor.extract_by_title("Agent Skills - Claude Code Docs")

# Multi-document extraction with metadata tracking (RECOMMENDED for doc-retriever)
result = extractor.extract_by_titles_with_metadata([
    "Hooks reference",
    "Deployment guide"
])
if result.requires_processing:
    print(f"Need md-doc-processor: {result.total_line_count} lines")
else:
    print(f"Within threshold: {result.total_line_count} lines")
print(result.to_summary())  # Print detailed summary

# Single file mode
extractor = MarkdownDocExtractor(single_file_path="/path/to/file.md")
content = extractor.extract_by_title()

# With fallback enabled (tries multiple search modes)
extractor = MarkdownDocExtractor(enable_fallback=True)
content = extractor.extract_by_title("Agent Skils")  # Typo still works!

# With compression for large documents
extractor = MarkdownDocExtractor(enable_compression=True, compress_threshold=500)
result = extractor.extract_with_compression("Large Doc", query="API reference")
```

## Using the Bundled Script

The `scripts/extract_md_doc.py` script provides CLI access to the extractor:

```bash
# List available documents
python scripts/extract_md_doc.py --list

# Extract by title (exact match)
python scripts/extract_md_doc.py --title "Agent Skills - Claude Code Docs"

# Search with fuzzy matching
python scripts/extract_md_doc.py --title "agent skills" --search-mode fuzzy

# Single file mode
python scripts/extract_md_doc.py --title "Guide" --file /path/to/file.md

# Search for matches
python scripts/extract_md_doc.py --title "skills" --search

# Output as JSON
python scripts/extract_md_doc.py --title "Guide" --json
```

## Search Modes

| Mode | Description |
|------|-------------|
| `exact` | Requires exact title match |
| `case_insensitive` | Case-insensitive exact match |
| `fuzzy` | Fuzzy string matching with similarity threshold |
| `partial` | Matches titles containing query as substring |

## API Methods

### `extract_by_title(title: str) -> str | None`

Extract content for a single document title. Returns `None` if not found.

**New in v2.0:** Supports automatic fallback to other search modes when `enable_fallback=True`.

### `extract_by_titles(titles: List[str]) -> Dict[str, str]`

Extract content for multiple document titles.

### `extract_by_titles_with_metadata(titles: List[str], threshold: int = 2100) -> ExtractionResult`

**NEW in v2.5.0:** Extract multiple documents with complete metadata tracking. This is the **RECOMMENDED method for doc-retriever agent** when handling multiple documents.

Returns an `ExtractionResult` dataclass with:
- `contents: Dict[str, str]` - Document titles mapped to their content
- `total_line_count: int` - **Cumulative line count across ALL documents**
- `individual_counts: Dict[str, int]` - Each document's line count
- `requires_processing: bool` - Whether `total_line_count` exceeds `threshold`
- `threshold: int` - The threshold used (default: 2100)
- `document_count: int` - Number of successfully extracted documents
- `to_summary() -> str` - Human-readable summary

**Critical for Multi-Document Scenarios:**
```python
from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor, ExtractionResult

extractor = MarkdownDocExtractor()

# Extract multiple documents with metadata
result = extractor.extract_by_titles_with_metadata([
    "Hooks reference",
    "Deployment guide",
    "Best practices"
])

# Check if post-processing is required
if result.requires_processing:
    # Total line count exceeds threshold
    # → MUST invoke md-doc-processor
    invoke_md_doc_processor(
        query=user_query,
        contents=result.contents,
        line_count=result.total_line_count
    )
else:
    # Within threshold - safe to return directly
    return format_with_citations(result.contents)

# Print detailed summary
print(result.to_summary())
```

**Why This Method is Critical:**
- **Prevents threshold bypass bugs** - Forces cumulative line count calculation
- **Hard constraint** - Returns `requires_processing` flag that cannot be ignored
- **Debug visibility** - Provides `to_summary()` for troubleshooting
- **Multi-document safety** - Designed specifically for fusion scenarios

### `search_documents(title: str) -> List[Dict]`

Search for documents matching a title pattern. Returns list with keys: `title`, `similarity`, `doc_name_version`.

### `extract_by_title_with_candidates(title: str, max_candidates: int = 5, min_threshold: float = 0.5) -> List[Dict]`

**New in v2.0:** Extract multiple candidate documents matching the query. Returns list with keys:
- `title`: Document title
- `similarity`: Similarity score (0.0 to 1.0)
- `doc_name_version`: Document name and version
- `content_preview`: First 200 characters of content

Useful when you want to present multiple options to the user.

```python
candidates = extractor.extract_by_title_with_candidates("agent skills", max_candidates=5)
for c in candidates:
    print(f"{c['title']} (similarity: {c['similarity']:.2f})")
```

### `semantic_search_titles(query: str, doc_set: str = None, max_results: int = 10) -> List[Dict]`

**New in v2.0:** Semantic search across document titles using multiple search strategies. Combines exact match, partial match, and fuzzy matching. Returns list with keys:
- `title`: Document title
- `similarity`: Similarity score (0.0 to 1.0)
- `match_type`: Type of match ("exact", "partial", "fuzzy")
- `doc_name_version`: Document name and version

```python
results = extractor.semantic_search_titles("skill", max_results=10)
for r in results:
    print(f"{r['title']} ({r['match_type']}, similarity: {r['similarity']:.2f})")
```

### `extract_with_compression(title: str, query: str = None, summarize_prompt: str = None) -> Dict`

**New in v2.0:** Extract document content with automatic compression for large documents. Returns dict with keys:
- `title`: Document title
- `content`: Document content (compressed or original)
- `line_count`: Number of lines in content
- `compressed`: Whether compression was applied
- `compression_ratio`: Compression ratio (0.0 to 1.0)
- `compression_method`: Method used ("query_based", "smart_truncate", or None)

```python
result = extractor.extract_with_compression("Large Doc", query="API reference")
if result['compressed']:
    print(f"Compressed: {result['compression_ratio']:.0%}")
```

### `list_available_documents(doc_name_version: str = None) -> List[str]`

List all available document titles.

### `get_document_info(title: str) -> Dict | None`

Get detailed information about a document.

## Configuration

Load from `doc4llm/config/config.json`:

```python
extractor = MarkdownDocExtractor.from_config()
```

Config structure:
```json
{
  "tool": {
    "markdown_extractor": {
      "base_dir": "md_docs",
      "default_search_mode": "exact",
      "case_sensitive": false,
      "max_results": 10,
      "fuzzy_threshold": 0.6,
      "enable_fallback": false,
      "fallback_modes": ["case_insensitive", "partial", "fuzzy"],
      "compress_threshold": 2000,
      "enable_compression": false
    }
  }
}
```

**New Configuration Options:**
- `enable_fallback`: Enable automatic fallback to other search modes on failure (default: false)
- `fallback_modes`: List of search modes to try as fallback (default: ["case_insensitive", "partial", "fuzzy"])
- `compress_threshold`: Line count threshold for content compression (default: 2000)
- `enable_compression`: Enable automatic content compression for large documents (default: false)

## Directory Structure

Expected format:
```
md_docs/
└── <doc_name>:<doc_version>/
    └── <PageTitle>/
        └── docContent.md
```
