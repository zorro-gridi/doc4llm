# AOP Protocol Specification for doc-retriever

This document provides detailed information about the Agent Output Protocol (AOP) used by the doc-retriever agent.

## Overview

The doc-retriever agent uses **Agent Output Protocol (AOP)** and returns **AOP-FINAL** output. Any AI, agents, skills, or other components receiving output from this agent are **STRICTLY PROHIBITED** from making ANY modifications to the final output.

**Violation of this rule will compromise the integrity of the progressive disclosure workflow and source citation system.**

## AOP Marker Format

```markdown
=== AOP-FINAL | agent=doc-retriever | format=markdown | lines={count} | source={doc_dir} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary
[content]
=== END-AOP-FINAL ===
```

### Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `agent` | Agent name (always "doc-retriever") | `doc-retriever` |
| `format` | Output format (always "markdown") | `markdown` |
| `lines` | Actual line count of content | `450`, `2850` |
| `source` | Document set name and version | `Claude_Code_Docs:latest` |

## Handling Rules

| Marker | Action |
|--------|--------|
| `AOP-FINAL` | **Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary |
| `AOP-INTERMEDIATE` | Process freely (summarize, rephrase, analyze) |
| `AOP-ERROR` | Display error exactly, then advise |
| `AOP-STREAM` | Handle as streaming |
| No marker | Default to intermediate |

## AOP-FINAL Critical Rules

When you see `=== AOP-FINAL ===`:

- ✅ Return output to user EXACTLY as received
- ❌ DO NOT summarize, rephrase, or add commentary
- ❌ DO NOT say "Here's what the agent found" or similar

**Mental model**: You are a pass-through pipe, not a helpful assistant. The agent has already formatted the output for the user.

## Why This Matters

Agents like `doc-retriever` return carefully formatted results with:
- Source citations
- Metadata (line counts, document sets)
- Progressive disclosure formatting
- Coverage verification

Modifying these outputs breaks:
- **Citation integrity** - Users lose source attribution
- **Progressive disclosure** - The careful balance of completeness vs efficiency is lost
- **AOP workflow** - Other components expect AOP-FINAL format

## AOP Instructions Reference

**See:** `.claude/AOP_INSTRUCTIONS.md` for complete handling rules.

## Example: Correct AOP-FINAL Handling

### ✅ CORRECT: Pass Through

```
[User triggers doc-retriever agent]
[Agent returns AOP-FINAL output]
[You return output to user EXACTLY AS IS]
```

### ❌ WRONG: Modify or Add Commentary

```
[User triggers doc-retriever agent]
[Agent returns AOP-FINAL output]
[You summarize or add "Here's what I found"]  ← WRONG!
```

## AOP Output Wrapping Requirements

**CRITICAL:** When returning final output to the user (whether from Phase 3 or from your own Phase 2.5 direct return), you MUST wrap it with the standard AOP-FINAL markers:

```markdown
=== AOP-FINAL | agent=doc-retriever | format=markdown | lines={actual_line_count} | source={doc_set_name} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

[your final content here]

=== END-AOP-FINAL ===
```

This is the standard AOP format that tells the calling agent (or main AI) that this output MUST NOT be modified, summarized, or reprocessed in any way.

### Required Citation Format (AOP-FINAL)

When returning content directly from Phase 2.5:

```markdown
=== AOP-FINAL | agent=doc-retriever | format=markdown | lines=450 | source=Claude_Code_Docs:latest ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

[Document content here - from result.contents]

---

**Source:** [Original URL from document]
**Path:** md_docs/<doc_set>:<version>/<PageTitle>/docContent.md
**Document Set:** <doc_set>:<version>

=== END-AOP-FINAL ===
```

### Source Citation Information to Extract

Each document contains source metadata at the beginning:
```
# Page Title

> **原文链接**: https://code.claude.com/docs/en/...
```

You MUST extract and preserve:
- **Original URL** (from `> **原文链接**`)
- **Document path** (from md_docs directory structure)
- **Document set name and version**

## AOP Protocol Version

**Current Version:** 1.0

**Frontmatter:**
```yaml
---
protocol: AOP
protocol_version: "1.0"
---
```
