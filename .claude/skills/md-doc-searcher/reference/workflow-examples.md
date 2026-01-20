# md-doc-searcher Workflow Examples

This document provides detailed workflow examples for the md-doc-searcher skill.

## v4.0.0 Key Updates

- All examples now include **success condition validation** at each level
- Examples show **PageTitle≥2**, **Heading≥2**, and **precision≥0.7** checks
- Output format updated to show **heading lists with scores**
- Added **match statistics by doc-set** in outputs

---

## Example 1: Single-Query Search with Validation (v4.0.0)

**Input from md-doc-query-optimizer:**
```
Optimized Queries (Ranked):
1. "hooks configuration" - translation: Direct English translation
```

**Step 1:** List and filter doc sets
```bash
SearchHelpers.get_list_command()
# Execute: ls -1 {knowledge_base}/

# Output:
# Claude_Code_Docs:latest
# Python_Docs:3.11
# React_Docs:v18

# Filter: "hooks" → Claude Code context
# Target: Claude_Code_Docs:latest
```

**Step 2-3:** List docTOC.md files
```python
SearchHelpers.build_toc_glob_pattern("Claude_Code_Docs:latest")
# → "{knowledge_base}/Claude_Code_Docs:latest/*/docTOC.md"

# Returns matches like:
# - Hooks reference/docTOC.md
# - Get started with Claude Code hooks/docTOC.md
# - Testing best practices/docTOC.md
```

**Step 4:** Semantic matching
```
Query: "hooks configuration"
Results:
  - Hooks reference (matched, score: 0.92) ✅
  - Get started with Claude Code hooks (matched, score: 0.85) ✅
  - Testing best practices (matched, score: 0.68)
```

**Step 4.1:** Validate Level 1 success conditions
```python
# Check PageTitle count >= 2
results = [{"title": "Hooks reference", "score": 0.92}, {"title": "Get started", "score": 0.85}, {"title": "Testing", "score": 0.68}]
pt_valid, pt_count = SearchHelpers.check_page_title_requirement(results, min_count=2)
# → (True, 3)

# Check precision match >= 0.7
prec_valid, prec_count = SearchHelpers.check_precision_requirement(results, precision_threshold=0.7)
# → (True, 2)  # 2 results >= 0.7

# Level 1 SUCCESS ✓
```

**Step 5:** Extract and score headings
```python
# For each matched PageTitle, extract headings
toc_content = read_toc_file("{knowledge_base}/Claude_Code_Docs:latest/Hooks reference/docTOC.md")
headings = SearchHelpers.extract_headings_with_levels(toc_content)

# Score each heading
for heading in headings:
    relevance = SearchHelpers.calculate_heading_relevance_score(
        heading["text"], "hooks configuration", {"primary_intent": "CONFIGURE"}
    )
    heading["score"] = relevance["score"]
    heading["is_precision"] = relevance["score"] >= 0.7

# Filter and rank
ranked = SearchHelpers.rank_headings_by_relevance(
    headings, "hooks configuration", min_relevance=0.6, precision_threshold=0.7
)

# Format
heading_list = SearchHelpers.format_heading_list_with_scores(ranked, "Hooks reference")
```

**Step 5.1:** Validate heading count
```python
# Check Heading count >= 2
head_valid, head_count = SearchHelpers.check_heading_requirement(ranked, min_count=2)
# → (True, N)
```

**Return format (v4.0.0):**
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=3 | doc_sets=Claude_Code_Docs:latest ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

## 检索结果摘要
- 文档集数量: 1
- 匹配PageTitle总数: 3
- 匹配Heading总数: 8
- 精准匹配(≥0.7)数量: 5

## 精准检索结果

### 高相关性文档 (High Relevance ≥0.8)

1. **Hooks reference** - PageTitle相关性: 0.92 ✅精准匹配
   - 意图匹配: 直接回答hooks配置需求
   - TOC 路径: `{knowledge_base}/Claude_Code_Docs:latest/Hooks reference/docTOC.md`
   - **匹配Heading列表**:
     - ## 1. Hook Configuration (0.94) ✅精准匹配
     - ### 1.1. Configuration Options (0.91) ✅精准匹配
     - ### 1.2. Environment Variables (0.88) ✅精准匹配
     - ## 2. Hook Types (0.85) ✅精准匹配
     - ### 2.1. Pre-commit Hooks (0.72)
   - **匹配统计**: PageTitle≥2个 ✅, Heading≥2个 ✅, 精准匹配≥1个 ✅

### 中等相关性文档 (0.6-0.79)

2. **Get started with Claude Code hooks** - PageTitle相关性: 0.85 ✅精准匹配
   - **匹配Heading列表**:
     - ## 1. Introduction to hooks (0.87) ✅精准匹配
     - ## 2. Basic configuration (0.82) ✅精准匹配
   - **匹配统计**: PageTitle≥2个 ✅, Heading≥2个 ✅, 精准匹配≥1个 ✅

3. **Testing best practices** - PageTitle相关性: 0.68
   - **匹配Heading列表**:
     - ## Testing with hooks (0.72)
   - **匹配统计**: PageTitle≥2个 ✅, Heading≥2个 ❌, 精准匹配≥1个 ❌

---

## 匹配统计 (按文档集)

- **Claude_Code_Docs:latest**:
  - PageTitle匹配: 3/2 ✅
  - Heading匹配: 8/2 ✅
  - 精准匹配: 5/1 ✅
  - 整体状态: ✅ 通过

---

### 文档来源

1. **Hooks reference**
   - 原文链接: https://code.claude.com/docs/en/hooks
   - TOC 路径: `{knowledge_base}/Claude_Code_Docs:latest/Hooks reference/docTOC.md`

2. **Get started with Claude Code hooks**
   - 原文链接: https://code.claude.com/docs/en/hooks-getting-started
   - TOC 路径: `{knowledge_base}/Claude_Code_Docs:latest/Get started with Claude Code hooks/docTOC.md`

3. **Testing best practices**
   - 原文链接: https://code.claude.com/docs/en/testing-best-practices
   - TOC 路径: `{knowledge_base}/Claude_Code_Docs:latest/Testing best practices/docTOC.md`

**Coverage:**
- ✅ Covered: Hooks configuration, basic setup, testing
- ⚠️  Partially covered: Advanced configuration patterns

=== END-AOP-FINAL ===
```

---

## Example 2: Multi-Query Aggregation with Validation (v4.0.0)

**Input from md-doc-query-optimizer:**
```
Optimized Queries (Ranked):
1. "skills" - direct match
2. "Agent Skills" - context-specific expansion
3. "skills reference" - expansion
```

**Step 1:** List and filter doc sets
```bash
SearchHelpers.get_list_command()
# Output:
# Claude_Code_Docs:latest
# Python_Docs:3.11
# React_Docs:v18

# 根据优化查询过滤：所有查询都指向 "skills" → Claude Code 上下文
# 目标文档集: Claude_Code_Docs:latest
```

**Step 2:** 在指定文档集中列出所有目录
```python
SearchHelpers.build_toc_glob_pattern("Claude_Code_Docs:latest")
# → "{knowledge_base}/Claude_Code_Docs:latest/*/docTOC.md"

# 返回:
# Agent Skills/
# CLI reference/
# Hooks reference/
# ...
```

**Step 3:** 多查询语义匹配 + 聚合

读取相关文档的 `docTOC.md` 获取更多上下文：
```bash
Read {knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docTOC.md
```

使用 LLM 语义理解进行匹配：
- 查询 1 "skills" → 匹配 "Agent Skills" (score: 0.95)
- 查询 2 "Agent Skills" → 匹配 "Agent Skills" (score: 0.98) ✅
- 查询 3 "skills reference" → 匹配 "Agent Skills" (score: 0.92)

**聚合结果并去重：** {"Agent Skills"}
**按匹配查询数量排序：** Agent Skills (matched by 3 queries)

**Step 3.1:** 验证 Level 1 成功条件
```python
results = [{"title": "Agent Skills", "score": 0.95}]

# Check PageTitle count >= 2
pt_valid, pt_count = SearchHelpers.check_page_title_requirement(results, min_count=2)
# → (False, 1)  # 仅1个PageTitle！

# Level 1 FAILS - 需要更多结果
# TRIGGER: 查看是否有其他匹配，或者尝试回退策略
```

**Step 3.2:** 补充搜索其他相关文档
```python
# 搜索其他可能相关的文档
additional_results = [
    {"title": "CLI Skills Integration", "score": 0.72},
    {"title": "Skills Best Practices", "score": 0.68}
]

# 合并结果
all_results = results + additional_results
# → [{"Agent Skills", 0.95}, {"CLI Skills", 0.72}, {"Skills Best", 0.68}]

# 重新验证
pt_valid, pt_count = SearchHelpers.check_page_title_requirement(all_results, min_count=2)
# → (True, 3)

prec_valid, prec_count = SearchHelpers.check_precision_requirement(all_results, precision_threshold=0.7)
# → (True, 1)  # Agent Skills >= 0.7

# Level 1 SUCCESS ✓
```

**Step 4:** 提取并评分 Heading
```python
# 对每个匹配的PageTitle提取heading
for result in all_results:
    toc_path = f"{knowledge_base}/Claude_Code_Docs:latest/{result['title']}/docTOC.md"
    headings = extract_and_score_headings(toc_path, query, query_intent)
    result["headings"] = headings

# 验证heading count
total_headings = sum(len(r["headings"]) for r in all_results)
head_valid, head_count = SearchHelpers.check_heading_requirement(
    [{"score": h["score"]} for r in all_results for h in r["headings"]], 
    min_count=2
)
```

**返回结果格式（v4.0.0）：**
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=3 | doc_sets=Claude_Code_Docs:latest ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

## 检索结果摘要
- 文档集数量: 1
- 匹配PageTitle总数: 3
- 匹配Heading总数: 10
- 精准匹配(≥0.7)数量: 4

## 精准检索结果

### 高相关性文档 (High Relevance ≥0.8)

1. **Agent Skills** - PageTitle相关性: 0.95 ✅精准匹配
   - 匹配查询数: 3 (skills, Agent Skills, skills reference)
   - **匹配Heading列表**:
     - ## 1. Create your first Skill (0.96) ✅精准匹配
     - ### 1.1. Where Skills live (0.93) ✅精准匹配
     - ## 2. Configure Skills (0.91) ✅精准匹配
     - ### 2.1. Write SKILL.md (0.88) ✅精准匹配
   - **匹配统计**: PageTitle≥2个 ✅, Heading≥2个 ✅, 精准匹配≥1个 ✅

### 中等相关性文档 (0.6-0.79)

2. **CLI Skills Integration** - PageTitle相关性: 0.72
   - **匹配Heading列表**:
     - ## CLI-based Skills (0.75)
   - **匹配统计**: PageTitle≥2个 ✅, Heading≥2个 ❌, 精准匹配≥1个 ❌

3. **Skills Best Practices** - PageTitle相关性: 0.68
   - **匹配Heading列表**:
     - ## Best Practices (0.71)
     - ## Common Patterns (0.65)
   - **匹配统计**: PageTitle≥2个 ✅, Heading≥2个 ✅, 精准匹配≥1个 ❌

---

## 匹配统计 (按文档集)

- **Claude_Code_Docs:latest**:
  - PageTitle匹配: 3/2 ✅
  - Heading匹配: 10/2 ✅
  - 精准匹配: 4/1 ✅
  - 整体状态: ✅ 通过

---

### 文档来源

1. **Agent Skills**
   - 原文链接: https://code.claude.com/docs/en/agent-skills
   - TOC 路径: `{knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docTOC.md`

2. **CLI Skills Integration**
   - 原文链接: https://code.claude.com/docs/en/cli-skills
   - TOC 路径: `{knowledge_base}/Claude_Code_Docs:latest/CLI Skills Integration/docTOC.md`

3. **Skills Best Practices**
   - 原文链接: https://code.claude.com/docs/en/skills-best-practices
   - TOC 路径: `{knowledge_base}/Claude_Code_Docs:latest/Skills Best Practices/docTOC.md`

**Coverage:**
- ✅ Covered: Skills design philosophy, working principles, configuration
- ❌ Not covered: Advanced skill authoring patterns

=== END-AOP-FINAL ===
```

---

## Example 3: Progressive Fallback with Validation (v4.0.0)

**Scenario:** Level 1 semantic matching returns low-quality results

**Input query:** "deployment considerations for production"

**Level 1:** Semantic title matching
```
Query: "deployment considerations for production"
Semantic matches:
  - Deployment guide (similarity: 0.65) → Below precision threshold!
  - Production setup (similarity: 0.68) → Below precision threshold!

Result count: 2
Precision count: 0 (no result >= 0.7)
→ LEVEL 1 FAILS
```

**Level 1 Validation:**
```python
results = [
    {"title": "Deployment guide", "score": 0.65},
    {"title": "Production setup", "score": 0.68}
]

pt_valid, pt_count = SearchHelpers.check_page_title_requirement(results, min_count=2)
# → (True, 2)  # PageTitle count OK

prec_valid, prec_count = SearchHelpers.check_precision_requirement(results, precision_threshold=0.7)
# → (False, 0)  # NO precision match!

# Level 1 FAILS - trigger Level 2
```

**Level 2:** TOC grep fallback
```python
# Extract keywords
keywords = SearchHelpers.extract_keywords("deployment considerations for production")
# → ['deployment', 'production', 'considerations']

# Build grep command
cmd = SearchHelpers.build_level2_grep_command(
    keywords=["deployment", "production", "considerations"],
    doc_set="Claude_Code_Docs:latest"
)
# → "grep -r -iE '(deployment|production|considerations)' {knowledge_base}/Claude_Code_Docs:latest/*/docTOC.md"

# Execute via Bash
```

**Bash output:**
```
{knowledge_base}/Claude_Code_Docs:latest/Deployment guide/docTOC.md:## Production Deployment
{knowledge_base}/Claude_Code_Docs:latest/Deployment guide/docTOC.md:### Production Considerations
{knowledge_base}/Claude_Code_Docs:latest/Hooks reference/docTOC.md:### Deployment Hooks
{knowledge_base}/Claude_Code_Docs:latest/Security best practices/docTOC.md:## Production Security
```

**Parse and validate Level 2:**
```python
level2_results = [
    {"title": "Deployment guide", "context": "Production Deployment, Production Considerations"},
    {"title": "Hooks reference", "context": "Deployment Hooks"},
    {"title": "Security best practices", "context": "Production Security"}
]

# Check heading count >= 2
# Extract headings from context
headings = [
    {"text": "Production Deployment", "score": 0.82},
    {"text": "Production Considerations", "score": 0.78},
    {"text": "Deployment Hooks", "score": 0.75},
    {"text": "Production Security", "score": 0.72}
]

head_valid, head_count = SearchHelpers.check_heading_requirement(headings, min_count=2)
# → (True, 4)

# Level 2 SUCCESS ✓
```

**Return format:**
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=3 | doc_sets=Claude_Code_Docs:latest ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

## 检索结果摘要
- 文档集数量: 1
- 匹配PageTitle总数: 3
- 匹配Heading总数: 4
- 精准匹配(≥0.7)数量: 4

## 检索策略说明
- **Level 1**: 语义标题匹配 - PageTitle数量满足，但无精准匹配(≥0.7)
- **Level 2**: TOC内容grep搜索 - 成功找到4个相关heading

## 精准检索结果

### 高相关性文档 (High Relevance ≥0.8)

1. **Deployment guide** - PageTitle相关性: 0.65 → Level 2提升
   - **匹配Heading列表**:
     - ## Production Deployment (0.82) ✅精准匹配
     - ### Production Considerations (0.78)
   - **匹配统计**: PageTitle≥2个 ✅, Heading≥2个 ✅, 精准匹配≥1个 ✅

### 中等相关性文档 (0.6-0.79)

2. **Hooks reference** - PageTitle相关性: 0.58 → Level 2提升
   - **匹配Heading列表**:
     - ### Deployment Hooks (0.75)
   - **匹配统计**: PageTitle≥2个 ✅, Heading≥2个 ❌, 精准匹配≥1个 ❌

3. **Security best practices** - PageTitle相关性: 0.55 → Level 2提升
   - **匹配Heading列表**:
     - ## Production Security (0.72)
   - **匹配统计**: PageTitle≥2个 ✅, Heading≥2个 ❌, 精准匹配≥1个 ❌

---

## 匹配统计 (按文档集)

- **Claude_Code_Docs:latest**:
  - PageTitle匹配: 3/2 ✅
  - Heading匹配: 4/2 ✅
  - 精准匹配: 4/1 ✅
  - 整体状态: ✅ 通过

---

### 文档来源

1. **Deployment guide**
   - 原文链接: https://code.claude.com/docs/en/deployment
   - TOC 路径: `{knowledge_base}/Claude_Code_Docs:latest/Deployment guide/docTOC.md`

2. **Hooks reference**
   - 原文链接: https://code.claude.com/docs/en/hooks
   - TOC 路径: `{knowledge_base}/Claude_Code_Docs:latest/Hooks reference/docTOC.md`

3. **Security best practices**
   - 原文链接: https://code.claude.com/docs/en/security
   - TOC 路径: `{knowledge_base}/Claude_Code_Docs:latest/Security best practices/docTOC.md`

=== END-AOP-FINAL ===
```

---

## Example 4: Full Progressive Fallback with Validation (v4.0.0)

**Scenario:** Generic concept search that escalates through all levels

**Input query:** "design philosophy"

**Level 1:** Semantic title matching
```
Query: "design philosophy"
Results: 0 matches
→ LEVEL 1 FAILS immediately
```

**Level 1 Validation:**
```python
results = []
pt_valid, pt_count = SearchHelpers.check_page_title_requirement(results, min_count=2)
# → (False, 0)
# Level 1 FAILS - trigger Level 2
```

**Level 2:** TOC grep fallback
```bash
grep -r -iE '(design|philosophy)' {knowledge_base}/Claude_Code_Docs:latest/*/docTOC.md
# Output: (no matches) → LEVEL 2 FAILS
```

**Level 2 Validation:**
```python
level2_results = []
head_valid, head_count = SearchHelpers.check_heading_requirement([], min_count=2)
# → (False, 0)
# Level 2 FAILS - trigger Level 3.1
```

**Level 3.1:** Cross-set TOC search
```python
# Domain keywords: none (generic query)
# → Search all doc sets
grep -r -i "design philosophy" {knowledge_base}/*/*/docTOC.md
# Output: (no matches) → LEVEL 3.1 FAILS
```

**Level 3.1 Validation:**
```python
cross_set_results = []
head_valid, head_count = SearchHelpers.check_heading_requirement([], min_count=2)
# → (False, 0)
# Level 3.1 FAILS - trigger Level 3.2
```

**Level 3.2:** Content search with context
```bash
grep -r -i -B 10 "design philosophy" {knowledge_base}/*/*/docContent.md
```

**Bash output:**
```
{knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docContent.md-Agent Skills are a powerful feature that extends Claude Code's capabilities...
{knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docContent.md-
{knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docContent.md-## Design Philosophy
{knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docContent.md-Agent Skills follow a design philosophy focused on...
```

**Parse and validate Level 3.2:**
```python
# Extract title from content
title_cmd = SearchHelpers.build_title_extraction_command(
    "{knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docContent.md", max_lines=5
)
# Execute: head -5 {knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docContent.md
# Extract: "Agent Skills"

level3_results = [
    {
        "title": "Agent Skills",
        "doc_set": "Claude_Code_Docs:latest",
        "context": "## Design Philosophy\nAgent Skills follow a design philosophy focused on...",
        "page_title": "Agent Skills"  # REQUIRED attribution
    }
]

# Check heading count >= 2 AND attribution
headings = [{"text": "Design Philosophy", "score": 0.88}]
head_valid, head_count = SearchHelpers.check_heading_requirement(headings, min_count=2)
# → (False, 1)  # Only 1 heading!

has_attribution = all("page_title" in r for r in level3_results)
# → True

# Level 3.2 FAILS - ALL FALLBACKS EXHAUSTED
```

**Failure Report:**
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=0 | doc_sets=Claude_Code_Docs:latest ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

## 检索失败报告 (Search Failure Report)

### 失败的检索策略

| 策略 | 条件要求 | 验证结果 | 状态 |
|------|---------|---------|------|
| Level 1: 语义标题匹配 | PageTitle≥2 且 精准匹配≥0.7 | PageTitle: 0 | ❌ 失败 |
| Level 2: TOC内容grep | Heading≥2 | Heading: 0 | ❌ 失败 |
| Level 3.1: 跨集TOC搜索 | Heading≥2 | Heading: 0 | ❌ 失败 |
| Level 3.2: 全文内容搜索 | Heading≥2 且 PageTitle归属 | Heading: 1, 归属: 有 | ❌ 失败 |

### 失败的详细原因
- Level 3.2 找到1个heading ("Design Philosophy")，但少于要求的2个
- 没有足够的证据支持这是一个有效的文档匹配

### 建议操作
1. 尝试使用更具体的查询关键词
2. 确认目标文档集是否包含 "design philosophy" 相关内容
3. 检查文档库是否需要更新

=== END-AOP-FINAL ===
```

---

## Example 5: Multi-Set Search with Cross-DocSet Validation (v4.0.0)

**Scenario:** User query requires searching multiple documentation sets

**Input query:** "Claude Code 和 Cursor 的 skills 功能对比"

**Step 1:** List and filter doc sets
```bash
SearchHelpers.get_list_command()
# All doc sets: Claude_Code_Docs:latest, Cursor_Docs:v1.0, Python_Docs:3.11

# Intent filtering:
# - "Claude Code" → Filter to *Claude* sets
# - "Cursor" → Filter to *Cursor* sets
# - "comparison" → Multi-set search required
# Target: Claude_Code_Docs:latest, Cursor_Docs:v1.0
```

**Step 2:** Search within each filtered set
```python
# Search Claude Code
claude_results = search_with_validation("skills comparison", "Claude_Code_Docs:latest")
# → {"level": 1, "success": True, ...}

# Search Cursor  
cursor_results = search_with_validation("skills comparison", "Cursor_Docs:v1.0")
# → {"level": 1, "success": True, ...}
```

**Step 3:** Cross-docset validation
```python
target_doc_sets = ["Claude_Code_Docs:latest", "Cursor_Docs:v1.0"]
matched_doc_sets = ["Claude_Code_Docs:latest", "Cursor_Docs:v1.0"]

coverage = SearchHelpers.validate_cross_docset_coverage(target_doc_sets, matched_doc_sets)
# → {
#      "complete": True,
#      "matched": ["Claude_Code_Docs:latest", "Cursor_Docs:v1.0"],
#      "missing": [],
#      "extra": [],
#      "coverage_percentage": 100.0
#    }
```

**Return with coverage notes:**
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=4 | doc_sets=Claude_Code_Docs:latest,Cursor_Docs:v1.0 ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

## 检索结果摘要
- 文档集数量: 2
- 匹配PageTitle总数: 4
- 匹配Heading总数: 12
- 精准匹配(≥0.7)数量: 8

## 精准检索结果

### Claude_Code_Docs:latest

1. **Agent Skills** - PageTitle相关性: 0.94 ✅精准匹配
   - **匹配Heading列表**:
     - ## Skills Configuration (0.95) ✅
     - ### Write SKILL.md (0.92) ✅
   - **匹配统计**: ✅✅✅

### Cursor_Docs:v1.0

2. **Cursor Skills** - PageTitle相关性: 0.91 ✅精准匹配
   - **匹配Heading列表**:
     - ## Skills Setup (0.93) ✅
     - ### Configure Skills (0.89) ✅
   - **匹配统计**: ✅✅✅

---

## 匹配统计 (按文档集)

- **Claude_Code_Docs:latest**:
  - PageTitle匹配: 2/2 ✅
  - Heading匹配: 6/2 ✅
  - 精准匹配: 4/1 ✅
  - 整体状态: ✅ 通过

- **Cursor_Docs:v1.0**:
  - PageTitle匹配: 2/2 ✅
  - Heading匹配: 6/2 ✅
  - 精准匹配: 4/1 ✅
  - 整体状态: ✅ 通过

**跨文档集覆盖度:**
- ✅ 完整覆盖: 所有目标文档集均匹配成功 (100%)

---

### 文档来源

1. **Agent Skills** (Claude_Code_Docs:latest)
   - 原文链接: https://code.claude.com/docs/en/agent-skills
   - TOC 路径: `{knowledge_base}/Claude_Code_Docs:latest/Agent Skills/docTOC.md`

2. **Cursor Skills** (Cursor_Docs:v1.0)
   - 原文链接: https://cursor.com/docs/skills
   - TOC 路径: `{knowledge_base}/Cursor_Docs:v1.0/Cursor Skills/docTOC.md`

=== END-AOP-FINAL ===
```

---

## Example 6: Coverage Completeness Check with Validation (v4.0.0)

**Scenario:** Generic "best practices" query requires multi-set search

**Input query:** "best practices for hooks"

**Step 1:** Assess query type
```
Query analysis:
- "best practices" → Generic concept (cross-cutting concern)
- "hooks" → Framework-specific (Claude Code context)

Decision: Search Claude_Code_Docs:latest first, then assess coverage
```

**Step 2:** Search and verify coverage
```
Initial results from Claude_Code_Docs:latest:
- Hooks best practices (score: 0.95) ✅
- Deployment hooks guide (score: 0.88) ✅
```

**Step 2.1:** Validate
```python
results = [
    {"title": "Hooks best practices", "score": 0.95},
    {"title": "Deployment hooks guide", "score": 0.88}
]

pt_valid, pt_count = SearchHelpers.check_page_title_requirement(results, min_count=2)
# → (True, 2)

prec_valid, prec_count = SearchHelpers.check_precision_requirement(results, precision_threshold=0.7)
# → (True, 2)

# Level 1 SUCCESS
```

**Step 3:** Check coverage gaps
```
Coverage check:
- ✅ Covered: Hooks best practices
- ❌ Not covered: Testing hooks (may exist in other docs)
```

**Step 4:** Expand search if gaps found
```
Since "testing hooks" gap identified, search with additional query:
- "testing hooks" → Found: "Testing with hooks" (score: 0.82)

Final coverage: Complete
```

**Return with comprehensive coverage notes:**
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=3 | doc_sets=Claude_Code_Docs:latest ===
**Pass through EXCEPT as-is** — NO summarizing, NO rephrasing, NO commentary

## 检索结果摘要
- 文档集数量: 1
- 匹配PageTitle总数: 3
- 匹配Heading总数: 9
- 精准匹配(≥0.7)数量: 6

## 精准检索结果

1. **Hooks best practices** - 0.95 ✅
   - **匹配Heading列表**:
     - ## Best Practices Overview (0.96) ✅
     - ### Common Patterns (0.92) ✅
   - **匹配统计**: ✅✅✅

2. **Deployment hooks guide** - 0.88 ✅
   - **匹配Heading列表**:
     - ## Deployment Best Practices (0.90) ✅
   - **匹配统计**: ✅✅✅

3. **Testing with hooks** - 0.82 ✅ (Coverage Gap补全)
   - **匹配Heading列表**:
     - ## Testing Best Practices (0.85) ✅
   - **匹配统计**: ✅✅✅

---

## 匹配统计 (按文档集)

- **Claude_Code_Docs:latest**:
  - PageTitle匹配: 3/2 ✅
  - Heading匹配: 9/2 ✅
  - 精准匹配: 6/1 ✅
  - 整体状态: ✅ 通过

**Coverage:**
- ✅ Covered: Hooks best practices, deployment, testing
- ✅ 完整覆盖: 所有 aspects 均已覆盖

=== END-AOP-FINAL ===
```

---

## Key Workflow Patterns (v4.0.0)

### Pattern 1: Multi-Query Aggregation with Validation
```python
# Search with all optimized queries
for query in optimized_queries:
    results = semantic_search(query)
    aggregated_results.extend(results)

# Deduplicate by document title
unique_results = deduplicate(aggregated_results)

# Sort by match count
sorted_results = sort_by_match_count(unique_results)

# Validate Level 1 success conditions
pt_valid, _ = SearchHelpers.check_page_title_requirement(sorted_results, min_count=2)
prec_valid, _ = SearchHelpers.check_precision_requirement(sorted_results, precision_threshold=0.7)

if not (pt_valid and prec_valid):
    # Trigger fallback
    sorted_results = fallback_level_2(sorted_results)
```

### Pattern 2: Progressive Fallback with Validation
```python
# Level 1: Semantic matching
results = semantic_search(query)

pt_valid, _ = SearchHelpers.check_page_title_requirement(results, min_count=2)
prec_valid, _ = SearchHelpers.check_precision_requirement(results, precision_threshold=0.7)

if not (pt_valid and prec_valid):
    # Level 2: TOC grep
    results = toc_grep_search(keywords, doc_set)
    head_valid, _ = SearchHelpers.check_heading_requirement(results, min_count=2)
    
    if not head_valid:
        # Level 3.1: Cross-set search
        results = cross_set_search(keywords, filtered_sets)
        head_valid, _ = SearchHelpers.check_heading_requirement(results, min_count=2)
        
        if not head_valid:
            # Level 3.2: Content search with attribution
            results = content_search_with_context(keywords, doc_sets)
            # Must include PageTitle attribution
```

### Pattern 3: Coverage Verification with Cross-DocSet Validation
```python
# After search, verify coverage
coverage = assess_coverage(query, results)

# Check for gaps
if coverage.has_gaps():
    expanded_results = search_for_gaps(coverage.gaps)
    results.extend(expanded_results)

# Cross-docset validation for multi-set searches
if target_doc_sets > 1:
    coverage_validation = SearchHelpers.validate_cross_docset_coverage(
        target_doc_sets,
        matched_doc_sets
    )
    
    if not coverage_validation["complete"]:
        # Report missing doc-sets
        print(f"Missing: {coverage_validation['missing']}")
```

### Pattern 4: Complete Validation Before Output
```python
# Validate all success conditions before returning
validation = SearchHelpers.validate_search_success(
    page_title_results,
    heading_results,
    precision_threshold=0.7
)

if validation["success"]:
    # Format output
    summary = SearchHelpers.format_search_summary(...)
    stats = SearchHelpers.format_match_statistics(...)
    output = format_aop_final(summary, stats, sources, coverage)
    return output
else:
    # Report failure
    failure_report = format_failure_report(validation)
    return failure_report
```

---

## Using Helper Functions in Workflows (v4.0.0)

### Quick Helper Usage Examples

```python
from doc4llm.tool.md_doc_retrieval import SearchHelpers

# Configure thresholds
SearchHelpers.set_basic_threshold(0.6)
SearchHelpers.set_precision_threshold(0.7)
SearchHelpers.set_min_page_title_matches(2)
SearchHelpers.set_min_heading_matches(2)

# Build patterns
pattern = SearchHelpers.build_toc_glob_pattern("Claude_Code_Docs:latest")

# Validate
page_title_valid, count = SearchHelpers.check_page_title_requirement(results, min_count=2)
heading_valid, count = SearchHelpers.check_heading_requirement(heading_results, min_count=2)
precision_valid, count = SearchHelpers.check_precision_requirement(results, precision_threshold=0.7)

# Format output
url = SearchHelpers.extract_original_url(toc_content)
sources = SearchHelpers.format_sources_section([
    ("Title", url, "path/to/docTOC.md")
])
coverage = SearchHelpers.format_coverage_section(
    covered=["A", "B"],
    partial=["C"],
    not_covered=["D"],
    suggestion="Search for D"
)

# v4.0.0 New helpers
summary = SearchHelpers.format_search_summary(page_title_count, heading_count, precision_count, doc_set_count)
stats = SearchHelpers.format_match_statistics(docset_results)
heading_list = SearchHelpers.format_heading_list_with_scores(headings, page_title)

# Cross-docset validation
coverage = SearchHelpers.validate_cross_docset_coverage(target_sets, matched_sets)
```

---

## API Version

This document describes Workflow Examples v4.0.0
