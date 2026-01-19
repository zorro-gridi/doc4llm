---
name: md-doc-searcher
description: Search and discover markdown documents in the doc4llm md_docs directory using semantic understanding. Use this skill when Claude needs to find documents matching a query, list available documentation, search document titles by understanding user intent, or discover which documentation sets contain relevant content. Performs comprehensive search across relevant documentation sets and returns exhaustive list of relevant document titles with coverage verification.
allowed-tools:
  - Read
  - Glob
  - Bash
context: fork
protocol: AOP
protocol_version: "1.0"
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

## SearchHelpers API

This skill leverages helper functions for deterministic operations:

```python
from doc4llm.tool.md_doc_retrieval import SearchHelpers

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

# Content language and TOC processing (v2.9.0)
SearchHelpers.extract_toc_headings(toc_content, max_headings=10)  # Extract markdown headings
SearchHelpers.detect_content_language(content)      # Detect language: 'zh', 'en', 'mixed'
SearchHelpers.format_language_appropriate_results(results, language)  # Language-aware formatting
SearchHelpers.build_toc_content_extraction_command(toc_path, max_lines=50)

# Formatting helpers
SearchHelpers.format_sources_section(titles_and_urls)
SearchHelpers.format_coverage_section(covered, partial, not_covered, suggestion)

# Documentation set helpers
SearchHelpers.get_list_command(base_dir="md_docs")  # → "ls -1 md_docs/"
SearchHelpers.build_doc_set_filter_pattern(intent_keywords)

# Intent analysis and filtering helpers (Step 6)
SearchHelpers.analyze_query_intent(original_query)  # → Intent classification
SearchHelpers.calculate_relevance_score(doc_title, doc_context, query_intent)
SearchHelpers.format_filtered_results(high_rel, medium_rel, filtered_out)
SearchHelpers.format_filtering_summary(original_count, final_count, precision_improvement)
```

**📖 See:** `reference/search-helpers-api.md` for complete API documentation

## Quick Start

When invoked with optimized queries from `md-doc-query-optimizer`, follow this workflow:

1. **List doc sets** - Use `SearchHelpers.get_list_command()` and filter based on query intent
2. **List docTOC.md files** - Use `SearchHelpers.build_toc_glob_pattern()` + `Glob`
3. **Read TOC files** - Get table of contents for semantic matching context
4. **Multi-query matching** - Search ALL optimized queries, aggregate and deduplicate
5. **Progressive fallback** - If Level 1 fails (<0.7 similarity), trigger Level 2→3
6. **Verify coverage** - Ensure completeness, search multiple sets for generic queries
7. **Intent-based filtering** - Analyze original query intent, remove low-relevance docs (see Step 6)
8. **Extract TOC content** - Detect language and extract headings from kept results
9. **Return AOP-FINAL** - See "Return Format Requirements" section for output format

**Example:** Query "hooks configuration" → 3 optimized queries → Select Claude_Code_Docs → Multi-query search → Intent filter (CONFIGURE) → 2 high-relevance docs → AOP-FINAL output

## Core Search Workflow

### Step 1: Identify Documentation Set with Intent Filtering

First, list available documentation sets and **filter based on user's query intent**:

```bash
SearchHelpers.get_list_command()  # → "ls -1 md_docs/"
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

### Step 2: List Document TOC Files in Specified Set

**CRITICAL:** This skill focuses on **document discovery** via TOC files. Always target `docTOC.md` files, NOT directories.

**Method 1: Using Glob pattern (CORRECT)**
```bash
SearchHelpers.build_toc_glob_pattern("Claude_Code_Docs:latest")
# → "md_docs/Claude_Code_Docs:latest/*/docTOC.md"
```

**Expected structure:**
```
md_docs/<doc_name>:<doc_version>/<PageTitle>/docTOC.md
```

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

### Step 4: Progressive Fallback

When Level 1 semantic matching returns **0 results OR low-quality matches** (max_similarity < 0.7), automatically invoke fallback levels:

**📖 See:** `reference/progressive-fallback.md` for detailed fallback level specifications

**Summary:**
- **Level 1:** Semantic title matching (default)
- **Level 2:** TOC content grep (when Level 1 fails)
- **Level 3.1:** Cross-set TOC search with domain filtering
- **Level 3.2:** Content search with context traceback (last resort)

### Step 5: Verify Coverage Completeness

**CRITICAL:** A search is ONLY complete when you have **verified** that all potentially relevant documents have been found.

**Multi-Set Search Triggers:**

| Query Pattern | Example | Action |
|--------------|---------|--------|
| Generic concepts | "best practices", "tips", "optimization" | Search ALL doc sets |
| Cross-cutting concerns | "deployment", "testing", "monitoring", "security" | Search ALL doc sets |
| Configuration/setup | "how to configure", "setup guide", "getting started" | Search ALL doc sets |
| Framework-specific | "React hooks", "Python async", "Claude skills" | Single set |

### Step 6: Redundancy Verification and Intent-Based Filtering

**PURPOSE:** After coverage verification, perform LLM-based analysis to eliminate documents that don't align with the user's actual query intent, ensuring precision over recall.

**Core Principle:** Use semantic intent analysis to filter out documents that may have matched keywords but don't serve the user's actual information need.

#### Intent Analysis Framework

**Step 6.1: Query Intent Classification**

Analyze the original user query (not optimized queries) to determine:

1. **Primary Intent Type:**
   - `LEARN` - User wants to understand concepts, principles, or how things work
   - `CONFIGURE` - User wants to set up, customize, or modify settings
   - `TROUBLESHOOT` - User wants to solve problems or fix issues
   - `REFERENCE` - User wants quick lookup of syntax, parameters, or specifications
   - `COMPARE` - User wants to understand differences or choose between options

2. **Scope Specificity:**
   - `SPECIFIC` - Targets a particular feature, component, or use case
   - `GENERAL` - Covers broad topics or multiple related areas
   - `CONTEXTUAL` - Depends on user's current situation or environment

3. **Information Depth:**
   - `OVERVIEW` - High-level understanding or introduction
   - `DETAILED` - In-depth technical information or comprehensive guides
   - `PRACTICAL` - Step-by-step instructions or hands-on examples

**Step 6.2: Document Relevance Scoring**

For each document in the search results, evaluate:

```
Relevance Score = Intent_Match × Scope_Alignment × Depth_Appropriateness × Specificity_Match

Where each factor is scored 0.0-1.0:
- Intent_Match: How well the document serves the identified intent
- Scope_Alignment: How well the document's scope matches query scope
- Depth_Appropriateness: How well the document's depth matches information need
- Specificity_Match: How well the document's specificity matches query specificity
```

**Step 6.3: Filtering Thresholds**

- **High Relevance (≥0.8):** Keep - Strong alignment with user intent
- **Medium Relevance (0.5-0.79):** Review - May be tangentially related, include with caveats
- **Low Relevance (<0.5):** Remove - Likely noise or off-topic

## Content Language and Structure Constraints (v2.9.0)

**CRITICAL CONSTRAINTS for search result content:**

1. **Language Consistency**:
   - If source docTOC.md is in English → Return English headings
   - If source docTOC.md is in Chinese → Return Chinese headings
   - If source docTOC.md is mixed → Preserve original mixed language format
   - Use `SearchHelpers.detect_content_language()` to determine source language

2. **Content Structure**:
   - Extract actual markdown headings from docTOC.md using `SearchHelpers.extract_toc_headings()`
   - Preserve hierarchical structure (# ## ### ####)
   - Remove URL links from headings for cleaner display
   - Include up to 10 most relevant headings per document
   - Format headings with proper indentation to show hierarchy

**Implementation Steps:**
1. Read docTOC.md content for each relevant document
2. Use `SearchHelpers.detect_content_language()` to determine language
3. Use `SearchHelpers.extract_toc_headings()` to get clean markdown headings
4. Include extracted headings in the `toc_content` field of result dictionaries
5. Use `SearchHelpers.format_language_appropriate_results()` for proper formatting

## 输出样例格式 (Output Example Format)

以下是一个典型的搜索结果输出样例：

```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=3 | doc_sets=Claude_Code_Docs:latest ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

## 精准检索结果 (Intent-Filtered Results)

### 高相关性文档 (High Relevance ≥0.8)

1. **Agent Skills** - 相关性: 0.9
   - 意图匹配: 直接回答用户关于技能配置的需求
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md`
   - 正文内容:
     # Agent Skills
     ## 1. Create your first Skill
     ### 1.1. Where Skills live
     #### 1.1.1. Automatic discovery from nested directories
     ## 2. Configure Skills
     ### 2.1. Write SKILL.md

2. **Get started with Claude Code hooks** - 相关性: 0.8
   - 意图匹配: 提供hooks设置的入门指导
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Get started with Claude Code hooks/docTOC.md`
   - 正文内容:
     # Get started with Claude Code hooks
     ## 1. Introduction to hooks
     ## 2. Basic configuration
     ### 2.1. Hook types
     ### 2.2. Configuration files

### 相关文档 (Medium Relevance 0.5-0.79)

3. **Testing best practices** - 相关性: 0.6
   - 意图匹配: 提供测试相关的上下文信息
   - 注意: 通用测试上下文，非hooks专用
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Testing best practices/docTOC.md`

### 已过滤文档 (Filtered Out <0.5)
- "Claude Code overview" - 原因: 对于具体配置查询过于宽泛
- "API reference" - 原因: 不同主题 (API vs 配置)

---

### 文档来源 (Sources)

1. **Agent Skills**
   - 原文链接: https://code.claude.com/docs/en/agent-skills
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md`

2. **Get started with Claude Code hooks**
   - 原文链接: https://code.claude.com/docs/en/get-started-hooks
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Get started with Claude Code hooks/docTOC.md`

3. **Testing best practices**
   - 原文链接: https://code.claude.com/docs/en/testing-best-practices
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Testing best practices/docTOC.md`

**Coverage:**
- ✅ Covered: 配置方法, 入门指导, 基本设置
- ⚠️  Partially covered: 高级配置模式
- ❌ Not covered: 性能优化, 故障排除
- 💡 Suggestion: 搜索 'hooks troubleshooting' 获取故障排除信息

=== END-AOP-FINAL ===
```

### 样例说明 (Example Explanation)

完整输出样例包含：分层结果（AOP-FINAL标记）、意图过滤、 TOC内容、过滤总结、来源信息、覆盖度分析。详见 "Return Format Requirements" 章节。

## Return Format Requirements

### AOP-FINAL Output Format

**CRITICAL:** All final search results MUST be wrapped with AOP-FINAL markers to prevent modification by the main session AI.

```markdown
=== AOP-FINAL | agent=md-doc-searcher | results={count} | doc_sets={sets} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

[Search results content here]

### 文档来源 (Sources)
[Sources section]

**Coverage:**
[Coverage section]

=== END-AOP-FINAL ===
```

**Required Attributes:**
- `agent=md-doc-searcher` - Identifies this skill as the source
- `results={count}` - Number of documents found
- `doc_sets={sets}` - Documentation sets searched (comma-separated)

### Sources Format (ALWAYS REQUIRED)

**CRITICAL:** You MUST include a **Sources** section at the end of ALL search results.

**Helper for formatting:**
```python
SearchHelpers.format_sources_section([
    ("Agent Skills", "https://code.claude.com/docs/en/agent-skills", "md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md")
])
```

**Required Format:**
```markdown
---

### 文档来源 (Sources)

1. **Document Title**
   - 原文链接: https://original-url.com/docs/page
   - TOC 路径: `md_docs/<doc_name>:<doc_version>/<PageTitle>/docTOC.md`
```

### Coverage Format

```markdown
**Coverage:**
- ✅ Covered: [aspects covered by results]
- ⚠️  Partially covered: [aspects partially covered]
- ❌ Not covered: [aspects that may exist in other documents/sets]
- 💡 Suggestion: [if applicable, suggest other searches]
```

**Helper:**
```python
SearchHelpers.format_coverage_section(
    covered=["Configuration", "Setup"],
    partial=["Advanced patterns"],
    not_covered=["Performance"],
    suggestion="Search 'performance' for optimization tips"
)
```

## Output Prohibition

AOP-FINAL output must be returned EXACTLY as received — NO summarizing, rephrasing, commentary, or reformatting. The AOP-FINAL marker preserves integrity of document paths, coverage analysis, and source attribution.

## Error Handling

If a document cannot be found: state clearly which was not found, suggest alternatives, try progressive fallback. Do NOT return partial/empty results.

## Bash Tool Timeout

When using Bash for file operations: always specify `timeout` parameter (recommended: 30000ms). Use `run_in_background: true` for long-running operations.

## Detailed Reference

- **Progressive Fallback Strategy:** `reference/progressive-fallback.md` - Complete Level 1-3.2 specifications with flow diagrams
- **SearchHelpers API:** `reference/search-helpers-api.md` - Complete function reference with examples
- **Workflow Examples:** `reference/workflow-examples.md` - Detailed workflow examples for various scenarios