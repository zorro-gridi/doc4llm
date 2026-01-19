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

## Quick Start

**For agent/skill usage (recommended - zero context overhead):**
```bash
python scripts/extract_md_doc.py --title "Agent Skills"
```

**For Python integration:**
```python
from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor
extractor = MarkdownDocExtractor()
content = extractor.extract_by_title("Agent Skills")
```

## Usage Scenarios

| Scenario | Recommended Approach | Reason |
|----------|---------------------|--------|
| Called from other skills/agents | **CLI** | Zero context overhead - script executes without loading into context |
| Python code integration | **Python API** | Direct programmatic access |
| Interactive exploration | **CLI** | Quick ad-hoc queries |

For complete documentation:
- [CLI Reference](reference/cli.md) - Complete CLI documentation
- [Python API](reference/python_api.md) - API documentation
- [Configuration](reference/config.md) - Config options and priority

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
md_docs/
└── <doc_name>:<doc_version>/
    └── <PageTitle>/
        └── docContent.md
```
