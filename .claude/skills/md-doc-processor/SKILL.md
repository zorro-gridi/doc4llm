---
name: md-doc-processor
description: "Post-process extracted markdown documentation to decide between returning full content or performing intelligent compression. Conditionally invoked as Phase 3 of doc-retriever agent workflow ONLY when: (1) document exceeds 2100 lines (threshold 2000 + buffer 100), OR (2) user explicitly requested compression. Receives user query, full document content, and line count from doc-retriever agent. Detects explicit full-content requests (Chinese: 不压缩/完整内容/完整版, English: full content/don't compress/no compression) and performs query-relevant intelligent summarization when needed."
allowed-tools:
  - Read
  - Bash
---

# Markdown Document Post-Processor

## Overview

This skill is the **post-processing phase** of the doc-retriever agent workflow. It receives complete document content from md-doc-reader and intelligently decides whether to return full content or perform query-relevant compression based on user intent and document size.

## Position in Workflow

```
Phase 1: md-doc-searcher  →  Phase 2: md-doc-reader  →  Phase 2.5: Conditional Check
     (Find titles)              (Extract full content)       (Decide: invoke Phase 3?)
                                                               │
                                        ┌──────────────────────┴──────────────────────┐
                                        │                                             │
                                  [SKIP Phase 3]                            [INVOKE Phase 3]
                                  Return directly                           You (md-doc-processor)
                                                                        (Decide: full or compress?)
                                                                                ↓
                                                                         Final Output to User
```

## When You Are Invoked

You are **NOT** always invoked. The doc-retriever agent performs a conditional check after Phase 2:

**You ARE invoked when:**
- Document line count > 2100 (exceeds threshold + buffer)
- User explicitly requested compression ("压缩", "总结", "summary", etc.)

**You are NOT invoked when:**
- Document line count ≤ 2100 AND user did not request compression
- → Content returned directly to user without processing

**Compression Threshold Rules:**
| Line Count Range | Action |
|------------------|--------|
| ≤ 2000 | No compression (within base threshold) |
| 2001 - 2100 | No compression (within buffer zone) |
| > 2100 | Compress to ~2000 lines (target threshold) |

**Key Concepts:**
- **Base Threshold**: 2000 lines
- **Buffer Zone**: ±100 lines (2001-2100)
- **Target Output**: ~2000 lines when compression is triggered

## Input from doc-retriever Agent

You receive the following from the doc-retriever agent:

1. **User's original query** - The search query provided by the user
2. **Complete document content** - Full markdown content from md-doc-reader
3. **Line count** - Number of lines in the document

## Decision Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: User Query + Full Content + Line Count              │
│  (Note: You are only invoked when processing is needed)      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: User Intent Analysis                               │
│  Check for explicit full-content keywords:                   │
│  - Chinese: 不压缩, 完整内容, 完整版, 原文, 全部内容, 不要压缩   │
│  - English: full content, don't compress, no compression,    │
│             complete, original, uncompressed                 │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
    [Keywords Detected]              [No Keywords]
            │                               │
            ▼                               ▼
┌───────────────────────┐   ┌───────────────────────────────┐
│ RETURN FULL CONTENT   │   │  Perform Intelligent          │
│ (bypass compression)  │   │  Compression/Summary          │
└───────────────────────┘   │  (User wants compression or    │
                            │   doc is large and no         │
                            │   full-content request)       │
                            └───────────────────────────────┘
```

**Note:** Since you are only invoked when processing is needed, the "line count ≤ 2100" check is already handled by doc-retriever agent's conditional check. You focus on intent analysis and compression quality.

## Decision Rules

### Rule 1: Explicit Full Content Request (Bypass Compression)

**Trigger:** ANY full-content keyword present in user query

**Action:** Return original content unchanged, regardless of document size

| Language | Keywords |
|----------|----------|
| Chinese | "不压缩", "完整内容", "完整版", "原文", "全部内容", "不要压缩" |
| English | "full content", "don't compress", "no compression", "complete", "original", "uncompressed" |

---

### Rule 2: Perform Intelligent Compression/Summary

**Trigger:** No full-content keywords AND processing is needed

**When this applies:**
- Document is large (>2100 lines) and user didn't request full content
- User explicitly requested compression ("压缩", "总结", "summary", "condense")

**Action:** Perform query-relevant intelligent summarization

---

## Intelligent Compression Guidelines

When Rule 3 is triggered, perform query-relevant intelligent summarization:

### Core Principles

1. **Semantic Fidelity** - Absolutely faithful to original content
   - Do NOT alter technical meaning
   - Do NOT rephrase in ways that change intent
   - Preserve all critical information

2. **Query Optimization** - Structure summary based on user's search intent
   - Identify what user is looking for
   - Prioritize sections relevant to query
   - Maintain logical flow

3. **Smart Extraction** - NOT crude truncation
   - Extract complete relevant sections
   - Preserve code blocks and examples
   - Maintain document structure

### Compression Strategy

```
Original Document (e.g., 2850 lines)
    │
    ▼
1. Check compression target
   - Target: ~2000 lines (base threshold)
   - Calculate reduction needed: ~850 lines to remove
    │
    ▼
2. Analyze user query intent
   - What is user looking for?
   - Which sections are most relevant?
    │
    ▼
3. Identify high-relevance sections
   - Match query keywords with headings
   - Score sections by relevance
    │
    ▼
4. Extract complete relevant content
   - Keep full sections (not partial)
   - Preserve code blocks
   - Maintain code examples
    │
    ▼
5. Structure compressed output to ~2000 lines
   - Start with overview/introduction
   - Include most relevant sections
   - Add navigation notes for skipped sections
   - Add mandatory compression notice at end
    │
    ▼
Compressed Output (~2000 lines with notice)
```

### What to Preserve

| Content Type | Preservation Strategy |
|--------------|----------------------|
| **Code blocks** | Always preserve completely |
| **API definitions** | Always preserve completely |
| **Configuration examples** | Always preserve completely |
| **Query-relevant sections** | Preserve in full |
| **Overview/Introduction** | Preserve |
| **Critical warnings** | Always preserve |

### What to Compress

| Content Type | Compression Strategy |
|--------------|----------------------|
| **Unrelated sections** | Omit entirely |
| **Repetitive examples** | Keep 1-2 representative examples |
| **Verbose explanations** | Summarize key points |
| **Optional/advanced topics** | Note existence, skip detail |

### Output Format

When performing intelligent compression, structure output as:

```markdown
# [Document Title]

## Overview
[Brief introduction from original document]

## Relevant Content for: "[User Query]"
[Extracted sections relevant to query]

---

### 文档来源 (Sources)
[Source information...]

---

**注意：原始文档已被压缩输出；原文: [X] 行, 压缩后: [Y] 行**
```

---

## Sources Format (REQUIRED)

**CRITICAL:** ALL content returned to the user MUST include a **Sources** section at the end. This applies to both full content and compressed output.

### Required Sources Format

After the main content, always append a Sources section:

```markdown

---

### 文档来源 (Sources)

1. **Document Title**
   - 原文链接: https://original-url.com/docs/page
   - 路径: `md_docs/<doc_name>:<doc_version>/<PageTitle>/docContent.md`

2. **Another Document Title**
   - 原文链接: https://original-url.com/docs/another-page
   - 路径: `md_docs/<doc_name>:<doc_version>/<AnotherPageTitle>/docContent.md`
```

### Example with Sources

```markdown
# Hooks Reference

## Overview
Hooks are automation scripts that run at specific points in your workflow...

## Configuration for Deployment
[Content...]

---

**注意：源文档已被压缩输出；原文: 2850 行, 压缩后: 1980 行**

### 文档来源 (Sources)

1. **Hooks reference**
   - 原文链接: https://code.claude.com/docs/en/hooks
   - 路径: `md_docs/Claude_Code_Docs:latest/Hooks reference/docContent.md`
```

### How to Get Source Information

Extract from the docContent.md files:

1. **Original URL**: Found at the top of each document:
   ```markdown
   > **原文链接**: https://code.claude.com/docs/en/common-workflows
   ```

2. **Local Path**: Construct using the directory structure:
   ```
   md_docs/<doc_name>:<doc_version>/<PageTitle>/docContent.md
   ```

### Why Sources Are Required

- **Transparency** - Users can verify and trace the information source
- **Credibility** - Shows where the information came from
- **Debugging** - Helps identify outdated documentation
- **Best Practice** - Follows academic and professional documentation standards

## Examples

### Example 1: Explicit Full Content Request (Large Document)

**Input from doc-retriever agent:**
- Query: "查找关于 Hooks 的文档，返回完整内容，不要压缩"
- Content: [2850 lines of complete content]
- Line count: 2850
- **Why invoked:** Line count > 2100 (exceeds threshold + buffer)

**Intent Analysis:** Keywords detected: "完整内容", "不要压缩"

**Decision:** RETURN FULL CONTENT (Rule 1)

**Output:** [All 2850 lines unchanged, with Sources section appended]

```markdown
[Full 2850 lines of content...]

### 文档来源 (Sources)

1. **Hooks reference**
   - 原文链接: https://code.claude.com/docs/en/hooks
   - 路径: `md_docs/Claude_Code_Docs:latest/Hooks reference/docContent.md`
```

---

### Example 2: User Requested Compression (Small Document)

**Input from doc-retriever agent:**
- Query: "Find content about Agent Skills，请压缩总结"
- Content: [450 lines of complete content]
- Line count: 450
- **Why invoked:** User explicitly requested compression

**Intent Analysis:** No full-content keywords, but user requested compression ("压缩", "总结")

**Decision:** INTELLIGENT COMPRESSION (Rule 2)

**Process:**
1. Query intent: "Agent Skills" general overview
2. Extract most relevant sections for summary

**Compressed Output:** [~150 lines focusing on core Agent Skills concepts, with Sources section]

```markdown
# Agent Skills

## Overview
[Core concepts...]

## Key Features
[Relevant content...]

### 文档来源 (Sources)

1. **Agent Skills**
   - 原文链接: https://code.claude.com/docs/en/agent-skills
   - 路径: `md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md`
```

---

### Example 3: Large Document - Intelligent Compression

**Input from doc-retriever agent:**
- Query: "How to configure hooks for deployment?"
- Content: [2850 lines from "Hooks reference"]
- Line count: 2850
- **Why invoked:** Line count > 2100 (exceeds threshold + buffer)

**Intent Analysis:** No full-content keywords, processing needed

**Decision:** INTELLIGENT COMPRESSION (Rule 2)

**Process:**
1. Query intent: "configure hooks for deployment"
2. Relevant sections identified:
   - "Hooks Configuration"
   - "Deployment Hooks"
   - "Hook Parameters"
3. Irrelevant sections:
   - "Hook Development Guide"
   - "Advanced Hook Patterns"
   - "Hook Debugging"

**Compressed Output Structure:**
```markdown
# Hooks Reference

## Overview
Hooks are automation scripts that run at specific points in your workflow...

## Configuration for Deployment

### Setting Up Deployment Hooks
[Full section on deployment hook setup]

### Deployment Hook Parameters
[Full parameter reference with code examples]

### Common Deployment Patterns
[Relevant code examples]

---

**注意：原始文档已被压缩输出；原文: 2850 行, 压缩后: 1980 行**

### 文档来源 (Sources)

1. **Hooks reference**
   - 原文链接: https://code.claude.com/docs/en/hooks
   - 路径: `md_docs/Claude_Code_Docs:latest/Hooks reference/docContent.md`
```

---

## Integration Notes

This skill works as part of the doc-retriever agent orchestration:

1. **Conditional invocation** - You are only invoked when processing is needed:
   - Document > 2100 lines (exceeds 2000 threshold + 100 buffer), OR
   - User explicitly requested compression

2. **Do NOT call** md-doc-reader or md-doc-searcher directly

3. **Wait for** doc-retriever agent to provide input (query + content + line count)

4. **Process** the provided content according to decision rules

5. **Return** final content to doc-retriever agent for delivery to user

**Performance Note:** The conditional check in doc-retriever agent (Phase 2.5) ensures you are only invoked when necessary, optimizing overall workflow efficiency.

## Quality Standards

When performing intelligent compression:

- ✅ Maintain technical accuracy
- ✅ Preserve code syntax and structure
- ✅ Keep complete relevant sections (not partial sentences)
- ✅ Add clear notes about what was compressed
- ❌ Do NOT cut sentences mid-way
- ❌ Do NOT alter code examples
- ❌ Do NOT change technical terminology
- ❌ Do NOT lose critical warnings or cautions
