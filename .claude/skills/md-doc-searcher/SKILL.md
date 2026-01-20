---
name: md-doc-searcher
description: Search and discover markdown documents in the doc4llm knowledge base using semantic understanding. Use this skill when Claude needs to find documents matching a query, list available documentation, search document titles by understanding user intent, or discover which documentation sets contain relevant content. Performs comprehensive search across relevant documentation sets and returns exhaustive list of relevant document titles with coverage verification.
allowed-tools:
  - Read
  - Glob
  - Bash
context: fork
protocol: AOP
protocol_version: "1.0"
---

# Markdown Document Searcher

Search and discover markdown documents in the doc4llm knowledge base directory structure using semantic matching.

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
│  Output: Document titles with heading lists                 │
└─────────────────────────────────────────────────────────────┘
```

**Why This Matters:**
- **Multi-perspective search:** Receives 3-5 query variations instead of a single raw query
- **Better recall:** Decomposition, expansion, and translation strategies improve coverage
- **Language handling:** Pre-translated queries (Chinese→English) improve matching accuracy
- **Ambiguity resolution:** Multiple query variants capture different interpretations

## Core Principle

This skill focuses on **document discovery via TOC (Table of Contents)** - finding which documents match your query by searching `docTOC.md` index files.

## Bash Tool Operations

### Read Knowledge Base Configuration

```bash
Bash: Read .claude/knowledge_base.json
```

### List Documentation Sets

```bash
Bash: ls -1 "{knowledge_base}/"
```

### Find TOC Files in Doc-Set

```bash
Bash: find "{knowledge_base}/<doc_name>:<doc_version>" -name "docTOC.md" -type f
```

### Grep in TOC Content (Fallback Strategy 1)

```bash
Bash: grep -r -iE "(keyword1|keyword2)" "{knowledge_base}/<doc_set>"/*/docTOC.md
```

### Grep in Content with Context (Fallback Strategy 2)

```bash
Bash: grep -r -i -B 10 "keyword" "{knowledge_base}/<doc_set>"/*/docContent.md
```
**Purpose:** Get context only for heading traceback - discard after use

**Retry with expanded context:**
```bash
Bash: grep -r -i -B 20 "keyword" "{knowledge_base}/<doc_set>"/*/docContent.md  # 2nd attempt
Bash: grep -r -i -B 50 "keyword" "{knowledge_base}/<doc_set>"/*/docContent.md  # 3rd attempt
```

### Extract Title from Content

```bash
Bash: head -n 5 "{knowledge_base}/<doc_set>/<PageTitle>/docContent.md"
```

## Semantic Retrieval Functions

Use these functions for semantic analysis. See [API Reference](reference/search-helpers-api.md) for complete documentation.

### Content Extraction

- **`SearchHelpers.extract_keywords(query: str) -> List[str]`** - Extract keywords from query
- **`SearchHelpers.extract_headings_with_levels(toc_content: str) -> List[dict]`** - Parse TOC headings

### Intent & Scoring Framework

- **`SearchHelpers.analyze_query_intent(original_query: str) -> dict`** - Get intent framework
- **`SearchHelpers.calculate_page_title_relevance_score(query: str, toc_content: str = None) -> dict`** - PageTitle scoring framework
- **`SearchHelpers.calculate_heading_relevance_score(heading_text: str, query: str, query_intent: dict = None) -> dict`** - Heading scoring framework

### Fallback Support

- **`SearchHelpers.annotate_headings_with_page_title(grep_results: list[dict], doc_set: str) -> list[dict]`** - Annotate grep results
- **`SearchHelpers.traceback_to_heading(content_path: str, match_line: int, context_lines: int = 10) -> dict`** - Trace content match to heading

## Core Retrieval Flow

This skill implements a **4-step retrieval process** based on the specification. Each step has explicit success conditions and fallback triggers.

### Step 1: Identify Matching Doc-Sets

**Purpose:** Find all `<doc_name>:<doc_version>` doc-sets that match the query intent.

**Method:**
1. Use `ls -1 "{knowledge_base}/"` to list available doc-sets
2. Analyze query intent to identify target domains (e.g., "Claude" → `*Claude*`)
3. Filter doc-sets based on intent keywords using LLM semantic understanding

**Output:** List of matching doc-set names

```python
["Claude_Code_Docs:latest", "Cursor_Docs:v1.0"]
```

**Match Anomaly Handling:**
- If **no doc-sets match** → Report failure immediately: "Target documentation set not found"
- This is a terminal failure - no fallback strategies apply

### Step 2: Identify Matching PageTitles

**Purpose:** Find all `<PageTitle>` directories within matched doc-sets that meet basic relevance threshold (≥0.6).

**Method:**
1. List all `docTOC.md` files in each matched doc-set
2. For each PageTitle, read its `docTOC.md` content
3. Calculate PageTitle relevance score using `calculate_page_title_relevance_score(query, toc_context)`
4. Filter by **basic threshold (0.6)** - only keep PageTitles with score ≥ 0.6

**Success Conditions:**
- PageTitle count ≥ 1 per doc-set
- At least one PageTitle with precision score (≥ 0.7)

**Fallback Trigger:** If conditions not met → Execute Fallback Strategy 1

### Step 3: Identify Matching Headings (via docTOC.md)

**Purpose:** From filtered PageTitles, find headings that match the query.

**Method:**
1. Read `docTOC.md` files from matched PageTitles
2. Extract all headings using `extract_headings_with_levels()`
3. Score each heading using `calculate_heading_relevance_score()` with **prompt-based retrieval strategy**
4. Filter by basic threshold (≥ 0.6)

**Success Conditions:**
- Heading count ≥ 2 per doc-set (across all matched PageTitles)

**Fallback Trigger:** If conditions not met → Execute Fallback Strategy 2

### Step 4: Return Heading Lists

**Purpose:** Return all matching headings with scores and attribution.

**CRITICAL:** Output must be based on **heading-level relevance scores**, not PageTitle-level scores. Each heading is evaluated independently.

### Fallback Strategy 1: TOC Content Grep

**Trigger:** Step 2 success conditions not met (PageTitle < 1 OR no precision match)

**Method:**
1. Extract keywords from query using `extract_keywords()`
2. Execute grep across all `docTOC.md` files in matched doc-sets
3. Parse grep results to identify matching headings
4. **Annotate each heading with its PageTitle ownership** using `annotate_headings_with_page_title()`

**Success Conditions:**
- Heading count ≥ 2 per doc-set
- All results include PageTitle attribution

**Fallback Trigger:** If conditions not met → Execute Fallback Strategy 2

### Fallback Strategy 2: Content Context Traceback

**Trigger:** Fallback Strategy 1 success conditions not met

**Purpose:** Use docContent.md only as a hint to locate relevant headings in docTOC.md

**Method:**
1. Execute grep across `docContent.md` files **with context only** (`grep -B 10`)
2. **For each match, trace back to the nearest heading** in `docTOC.md` using `traceback_to_heading()`
3. **Discard the content context** - use it only to identify which heading to return
4. **Retry with expanded context if no heading found:**
   - If `grep -B 10` fails to traceback to any heading → Retry with `grep -B 20`
   - If still no heading → Retry with `grep -B 50`
5. Return **only the heading list from docTOC.md**, never docContent content

**CRITICAL:** This strategy must NOT return any docContent.md content. The grep result is a hint, not output.

**Success Conditions:**
- Heading count ≥ 2 per doc-set
- All results include PageTitle attribution
- Results contain ONLY docTOC.md headings (no docContent content)

**Fallback Trigger:** If conditions not met → Report failure

## Prompt-based Retrieval Strategy

This skill uses **LLM-based semantic evaluation** for heading relevance scoring. The following prompt template guides consistent heading-level relevance assessment.

### Heading Evaluation Prompt Template

```markdown
## Query Analysis
Original Query: {query}
Query Intent: {intent}
Domain Context: {context}

## Heading to Evaluate
Heading Text: {heading_text}
Heading Level: {heading_level}
Parent PageTitle: {page_title}

## Evaluation Criteria (0.0 - 1.0)

### Semantic Relevance (0-1)
- Does the heading directly address the query topic?
- Consider technical terminology and concept alignment

### Intent Alignment (0-1)
- Does the heading serve the user's intent (LEARN/CONFIGURE/TROUBLESHOOT/REFERENCE/COMPARE)?
- Is the scope appropriate (SPECIFIC/GENERAL)?

### Context Appropriateness (0-1)
- Given the PageTitle context, how relevant is this heading?
- Does the heading belong to a related section?

## Scoring Formula
final_score = (semantic_relevance * 0.4) + (intent_alignment * 0.4) + (context_appropriateness * 0.2)
```

## Output Format

 ```
 {
   "score": 0.XX,
   "is_basic": true/false,  // >= 0.6
   "is_precision": true/false,  // >= 0.7
   "rationale": "Brief explanation"
 }
 ```

## Examples

| Query | Heading | Score | Rationale |
|-------|---------|-------|-----------|
| "如何配置 skills" | "Configure Skills" | 0.92 | Direct semantic match, CONFIG intent alignment |
| "如何配置 skills" | "Write SKILL.md" | 0.85 | Related configuration topic |
| "hooks 故障排除" | "Hook types" | 0.65 | Related but not troubleshooting focus |
| "API 参考" | "Testing best practices" | 0.35 | Different topic entirely |

### Key Principles

1. **Independent Scoring**: Heading-level scores are independent of PageTitle-level scores
2. **Basic Threshold (0.6)**: Minimum score for inclusion in results
3. **Precision Threshold (0.7)**: Minimum score for "精准匹配" marker
4. **Consistency**: Use the same prompt template across all heading evaluations

## Content Language and Structure Constraints

**CRITICAL CONSTRAINTS for search result content:**

1. **Language Consistency:**
   - Output keep the same the Language with source `docTOC.md` docs

2. **Content Structure:**
   - Extract actual markdown headings from docTOC.md using `SearchHelpers.extract_headings_with_levels()`

## Heading-Level Scoring Independence

**CRITICAL CONSTRAINT:** Returned heading lists must be based on **heading-level relevance scores**, NOT PageTitle-level scores.

### Why Independence Matters

- A PageTitle may have high relevance (0.85) but contain some low-relevance headings (<0.6)
- A PageTitle may have medium relevance (0.68) but contain highly relevant headings (≥0.8)
- **Results should reflect actual heading relevance**, not inherited PageTitle scores

### Result Filtering

- Filter headings by **heading-level basic threshold (0.6)**
- Mark precision by **heading-level precision threshold (0.7)**
- Group results by PageTitle for readability
- Show individual heading scores in output

## 输出样例格式 (Output Example Format)
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results={count} | doc_sets={sets} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

## 检索结果摘要
- 文档集数量: {doc_set_count}
- 匹配PageTitle总数: {page_title_count}
- 匹配Heading总数: {heading_count}
- 精准匹配(≥0.7)数量: {precision_count}

## 精准检索结果 (Intent-Filtered Results)

### 高相关性文档 (High Relevance ≥0.8)
<!-- relevance_score 分组: ≥0.8 高, 0.6-0.79 中, <0.5 过滤 -->

**{doc_name}:{doc_version}**

**{PageTitle}** - PageTitle相关性: {score} ✅精准匹配
   - 意图匹配: {intent_rationale}
   - TOC 路径: `{knowledge_base}/{doc_name}:{doc_version}/{PageTitle}/docTOC.md`
   - **匹配Heading列表**:
     - ## {Heading1} ({score}) ✅精准匹配
     - ### {Heading2} ({score})
   - **匹配统计**: PageTitle≥2个 ✅, Heading≥2个 ✅, 精准匹配≥1个 ✅

### 中等相关性文档 (Medium Relevance 0.6-0.79)
<!-- 格式同上，移除高分标记 -->

### 已过滤文档 (Filtered Out <0.5)
**{doc_name}:{doc_version}**
- "{PageTitle}" - 原因: {filter_rationale}

---

## 匹配统计 (按文档集)

- **{doc_set_name}**:
  - PageTitle匹配: {matched}/{total} ✅/❌
  - Heading匹配: {matched}/{total} ✅/❌
  - 精准匹配: {matched}/1 ✅/❌
  - 整体状态: ✅ 通过 / ❌ 失败

---

### 文档来源 (Sources)
<!-- 每匹配一个 PageTitle 输出一条来源记录 -->

1. **{PageTitle}**
   - 文档集: {doc_name}:{doc_version}
   - 原文链接: {original_url}
   - TOC 路径: `{knowledge_base}/{doc_name}:{doc_version}/{PageTitle}/docTOC.md`

**Coverage:**
- ✅ Covered: {covered_aspects}
- ⚠️  Partially covered: {partial_aspects}
- ❌ Not covered: {missing_aspects}
- 💡 Suggestion: {suggestion}
```

### 样例说明

完整输出样例包含：
- 分层结果（AOP-FINAL标记）
- 意图过滤
- **明确的归属标注**：每个 Heading 都归属于特定的 `<doc_name>:<doc_version>` 和 `<PageTitle>`
- **按文档集分组的匹配Heading列表**（带评分和精准标记）
- **按文档集分组的匹配统计**
- 过滤总结
- 来源信息
- 覆盖度分析

## Output Prohibition

AOP-FINAL output must be returned EXACTLY as received — NO summarizing, rephrasing, commentary, or reformatting. The AOP-FINAL marker preserves integrity of document paths, coverage analysis, and source attribution.

## 分组归属规范

All headings MUST be organized with explicit ownership hierarchy: `<doc_name>:<doc_version>` → `<PageTitle>` → `## Heading1 (score) ✅精准匹配`

Every heading must clearly show:
1. Which `<doc_name>:<doc_version>` it belongs to
2. Which `<PageTitle>` (directory) it belongs to

## Error Handling

If a document cannot be found: state clearly which was not found, suggest alternatives, try progressive fallback. **If no results meet success conditions after all fallbacks, report failure immediately.**

**Failure Report Format:**
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=0 | doc_sets=X ===

**检索失败** - 未找到满足成功条件的文档

**尝试的检索策略:**
1. Level 1: 语义标题匹配 - 未满足 PageTitle≥1 或 精准匹配要求
2. Level 2: TOC内容grep搜索 - 未满足 Heading≥2 要求
3. Level 3: 全文内容搜索 (含重试):
   - grep -B 10: 未找到 heading
   - grep -B 20: 未找到 heading
   - grep -B 50: 未找到 heading
   - 未能回溯到任何有效 heading

**可能原因:**
- 目标文档集不存在: [缺失的文档集]
- 文档库中缺少相关内容
- 查询关键词过于特定

**建议:**
- 确认目标文档集名称是否正确
- 尝试使用更宽泛的查询关键词
- 确认文档库是否包含相关内容

=== END-AOP-FINAL ===
```

## Knowledge Base Path Configuration

**CRITICAL:** All document paths in this skill use `{knowledge_base}` as a placeholder that MUST be resolved from the configuration file.

### Configuration File Location
```
.claude/knowledge_base.json
```

### Configuration Format
```json
{
  "knowledge_base": {
    "base_dir": "~/project/md_docs_base"
  }
}
```

## Bash Tool Timeout

When using Bash for file operations: always specify `timeout` parameter (recommended: 30000ms). Use `run_in_background: true` for long-running operations.

## Detailed Reference

- **SearchHelpers API:** `reference/search-helpers-api.md` - Semantic retrieval function reference
