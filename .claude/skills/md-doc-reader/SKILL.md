---
name: md-doc-reader
description: Extract content from markdown documents by title in the knowledge base configured in `.claude/knowledge_base.json`. Use this skill when Claude needs to read documentation pages that were previously scraped and converted to markdown, query specific titles within documentation sets, extract content from the knowledge base directory or individual .md files, or search and list available documentation titles. Supports exact, case-insensitive, fuzzy, and partial matching modes.
allowed-tools:
  - Bash
disable-model-invocation: true
context: fork
---

# Markdown Document Reader

Extract content from markdown documents in the knowledge base directory configured in `.claude/knowledge_base.json` using the `MarkdownDocExtractor`.

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
conda run -n k8s python .claude/skills/md-doc-reader/scripts/extract_md_doc.py \
  --extractor-config .claude/skills/md-doc-reader/scripts/extractor_config.json \
  --config '{"page_title": "Agent Skills", "doc_set": "doc_set@version"}'
```

**With config file (recommended for complex extractions):**
```bash
conda run -n k8s python .claude/skills/md-doc-reader/scripts/extract_md_doc.py \
  --extractor-config .claude/skills/md-doc-reader/scripts/extractor_config.json \
  --config params.json
```

## MANDATORY: CLI-Only Extraction

**CRITICAL: You MUST use CLI for all document extraction operations.**

**NEVER use Read/Glob tools to directly access docContent.md files.**


### CLI-Only Patterns

| Instead of... | Always use... |
|--------------|---------------|
| `Read "path/to/docContent.md"` | `conda run -n k8s python .claude/skills/md-doc-reader/scripts/extract_md_doc.py --extractor-config .claude/skills/md-doc-reader/scripts/extractor_config.json --config '{"page_title": "Page Title", "doc_set": "doc_set@version"}'` |
| `wc -l path/to/docContent.md` | `conda run -n k8s python .claude/skills/md-doc-reader/scripts/extract_md_doc.py --extractor-config .claude/skills/md-doc-reader/scripts/extractor_config.json --config '{"page_title": "Page Title", "doc_set": "doc_set@version"}' --doc-info` |
| `Glob "**/docContent.md"` | `conda run -n k8s python .claude/skills/md-doc-reader/scripts/extract_md_doc.py --extractor-config .claude/skills/md-doc-reader/scripts/extractor_config.json --config '{"doc_set": "doc_set@version"}' --list` |
| `Search for docs matching "query"` | `conda run -n k8s python .claude/skills/md-doc-reader/scripts/extract_md_doc.py --extractor-config .claude/skills/md-doc-reader/scripts/extractor_config.json --config '{"page_title": "query"}' --search` |
| Manual file traversal | CLI extraction with appropriate parameters |

### Quick CLI Reference

**VIOLATION: Using Read/Glob tools for docContent.md access is prohibited.**

## Usage Scenarios

| Scenario | Approach | Reason |
|----------|----------|--------|
| Called from other skills/agents | **CLI (MANDATORY)** | Zero context overhead - script executes without loading into context |
| Interactive exploration | **CLI** | Quick ad-hoc queries |

**NOTE: Direct Read/Glob tool access to docContent.md is PROHIBITED. Always use CLI.**

## Search Modes

| Mode | Description |
|------|-------------|
| `exact` | Requires exact title match |
| `case_insensitive` | Case-insensitive exact match |
| `fuzzy` | Fuzzy string matching with similarity threshold |
| `partial` | Matches titles containing query as substring |

## Directory Structure

Expected format:
```
<base_dir>/
└── <doc_name>@<doc_version>/
    └── <PageTitle>/
        └── docContent.md
```

Where `<base_dir>` is configured in `.claude/knowledge_base.json` (default: `md_docs`).

### --config vs --extractor-config

| Parameter | Purpose | Configuration Items |
|-----------|---------|---------------------|
| `--config` | Extraction operation parameters | page_title, doc_set, sections, format, with_metadata, etc. |
| `--extractor-config` | MarkdownDocExtractor initialization | search_mode, fuzzy_threshold, compression, fallback modes, etc. |

**Usage:**
- `--extractor-config`: Points to `extractor_config.json` for extractor behavior settings
- `--config`: Points to operation params for the specific extraction task

```bash
# Example: Using both parameters
conda run -n k8s python .claude/skills/md-doc-reader/scripts/extract_md_doc.py \
  --extractor-config .claude/skills/md-doc-reader/scripts/extractor_config.json \
  --config '{"page_title": "Agent Skills", "doc_set": "doc_set@latest"}'
```

## Unified Parameter Structure (Recommended)

All parameters can be passed via a JSON file or inline JSON string using `--config`. This provides a single, consistent interface for all extraction scenarios.

### Parameter Schema

```json
{
  "with_metadata": false,
  "threshold": 2100,
  "format": "text",
  "search_mode": "exact",
  "fuzzy_threshold": 0.6,
  "doc_set": "doc_name@version",

  // Single document: ["Title"]
  // Multiple documents: ["Title1", "Title2", "Title3"]
  // Single document with headings: [{"title": "Title", "headings": ["Heading1"]}]
  // Multiple doc-sets: [{"title": "Title1", "doc_set": "DocSet1@version"}, {"title": "Title2", "doc_set": "DocSet2@version"}]
  "page_titles": ["文档标题"] | ["标题1", "标题2"] | [{"title": "标题", "headings": ["章节"]}] | [...]
}
```

### page_titles Element Format

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Document page title (required) |
| `headings` | string[] | Optional, specific sections to extract |
| `doc_set` | string | Optional, overrides top-level doc_set |

### Usage Scenarios

**Single document:**
```json
{
  "page_titles": ["Agent Skills"],
  "doc_set": "Claude_Code_Docs@latest"
}
```

**Multiple documents:**
```json
{
  "page_titles": ["Agent Skills", "Slash Commands", "Hooks"],
  "doc_set": "Claude_Code_Docs@latest",
  "with_metadata": true,
  "threshold": 2100
}
```

**Single document with specific sections:**
```json
{
  "page_titles": [{"title": "Agent Skills", "headings": ["Create Skills"]}],
  "doc_set": "Claude_Code_Docs@latest"
}
```

**Multiple doc-sets with sections:**
```json
{
  "page_titles": [
    {
      "title": "Agent Skills",
      "headings": ["Create Skills", "Configure Hooks"],
      "doc_set": "OpenCode_Docs@latest"
    },
    {
      "title": "API Reference",
      "headings": ["Authentication"],
      "doc_set": "Anthropic_Docs:v2"
    },
    {
      "title": "Getting Started",
      "doc_set": "Other_Docs@latest"
    }
  ]
}
```

**List documents:**
```json
{
  "doc_set": "Claude_Code_Docs@latest"
}
```

### CLI Usage

```bash
# Using config file
conda run -n k8s python .claude/skills/md-doc-reader/scripts/extract_md_doc.py \
  --extractor-config .claude/skills/md-doc-reader/scripts/extractor_config.json \
  --config params.json

# Using inline JSON
conda run -n k8s python .claude/skills/md-doc-reader/scripts/extract_md_doc.py \
  --extractor-config .claude/skills/md-doc-reader/scripts/extractor_config.json \
  --config '{"page_titles":["Agent Skills"],"doc_set":"Claude_Code_Docs@latest"}'

# With output format
conda run -n k8s python .claude/skills/md-doc-reader/scripts/extract_md_doc.py \
  --extractor-config .claude/skills/md-doc-reader/scripts/extractor_config.json \
  --config params.json --format json

# List documents via config
conda run -n k8s python .claude/skills/md-doc-reader/scripts/extract_md_doc.py \
  --extractor-config .claude/skills/md-doc-reader/scripts/extractor_config.json \
  --config '{"doc_set":"Claude_Code_Docs@latest"}' --list
```

### Required Parameters by Scenario

| Scenario | doc_set | page_titles | headings |
|----------|---------|-------------|----------|
| Single document | Required | Required | Optional |
| Multiple documents | Required | Required | N/A |
| Document with sections | Required | Required | Optional |
| Multiple doc-sets | Optional* | Required | Optional |
| List documents | Required | N/A | N/A |

*When each `page_titles` item has its own `doc_set`, the top-level `doc_set` can be omitted.
