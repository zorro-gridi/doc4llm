---
name: md-doc-searcher
description: Search and discover markdown documents in the doc4llm md_docs directory using semantic understanding. Use this skill when Claude needs to find documents matching a query, list available documentation, search document titles by understanding user intent, or discover which documentation sets contain relevant content. Performs comprehensive search across relevant documentation sets and returns exhaustive list of relevant document titles with coverage verification.
allowed-tools:
  - Read
  - Glob
  - Bash
context: fork
---

# Markdown Document Searcher

Search and discover markdown documents in the doc4llm md_docs directory structure using semantic matching.

## Data Flow Integration

**Input Source:** This skill receives **optimized queries from `md-doc-query-optimizer`** skill, not raw user queries.

```
┌─────────────────────────────────────────────────────────────┐
│                   Query Optimization Phase                  │
│                   (md-doc-query-optimizer)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ 3-5 optimized queries
                            │ with strategy annotations
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Document Discovery Phase                  │
│                      (md-doc-searcher)                       │
│                                                              │
│  Input: Optimized queries from Phase 0                      │
│  Output: Document titles with TOC paths                     │
└─────────────────────────────────────────────────────────────┘
```

**Why This Matters:**
- **Multi-perspective search:** Receives 3-5 query variations instead of a single raw query
- **Better recall:** Decomposition, expansion, and translation strategies improve coverage
- **Language handling:** Pre-translated queries (Chinese→English) improve matching accuracy
- **Ambiguity resolution:** Multiple query variants capture different interpretations

## Core Principle

This skill focuses on **document discovery via TOC (Table of Contents)** - finding which documents match your query by searching `docTOC.md` index files.

**CRITICAL:**
- ✅ **DO:** Search `docTOC.md` files and return TOC paths
- ✅ **DO:** Use `grep -B 10` for context when needed (Level 3.2)
- ❌ **DON'T:** Use `Read` tool to load entire `docContent.md` files
- ❌ **DON'T:** Return `docContent.md` paths as primary results

**Workflow:** This skill finds documents → returns `docTOC.md` paths → `md-doc-reader` skill extracts content

This follows the **progressive disclosure** principle: discover structure first (TOC), then access content later.

## Helper Functions (v2.6.0)

This skill now leverages helper functions for deterministic operations, while preserving LLM semantic understanding for core matching logic.

```python
from doc4llm.tool.md_doc_extractor import SearchHelpers

# Path construction
SearchHelpers.build_toc_glob_pattern(doc_set)      # → "md_docs/<doc_set>/*/docTOC.md"
SearchHelpers.build_toc_path(doc_set, title)        # → "md_docs/<doc_set>/<title>/docTOC.md"
SearchHelpers.build_content_path(doc_set, title)    # → "md_docs/<doc_set>/<title>/docContent.md"

# Command construction (for Level 2/3 fallback)
SearchHelpers.build_level2_grep_command(keywords, doc_set)
SearchHelpers.build_level3_content_grep_command(keywords, doc_sets, context_lines=10)

# Extraction helpers
SearchHelpers.extract_original_url(toc_content)     # Extract source URL from TOC
SearchHelpers.extract_keywords(query)               # Basic keyword extraction
SearchHelpers.build_title_extraction_command(path, max_lines=5)

# Formatting helpers
SearchHelpers.format_sources_section(titles_and_urls)
SearchHelpers.format_coverage_section(covered, partial, not_covered, suggestion)

# Documentation set helpers
SearchHelpers.get_list_command(base_dir="md_docs")  # → "ls -1 md_docs/"
SearchHelpers.build_doc_set_filter_pattern(intent_keywords)
```

**Key Principle:** These helpers handle repetitive formatting and construction tasks. Core semantic understanding (intent analysis, concept matching, context reasoning) remains with the LLM.

## Quick Start

When invoked with optimized queries from `md-doc-query-optimizer`, follow this workflow:

**Input:** 3-5 optimized queries (e.g., ["hooks configuration", "setup hooks", "hooks settings"])

1. **List documentation sets** - Use `SearchHelpers.get_list_command()` and **filter based on optimized queries**
2. **Select target set(s)** - Choose the most relevant documentation set(s). For generic/cross-cutting queries, consider searching MULTIPLE sets.
3. **List docTOC.md files** - Use `Glob` or `SearchHelpers.build_toc_glob_pattern()`
4. **Read docTOC.md files** - Use `Read` tool to get table of contents for context
5. **Multi-query semantic matching** - Search with ALL optimized queries, aggregate results, deduplicate
6. **Apply progressive fallback** - If Level 1 returns insufficient results, trigger Level 2 (TOC grep) then Level 3 (cross-set + content search with context traceback)
7. **Verify coverage completeness** - CRITICAL: Check if search results are comprehensive. Expand search if gaps exist.
8. **Return comprehensive list** - Provide exhaustive list with TOC paths, coverage notes, and Sources section

**Example:**
```
Input from md-doc-query-optimizer:
  1. "hooks configuration" - translation
  2. "setup hooks" - expansion
  3. "hooks settings" - expansion

Step 1: List and filter doc sets
  → Available: Claude_Code_Docs:latest, Python_Docs:3.11, ...
  → Filter: Optimized queries indicate "hooks" → Select Claude_Code_Docs:latest

Step 2-3: List docTOC.md files in selected set
  → Glob: md_docs/Claude_Code_Docs:latest/*/docTOC.md
  → Or use: SearchHelpers.build_toc_glob_pattern("Claude_Code_Docs:latest")

Step 4-6: Multi-query search within Claude_Code_Docs:latest
  → Search with query 1: "hooks configuration"
  → Search with query 2: "setup hooks"
  → Search with query 3: "hooks settings"
  → Aggregate and deduplicate results
  → Results:
    - Hooks reference (matched by queries 1, 2, 3)
    - Get started with Claude Code hooks (matched by query 2)
  → TOC Paths returned for md-doc-reader use
```

## Discovery Workflow

### Step 1: Identify Documentation Set with Intent Filtering

First, list available documentation sets and **filter based on user's query intent**:

```bash
# Use helper to get the list command
SearchHelpers.get_list_command()  # → "ls -1 md_docs/"
# Then execute via Bash tool
```

**Intent-Based Filtering (LLM Semantic Analysis):**
- If user mentions "Claude", "Claude Code" → Filter to `*Claude*` sets
- If user mentions "Python" → Filter to `*Python*` sets
- If user mentions specific framework → Filter to matching sets
- If no specific mention → Ask user to clarify or search all sets

**Examples:**

| User Query | Filter To | Reason |
|------------|-----------|--------|
| "Claude Code 中关于 skills 的文档" | `Claude_Code_Docs:latest` | User explicitly mentioned Claude Code |
| "Python 异常处理文档" | `*Python*` | User mentioned Python |
| "如何配置 hooks" | `Claude_Code_Docs:latest` (context) | "hooks" suggests Claude Code context |
| "所有关于 deployment 的文档" | Ask user | Multiple sets may contain deployment info |

**Helper for filtered patterns:**
```python
SearchHelpers.build_doc_set_filter_pattern(["Claude", "Code"])
# → "md_docs/*Claude* md_docs/*Code*"
```

**Important:** Always search within a **specific documentation set** to ensure accurate results. If multiple sets match the query, ask the user to confirm which one to search.

### Step 2: List Document TOC Files in Specified Set

**CRITICAL:** This skill focuses on **document discovery** via TOC files. Always target `docTOC.md` files, NOT directories.

**Method 1: Using Glob pattern (CORRECT)**
```bash
# Use helper to build pattern
SearchHelpers.build_toc_glob_pattern("Claude_Code_Docs:latest")
# → "md_docs/Claude_Code_Docs:latest/*/docTOC.md"
```

**Method 2: Using find command (CORRECT)**
```bash
find md_docs/Claude_Code_Docs:latest -name "docTOC.md"
```

**❌ WRONG - Do NOT use directory-only patterns:**
```bash
md_docs/Claude_Code_Docs:latest/*/
```

**Expected structure:**
```
md_docs/<doc_name>:<doc_version>/<PageTitle>/docTOC.md
```

**Key points:**
- Always specify `docTOC.md` in the pattern to limit search to TOC files only
- This ensures we're discovering documents through their index/structure, not full content
- Follows **progressive disclosure** - TOC first, content later via md-doc-reader

### Step 3: Semantic Matching (via LLM Prompt)

**Core Principle:** Use **LLM semantic understanding**, not simple keyword matching.

After listing TOC files, use semantic understanding to match the user's query:

1. **Read docTOC.md files** - For better context, read table of contents from each document
2. **Use semantic understanding** - Match related concepts using your language capabilities
3. **Consider context and intent** - Understand domain-specific terminology and user intent
4. **Return matching directories** - List relevant document paths based on semantic relevance

**Semantic Matching Examples (LLM Capabilities):**

| User Query | Should Match | Reason |
|------------|--------------|--------|
| "how to configure" | Settings, Configuration, Setup, Preferences | LLM understands these are synonyms |
| "deployment" | Enterprise deployment, Install, Setup, Production | LLM recognizes related concepts |
| "security" | Authentication, Authorization, Security settings, Permissions | LLM maps domain relationships |
| "API" | API reference, Connect, Integration, Endpoints | LLM understands technical context |

**Domain-Specific Context:**
- "hooks" in Claude Code context → Claude hooks (not webhooks)
- "skills" in AI context → Agent capabilities (not job skills)
- "deployment" in web context → Production deployment (not military deployment)

**Helper for section extraction:**
```python
from doc4llm.tool.md_doc_extractor.utils import extract_toc_sections, semantic_match_toc_sections

# Extract sections from docTOC.md content
sections = extract_toc_sections(toc_content, query="hooks", max_sections=20)
# Returns: [{'level': 2, 'title': 'Configure hooks', 'anchor': 'configure-hooks', 'line_number': 5}]

# Or semantic match existing sections
matched = semantic_match_toc_sections(sections, "hooks")
# Returns sections sorted by relevance score
```

**Benefits:**
- Structured TOC parsing with metadata
- Semantic matching on section titles
- Anchor link generation for navigation
- Line number tracking for debugging

### Step 3.5: Progressive Fallback Strategy

When Level 1 semantic matching returns **0 results OR low-quality matches** (max_similarity < 0.7), automatically invoke fallback levels:

#### Level 1: Semantic Title Matching (Default)

- Current implementation using LLM semantic understanding
- Fast path for well-titled documents
- **Quality threshold:** `max_similarity >= 0.7` to return results

#### Level 2: TOC Content Grep (Fallback)

**Trigger:** Level 1 returns 0 results **OR** `max_similarity < 0.7` (low quality matches)

**Use helper to build command:**
```python
from doc4llm.tool.md_doc_extractor import SearchHelpers

# First extract keywords
keywords = SearchHelpers.extract_keywords("how to configure hooks for deployment")
# → ['configure', 'hooks', 'deployment']

# Then build grep command
SearchHelpers.build_level2_grep_command(
    keywords=["configure", "hooks", "deployment"],
    doc_set="Claude_Code_Docs:latest"
)
# → "grep -r -iE '(configure|hooks|deployment)' md_docs/Claude_Code_Docs:latest/*/docTOC.md"
```

**Execute via Bash tool:**
```bash
grep -r -iE '(configure|hooks|deployment)' md_docs/Claude_Code_Docs:latest/*/docTOC.md
```

#### Level 3: Cross-Set + Content Search (Last Resort)

**Trigger:** Level 2 returns 0 results

**CRITICAL:** This level requires careful relevance filtering and context traceback to avoid meaningless results.

##### Level 3.1: Cross-Set TOC Search (with Relevance Constraints)

**Step 1: Extract domain keywords from user query** (LLM semantic analysis)
```python
# Example: User queries "Claude Code skills design philosophy"
# Domain keywords: Claude, Code
# Topic keywords: skills, design, philosophy
```

**Step 2: Filter documentation sets by domain relevance**
```python
# Use helper to build filter pattern
SearchHelpers.build_doc_set_filter_pattern(["Claude", "Code"])
# → "md_docs/*Claude* md_docs/*Code*"

# For "Claude Code skills", only search:
# - Claude_Code_Docs:latest
# NOT: Python_Docs, React_Docs, etc.
```

**Step 3: Search TOC files in filtered sets**
```bash
# Cross-set TOC search WITH domain filter
grep -r -i "keyword" md_docs/*Claude*/*/docTOC.md md_docs/*Code*/*/docTOC.md
```

**Why this matters:** Searching "best practices" across ALL doc sets could return Python, React, or other framework-specific practices that are irrelevant to the user's actual query context.

##### Level 3.2: docContent.md Context Search (with Traceback)

**Trigger:** Level 3.1 returns 0 results

**CRITICAL CONSTRAINTS:**
- ❌ **NEVER** use `Read` tool to load entire docContent.md files
- ✅ Only use `grep` with context to extract minimal information
- ✅ Return docTOC.md paths for subsequent use by md-doc-reader

**Search with context traceback:**
```python
# Use helper to build command
SearchHelpers.build_level3_content_grep_command(
    keywords=["design philosophy"],
    doc_sets=["Claude_Code_Docs:latest"],
    context_lines=10
)
# → "grep -r -i -B 10 'design philosophy' md_docs/Claude_Code_Docs:latest/*/docContent.md"
```

**Execute via Bash tool:**
```bash
grep -r -i -B 10 "design philosophy" md_docs/*Claude*/*/docContent.md
```

**Parse results to extract:**
1. **Documentation set name** - Extract from file path
2. **Document title** - Extract from docContent.md (first 5 lines, look for `#` headings)
3. **Match context** - The 10 lines before the match showing relevant section

**Helper for title extraction:**
```python
SearchHelpers.build_title_extraction_command(
    "md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md",
    max_lines=5
)
# → "head -5 md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md"
```

**Return format for Level 3.2:**
```markdown
Found N relevant document(s) via Level 3.2 content search:

1. **Document Title** (Doc_Set:Version)
   - Relevance: Content contains "keyword" in section context
   - Context: [Brief excerpt from grep -B 10 output]
   - TOC Path: `md_docs/<doc_set>/<PageTitle>/docTOC.md`

**Note:** Use `/md-doc-reader "Document Title"` to view full TOC and structure.
```

### Step 4: Delegate to md-doc-reader

Once relevant directories are found, delegate content extraction to `md-doc-reader` skill.

## Semantic Search Instructions

When performing document search, follow these guidelines:

### 1. Intent Filtering at Documentation Set Level

First level of filtering - determine which documentation set to search:

**Filtering Strategies:**

| Strategy | When to Use | Example |
|----------|-------------|---------|
| **Explicit mention** | User names the framework | "Python" → `*Python*` sets |
| **Domain-specific terms** | Unique terminology maps to specific set | "hooks" → Claude Code |
| **Context inference** | Current session context | Previous question about React → React docs |
| **Ask user** | Ambiguous or multiple matches | "deployment" → Ask which project |

### 2. Use Semantic Understanding, Not Keyword Matching

**❌ Avoid:** Simple keyword/substring matching
**✅ Use:** Language understanding to match concepts and context

**Core LLM Capabilities:**
- Understand synonyms and related concepts
- Recognize domain-specific terminology
- Consider context and user intent
- Distinguish homonyms based on context (e.g., "hooks" in Claude Code vs webhooks)

### 3. Consider Synonyms and Related Concepts

| User Query | Should Match (LLM Semantic Understanding) |
|------------|-------------------------------------------|
| "how to configure" | Settings, Configuration, Setup, Preferences |
| "deployment" | Enterprise deployment, Install, Setup, Production |
| "security" | Authentication, Authorization, Security settings, Permissions |
| "API" | API reference, Connect, Integration, Endpoints |

### 4. Return Format with Coverage Notes

Return results as a list of document titles with relevance notes AND coverage verification:

```markdown
Found N relevant document(s) in <doc_set>:

1. **Document Title** - Relevance: why it matches
2. **Another Title** - Relevance: contains section about topic
...

**Coverage:**
- ✅ Covered: [aspects covered by results]
- ⚠️  Partially covered: [aspects partially covered]
- ❌ Not covered: [aspects that may exist in other documents/sets]
- 💡 Suggestion: [if applicable, suggest other searches]
```

**Use helper for formatting:**
```python
SearchHelpers.format_coverage_section(
    covered=["Configuration", "Setup"],
    partial=["Advanced patterns"],
    not_covered=["Performance"],
    suggestion="Search 'performance' for optimization tips"
)
```

### 5. Sources Format (ALWAYS REQUIRED)

**CRITICAL:** You MUST include a **Sources** section at the end of ALL search results, regardless of document length or content type.

This ensures proper attribution and allows users to locate the original documents for further reading.

**Helper for formatting:**
```python
# Extract URLs from TOC content
url = SearchHelpers.extract_original_url(toc_content)

# Format sources section
SearchHelpers.format_sources_section([
    ("Agent Skills", "https://code.claude.com/docs/en/agent-skills", "md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md")
])
```

**Required Format:**
```markdown
---

### 文档来源

1. **Document Title**
   - 原文链接: https://original-url.com/docs/page
   - TOC 路径: `md_docs/<doc_name>:<doc_version>/<PageTitle>/docTOC.md`
```

## Progressive Fallback Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SEARCH REQUEST                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  Level 1: Title Semantic Match │
              │  - LLM semantic understanding  │
              │  - Fast: O(k) where k = matches│
              │  - Threshold: max_sim >= 0.7   │
              └───────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
        [Results > 0 AND                 [Results = 0 OR
         max_sim >= 0.7]                  max_sim < 0.7]
              │                               │
              ▼                               ▼
        To Coverage Check            ┌───────────────────────────────┐
                                    │  Level 2: TOC Grep Fallback   │
                                    │  - grep -r across TOC files   │
                                    │  - Balanced: O(1) operation   │
                                    └───────────────────────────────┘
                                              │
                                    ┌─────────┴─────────┐
                                    │                   │
                              [Results > 0]      [Results = 0]
                                    │                   │
                                    ▼                   ▼
                          To Coverage Check    ┌───────────────────────────────┐
                                                  │  Level 3.1: Cross-Set TOC   │
                                                  │  - Filter by domain        │
                                                  │  - grep -r across filtered │
                                                  │    doc sets                │
                                                  └───────────────────────────────┘
                                                            │
                                                  ┌─────────┴─────────┐
                                                  │                   │
                                            [Results > 0]      [Results = 0]
                                                  │                   │
                                                  ▼                   ▼
                                        To Coverage Check    ┌───────────────────────────────┐
                                                                      │  Level 3.2: Content Search │
                                                                      │  - grep -B 10 for context │
                                                                      │  - Extract title from 5   │
                                                                      │    lines (retry: 20)      │
                                                                      │  - Return TOC paths only  │
                                                                      └───────────────────────────────┘
                                                                                │
                                                                                ▼
                                                                      ┌─────────────────────────┐
                                                                      │   Coverage Completeness │
                                                                      │   Verification Check    │
                                                                      │   - Assess query type   │
                                                                      │   - Check result diversity
                                                                      │   - Identify gaps      │
                                                                      └─────────────────────────┘
                                                                                │
                                                              ┌─────────────┴─────────────┐
                                                              │                           │
                                                        [Coverage Complete]          [Gaps Found]
                                                        - Generic queries handled   - Expand scope
                                                        - All aspects covered      - Search other sets
                                                              │                           │
                                                              └─────────────┬─────────────┘
                                                                            ▼
                                                              ┌─────────────────────────┐
                                                              │    Return Results        │
                                                              │    With Coverage Notes   │
                                                              │    - What's covered       │
                                                              │    - What's not           │
                                                              │    + TOC Paths            │
                                                              └─────────────────────────┘
```

## Search Completeness Guidelines

### When is Search Considered Complete?

**CRITICAL:** A search is ONLY complete when you have **verified** that all potentially relevant documents have been found. The progressive fallback strategy finds matches within a scope, but you MUST verify coverage completeness.

#### Completeness Checklist

Before returning results, ask yourself:

- [ ] Have I searched ALL relevant documentation sets?
- [ ] Do the results cover different aspects of the query?
- [ ] Could related concepts exist in documents with different titles?
- [ ] Should I cross-reference with other documentation sets?
- [ ] Have I explicitly stated what is/isn't covered in the results?

#### Multi-Set Search Triggers

**ALWAYS search multiple documentation sets when:**

| Query Pattern | Example | Action | Rationale |
|--------------|---------|--------|-----------|
| Generic concepts | "best practices", "tips", "optimization" | Search ALL doc sets | These concepts apply across multiple domains |
| Cross-cutting concerns | "deployment", "testing", "monitoring", "security" | Search ALL doc sets | May have framework-specific and general implementations |
| Configuration/setup | "how to configure", "setup guide", "getting started" | Search ALL doc sets | Setup varies by framework/context |
| Comparison questions | "difference between X and Y", "X vs Y" | Search ALL doc sets | Requires comprehensive comparison |
| Framework-specific | "React hooks", "Python async", "Claude skills" | Single set | Terminology is domain-specific |

#### Coverage Verification Steps

After completing Level 1-3 search:

1. **Assess result diversity** - Do results cover different perspectives/aspects?
2. **Identify gaps** - What aspects of the query are NOT covered?
3. **Expand if needed** - If gaps found, search other doc sets
4. **Document coverage** - Explicitly state what IS and ISN'T covered

#### Decision Tree: Is Coverage Complete?

```
┌─────────────────────────────────────────┐
│     After Level 1-3 Search              │
└─────────────────────────────────────────┘
                  │
                  ▼
        ┌─────────────────────┐
        │ Assess Query Type   │
        └─────────────────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
Generic/Cross-cutting    Framework-specific
    │                           │
    ▼                           ▼
┌─────────────┐          ┌─────────────┐
│ Search ALL  │          │ Single set  │
│ doc sets?   │          │ sufficient │
└─────────────┘          └─────────────┘
    │                           │
    ▼                           ▼
Multiple results           Verify specific
from various sets          terms covered
    │                           │
    └─────────────┬─────────────┘
                  │
                  ▼
        ┌─────────────────────┐
        │ Document Coverage   │
        │ - What's covered     │
        │ - What's not         │
        │ - Gaps identified    │
        └─────────────────────┘
```

## Delegation Pattern

This skill is designed to work with the `doc-retriever` agent and `md-doc-query-optimizer` skill in a multi-phase retrieval workflow:

**Workflow:**
```
Phase 0: Query Optimization (md-doc-query-optimizer)
    │ Input: Raw user query
    │ Output: 3-5 optimized queries with annotations
    ▼
Phase 1: Document Discovery (this skill - md-doc-searcher)
    │ Input: Optimized queries from Phase 0
    │ Output: Document titles with TOC paths
    ▼
Phase 2: Content Extraction (md-doc-reader)
    │ Input: Document titles
    │ Output: Full content + line count
    ▼
Phase 3: Post-Processing (md-doc-processor) [Conditional]
```

When the `doc-retriever` agent needs to find documents:

1. **Receive optimized queries** - Input from `md-doc-query-optimizer` (3-5 queries with strategy annotations)
2. **List available doc sets** - Use `SearchHelpers.get_list_command()`
3. **Apply intent filtering** - Filter doc sets based on optimized queries (LLM semantic analysis)
4. **List directories in selected set(s)** - Use `Glob` or `SearchHelpers.build_toc_glob_pattern()`
5. **Read docTOC.md for context** - Use `Read` tool to get table of contents
6. **Multi-query semantic matching** - Search with ALL optimized queries using LLM semantic understanding
7. **Apply progressive fallback** - Trigger Level 2 (TOC grep) or Level 3 (cross-set) if needed
8. **Verify coverage completeness** - CRITICAL: Check if search is comprehensive
9. **Return comprehensive list with coverage notes** - Use helpers for formatting

## Workflow Example

**Input from md-doc-query-optimizer:**
```
Optimized Queries (Ranked):
1. "skills" - direct match
2. "Agent Skills" - context-specific expansion
3. "skills reference" - expansion
```

**Step 1:** 列出文档集并根据意图过滤
```bash
# Use helper to get list command
SearchHelpers.get_list_command()
# Execute: ls -1 md_docs/

# Output:
# Claude_Code_Docs:latest
# Python_Docs:3.11
# React_Docs:v18

# 根据优化查询过滤：所有查询都指向 "skills" → Claude Code context
# 目标文档集: Claude_Code_Docs:latest
```

**Step 2:** 在指定文档集中列出所有目录
```python
# Use helper to build glob pattern
SearchHelpers.build_toc_glob_pattern("Claude_Code_Docs:latest")
# → "md_docs/Claude_Code_Docs:latest/*/docTOC.md"

# Returns:
# Agent Skills/
# CLI reference/
# Hooks reference/
# ...
```

**Step 3:** 多查询语义匹配

读取相关文档的 `docTOC.md` 获取更多上下文：
```bash
# Read md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md
```

使用 LLM 语义理解进行匹配：
- 查询 1 "skills" → 匹配 "Agent Skills"
- 查询 2 "Agent Skills" → 匹配 "Agent Skills" (高相关度)
- 查询 3 "skills reference" → 匹配 "Agent Skills"
- 聚合结果并去重：{"Agent Skills"}
- 按匹配查询数量排序：Agent Skills (matched by 3 queries)

**返回结果格式：**
```markdown
Found 1 relevant document(s):

1. **Agent Skills** - Relevance: Matched by 3 optimized queries (skills, Agent Skills, skills reference)

**Coverage:**
- ✅ Covered: Skills design philosophy and working principles
- ❌ Not covered: Best practices for skill authoring
```

**Step 4:** 返回结果时始终包含 Sources

使用辅助函数提取和格式化：
```python
# Extract URL
url = SearchHelpers.extract_original_url(toc_content)

# Format sources
SearchHelpers.format_sources_section([
    ("Agent Skills", url, "md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md")
])
```

```markdown
### 文档来源

1. **Agent Skills**
   - 原文链接: https://code.claude.com/docs/en/agent-skills
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md`

**Note:** Use `/md-doc-reader "Agent Skills"` to view the full TOC and document structure.
```

---

## Version History

- **v2.6.0** - Added SearchHelpers for deterministic operations, reduced SKILL.md complexity by ~25%
- **v2.5.0** - Added Level 3.2 content search with context traceback
- **v2.4.0** - Added Level 3.1 cross-set search with domain relevance filtering
- **v2.3.0** - Added Level 2 TOC grep fallback strategy
- **v2.2.0** - Added multi-query semantic matching with result aggregation
- **v2.1.0** - Added coverage completeness verification
- **v2.0.0** - Initial release with progressive disclosure principle
