# Python API Reference

The `MarkdownDocExtractor` class provides a Python API for extracting content from markdown documents stored in the doc4llm md_docs directory structure.

## Import

```python
from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor, ExtractionResult
```

## Class: MarkdownDocExtractor

### Constructor

```python
MarkdownDocExtractor(
    base_dir: str | None = None,
    single_file_path: str | None = None,
    search_mode: str = "exact",
    case_sensitive: bool = False,
    max_results: int | None = None,
    fuzzy_threshold: float = 0.6,
    debug_mode: bool = False,
    enable_fallback: bool = False,
    fallback_modes: List[str] | None = None,
    compress_threshold: int = 1000,
    enable_compression: bool = False,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_dir` | `str \| None` | `"md_docs"` | Base documentation directory |
| `single_file_path` | `str \| None` | `None` | Path to a single .md file for single-file mode |
| `search_mode` | `str` | `"exact"` | Search mode: `"exact"`, `"case_insensitive"`, `"fuzzy"`, `"partial"` |
| `case_sensitive` | `bool` | `False` | Whether exact matching should be case sensitive |
| `max_results` | `int \| None` | `None` | Maximum results for fuzzy/partial searches |
| `fuzzy_threshold` | `float` | `0.6` | Minimum similarity ratio (0.0 to 1.0) for fuzzy matching |
| `debug_mode` | `bool` | `False` | Enable debug output |
| `enable_fallback` | `bool` | `False` | Enable automatic fallback to other search modes on failure |
| `fallback_modes` | `List[str] \| None` | `["case_insensitive", "partial", "fuzzy"]` | Search modes to try as fallback |
| `compress_threshold` | `int` | `1000` | Line count threshold for content compression |
| `enable_compression` | `bool` | `False` | Enable automatic content compression for large documents |

#### Raises

- `ConfigurationError`: If search_mode or other configuration is invalid
- `SingleFileNotFoundError`: If single_file_path is provided but invalid

### Class Methods

#### from_config()

```python
@classmethod
def from_config(
    cls,
    config_path: str | None = None,
    config_dict: dict | None = None
) -> MarkdownDocExtractor
```

Create an extractor instance from a configuration file or dictionary.

**Parameters:**
- `config_path`: Path to config.json. If None, uses package default config.
- `config_dict`: Optional config dict (overrides config_path if both provided).

**Returns:** A configured `MarkdownDocExtractor` instance

```python
# From config file
extractor = MarkdownDocExtractor.from_config("path/to/config.json")

# From config dict
config = {
    "base_dir": "md_docs",
    "default_search_mode": "fuzzy",
    "fuzzy_threshold": 0.7
}
extractor = MarkdownDocExtractor.from_config(config_dict=config)

# Using package default
extractor = MarkdownDocExtractor.from_config()
```

### Instance Methods

#### extract_by_title()

```python
def extract_by_title(self, title: str | None = None) -> str | None
```

Extract content for a single document title.

**Parameters:**
- `title`: The document title to extract. In single file mode, if None, returns the file content directly.

**Returns:**
- **Single file mode:**
  - If title is None: returns the file content
  - If title matches: returns the file content
  - If title doesn't match: returns empty string `""`
- **Directory mode:** The document content as a string, or `None` if not found

```python
extractor = MarkdownDocExtractor()

# Directory mode - exact match
content = extractor.extract_by_title("Agent Skills - Claude Code Docs")

# Single file mode - direct read
extractor = MarkdownDocExtractor(single_file_path="/path/to/file.md")
content = extractor.extract_by_title()  # Returns all content
content = extractor.extract_by_title("Agent Skills")  # Returns content if title matches
```

#### extract_by_titles()

```python
def extract_by_titles(self, titles: List[str]) -> Dict[str, str]
```

Extract content for multiple document titles.

**Parameters:**
- `titles`: List of document titles to extract

**Returns:** Dictionary mapping title to content. Titles that cannot be found will not be included.

```python
extractor = MarkdownDocExtractor()
results = extractor.extract_by_titles([
    "Agent Skills - Claude Code Docs",
    "Slash Commands",
    "Hooks reference"
])

for title, content in results.items():
    print(f"{title}: {len(content)} characters")
```

#### extract_by_titles_with_metadata()

```python
def extract_by_titles_with_metadata(
    self,
    titles: List[str],
    threshold: int = 2100
) -> ExtractionResult
```

Extract multiple documents with complete metadata including line counts. Designed for multi-document scenarios where cumulative line count tracking is critical for determining whether post-processing is required.

**Parameters:**
- `titles`: List of document titles to extract
- `threshold`: Line count threshold for requiring post-processing (default: 2100)

**Returns:** `ExtractionResult` object

```python
extractor = MarkdownDocExtractor()
result = extractor.extract_by_titles_with_metadata([
    "Hooks reference",
    "Deployment guide",
    "Best practices"
])

# Check if processing is required
if result.requires_processing:
    print(f"Need to process: {result.total_line_count} lines")
    # Invoke md-doc-processor
else:
    print(f"Within threshold: {result.total_line_count} lines")
    # Return directly

# Print summary
print(result.to_summary())
```

#### search_documents()

```python
def search_documents(self, title: str) -> List[Dict[str, Any]]
```

Search for documents matching a title pattern with detailed information including similarity scores.

**Parameters:**
- `title`: The title pattern to search for

**Returns:** List of dictionaries containing:
- `title`: The matched document title
- `similarity`: Similarity score (for fuzzy search)
- `doc_name_version`: Document name and version (e.g., `"code_claude_com:latest"`)

```python
extractor = MarkdownDocExtractor(search_mode="fuzzy")
results = extractor.search_documents("agent skills")

for result in results:
    print(f"{result['title']} (similarity: {result['similarity']:.2f})")
    print(f"  Source: {result['doc_name_version']}")
```

#### list_available_documents()

```python
def list_available_documents(
    self,
    doc_name_version: str | None = None
) -> List[str]
```

List all available document titles.

**Parameters:**
- `doc_name_version`: Optional document name and version filter (e.g., `"code_claude_com:latest"`). If None, lists all documents from all sets.

**Returns:** List of available document titles

```python
extractor = MarkdownDocExtractor()

# List all documents
all_docs = extractor.list_available_documents()

# List from specific document set
claude_docs = extractor.list_available_documents("code_claude_com:latest")
```

#### get_document_info()

```python
def get_document_info(self, title: str) -> Dict[str, Any] | None
```

Get detailed information about a document.

**Parameters:**
- `title`: The document title

**Returns:** Dictionary containing:
- `title`: Document title
- `doc_name_version`: Document name and version
- `path`: Full path to docContent.md
- `exists`: Whether the file exists
- `size`: File size in bytes (if exists)

Returns `None` if document is not found.

```python
extractor = MarkdownDocExtractor()
info = extractor.get_document_info("Agent Skills - Claude Code Docs")

if info:
    print(f"Size: {info['size']} bytes")
    print(f"Path: {info['path']}")
```

#### extract_by_title_with_candidates()

```python
def extract_by_title_with_candidates(
    self,
    title: str,
    max_candidates: int = 5,
    min_threshold: float = 0.5
) -> List[Dict[str, Any]]
```

Extract multiple candidate documents matching the query. Returns multiple documents that match the query, sorted by similarity.

**Parameters:**
- `title`: The title query to search for
- `max_candidates`: Maximum number of candidates to return
- `min_threshold`: Minimum similarity threshold (0.0 to 1.0)

**Returns:** List of dictionaries containing:
- `title`: Document title
- `similarity`: Similarity score (0.0 to 1.0)
- `doc_name_version`: Document name and version
- `content_preview`: First 200 characters of content

```python
extractor = MarkdownDocExtractor()
candidates = extractor.extract_by_title_with_candidates("agent skills", max_candidates=3)

for c in candidates:
    print(f"{c['title']} (similarity: {c['similarity']:.2f})")
    print(f"  Preview: {c['content_preview'][:100]}...")
```

#### semantic_search_titles()

```python
def semantic_search_titles(
    self,
    query: str,
    doc_set: str | None = None,
    max_results: int = 10
) -> List[Dict[str, Any]]
```

Semantic search across document titles using multiple search strategies. Combines exact match, partial match, and fuzzy matching.

**Parameters:**
- `query`: The search query
- `doc_set`: Optional document set filter (e.g., `"code_claude_com:latest"`)
- `max_results`: Maximum number of results to return

**Returns:** List of dictionaries containing:
- `title`: Document title
- `similarity`: Similarity score (0.0 to 1.0)
- `match_type`: Type of match (`"exact"`, `"partial"`, `"fuzzy"`)
- `doc_name_version`: Document name and version

```python
extractor = MarkdownDocExtractor()
results = extractor.semantic_search_titles("hooks", max_results=5)

for r in results:
    print(f"{r['title']} ({r['match_type']}, similarity: {r['similarity']:.2f})")
```

#### extract_with_compression()

```python
def extract_with_compression(
    self,
    title: str,
    query: str | None = None,
    summarize_prompt: str | None = None
) -> Dict[str, Any]
```

Extract document content with automatic compression for large documents. For documents exceeding the compress_threshold, applies intelligent compression based on the query or smart truncation.

**Parameters:**
- `title`: The document title to extract
- `query`: Optional query for relevance-based compression
- `summarize_prompt`: Optional custom prompt for summarization (future use)

**Returns:** Dictionary containing:
- `title`: Document title
- `content`: Document content (compressed or original)
- `line_count`: Number of lines in content
- `compressed`: Whether compression was applied
- `compression_ratio`: Compression ratio (0.0 to 1.0)
- `compression_method`: Method used (`"query_based"`, `"smart_truncate"`, or `None`)

```python
extractor = MarkdownDocExtractor(enable_compression=True, compress_threshold=100)
result = extractor.extract_with_compression("Large Doc", query="API reference")

if result['compressed']:
    print(f"Compressed: {result['compression_ratio']:.0%}")
    print(f"Method: {result['compression_method']}")
```

## Data Classes

### ExtractionResult

Result of multi-document extraction with metadata.

```python
@dataclass
class ExtractionResult:
    contents: Dict[str, str]
    total_line_count: int
    individual_counts: Dict[str, int] = field(default_factory=dict)
    requires_processing: bool = False
    threshold: int = 2100
    document_count: int = 0
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `contents` | `Dict[str, str]` | Dictionary mapping document titles to their content |
| `total_line_count` | `int` | Cumulative line count across all extracted documents |
| `individual_counts` | `Dict[str, int]` | Dictionary mapping document titles to their line counts |
| `requires_processing` | `bool` | Whether total line count exceeds threshold |
| `threshold` | `int` | The threshold used for requires_processing check |
| `document_count` | `int` | Number of successfully extracted documents |

#### Methods

**to_summary()**
```python
def to_summary(self) -> str
```

Return a human-readable summary of the extraction result.

```python
result = extractor.extract_by_titles_with_metadata(["Hooks", "Deployment"])
print(result.to_summary())
```

**Example output:**
```
📊 Extraction Result Summary:
   Documents extracted: 2
   Total line count: 2500
   Threshold: 2100
   ⚠️  THRESHOLD EXCEEDED by 400 lines
   → md-doc-processor SHOULD be invoked

 Individual document breakdown:
   - Hooks: 1200 lines
   - Deployment: 1300 lines
```

## Directory Structure

The expected directory structure is:

```
md_docs/
└── <doc_name>:<doc_version>/
    └── <PageTitle>/
        └── docContent.md
```

**Example:**
```
md_docs/
└── code_claude_com:latest/
    ├── Agent Skills - Claude Code Docs/
    │   └── docContent.md
    ├── Slash Commands/
    │   └── docContent.md
    └── Hooks reference/
        └── docContent.md
```

## Search Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `exact` | Requires exact title match | Known exact titles |
| `case_insensitive` | Case-insensitive exact match | Titles with uncertain casing |
| `fuzzy` | Fuzzy string matching with similarity threshold | Typos or approximate titles |
| `partial` | Matches titles containing query as substring | Searching for keywords in titles |

## Exceptions

| Exception | Description |
|-----------|-------------|
| `BaseDirectoryNotFoundError` | Base directory doesn't exist |
| `ConfigurationError` | Invalid configuration parameter |
| `DocumentNotFoundError` | Document file doesn't exist |
| `InvalidTitleError` | Invalid title provided |
| `NoDocumentsFoundError` | No documents found in directory |
| `SingleFileNotFoundError` | Single file path is invalid |

## Example Usage

```python
from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor, ExtractionResult

# Basic usage
extractor = MarkdownDocExtractor()
content = extractor.extract_by_title("Agent Skills - Claude Code Docs")

# Multi-document with metadata (recommended for agents)
result = extractor.extract_by_titles_with_metadata([
    "Hooks reference",
    "Deployment guide"
])
if result.requires_processing:
    # Invoke md-doc-processor
    print(f"Need processing: {result.total_line_count} lines")
else:
    print(result.to_summary())

# Compression mode
extractor = MarkdownDocExtractor(enable_compression=True, compress_threshold=100)
result = extractor.extract_with_compression("Large Doc", query="API")

# Semantic search
results = extractor.semantic_search_titles("hooks", max_results=10)

# Document info
info = extractor.get_document_info("Agent Skills")
```

## See Also

- [CLI Reference](cli.md)
- [SKILL.md](../SKILL.md) - Main skill documentation
- Source: `doc4llm/tool/md_doc_retrieval/doc_extractor.py`
