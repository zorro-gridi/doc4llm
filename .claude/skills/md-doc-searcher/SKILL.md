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

## Quick Start

When invoked with optimized queries from `md-doc-query-optimizer`, follow this workflow:

**Input:** 3-5 optimized queries (e.g., ["hooks configuration", "setup hooks", "hooks settings"])

1. **List documentation sets** - Use `ls -1 md_docs/` and **filter based on optimized queries**
2. **Select target set(s)** - Choose the most relevant documentation set(s). For generic/cross-cutting queries, consider searching MULTIPLE sets.
3. **List docTOC.md files** - Use `Glob` or `Bash(find)` to find TOC files: `md_docs/<doc_set>/*/docTOC.md`
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
# List all available documentation sets
ls -1 md_docs/

# Example output:
# Claude_Code_Docs:latest/
# Python_Docs:3.11/
# React_Docs:v18/
# Another_Doc:v1.0/
```

**Intent-Based Filtering:**
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

**Commands for filtered listing:**
```bash
# List all sets (for context)
ls -1 md_docs/

# Filter by pattern (e.g., Claude-related)
ls -1 md_docs/ | grep -i claude

# Or use Glob
md_docs/*Claude*/
```

**Important:** Always search within a **specific documentation set** to ensure accurate results. If multiple sets match the query, ask the user to confirm which one to search.

### Step 2: List Document TOC Files in Specified Set

**CRITICAL:** This skill focuses on **document discovery** via TOC files. Always target `docTOC.md` files, NOT directories.

Use `Glob` or `Bash(find)` to discover `docTOC.md` files **within the specified set**:

```bash
# Method 1: Using find to locate TOC files (CORRECT)
find md_docs/Claude_Code_Docs:latest -name "docTOC.md"

# Method 2: Using Glob pattern (CORRECT)
md_docs/Claude_Code_Docs:latest/*/docTOC.md

# ❌ WRONG - Do NOT use directory-only patterns
md_docs/Claude_Code_Docs:latest/*/

# Expected structure:
# md_docs/<doc_name>:<doc_version>/<PageTitle>/docTOC.md
```

**Key points:**
- Always specify `docTOC.md` in the pattern to limit search to TOC files only
- This ensures we're discovering documents through their index/structure, not full content
- Follows **progressive disclosure** principle - TOC first, content later via md-doc-reader

### Step 3: Semantic Matching (via Prompt)

After listing directories, use **semantic understanding via prompt instructions** to match the user's query:

1. **Read docTOC.md files** - For better context, read table of contents from each document
2. **Use new TOC processing utilities** - Extract and match TOC sections using the new utility functions
3. **Semantic matching** - Use your language understanding to match query intent with document content
4. **Return matching directories** - List relevant document paths based on semantic relevance

**Important:** Do NOT rely on simple keyword matching. Use your semantic understanding to:
- Match related concepts (e.g., "configuration" → "settings", "setup")
- Understand domain-specific terminology
- Consider context and user intent

**New in v2.0:** TOC Processing Utilities

The `utils` module now provides enhanced TOC processing functions:

```python
from doc4llm.tool.md_doc_extractor.utils import extract_toc_sections, semantic_match_toc_sections

# Extract sections from docTOC.md content
sections = extract_toc_sections(toc_content, query="hooks", max_sections=20)
# Returns: [{'level': 2, 'title': 'Configure hooks', 'anchor': 'configure-hooks', 'line_number': 5}]

# Or semantic match existing sections
matched = semantic_match_toc_sections(sections, "hooks")
# Returns sections sorted by relevance score
```

**TOC Extraction Workflow:**
1. Read `docTOC.md` file using `Read` tool
2. Parse sections using `extract_toc_sections()` - extracts level, title, anchor, line_number
3. Optionally filter by query or relevance using `semantic_match_toc_sections()`
4. Return matched sections with relevance scores

**Benefits:**
- Structured TOC parsing with metadata
- Semantic matching on section titles
- Anchor link generation for navigation
- Line number tracking for debugging

### Step 3.5: Progressive Fallback Strategy (NEW)

When Level 1 semantic matching returns **0 results OR low-quality matches** (max_similarity < 0.7), automatically invoke fallback levels:

#### Level 1: Semantic Title Matching (Default)
- Current implementation
- Fast path for well-titled documents
- **Quality threshold:** `max_similarity >= 0.7` to return results

#### Level 2: TOC Content Grep (Fallback)

**Trigger:** Level 1 returns 0 results **OR** `max_similarity < 0.7` (low quality matches)

**Command:**
```bash
# Extract core keywords from query and grep TOC files
grep -r -i "core_keyword" md_docs/<doc_set>/*/docTOC.md
```

**Keyword Extraction Rules:**
- Remove stop words: the, a, an, how, to, for, with, by, from, at, on, in, about
- Preserve technical terms: API, hooks, JWT, OAuth, CLI, SDK, HTTP, etc.
- Use root form: configure → config, authenticate → auth, deploy → deployment

**Example:**
```
Query: "how to configure hooks for deployment"
Keywords extracted: configure, hooks, deployment
Grep command: grep -r -iE "(configure|hooks|deployment)" md_docs/<doc_set>/*/docTOC.md
```

#### Level 3: Cross-Set + Content Search (Last Resort)

**Trigger:** Level 2 returns 0 results

**CRITICAL:** This level requires careful relevance filtering and context traceback to avoid meaningless results.

##### Level 3.1: Cross-Set TOC Search (with Relevance Constraints)

**Step 1: Extract domain keywords from user query**
```bash
# Example: User queries "Claude Code skills design philosophy"
# Domain keywords: Claude, Code
# Topic keywords: skills, design, philosophy
```

**Step 2: Filter documentation sets by domain relevance**
```bash
# List all doc sets first
ls -1 md_docs/

# Filter to only relevant sets (e.g., *Claude*, *Code*)
# For "Claude Code skills", only search:
# - Claude_Code_Docs:latest
# NOT: Python_Docs, React_Docs, etc.
```

**Step 3: Search TOC files in filtered sets**
```bash
# Cross-set TOC search WITH domain filter
grep -r -i "keyword" md_docs/*Claude*/docTOC.md md_docs/*Code*/docTOC.md
```

**Why this matters:** Searching "best practices" across ALL doc sets could return Python, React, or other framework-specific practices that are irrelevant to the user's actual query context.

##### Level 3.2: docContent.md Context Search (with Traceback)

**Trigger:** Level 3.1 returns 0 results

**CRITICAL CONSTRAINTS:**
- ❌ **NEVER** use `Read` tool to load entire docContent.md files
- ✅ Only use `grep` with context to extract minimal information
- ✅ Return docTOC.md paths for subsequent use by md-doc-reader

**Search with context traceback:**
```bash
# Use grep -B to get 10 lines of context BEFORE the match
grep -r -i -B 10 "keyword" md_docs/*RelevantSet*/docContent.md
```

**Parse results to extract:**
1. **Documentation set name** - Extract from file path
2. **Document title** - Extract from docContent.md (first 5 lines, look for `#` headings)
3. **Match context** - The 10 lines before the match showing relevant section

**Traceback workflow:**
```bash
# Step 1: Get context from grep (10 lines before match)
grep -r -i -B 10 "design philosophy" md_docs/*Claude*/docContent.md

# Step 2: Parse each result
# Input: md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md:95: ## How Skills work
# Extract:
#   - Doc set: Claude_Code_Docs:latest
#   - Document: Agent Skills
#   - Title: (from first 5 lines of that docContent.md) → "# Agent Skills"
#   - Context: Lines around the match

# Step 3: If title not found in first 5 lines, retry with more lines
# Retry: Check first 20 lines for title
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

**⚠️ Updated Logic (v2.2):** Level 3 is now split into:
- **Level 3.1:** Cross-set TOC search WITH domain relevance filtering
- **Level 3.2:** Content search with context traceback (grep -B 10, title from 5 lines with retry)

This ensures:
1. Cross-set searches respect the user's query domain (no Python results for Claude queries)
2. Content searches provide proper document attribution without loading full files
3. All results point to docTOC.md for follow-up via md-doc-reader

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

**Commands:**
```bash
# List all doc sets
ls -1 md_docs/

# Filter by pattern
ls -1 md_docs/ | grep -i python

# Check if specific set exists
ls -1 md_docs/ | grep -i claude
```

### 2. Use Semantic Understanding, Not Keyword Matching

**❌ Avoid:** Simple keyword/substring matching
**✅ Use:** Language understanding to match concepts and context

### 3. Read docTOC.md for Context

Before matching, read the `docTOC.md` file to understand the document structure:
```
Read: md_docs/<doc_set>/<PageTitle>/docTOC.md
```

### 4. Consider Synonyms and Related Concepts

| User Query | Should Match |
|------------|--------------|
| "how to configure" | Settings, Configuration, Setup, Preferences |
| "deployment" | Enterprise deployment, Install, Setup |
| "security" | Authentication, Authorization, Security settings |
| "API" | API reference, Connect, Integration |

### 5. Return Format

Return results as a list of document titles with relevance notes AND coverage verification:

```
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

**Example with coverage notes:**
```
Found 3 relevant document(s) in Claude_Code_Docs:latest:

1. **Quickstart** - Relevance: Contains "Pro tips for beginners" section
2. **Common workflows** - Relevance: Contains explicit "best practices" guidance
3. **Agent Skills** - Relevance: Covers skill usage best practices

**Coverage:**
- ✅ Covered: Workflow best practices, skill usage patterns
- ⚠️  Partially covered: Configuration best practices (check Settings doc)
- ❌ Not covered: Performance optimization, security best practices
- 💡 Suggestion: Search "performance" or "security" for those topics
```

### 6. Sources Format (ALWAYS REQUIRED)

**CRITICAL:** You MUST include a **Sources** section at the end of ALL search results, regardless of document length or content type.

This ensures proper attribution and allows users to locate the original documents for further reading.

#### Required Format

```markdown

---

### 文档来源 (Sources)

1. **Document Title**
   - 原文链接: https://original-url.com/docs/page
   - TOC 路径: `md_docs/<doc_name>:<doc_version>/<PageTitle>/docTOC.md`
```

#### Example

```markdown
Found N relevant document(s):

1. **Common workflows** - Relevance: Contains explicit "best practices" guidance

**Coverage:**
- ✅ Covered: Workflow best practices
- ❌ Not covered: Performance optimization

### 文档来源 (Sources)

1. **Common workflows**
   - 原文链接: https://code.claude.com/docs/en/common-workflows
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Common workflows/docTOC.md`
```

#### How to Get Source Information

1. **Original URL**: Found at the top of docTOC.md:
   ```markdown
   > **原文链接**: https://code.claude.com/docs/en/common-workflows
   ```

2. **Local TOC Path**: `md_docs/<doc_name>:<doc_version>/<PageTitle>/docTOC.md`

**Note:** Use `/md-doc-reader "Document Title"` to view the full TOC and document structure.

## Directory Structure

Expected format:
```
md_docs/
└── <doc_name>:<doc_version>/
    └── <PageTitle>/
        ├── docContent.md    # Main content
        └── docTOC.md        # Table of contents
```

Each `<PageTitle>` directory represents one document page.

## Progressive Fallback Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SEARCH REQUEST                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  Level 1: Title Semantic Match │
              │  - List docTOC.md files       │
              │  - Semantic understanding      │
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

#### Return Format with Coverage Notes

```markdown
Found N relevant document(s) in <doc_set>:

1. **Document Title** - Relevance: why it matches
2. **Another Title** - Relevance: contains section about topic

**Coverage:**
- ✅ Covered: [aspects covered by results]
- ⚠️  Not covered: [aspects that may exist in other documents]
- 💡 Suggestion: [if applicable, suggest other doc sets to search]
```

#### Example: Comprehensive vs Incomplete Search

**Query:** "Claude Code best practices"

**❌ Incomplete search (what was done before):**
- Single doc set: Claude_Code_Docs:latest
- 2 documents found: Quickstart, Common workflows
- Missing: Agent Skills, Settings, CLI reference

**✅ Comprehensive search (correct approach):**
- Recognize "best practices" is a generic concept
- Search ALL doc sets for "best practices", "tips", "optimization"
- Results from multiple sources:
  - Quickstart (Pro tips for beginners)
  - Common workflows (best practices section)
  - Agent Skills (skill usage best practices)
  - CLI reference (efficient CLI usage)
  - Settings (configuration best practices)

**Coverage note:** "Found 5 documents covering workflows, skills, configuration, and CLI usage. Performance optimization best practices may be in additional documentation."

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
2. **List available doc sets** - Use `ls -1 md_docs/`
3. **Apply intent filtering** - Filter doc sets based on optimized queries:
   - Extract domain keywords from optimized queries
   - Explicit mentions (e.g., "Claude" → `*Claude*`)
   - Domain-specific terms (e.g., "hooks" → Claude Code context)
   - **NEW: Check for generic/cross-cutting patterns** (e.g., "best practices" → search ALL sets)
   - Ask user if ambiguous
4. **List directories in selected set(s)** - Use `Glob` or `Bash(ls)` with full path
5. **Read docTOC.md for context** - Use `Read` tool to get table of contents
6. **Multi-query semantic matching** - Search with ALL optimized queries:
   - For each optimized query, perform semantic matching
   - Aggregate results from all queries
   - Deduplicate by document title
   - Rank by relevance (documents matched by multiple queries rank higher)
7. **Apply progressive fallback** - Trigger Level 2 (TOC grep) or Level 3 (cross-set) if needed
8. **Verify coverage completeness** - CRITICAL: Check if search is comprehensive
   - Assess query type (generic vs framework-specific)
   - Check result diversity
   - Identify gaps and expand search if needed
9. **Return comprehensive list with coverage notes** - Provide exhaustive list with what is/isn't covered
10. **Delegate to md-doc-reader** - Extract content from found documents

**Critical:** Always specify the documentation set path when listing directories:
- ✅ `find md_docs/Claude_Code_Docs:latest -type d -mindepth 1`
- ❌ `find md_docs -type d -mindepth 2` (too broad, searches all sets)

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
# 列出所有文档集
ls -1 md_docs/
# Output:
# Claude_Code_Docs:latest
# Python_Docs:3.11
# React_Docs:v18

# 根据优化查询过滤：所有查询都指向 "skills" → Claude Code context
# 目标文档集: Claude_Code_Docs:latest
```

**Step 2:** 在指定文档集中列出所有目录
```bash
ls -1 md_docs/Claude_Code_Docs:latest/

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

使用语义理解进行匹配：
- 查询 1 "skills" → 匹配 "Agent Skills"
- 查询 2 "Agent Skills" → 匹配 "Agent Skills" (高相关度)
- 查询 3 "skills reference" → 匹配 "Agent Skills"
- 聚合结果并去重：{"Agent Skills"}
- 按匹配查询数量排序：Agent Skills (matched by 3 queries)

**返回结果格式：**
```
Found 1 relevant document(s):

1. **Agent Skills** - Relevance: Matched by 3 optimized queries (skills, Agent Skills, skills reference)
```

**Step 4:** 委托给 md-doc-reader 查看完整 TOC
```python
# 使用 md-doc-reader skill 查看 TOC 结构
from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor
extractor = MarkdownDocExtractor()
toc = extractor.extract_by_title("Agent Skills")
```

**Step 5:** 返回结果时始终包含 Sources

所有搜索结果都必须包含 Sources 部分：

```markdown
Found 1 relevant document(s):

1. **Agent Skills** - Relevance: Matched by 3 optimized queries

**Coverage:**
- ✅ Covered: Skills design philosophy and working principles
- ❌ Not covered: Best practices for skill authoring

### 文档来源 (Sources)

1. **Agent Skills**
   - 原文链接: https://code.claude.com/docs/en/agent-skills
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md`

**Note:** Use `/md-doc-reader "Agent Skills"` to view the full TOC and document structure.
```

### Workflow Example: Progressive Fallback in Action

**Input from md-doc-query-optimizer:**
```
Optimized Queries (Ranked):
1. "configure hooks deployment" - decomposition
2. "hooks configuration" - translation
3. "deployment hooks" - decomposition
4. "setup hooks" - expansion
```

**Step 1:** 列出文档集并根据意图过滤
```bash
ls -1 md_docs/
# Output: Claude_Code_Docs:latest
# 根据优化查询过滤：所有查询都指向 "hooks" → Claude Code context
# 目标文档集: Claude_Code_Docs:latest
```

**Step 2:** 在指定文档集中列出所有目录
```bash
ls -1 md_docs/Claude_Code_Docs:latest/
# Returns many directories
```

**Step 3:** 多查询语义匹配（Level 1）

```bash
# Multi-query semantic match on titles
# Result: Found matches with varying similarity
# Query 1 "configure hooks deployment" → max_sim = 0.5 (low)
# Query 2 "hooks configuration" → max_sim = 0.6 (low)
# Query 3 "deployment hooks" → max_sim = 0.55 (low)
# Query 4 "setup hooks" → max_sim = 0.58 (low)
```

**Decision:** max_similarity (0.6) < threshold (0.7) → **Trigger Level 2 fallback**

**Step 3.5:** 触发渐进式回退策略

**Level 1 quality insufficient → 进入 Level 2**

从优化查询中提取核心关键词: `configure`, `hooks`, `deployment`, `setup`

```bash
# Level 2: TOC grep fallback
grep -r -iE "(configure|hooks|deployment|setup)" md_docs/Claude_Code_Docs:latest/*/docTOC.md
```

**Result:** Found matches in TOC files
```
md_docs/Claude_Code_Docs:latest/Hooks reference/docTOC.md:   ## Configure hooks
md_docs/Claude_Code_Docs:latest/Get started with Claude Code hooks/docTOC.md:   ## Deployment hooks
```

**返回结果:**
```
Found 2 relevant document(s) via Level 2 fallback:

1. **Hooks reference** - Relevance: TOC contains "Configure hooks" section (matched by queries 1, 2, 4)
2. **Get started with Claude Code hooks** - Relevance: TOC contains "Deployment hooks" section (matched by queries 1, 3)
```

**Level 3 未触发** (Level 2 已返回结果)

**Step 4:** 返回结果并包含 Sources（始终必需）

返回时必须包含 Sources：

```markdown
Found 2 relevant document(s) via Level 2 fallback:

1. **Hooks reference** - Relevance: TOC contains "Configure hooks" section
2. **Get started with Claude Code hooks** - Relevance: TOC contains "Deployment hooks" section

**Coverage:**
- ✅ Covered: Hooks configuration and deployment
- ❌ Not covered: Advanced hooks patterns

### 文档来源 (Sources)

1. **Hooks reference**
   - 原文链接: https://code.claude.com/docs/en/hooks
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Hooks reference/docTOC.md`

2. **Get started with Claude Code hooks**
   - 原文链接: https://code.claude.com/docs/en/hooks-get-started
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Get started with Claude Code hooks/docTOC.md`

**Note:** Use `/md-doc-reader "Hooks reference"` to view the full TOC and document structure.
```

---

**⚠️ Updated Logic (v2.2):** Major improvements to progressive fallback:
1. **Level 2** is triggered when: No results OR low quality matches (max_similarity < 0.7)
2. **Level 3.1** adds domain relevance filtering for cross-set TOC searches
3. **Level 3.2** adds context traceback for content searches (grep -B 10, title from 5 lines with retry)
4. **All results** now include TOC paths instead of content paths
5. **Sources section** is now always required regardless of document length

This ensures:
- Cross-set searches respect the user's query domain
- Content searches provide proper attribution without loading full files
- All results point to docTOC.md for follow-up via md-doc-reader

---

## More Intent Filtering Examples

**Example 1: Explicit framework mention**
```
User: "查找 Python 中关于装饰器的文档"

Intent filtering:
  → User mentioned "Python"
  → Filter doc sets to: *Python*
  → Selected: Python_Docs:3.11

Results:
  - Python Decorators
  - Functions (contains decorator info)
```

**Example 2: Implicit context**
```
User: "如何配置 hooks"

Intent analysis:
  → "hooks" is Claude Code specific terminology
  → Filter doc sets to: *Claude*
  → Selected: Claude_Code_Docs:latest

Results:
  - Hooks reference
  - Get started with Claude Code hooks
```

**Example 3: Ambiguous query**
```
User: "查找关于部署的文档"

Intent analysis:
  → "deployment" is generic term
  → Multiple doc sets may contain this info
  → Ask user: "您想查找哪个项目的部署文档？"
  → User clarifies: "Claude Code"
  → Proceed with Claude_Code_Docs:latest
```

**Example 4: Cross-cutting concept (Multi-Set Search) - NEW**
```
User: "Claude Code best practices"

Intent analysis:
  → "best practices" is a generic/cross-cutting concept
  → Could apply to: workflows, skills, configuration, CLI usage, etc.
  → Action: Search ALL doc sets for "best practices" OR related terms

Step 1: List all doc sets
```bash
ls -1 md_docs/
# Claude_Code_Docs:latest
# Python_Docs:3.11
# React_Docs:v18
# ...
```

Step 2: Recognize generic pattern - "best practices"
→ This is NOT framework-specific
→ Multi-set search is REQUIRED

Step 3: Comprehensive search across all sets
```bash
# Search Claude_Code_Docs:latest
grep -r -iE "(best.practice|tips|optimization|guide)" "md_docs/Claude_Code_Docs:latest/*/docTOC.md"

# Results from Claude_Code_Docs:latest:
# - Quickstart (Pro tips for beginners)
# - Common workflows (best practices section)
# - Agent Skills (skill usage best practices)
# - CLI reference (efficient CLI usage)
# - Claude Code settings (configuration best practices)
```

**Coverage verification:**
- ✅ Workflows and usage patterns covered
- ✅ Skills and configuration covered
- ✅ CLI best practices covered
- ⚠️  Performance optimization may need additional search

**Return with coverage notes:**
```
Found 5 relevant document(s) in Claude_Code_Docs:latest:

1. **Quickstart** - Relevance: Contains "Pro tips for beginners" section
2. **Common workflows** - Relevance: Contains explicit "best practices" guidance
3. **Agent Skills** - Relevance: Covers skill usage best practices
4. **CLI reference** - Relevance: Contains efficient CLI usage patterns
5. **Claude Code settings** - Relevance: Configuration best practices

**Coverage:**
- ✅ Covered: Workflows, skills, configuration, CLI usage patterns
- ⚠️  Partially covered: Performance optimization (check individual workflow docs)
- 💡 For advanced optimization techniques, consider searching for "performance" or "optimization" specifically
```

**Key difference from Example 3:**
- Example 3 (deployment): Ambiguous but context-specific → Ask user to clarify
- Example 4 (best practices): Generic/cross-cutting → Comprehensive multi-set search automatically
```

**Example 5: Configuration/setup (Multi-Set Search)**
```
User: "how to configure authentication"

Intent analysis:
  → "configure" + "authentication" = setup/configuration pattern
  → Could be framework-specific OR generic
  → Action: Start with context inference, then expand

Step 1: Check for context
→ Previous messages about Claude Code? → Search Claude_Code_Docs:latest
→ No context? → Multi-set search

Step 2: Multi-set search (no context)
```bash
# Search multiple sets for "configure" + "authentication"
for doc_set in md_docs/*/; do
  grep -r -iE "(configure.*auth|authentication.*config|setup.*auth)" "$doc_set"*/docTOC.md
done
```

Results could include:
- Claude_Code_Docs:latest → "Claude Code settings" (authentication configuration)
- Python_Docs:3.11 → "Authentication" (Python-specific auth setup)
- Generic docs → "Security configuration" patterns

**Return format:**
```
Found 3 relevant document(s) across multiple doc sets:

1. **Claude Code settings** (Claude_Code_Docs:latest)
   - Relevance: Authentication configuration for Claude Code
2. **Authentication** (Python_Docs:3.11)
   - Relevance: Python authentication setup patterns
3. **Security** (General_Docs)
   - Relevance: Generic authentication configuration

**Coverage:**
- ✅ Claude Code authentication: Covered
- ✅ Python authentication: Covered
- ✅ Generic security patterns: Covered
- 💡 Specify your framework for targeted results
```

## Search Scope Control

**Important:** Always limit searches to specific docTOC.md files within a documentation set:

| Method | Command | Scope |
|--------|---------|-------|
| **Incorrect** | `find md_docs -type d -mindepth 2` | Searches ALL documentation sets (directories) |
| **Incorrect** | `md_docs/Claude_Code_Docs:latest/*/` | Returns directories, not TOC files |
| **Correct** | `find md_docs/Claude_Code_Docs:latest -name "docTOC.md"` | Searches ONLY TOC files in specified set |
| **Correct** | Glob `md_docs/Claude_Code_Docs:latest/*/docTOC.md` | Searches ONLY TOC files in specified set |

**Why this matters:**
- Prevents cross-contamination between different documentation sets
- Ensures accurate semantic matching within the correct domain
- Improves search performance by reducing search space
- Follows **progressive disclosure** - TOC first, content later via md-doc-reader

## Keyword Extraction for Fallback Searches

When invoking Level 2 or Level 3 fallback, extract core keywords from user query:

### Extraction Rules

| Rule | Example | Extracted Keywords |
|------|---------|-------------------|
| Remove stop words | "how to configure hooks" | configure, hooks |
| Preserve technical terms | "API authentication with JWT" | API, authentication, JWT |
| Use root forms | "deploying, deployed, deployment" | deploy |
| Remove question words | "what is the best way to" | best, way |
| Split compound terms | "webhook configuration" | webhook, configuration |

### Stop Words to Remove

**Common stop words:** the, a, an, and, or, but, is, are, was, were, to, for, with, by, from, at, on, in, about, how, what, where, when, why, which, that, this, these, those

**Preserve:** API, CLI, SDK, HTTP, JWT, OAuth, hooks, config, deploy, auth, token, endpoint, webhook, middleware, etc.

### Extraction Examples

| User Query | Extracted Keywords | Grep Command |
|------------|-------------------|--------------|
| "how to configure hooks for deployment" | configure, hooks, deployment | `grep -r -iE "(configure|hooks|deployment)"` |
| "API authentication with JWT tokens" | API, authentication, JWT, tokens | `grep -r -iE "(API|authentication|JWT|tokens)"` |
| "what is the best way to deploy" | best, way, deploy | `grep -r -iE "(best|way|deploy)"` |
| "webhook configuration guide" | webhook, configuration, guide | `grep -r -iE "(webhook|configuration|guide)"` |
