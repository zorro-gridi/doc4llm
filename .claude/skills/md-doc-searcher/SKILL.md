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

## CLI Usage

### You MUST Run one of the following Basic Commands

```bash

# Direct script execution
python .claude/skills/md-doc-searcher/scripts/doc_searcher_cli.py --query "hooks configuration"

# Use json format output for other better data flow exchange
python .claude/skills/md-doc-searcher/scripts/doc_searcher_cli.py --query "hooks configuration" --json

# Multiple queries (search for multiple terms)
python .claude/skills/md-doc-searcher/scripts/doc_searcher_cli.py --query "authentication" --query "JWT" --query "OAuth"

# Search with custom BM25 parameters
python .claude/skills/md-doc-searcher/scripts/doc_searcher_cli.py --query "api reference" --bm25-k1 1.5 --bm25-b 0.8
```

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--query` | string | **required** | Search query string (can be specified multiple times) |
| `--bm25-k1` | float | 1.2 | BM25 k1 parameter |
| `--bm25-b` | float | 0.75 | BM25 b parameter |
| `--json` | flag | false | Output structured JSON metadata instead of AOP-FINAL format |

### Structured JSON Output

When using `--json` flag, the searcher outputs machine-parsable JSON metadata:

```json
{
  "success": true,
  "doc_sets_found": ["code_claude_com:latest"],
  "results": [
    {
      "doc_set": "code_claude_com:latest",
      "page_title": "Agent Skills",
      "toc_path": "/path/to/docTOC.md",
      "headings": [
        {"level": 2, "text": "Create Skills"},
        {"level": 3, "text": "Configure Hooks"}
      ]
    }
  ]
}
```

**Purpose:** Enable downstream skills (md-doc-reader) to extract content by specific headings for token-efficient retrieval.

**Multi-Document Extraction:** When multiple results are returned, the JSON output enables md-doc-reader to extract multiple sections from multiple documents using `--sections-file` or `--sections-json` parameters, maintaining proper title-headings associations.

```markdown
=== AOP-FINAL | agent=md-doc-searcher | results={count} | doc_sets={sets} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

**{doc_name}:{doc_version}**

**{PageTitle}**
   - TOC 路径: `{base_dir}/{doc_name}:{doc_version}/{PageTitle}/docTOC.md`
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
