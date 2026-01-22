---
name: md-doc-reader
description: "Extract content from markdown documents by title in the knowledge base configured in `.opencode/knowledge_base.json`. Use this skill when Claude needs to read documentation pages that were previously scraped and converted to markdown, query specific titles within documentation sets, extract content from the knowledge base directory or individual .md files, or search and list available documentation titles. Supports exact, case-insensitive, fuzzy, and partial matching modes."
context: fork
---

# Markdown Document Reader

Extract content from markdown documents in the knowledge base directory configured in `.opencode/knowledge_base.json` using the `MarkdownDocExtractor`.

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

## CLI-First Design

This skill uses a **CLI-first design**. All operations are executed through CLI scripts to ensure zero context overhead and consistent behavior.

## Quick Start

**CLI (recommended - zero context overhead):**
```bash
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py --title "Agent Skills" --doc-set "doc_set:version"
```

## MANDATORY: CLI-Only Extraction

**CRITICAL: You MUST use CLI for all document extraction operations.**

**NEVER use Read/Glob tools to directly access docContent.md files.**

### Why CLI-Only is Required

1. **Zero context overhead**: CLI scripts execute without loading into context
2. **Consistent behavior**: All extractions go through the same code path
3. **Proper metadata**: CLI provides line counts, document info, and extraction results
4. **Error handling**: CLI scripts provide consistent error messages

### CLI-Only Patterns

| Instead of... | Always use... |
|--------------|---------------|
| `Read "path/to/docContent.md"` | `python scripts/extract_md_doc.py --title "Page Title" --doc-set "doc_set:version"` |
| `wc -l path/to/docContent.md` | `python scripts/extract_md_doc.py --title "Page Title" --doc-set "doc_set:version" --doc-info` |
| `Glob "**/docContent.md"` | `python scripts/extract_md_doc.py --list --doc-set "doc_set:version"` |
| Manual file traversal | CLI extraction with appropriate parameters |

### Quick CLI Reference

```bash
# Extract full document (REQUIRED pattern)
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py \
  --title "Agent Skills" \
  --doc-set "Claude_Code_Docs:latest"

# Extract with metadata (for threshold checking)
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py \
  --title "Agent Skills" \
  --doc-set "Claude_Code_Docs:latest" \
  --with-metadata

# Get document info
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py \
  --title "Agent Skills" \
  --doc-set "Claude_Code_Docs:latest" \
  --doc-info

# List documents
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py \
  --list \
  --doc-set "Claude_Code_Docs:latest"
```

**VIOLATION: Using Read/Glob tools for docContent.md access is prohibited.**

## Usage Scenarios

| Scenario | Approach | Reason |
|----------|----------|--------|
| Called from other skills/agents | **CLI (MANDATORY)** | Zero context overhead - script executes without loading into context |
| Interactive exploration | **CLI** | Quick ad-hoc queries |

**NOTE: Direct Read/Glob tool access to docContent.md is PROHIBITED. Always use CLI.**

For complete documentation:
- [CLI Reference](reference/cli.md) - Complete CLI documentation
- [Configuration](reference/config.md) - Config options and priority

## Search Modes

| Mode | Description |
|------|-------------|
| `exact` | Requires exact title match |
| `case_insensitive` | Case-insensitive exact match |
| `fuzzy` | Fuzzy string matching with similarity threshold |
| `partial` | Matches titles containing query as substring |

## Section Extraction by Headings

**NEW:** Extract specific sections from a document using heading titles for token-efficient retrieval.

### CLI Usage

```bash
# Extract specific sections by headings
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py \
  --title "Agent Skills" \
  --headings "Create Skills,Configure Hooks" \
  --doc-set "code_claude_com:latest"

# Output in JSON format
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py \
  --title "Agent Skills" \
  --headings "Create Skills,Configure Hooks" \
  --format json
```

### CLI Arguments (Section Extraction)

| Argument | Type | Description |
|----------|------|-------------|
| `--title` | string | **Required** document page title |
| `--headings` | string | Comma-separated heading names for section extraction (optional) |
| `--doc-set` | string | **Required** document set identifier (e.g., "code_claude_com:latest") |
| `--format` | string | Output format: `text` (default), `json`, or `summary` |

**CRITICAL REQUIRED PARAMETERS:**
- **`--title`**: **Required for ALL CLI invocations** (except when using `--list`, `--titles-csv`, `--titles-file`, or `--semantic-search`)
- **`--doc-set`**: **Required for ALL CLI invocations**

These parameters ensure the correct document and section are targeted from the correct document set.

**Benefits:**
- Token-efficient: Only extract relevant sections identified by md-doc-searcher
- Precise: Content matches searcher-identified headings exactly
- Fast: Smaller content = faster LLM processing

## Directory Structure

Expected format:
```
<base_dir>/
└── <doc_name>:<doc_version>/
    └── <PageTitle>/
        └── docContent.md
```

Where `<base_dir>` is configured in `.opencode/knowledge_base.json` (default: `md_docs`).

## CLI Parameter Decision Guide

### Scenario 1: Single Document (Full Content)
```bash
# CRITICAL: --doc-set is REQUIRED for all CLI calls
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py \
  --title "Agent Skills" \
  --doc-set "code_claude_com:latest"
```

### Scenario 2: Section Extraction (by Headings)
```bash
# Extract specific sections - --doc-set is REQUIRED
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py \
  --title "Agent Skills" \
  --headings "Create Skills,Configure Hooks" \
  --doc-set "code_claude_com:latest"
```

### Scenario 3: Multiple Documents (Full Content)
```bash
# Extract multiple documents with metadata - --doc-set is REQUIRED
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py \
  --titles-csv "Agent Skills,Slash Commands,Hooks" \
  --doc-set "code_claude_com:latest" \
  --with-metadata \
  --threshold 2100
```

### Scenario 4: Multi-Section Extraction (Multiple Documents with Headings)

**NEW:** Extract specific sections from multiple documents, maintaining title-headings associations.

**CLI Usage (JSON file):**
```bash
# Create sections.json file
cat > sections.json << 'EOF'
[
  {
    "title": "Agent Skills",
    "headings": ["Create Skills", "Configure Hooks"],
    "doc_set": "code_claude_com:latest"
  },
  {
    "title": "Hooks Reference",
    "headings": ["Hook Types", "Configuration"],
    "doc_set": "code_claude_com:latest"
  }
]
EOF

# Extract using --sections-file
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py \
  --sections-file sections.json \
  --format json
```

**CLI Usage (inline JSON):**
```bash
conda run -n k8s python .opencode/skills/md-doc-reader/scripts/extract_md_doc.py \
  --sections-json '[{"title":"Agent Skills","headings":["Create Skills"],"doc_set":"code_claude_com:latest"}]' \
  --format json
```

**Benefits:**
- Token-efficient: Only extract relevant sections from multiple documents
- Maintains associations: Title-headings pairs preserved via composite keys
- Cumulative tracking: Automatic line count across all sections
- Ideal for doc-retriever workflow: Directly use Phase 1 JSON output

### Parameter Decision Tree

```
What do you want to extract?
│
├─ Multiple documents, each with specific sections?
│  └─ Use: --sections-file sections.json OR --sections-json '[...]' (NEW)
│     └─ Format: JSON array of {title, headings[], doc_set} objects
│
├─ Single document, full content?
│  └─ Use: --title "Document Title" --doc-set "doc_set:version"
│     └─ --doc-set: **REQUIRED**
│
├─ Specific sections within a single document?
│  └─ Use: --title "Document Title" --headings "Heading1,Heading2" --doc-set "doc_set:version"
│     └─ --doc-set: **REQUIRED**
│
├─ Multiple documents, full content?
│  └─ Use: --titles-csv "Doc1,Doc2,Doc3" --doc-set "doc_set:version"
│     └─ --with-metadata: Recommended (gets line counts)
│     └─ --doc-set: **REQUIRED**
│
└─ List available documents?
   └─ Use: --list --doc-set "doc_set:version"
      └─ --doc-set: **REQUIRED**
```

### Common Mistakes to Avoid

| Mistake | Error | Fix |
|---------|-------|-----|
| **Missing `--title` in ANY CLI call** | `--title is required unless using --list, --titles-csv, --titles-file, --semantic-search, --sections-file, or --sections-json` | **Always add** `--title "Your Page Title"` |
| **Missing `--doc-set` in ANY CLI call** | Document not found or ambiguous results | **Always add** `--doc-set "your_doc_set:version"` |
| Using `--title` with `--titles-csv` | Conflicting arguments | Use only one title specification method |
| Wrong `--doc-set` format | Document not found | Use format: `"doc_name:version"` (e.g., `"code_claude_com:latest"`) |
| **Invalid JSON in `--sections-json`** | JSON decode error | Ensure valid JSON array with proper escaping |

### Why --doc-set is Always Required

1. **Multiple document sets**: Your knowledge base may contain multiple document sets (e.g., "code_claude_com:latest", "anthropic_docs:v2")
2. **Title collisions**: Different document sets may contain pages with identical titles
3. **Deterministic behavior**: Explicitly specifying the document set ensures consistent and predictable results
4. **Performance**: Directly targeting a specific document set is faster than searching all sets
