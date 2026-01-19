# CLI Reference: extract_md_doc.py

The `extract_md_doc.py` script provides a command-line interface for extracting markdown documents from the doc4llm md_docs directory structure.

## Usage

```bash
python scripts/extract_md_doc.py [OPTIONS]
```

## CLI Arguments

### Basic Options

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--title` | `-t` | string | - | Document title to extract (required unless using --list, --titles-csv, --titles-file, or --semantic-search) |
| `--base-dir` | `-b` | string | `md_docs` | Base documentation directory |
| `--file` | `-f` | string | - | Single .md file path for single-file mode |
| `--search-mode` | `-s` | choice | `exact` | Search mode: `exact`, `case_insensitive`, `fuzzy`, `partial` |
| `--fuzzy-threshold` | `-T` | float | `0.6` | Fuzzy threshold 0.0-1.0 for fuzzy matching |
| `--max-results` | `-m` | int | - | Maximum results for fuzzy/partial search |

### Discovery Options

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--list` | `-l` | flag | - | List available documents instead of extracting |
| `--search` | `-S` | flag | - | Search for documents matching the title |
| `--doc-info` | - | flag | - | Get document metadata |
| `--semantic-search` | - | flag | - | Use semantic search (combines multiple search strategies) |
| `--doc-set` | - | string | - | Filter by document set (e.g., `anthropic:claude-docs`) |

### Multi-Document Extraction

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--titles-csv` | - | string | - | Comma-separated titles for multi-document extraction |
| `--titles-file` | - | string | - | File containing titles (one per line) |
| `--with-metadata` | - | flag | - | Return ExtractionResult with line counts |
| `--threshold` | - | int | `2100` | Threshold for requires_processing check |

### Advanced Options

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--compress` | - | flag | - | Enable compression mode |
| `--compress-query` | - | string | - | Query for relevance-based compression |
| `--candidates` | - | flag | - | Extract candidate matches |
| `--max-candidates` | - | int | `5` | Max candidates to return |
| `--min-threshold` | - | float | `0.5` | Min similarity threshold for candidates |

### Output Options

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--format` | - | choice | `text` | Output format: `text`, `json`, `summary` |
| `--json` | `-j` | flag | - | Output in JSON format (shorthand for `--format json`) |

### Configuration

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--config` | `-c` | string | - | Path to config.json file |
| `--debug` | `-d` | flag | - | Enable debug output |

## Configuration Loading Priority

The CLI loads configuration in the following order (highest to lowest priority):

1. **`--config` CLI argument** - Explicitly specified config file
2. **`scripts/config.json`** - Skill's default config file
3. **Hardcoded defaults** - Built-in default values
4. **Deprecated package config** - Old location (shows warning)

## Basic Operations

### List Available Documents

```bash
# List all documents
python scripts/extract_md_doc.py --list

# JSON output
python scripts/extract_md_doc.py --list --format json
```

### Extract Single Document

```bash
# Exact match (default)
python scripts/extract_md_doc.py --title "Agent Skills"

# Case-insensitive search
python scripts/extract_md_doc.py --title "agent skills" --search-mode case_insensitive

# Fuzzy matching
python scripts/extract_md_doc.py --title "agent skills" --search-mode fuzzy --fuzzy-threshold 0.7

# Partial matching
python scripts/extract_md_doc.py --title "skills" --search-mode partial
```

### Single File Mode

```bash
# Work with a single markdown file
python scripts/extract_md_doc.py --title "Guide" --file /path/to/file.md

# List single file title
python scripts/extract_md_doc.py --file /path/to/file.md --list
```

### Search for Documents

```bash
# Search with similarity scores
python scripts/extract_md_doc.py --title "skills" --search

# JSON output for parsing
python scripts/extract_md_doc.py --title "skills" --search --format json
```

## Multi-Document Extraction

### Comma-Separated Titles

```bash
python scripts/extract_md_doc.py --titles-csv "Hooks,Deployment,Best practices"
```

### Titles from File

```bash
# Create titles.txt with one title per line
python scripts/extract_md_doc.py --titles-file titles.txt
```

### With Metadata (Recommended for doc-retriever)

```bash
# Returns ExtractionResult with line counts and processing flag
python scripts/extract_md_doc.py \
  --titles-csv "Hooks,Deployment" \
  --with-metadata \
  --threshold 2100 \
  --format json

# Summary format
python scripts/extract_md_doc.py \
  --titles-csv "Hooks,Deployment" \
  --with-metadata \
  --format summary
```

**Example JSON output:**
```json
{
  "contents": {
    "Hooks": "...",
    "Deployment": "..."
  },
  "total_line_count": 2500,
  "individual_counts": {
    "Hooks": 1200,
    "Deployment": 1300
  },
  "requires_processing": true,
  "threshold": 2100,
  "document_count": 2
}
```

## Advanced Operations

### Compression Mode

```bash
# Compress large documents using query-based extraction
python scripts/extract_md_doc.py \
  --title "Large API Reference" \
  --compress \
  --compress-query "authentication methods"

# JSON output shows compression metrics
python scripts/extract_md_doc.py \
  --title "Large Doc" \
  --compress \
  --format json
```

**Example output:**
```json
{
  "title": "Large API Reference",
  "content": "...",
  "line_count": 5000,
  "compressed": true,
  "compression_ratio": 0.35,
  "compression_method": "query_based"
}
```

### Candidate Extraction

```bash
# Get multiple matches with similarity scores
python scripts/extract_md_doc.py \
  --title "skills" \
  --candidates \
  --max-candidates 5 \
  --format summary

# With custom threshold
python scripts/extract_md_doc.py \
  --title "api" \
  --candidates \
  --min-threshold 0.7
```

### Semantic Search

```bash
# Combines exact, partial, and fuzzy matching
python scripts/extract_md_doc.py \
  --title "hooks" \
  --semantic-search \
  --max-results 10

# Filter by document set
python scripts/extract_md_doc.py \
  --title "authentication" \
  --semantic-search \
  --doc-set "anthropic:claude-docs"
```

### Document Metadata

```bash
# Get detailed document info
python scripts/extract_md_doc.py \
  --title "Agent Skills" \
  --doc-info

# Summary format
python scripts/extract_md_doc.py \
  --title "Agent Skills" \
  --doc-info \
  --format summary
```

## Output Formats

### text (default)

Plain text output of document content.

```bash
python scripts/extract_md_doc.py --title "Agent Skills"
```

### json

Structured JSON for programmatic parsing.

```bash
python scripts/extract_md_doc.py --title "Agent Skills" --format json
```

### summary

Human-readable summary with key metrics.

```bash
python scripts/extract_md_doc.py --title "Agent Skills" --format summary
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (document not found, import error, etc.) |

## Search Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `exact` | Requires exact title match (case-sensitive if configured) | Known exact titles |
| `case_insensitive` | Case-insensitive exact match | Titles with uncertain casing |
| `fuzzy` | Fuzzy string matching with similarity threshold | Typos or approximate titles |
| `partial` | Matches titles containing query as substring | Searching for keywords in titles |

## Examples

### Common Workflows

```bash
# Quick lookup: list then extract
python scripts/extract_md_doc.py --list | grep -i skill
python scripts/extract_md_doc.py --title "Agent Skills"

# Batch extraction for agent workflow
python scripts/extract_md_doc.py \
  --titles-file queries.txt \
  --with-metadata \
  --threshold 2100 \
  --format json > results.json

# Find similar titles when exact match fails
python scripts/extract_md_doc.py --title "auth" --semantic-search

# Handle large documents
python scripts/extract_md_doc.py \
  --title "Large Reference" \
  --compress \
  --compress-query "API endpoints"
```

## See Also

- [Python API Reference](python_api.md)
- [SKILL.md](../SKILL.md) - Main skill documentation
