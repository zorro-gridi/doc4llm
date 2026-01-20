# Progressive Fallback Strategy

This document provides detailed information about the progressive fallback levels used in md-doc-searcher.

## Overview

The progressive fallback strategy ensures comprehensive document discovery by automatically escalating search sophistication when simpler methods fail.

## Success Conditions Summary

| Level | Trigger | Success Condition |
|-------|---------|-------------------|
| 1 (Step 2) | Always (start) | PageTitle count >= 1 **AND** has precision match (>=0.7) |
| Step 3 | After Level 1 success | Heading count >= 2 (per doc-set) |
| 2 (Fallback 1) | Step 3 fails | Heading count >= 2 |
| 3.1 | Level 2 fails | Heading count >= 2 (cross-set) |
| 3.2 | Level 3.1 fails | Heading count >= 2 (with PageTitle attribution) |

## Level 1: Semantic Title Matching (Default)

**Purpose:** Fast semantic matching using LLM understanding

**How it works:**
- Uses LLM semantic understanding to match query concepts to document titles
- Leverages synonym recognition, domain knowledge, and context understanding
- Fast operation: O(k) where k = number of matches

**Quality threshold:** `max_similarity >= 0.7` for precision match

**When triggered:** Always (starting point)

**Success Condition:**
```python
# Must satisfy ALL:
page_title_count >= 1  AND  precision_count >= 1

# Validation
page_title_valid, count = SearchHelpers.check_page_title_requirement(results, min_count=1)
precision_valid, p_count = SearchHelpers.check_precision_requirement(results, precision_threshold=0.7)

if page_title_valid and precision_valid:
    # Level 1 SUCCESS - proceed to Step 3 (heading identification)
    proceed_to_step_3()
else:
    # Level 1 FAILS - trigger Fallback Strategy 1 (Level 2)
    trigger_fallback_level_2()
```

**Example:**
```
Query: "how to configure"
Matches: "Settings", "Configuration", "Setup", "Preferences"
Result: 4 PageTitles, 3 with score >= 0.7
→ Level 1 SUCCESS ✓
```

## Level 2: TOC Content Grep (Fallback Strategy 1)

**Purpose:** Search within TOC file contents when Level 1 success conditions not met

**Trigger:** Level 1 fails (PageTitle count < 1 OR no precision match)

**How to use:**

```python
from doc4llm.tool.md_doc_retrieval import SearchHelpers

# First extract keywords
keywords = SearchHelpers.extract_keywords("how to configure hooks for deployment")
# → ['configure', 'hooks', 'deployment']

# Then build grep command
SearchHelpers.build_level2_grep_command(
    keywords=["configure", "hooks", "deployment"],
    doc_set="Claude_Code_Docs:latest"
)
# → "grep -r -iE '(configure|hooks|deployment)' {knowledge_base}/Claude_Code_Docs:latest/*/docTOC.md"
```

**Execute via Bash tool:**
```bash
grep -r -iE '(configure|hooks|deployment)' {knowledge_base}/Claude_Code_Docs:latest/*/docTOC.md
```

**Annotate results with PageTitle ownership (REQUIRED):**
```python
# Parse grep results first
grep_results = [
    {"file": "{knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docTOC.md", "match": "Configure Skills"},
    {"file": "{knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docTOC.md", "match": "Write SKILL.md"}
]

# CRITICAL: Annotate with PageTitle ownership
annotated_results = SearchHelpers.annotate_headings_with_page_title(
    grep_results, "Claude_Code_Docs:latest"
)

# Then score headings
for result in annotated_results:
    relevance = SearchHelpers.calculate_heading_relevance_score(
        result["heading_text"], query, query_intent
    )
    result["score"] = relevance["score"]
```

**Benefits:**
- Finds content within sections that don't match title exactly
- Captures documents where relevant content is in subsections
- Balanced performance: O(1) operation

**Success Condition:**
```python
# Parse grep results to extract headings
heading_results = parse_grep_results(grep_output)

# Must satisfy:
heading_count >= 2

# Validation
heading_valid, count = SearchHelpers.check_heading_requirement(heading_results, min_count=2)

if heading_valid:
    # Level 2 SUCCESS - proceed to heading extraction
    proceed_to_step_5()
else:
    # Level 2 FAILS - trigger Level 3
    trigger_fallback_level_3()
```

## Level 3: Cross-Set + Content Search (Last Resort)

Level 3 has two sub-levels:

### Level 3.1: Cross-Set TOC Search (with Relevance Constraints)

**Purpose:** Search across multiple documentation sets when single-set search fails

**Trigger:** Level 2 fails (heading count < 2)

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
# → "{knowledge_base}/*Claude* {knowledge_base}/*Code*"

# For "Claude Code skills", only search:
# - Claude_Code_Docs:latest
# NOT: Python_Docs, React_Docs, etc.
```

**Step 3: Search TOC files in filtered sets**
```bash
# Cross-set TOC search WITH domain filter
grep -r -i "keyword" {knowledge_base}/*Claude*/*/docTOC.md {knowledge_base}/*Code*/*/docTOC.md
```

**Why domain filtering matters:**
Searching "best practices" across ALL doc sets could return Python, React, or other framework-specific practices that are irrelevant to the user's actual query context.

**Success Condition:**
```python
# Cross-set search results
cross_set_results = cross_set_toc_search(keywords, filtered_sets)

# Must satisfy:
total_heading_count >= 2

if len(cross_set_results) >= 2:
    # Level 3.1 SUCCESS
    proceed_to_step_5()
else:
    # Level 3.1 FAILS - trigger Level 3.2
    trigger_fallback_level_3_2()
```

### Level 3.2: docContent.md Context Search (with Traceback)

**Purpose:** Search within document contents when TOC search fails

**Trigger:** Level 3.1 fails (heading count < 2)

**CRITICAL CONSTRAINTS:**
- ❌ **NEVER** use `Read` tool to load entire docContent.md files
- ✅ Only use `grep` with context to extract minimal information
- ✅ Return docTOC.md paths for subsequent use by md-doc-reader
- ✅ **Must include PageTitle attribution** in results

**Search with context traceback:**
```python
# Use helper to build command
SearchHelpers.build_level3_content_grep_command(
    keywords=["design philosophy"],
    doc_sets=["Claude_Code_Docs:latest"],
    context_lines=10
)
# → "grep -r -i -B 10 'design philosophy' {knowledge_base}/Claude_Code_Docs:latest/*/docContent.md"
```

**Execute via Bash tool:**
```bash
grep -r -i -B 10 "design philosophy" {knowledge_base}/*Claude*/*/docContent.md
```

**Parse results to extract:**
1. **Documentation set name** - Extract from file path
2. **Document title** - Extract from docContent.md (first 5 lines, look for `#` headings)
3. **Match context** - The 10 lines before the match showing relevant section
4. **PageTitle attribution** - **REQUIRED**: Note which PageTitle this heading belongs to

**Traceback to heading (REQUIRED for Level 3.2):**
```python
# After grep finds match at specific line
content_results = []

# For each grep match, trace back to heading
for match in grep_output.split('\n'):
    if 'docContent.md' in match:
        # Extract file path and line number
        parts = match.split(':')
        file_path = parts[0]
        line_num = int(parts[1])

        # Trace back to nearest heading
        traceback = SearchHelpers.traceback_to_heading(
            content_path=file_path,
            match_line=line_num,
            context_lines=10
        )

        content_results.append({
            "heading_text": traceback["heading_text"],
            "page_title": traceback["page_title"],  # REQUIRED attribution
            "heading_level": traceback["heading_level"],
            "context_excerpt": traceback["context_excerpt"]
        })

# Then score headings
for result in content_results:
    relevance = SearchHelpers.calculate_heading_relevance_score(
        result["heading_text"], query, query_intent
    )
    result["score"] = relevance["score"]
```

**Helper for title extraction:**
```python
SearchHelpers.build_title_extraction_command(
    "{knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docContent.md",
    max_lines=5
)
# → "head -5 {knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docContent.md"
```

**Success Condition:**
```python
# Content search results with PageTitle attribution
content_results = content_search_with_context(keywords, doc_sets)

# Must satisfy:
heading_count >= 2  AND  all_results_have_page_title_attribution

if len(content_results) >= 2 and all_has_attribution(content_results):
    # Level 3.2 SUCCESS
    proceed_to_step_5()
else:
    # Level 3.2 FAILS - ALL FALLBACKS EXHAUSTED
    report_failure()
```

**Return format for Level 3.2:**
```markdown
Found N relevant document(s) via Level 3.2 content search:

1. **Document Title** (Doc_Set:Version)
   - Relevance: Content contains "keyword" in section context
   - Context: [Brief excerpt from grep -B 10 output]
   - PageTitle归属: [PageTitle Name]
   - TOC Path: `{knowledge_base}/<doc_set>/<PageTitle>/docTOC.md`

**Note:** Use `/md-doc-reader "Document Title"` to view full TOC and structure.
```

## Progressive Fallback Flow Diagram

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
        [PageTitle≥1 AND                  [PageTitle<1 OR
         has precision ≥0.7]               no precision match]
              │                               │
              ▼                               ▼
    ┌────────────────────┐    ┌───────────────────────────────┐
    │  Step 3: Identify  │    │  Level 2: TOC Grep Fallback   │
    │  Matching Headings │    │  - grep -r across TOC files   │
    │  Heading≥2?        │    │  - Balanced: O(1) operation   │
    └────────────────────┘    └───────────────────────────────┘
              │                         │
              │               ┌─────────┴─────────┐
              │               │                   │
              │         [Heading≥2]         [Heading<2]
              │               │                   │
              ▼               ▼                   ▼
    ┌────────────────────┐    ┌───────────────────────────────┐
    │  Coverage Check    │    │  Level 3.1: Cross-Set TOC     │
    │  Cross-DocSet      │    │  - Filter by domain           │
    │  Validation        │    │  - grep -r across filtered    │
    └────────────────────┘    │    doc sets                   │
              │               └───────────────────────────────┘
              │                         │
              │               ┌─────────┴─────────┐
              │               │                   │
              │         [Heading≥2]         [Heading<2]
              │               │                   │
              │               ▼                   ▼
              │    ┌────────────────────┐    ┌───────────────────────────────┐
              │    │  Coverage Check    │    │  Level 3.2: Content Search    │
              │    │  Cross-DocSet      │    │  - grep -B 10 for context     │
              │    │  Validation        │    │  - Extract title from 5       │
              │    └────────────────────┘    │    lines (retry: 20)          │
              │               │              │  - Return TOC paths only      │
              │               │              │  - PageTitle attribution REQ  │
              │               │              └───────────────────────────────┘
              │               │                        │
              │               │              ┌─────────┴─────────┐
              │               │              │                   │
              │               │        [Heading≥2 +          [Heading<2 OR
              │               │         attribution]          no attribution]
              │               │              │                   │
              │               │              ▼                   ▼
              │               │    ┌────────────────────┐    ┌────────────────────┐
              │               │    │  Coverage Check    │    │  FAILURE REPORT    │
              │               │    │  Cross-DocSet      │    │  - All fallbacks   │
              │               │    │  Validation        │    │    exhausted       │
              │               │    └────────────────────┘    │  - Prompt user     │
              │               │               │              └────────────────────┘
              │               │               │
              │               └───────────────┤
              │                               │
              ▼                               ▼
    ┌─────────────────────────────────────────────────────────┐
    │              SUCCESS - Return Results with              │
    │              - PageTitle list with scores               │
    │              - Heading list with scores                 │
    │              - Match statistics by doc-set              │
    │              - Sources and Coverage                     │
    └─────────────────────────────────────────────────────────┘
```

## Decision Criteria Summary

| Level | Trigger | Search Scope | Success Condition | Output |
|-------|---------|--------------|-------------------|--------|
| **1 (Step 2)** | Always (start) | Single set, titles only | PageTitle≥1 AND precision≥0.7 | Document titles with scores |
| **Step 3** | After Level 1 success | From matched PageTitles | Heading≥2 (per doc-set) | Headings with scores |
| **2 (Fallback 1)** | Step 3 fails | Single set, TOC contents | Heading≥2 | Document titles with heading context |
| **3.1** | Level 2 fails | Multiple filtered sets, TOC | Heading≥2 | Document titles with heading context |
| **3.2** | Level 3.1 fails | Multiple filtered sets, content | Heading≥2 AND attribution | Document titles with context + PageTitle attribution |

## Validation Helpers Usage

### Complete Validation Flow Example

```python
from doc4llm.tool.md_doc_retrieval import SearchHelpers

def search_with_validation(query, doc_set):
    """Complete search with validation at each level"""

    # Configure thresholds (optional, defaults exist)
    SearchHelpers.set_basic_threshold(0.6)
    SearchHelpers.set_precision_threshold(0.7)
    SearchHelpers.set_min_page_title_matches(1)
    SearchHelpers.set_min_heading_matches(2)

    # =========================================
    # LEVEL 1: Semantic Title Matching (Step 2)
    # =========================================
    level1_results = semantic_match(query, doc_set)

    # Validate Level 1
    pt_valid, pt_count = SearchHelpers.check_page_title_requirement(level1_results, min_count=1)
    prec_valid, prec_count = SearchHelpers.check_precision_requirement(level1_results, precision_threshold=0.7)

    if pt_valid and prec_valid:
        # Level 1 SUCCESS - validate headings and proceed
        heading_results = extract_headings_from_results(level1_results, query)
        head_valid, head_count = SearchHelpers.check_heading_requirement(heading_results, min_count=2)

        if head_valid:
            return {
                "level": 1,
                "success": True,
                "page_title_results": level1_results,
                "heading_results": heading_results
            }

    # =========================================
    # LEVEL 2: TOC Content Grep Fallback
    # =========================================
    keywords = SearchHelpers.extract_keywords(query)
    cmd = SearchHelpers.build_level2_grep_command(keywords, doc_set)
    grep_results = execute_bash(cmd)

    level2_results = parse_grep_results(grep_results)
    head_valid, head_count = SearchHelpers.check_heading_requirement(level2_results, min_count=2)

    if head_valid:
        return {
            "level": 2,
            "success": True,
            "page_title_results": level2_results
        }

    # =========================================
    # LEVEL 3.1: Cross-Set TOC Search
    # =========================================
    filtered_sets = filter_doc_sets_by_domain(query)
    cross_set_results = cross_set_toc_search(keywords, filtered_sets)
    head_valid, head_count = SearchHelpers.check_heading_requirement(cross_set_results, min_count=2)

    if head_valid:
        return {
            "level": 3.1,
            "success": True,
            "page_title_results": cross_set_results
        }

    # =========================================
    # LEVEL 3.2: Content Search with Traceback
    # =========================================
    content_results = content_search_with_context(keywords, filtered_sets, context_lines=10)

    # Check for heading count AND PageTitle attribution
    has_attribution = all("page_title" in r for r in content_results)
    head_valid, head_count = SearchHelpers.check_heading_requirement(content_results, min_count=2)

    if head_valid and has_attribution:
        return {
            "level": 3.2,
            "success": True,
            "page_title_results": content_results
        }

    # =========================================
    # ALL FALLBACKS EXHAUSTED
    # =========================================
    return {
        "level": "none",
        "success": False,
        "failure_reasons": [
            "Level 1: PageTitle count < 2 or no precision match",
            "Level 2: Heading count < 2",
            "Level 3.1: Heading count < 2 (cross-set)",
            "Level 3.2: Heading count < 2 or missing PageTitle attribution"
        ]
    }
```

## Failure Reporting

When all fallback levels are exhausted, report failure with clear diagnostic information:

```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=0 | doc_sets=X ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

## 检索失败报告 (Search Failure Report)

### 失败的检索策略

| 策略 | 条件要求 | 验证结果 | 状态 |
|------|---------|---------|------|
| Level 1: 语义标题匹配 | PageTitle≥1 且 精准匹配≥0.7 | PageTitle: X, 精准: Y | ❌ 失败 |
| Step 3: Heading识别 | Heading≥2 (per doc-set) | Heading: Z | ❌ 失败 |
| Level 2: TOC内容grep | Heading≥2 | Heading: Z | ❌ 失败 |
| Level 3.1: 跨集TOC搜索 | Heading≥2 | Heading: W | ❌ 失败 |
| Level 3.2: 全文内容搜索 | Heading≥2 且 PageTitle归属 | Heading: V, 归属: U | ❌ 失败 |

### 可能原因
1. [列出可能的原因]

### 建议操作
1. [提供用户建议]

=== END-AOP-FINAL ===
```
