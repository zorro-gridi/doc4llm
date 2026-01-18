---
name: md-doc-searcher
description: Search and discover markdown documents in the doc4llm md_docs directory using semantic understanding. Use this skill when Claude needs to find documents matching a query, list available documentation, search document titles by understanding user intent, or discover which documentation sets contain relevant content. Performs comprehensive search across relevant documentation sets and returns exhaustive list of relevant document titles with coverage verification.
allowed-tools:
  - Read
  - Glob
  - Bash
---

# Markdown Document Searcher

Search and discover markdown documents in the doc4llm md_docs directory structure using semantic matching.

This skill focuses on **document discovery** - finding which documents match your query. For content extraction, use the `md-doc-reader` skill.

## Quick Start

When a user requests document search, follow this workflow:

1. **List documentation sets** - Use `ls -1 md_docs/` and **filter based on user's query intent**
2. **Select target set(s)** - Choose the most relevant documentation set(s). For generic/cross-cutting queries, consider searching MULTIPLE sets.
3. **List document directories** - Use `Glob` or `Bash(ls)` in the selected set(s)
4. **Read docTOC.md files** - Use `Read` tool to get table of contents for context
5. **Semantic matching** - Use language understanding to match query with document titles
6. **Apply progressive fallback** - If Level 1 returns insufficient results, trigger Level 2 (TOC grep) then Level 3 (cross-set search)
7. **Verify coverage completeness** - CRITICAL: Check if search results are comprehensive. Expand search if gaps exist.
8. **Return comprehensive list** - Provide exhaustive list with coverage notes indicating what is/isn't covered

**Example:**
```
User: "查找关于配置 Claude Code 的文档"

Step 1: List and filter doc sets
  → Available: Claude_Code_Docs:latest, Python_Docs:3.11, ...
  → Filter: User mentioned "Claude Code" → Select Claude_Code_Docs:latest

Step 2-6: Search within Claude_Code_Docs:latest
  → Semantic match for "配置" (configuration)
  → Results:
    - Claude Code settings
    - Model configuration
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

### Step 2: List Document Directories in Specified Set

Use `Glob` or `Bash(find)` to discover document directories **within the specified set**:

```bash
# Method 1: Using find with path restriction
find md_docs/Claude_Code_Docs:latest -type d -mindepth 1

# Method 2: Using Glob pattern
md_docs/Claude_Code_Docs:latest/*/

# Expected structure:
# md_docs/<doc_name>:<doc_version>/<PageTitle>/
```

**Key point:** Specify the full path including the documentation set to limit search scope.

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

#### Level 3: Cross-Set + Full Content (Last Resort)

**Trigger:** Level 2 returns 0 results

**Commands:**
```bash
# Cross-set TOC search
grep -r -i "keyword" md_docs/*/docTOC.md

# If still empty, content search
grep -r -i "keyword" md_docs/*/docContent.md
```

**Note:** This is the slowest but provides maximum recall. Only invoke when Level 1 and Level 2 both return 0 results.

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

### 6. Sources Format (REQUIRED when returning content)

**IMPORTANT:** If you extract and return document content (e.g., when document is ≤ 1000 lines or user explicitly requests full content), you MUST include a **Sources** section at the end.

This is the same format requirement as `md-doc-processor` skill - see that skill's documentation for full details.

#### Required Format

```markdown

---

### 文档来源 (Sources)

1. **Document Title**
   - 原文链接: https://original-url.com/docs/page
   - 路径: `md_docs/<doc_name>:<doc_version>/<PageTitle>/docContent.md`
```

#### Example

```markdown
# Common workflows

[Content...]

### 文档来源 (Sources)

1. **Common workflows**
   - 原文链接: https://code.claude.com/docs/en/common-workflows
   - 路径: `md_docs/Claude_Code_Docs:latest/Common workflows/docContent.md`
```

#### How to Get Source Information

1. **Original URL**: Found at the top of docContent.md:
   ```markdown
   > **原文链接**: https://code.claude.com/docs/en/common-workflows
   ```

2. **Local Path**: `md_docs/<doc_name>:<doc_version>/<PageTitle>/docContent.md`

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
              │  - List directories            │
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
                                                  │  Level 3: Max Recall         │
                                                  │  - Cross-set TOC + Content   │
                                                  │  - Slowest but comprehensive│
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

This skill is designed to work with the `doc-retriever` agent for document discovery tasks:

1. **Discovery Phase** (this skill): Find matching document directories
2. **Extraction Phase** (`md-doc-reader` skill): Extract content from found documents

When the `doc-retriever` agent needs to find documents:

1. **List available doc sets** - Use `ls -1 md_docs/`
2. **Apply intent filtering** - Filter doc sets based on user's query:
   - Explicit mentions (e.g., "Claude" → `*Claude*`)
   - Domain-specific terms (e.g., "hooks" → Claude Code context)
   - **NEW: Check for generic/cross-cutting patterns** (e.g., "best practices" → search ALL sets)
   - Ask user if ambiguous
3. **List directories in selected set(s)** - Use `Glob` or `Bash(ls)` with full path
4. **Read docTOC.md for context** - Use `Read` tool to get table of contents
5. **Apply semantic matching** - Use language understanding, NOT simple keyword matching
6. **Apply progressive fallback** - Trigger Level 2 (TOC grep) or Level 3 (cross-set) if needed
7. **Verify coverage completeness** - CRITICAL: Check if search is comprehensive
   - Assess query type (generic vs framework-specific)
   - Check result diversity
   - Identify gaps and expand search if needed
8. **Return comprehensive list with coverage notes** - Provide exhaustive list with what is/isn't covered
9. **Delegate to md-doc-reader** - Extract content from found documents

**Critical:** Always specify the documentation set path when listing directories:
- ✅ `find md_docs/Claude_Code_Docs:latest -type d -mindepth 1`
- ❌ `find md_docs -type d -mindepth 2` (too broad, searches all sets)

## Workflow Example

**User query:** "在 Claude_Code_Docs:latest 中查找关于 skills 的文档"

**Step 1:** 列出文档集并根据意图过滤
```bash
# 列出所有文档集
ls -1 md_docs/
# Output:
# Claude_Code_Docs:latest
# Python_Docs:3.11
# React_Docs:v18

# 根据用户意图过滤：用户明确提到 "Claude_Code_Docs:latest"
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

**Step 3:** 语义匹配（通过 Prompt 指令）

读取相关文档的 `docTOC.md` 获取更多上下文：
```bash
# Read md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md
```

使用语义理解进行匹配：
- 查询 "skills" → 匹配 "Agent Skills"
- 考虑上下文：用户想要了解 Agent Skills 相关内容
- 返回匹配的文档标题列表

**返回结果格式：**
```
Found 1 relevant document(s):

1. **Agent Skills** - Relevance: Direct match for "skills" query
```

**Step 4:** 委托给 md-doc-reader 提取内容
```python
# 使用 md-doc-reader skill 提取内容
from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor
extractor = MarkdownDocExtractor()
content = extractor.extract_by_title("Agent Skills")
```

**Step 5:** 返回内容时包含 Sources

如果直接返回内容（文档 ≤ 1000 行或用户请求完整内容），必须添加 Sources 部分：

```markdown
# Agent Skills

[文档内容...]

### 文档来源 (Sources)

1. **Agent Skills**
   - 原文链接: https://code.claude.com/docs/en/agent-skills
   - 路径: `md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md`
```

### Workflow Example: Progressive Fallback in Action

**User query:** "查找如何配置 hooks 进行部署"
*(Query: "Find how to configure hooks for deployment")*

**Step 1:** 列出文档集并根据意图过滤
```bash
ls -1 md_docs/
# Output: Claude_Code_Docs:latest
# 目标文档集: Claude_Code_Docs:latest
```

**Step 2:** 在指定文档集中列出所有目录
```bash
ls -1 md_docs/Claude_Code_Docs:latest/
# Returns many directories, but none directly match "configure hooks for deployment"
```

**Step 3:** 语义匹配（Level 1）
```bash
# Semantic match on titles
# Result: Found 1 match with low similarity (max_sim = 0.5)
# Example: "Hooks" → similarity: 0.5
```

**Decision:** max_sim (0.5) < threshold (0.7) → **Trigger Level 2 fallback**

**Step 3.5:** 触发渐进式回退策略

**Level 1 quality insufficient → 进入 Level 2**

提取核心关键词: `configure`, `hooks`, `deployment`

```bash
# Level 2: TOC grep fallback
grep -r -iE "(configure|hooks|deployment)" md_docs/Claude_Code_Docs:latest/*/docTOC.md
```

**Result:** Found matches in TOC files
```
md_docs/Claude_Code_Docs:latest/Hooks reference/docTOC.md:   ## Configure hooks
md_docs/Claude_Code_Docs:latest/Get started with Claude Code hooks/docTOC.md:   ## Deployment hooks
```

**返回结果:**
```
Found 2 relevant document(s) via Level 2 fallback:

1. **Hooks reference** - Relevance: TOC contains "Configure hooks" section
2. **Get started with Claude Code hooks** - Relevance: TOC contains "Deployment hooks" section
```

**Level 3 未触发** (Level 2 已返回结果)

**Step 4:** 委托给 md-doc-reader 提取内容并添加 Sources

```python
# 使用 md-doc-reader skill 提取内容
from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor
extractor = MarkdownDocExtractor()
content = extractor.extract_by_title("Hooks reference")
```

返回时包含 Sources：

```markdown
# Hooks Reference

[文档内容...]

### 文档来源 (Sources)

1. **Hooks reference**
   - 原文链接: https://code.claude.com/docs/en/hooks
   - 路径: `md_docs/Claude_Code_Docs:latest/Hooks reference/docContent.md`

2. **Get started with Claude Code hooks**
   - 原文链接: https://code.claude.com/docs/en/hooks-get-started
   - 路径: `md_docs/Claude_Code_Docs:latest/Get started with Claude Code hooks/docContent.md`
```

---

**⚠️ Updated Logic (v2.1):** Level 2 is now triggered when:
1. **No results** (results = 0), OR
2. **Low quality matches** (max_similarity < 0.7)

This ensures better matching by falling back to TOC content search when title-only matching produces insufficient results.

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

**Important:** Always limit searches to a specific documentation set:

| Method | Command | Scope |
|--------|---------|-------|
| **Incorrect** | `find md_docs -type d -mindepth 2` | Searches ALL documentation sets |
| **Correct** | `find md_docs/Claude_Code_Docs:latest -type d -mindepth 1` | Searches ONLY specified set |
| **Correct** | Glob pattern `md_docs/Claude_Code_Docs:latest/*/` | Searches ONLY specified set |

**Why this matters:**
- Prevents cross-contamination between different documentation sets
- Ensures accurate semantic matching within the correct domain
- Improves search performance by reducing search space

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
