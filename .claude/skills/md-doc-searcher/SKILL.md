---
name: md-doc-searcher
description: Search and discover markdown documents in the local knowledge base using BM25-based retrieval via CLI interface. Performs comprehensive search across documentation sets and returns headings lists matching query criteria.
allowed-tools:
  - Read
  - Glob
  - Bash
disable-model-invocation: true
context: fork
protocol: AOP
protocol_version: "1.0"
hooks:
    PreToolUse:
      - matcher: "Read"
        hooks:
          - type: command
            command: |
                if [[ "$TOOL_FILE_PATH" == *"docContent.md" ]]; then
                echo "DENY: Access to docContent.md is blocked"
                exit 1
                fi
---

# Markdown Document Headings Searcher

Search and discover markdown documents headings in the local knowledge base using BM25-based retrieval via CLI interface.

## Critical Constraints

- **NO docContent.md access**: Only search docTOC.md files
- **Headings hierarchy**: Maintain page_title → headings structure in output
- **AOP format**: Output must follow AOP specification exactly
- **KEEP THE SAME LANGUAGE WITH THE SOURCE DOCS**
- **Pass through**: AOP-FINAL output must not be modified

## Knowledge base config info
`.claude/knowledge_base.json`

## CLI Usage

### JSON Configuration File

Use the `--config` parameter to pass configuration via a JSON file path or JSON text directly (when value starts with `{`). All configuration keys use Python naming convention (underscores).

### Query in Doc-Set Use Case

#### 1. Single query with Single doc-set

**Example config file (`search_config.json`):**
```json
{
  "query": ["hooks configuration"],  // Multi-query: ["query1", "query2", "query3"]
  "base_dir": "/path/to/knowledge_base",
  "doc_sets": "OpenCode_Docs@latest",  // Multi doc-set: "doc1@v1,doc2@v2,doc3@latest"
  "bm25_k1": 1.2,
  "bm25_b": 0.75,
  "reranker": true,
  "reranker_threshold": 0.68,
  "domain_nouns": ["hook", "tool", "agent"],
  "predicate_verbs": ["create", "delete"],
  "json": true
}
```

#### 2. Multi query with Multi doc-set

**Multi query & multi doc-set example:**
```json
{
  "query": ["authentication", "JWT", "OAuth"],
  "base_dir": "/path/to/knowledge_base",
  "doc_sets": "api_doc@v1,auth_service@v2",
  "reranker": true,
  "reranker_threshold": 0.68,
  "json": true
}
```

**Usage with config file:**
```bash
conda run -n k8s python .claude/skills/md-doc-searcher/scripts/doc_searcher_cli.py --config search_config.json
```

**Usage with JSON text directly:**
```bash
# Pass JSON text directly (starts with '{')
conda run -n k8s python .claude/skills/md-doc-searcher/scripts/doc_searcher_cli.py --config '{"query": ["hooks"], "doc_sets": "OpenCode_Docs@latest", "base_dir": "/path/to/knowledge_base", "json": true}'
```

#### Multi Query & Multi Doc-Set Support

**query**: 支持多个查询词，格式为字符串数组 `["query1", "query2", "query3"]`

**doc_sets**: 支持多个文档集，格式为逗号分隔的字符串 `"doc1@v1,doc2@v2,doc3@latest"`

#### JSON Config Parameters

When using `--config`, the following parameters are supported (Python naming convention):

| Config Key | Type | Default | CLI Equivalent |
|------------|------|---------|----------------|
| `query` | string[] | **required** | `--query` (multiple times) |
| `base_dir` | string | **required** | `--base-dir` |
| `doc_sets` | string | **required** | `--doc-sets` |
| `reranker_threshold` | float | 0.68 | `--reranker-threshold` |
| `bm25_k1` | float | 1.2 | `--bm25-k1` |
| `bm25_b` | float | 0.75 | `--bm25-b` |
| `threshold_page_title` | float | 0.6 | `--threshold-page-title` |
| `threshold_headings` | float | 0.25 | `--threshold-headings` |
| `threshold_precision` | float | 0.7 | `--threshold-precision` |
| `min_page_titles` | int | 3 | `--min-page-titles` |
| `min_headings` | int | 2 | `--min-headings` |
| `json` | boolean | false | `--json` |
| `hierarchical_filter` | int | 1 | `--hierarchical-filter` |
| `domain_nouns` | string[] | [] | `--domain-nouns` |
| `predicate_verbs` | string[] | [] | `--predicate-verbs` |

### Structured JSON Output

When using `--json` flag, the searcher outputs machine-parsable JSON metadata:

```json
{
  "success": true,
  "toc_fallback": true,
  "grep_fallback": true,
  "query": [
    "create rules"
  ],
  "doc_sets_found": [
    "OpenCode_Docs@latest"
  ],
  "results": [
    {
      "doc_set": "OpenCode_Docs@latest",
      "page_title": "Plugins",
      "toc_path": "/path/to/docTOC.md",
      "headings": [
        {
          "level": 2,
          "text": "## 3. Create a plugin",
          "rerank_sim": 0.7079395651817322,
          "bm25_sim": 0.28768207245178085
        }
      ]
    }
  ]
}
```

**Purpose:** Enable downstream skills (md-doc-reader) to extract content by specific headings for token-efficient retrieval.

**Multi-Document Extraction:** When multiple results are returned, the JSON output enables md-doc-reader to extract multiple sections from multiple documents using `--config` with `sections` or `sections_file` parameter, maintaining proper title-headings associations.

```markdown
=== AOP-FINAL | agent=md-doc-searcher | results={count} | doc_sets={sets} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

**{doc_name}:{doc_version}**

**{PageTitle}**
   - TOC 路径: `{base-dir}/{doc_name}:{doc_version}/{PageTitle}/docTOC.md`
   - **匹配Heading列表**:
     - ## {Heading1}
     - ### {Heading2}

=== END-AOP-FINAL ===
```

### No Headings Found

If no headings found after all fallbacks:

```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=0 | doc_sets={sets} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

No matched headings found!

=== END-AOP-FINAL ===
```

## Implementation Notes

**Current Search Strategy:**
- BM25-based retrieval across docTOC.md files
- Transformer reranker for semantic re-ranking
- STRICT doc-set boundary enforcement

**Search Scope Guarantee:**
- Only searches the EXACT doc-sets specified via `--doc-sets` parameter
- No glob patterns (like `*Code*`) for cross-set matching
- No grep-based fallback searches
- No automatic doc-set expansion

**BM25 Interface:**
```python
# bm25_recall.py
def recall_pages(
    self,
    doc_set: str,  # Comma-separated: "doc1@v1,doc2@v2"
    query: Union[str, List[str]],
    min_headings: int = 2
) -> List[Dict[str, Any]]:
    # Parses doc_set and searches ONLY specified doc-sets
```

**What We DON'T Do:**
- No grep-based fallback searches
- No cross-set glob pattern matching
- No direct docContent.md access (blocked by hooks)