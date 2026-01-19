# md-doc-searcher Workflow Examples

This document provides detailed workflow examples for the md-doc-searcher skill.

## Example 1: Single-Query Search

**Input from md-doc-query-optimizer:**
```
Optimized Queries (Ranked):
1. "hooks configuration" - translation: Direct English translation
```

**Step 1:** List and filter doc sets
```bash
SearchHelpers.get_list_command()
# Execute: ls -1 md_docs/

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
# → "md_docs/Claude_Code_Docs:latest/*/docTOC.md"

# Returns matches like:
# - Hooks reference/docTOC.md
# - Get started with Claude Code hooks/docTOC.md
```

**Step 4-6:** Semantic matching
```
Query: "hooks configuration"
Results:
  - Hooks reference (matched)
  - Get started with Claude Code hooks (matched)
```

**Return format:**
```markdown
Found 2 relevant document(s):

1. **Hooks reference** - Relevance: Matched by "hooks configuration"
2. **Get started with Claude Code hooks** - Relevance: Contains setup information

**Coverage:**
- ✅ Covered: Hooks configuration and setup
- ⚠️  Partially covered: Deployment-specific configuration

### 文档来源

1. **Hooks reference**
   - 原文链接: https://code.claude.com/docs/en/hooks
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Hooks reference/docTOC.md`

2. **Get started with Claude Code hooks**
   - 原文链接: https://code.claude.com/docs/en/hooks-getting-started
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Get started with Claude Code hooks/docTOC.md`
```

---

## Example 2: Multi-Query Aggregation

**Input from md-doc-query-optimizer:**
```
Optimized Queries (Ranked):
1. "skills" - direct match
2. "Agent Skills" - context-specific expansion
3. "skills reference" - expansion
```

**Step 1:** 列出文档集并根据意图过滤
```bash
SearchHelpers.get_list_command()
# Execute: ls -1 md_docs/

# 输出:
# Claude_Code_Docs:latest
# Python_Docs:3.11
# React_Docs:v18

# 根据优化查询过滤：所有查询都指向 "skills" → Claude Code 上下文
# 目标文档集: Claude_Code_Docs:latest
```

**Step 2:** 在指定文档集中列出所有目录
```python
SearchHelpers.build_toc_glob_pattern("Claude_Code_Docs:latest")
# → "md_docs/Claude_Code_Docs:latest/*/docTOC.md"

# 返回:
# Agent Skills/
# CLI reference/
# Hooks reference/
# ...
```

**Step 3:** 多查询语义匹配

读取相关文档的 `docTOC.md` 获取更多上下文：
```bash
Read md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md
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

### 文档来源

1. **Agent Skills**
   - 原文链接: https://code.claude.com/docs/en/agent-skills
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md`

**Note:** Use `/md-doc-reader "Agent Skills"` to view the full TOC and document structure.
```

---

## Example 3: Progressive Fallback (Level 1 → Level 2)

**Scenario:** Level 1 semantic matching returns low-quality results

**Input query:** "deployment considerations for production"

**Step 1:** Level 1 semantic matching
```
Query: "deployment considerations for production"
Semantic matches:
  - Deployment guide (similarity: 0.65) → Below threshold!
  - Production setup (similarity: 0.68) → Below threshold!

Result: max_similarity < 0.7 → TRIGGER LEVEL 2
```

**Step 2:** Level 2 TOC grep fallback
```python
# Extract keywords
keywords = SearchHelpers.extract_keywords("deployment considerations for production")
# → ['deployment', 'production']

# Build grep command
cmd = SearchHelpers.build_level2_grep_command(
    keywords=["deployment", "production"],
    doc_set="Claude_Code_Docs:latest"
)
# → "grep -r -iE '(deployment|production)' md_docs/Claude_Code_Docs:latest/*/docTOC.md"

# Execute via Bash
```

**Bash output:**
```
md_docs/Claude_Code_Docs:latest/Deployment guide/docTOC.md:## Production Deployment
md_docs/Claude_Code_Docs:latest/Deployment guide/docTOC.md:### Production Considerations
md_docs/Claude_Code_Docs:latest/Hooks reference/docTOC.md:### Deployment Hooks
```

**Step 3:** Aggregate and return results
```markdown
Found 2 relevant document(s) via Level 2 TOC search:

1. **Deployment guide** - Relevance: Contains "Production Deployment" and "Production Considerations" sections
2. **Hooks reference** - Relevance: Contains "Deployment Hooks" section

**Coverage:**
- ✅ Covered: Production deployment considerations
- ✅ Covered: Deployment hooks configuration

### 文档来源

1. **Deployment guide**
   - 原文链接: https://code.claude.com/docs/en/deployment
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Deployment guide/docTOC.md`

2. **Hooks reference**
   - 原文链接: https://code.claude.com/docs/en/hooks
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Hooks reference/docTOC.md`
```

---

## Example 4: Full Progressive Fallback (Level 1 → 2 → 3.1 → 3.2)

**Scenario:** Generic concept search that escalates through all levels

**Input query:** "design philosophy"

**Level 1:** Semantic title matching
```
Query: "design philosophy"
Results: 0 matches → TRIGGER LEVEL 2
```

**Level 2:** TOC grep fallback
```bash
grep -r -iE '(design|philosophy)' md_docs/Claude_Code_Docs:latest/*/docTOC.md
# Output: (no matches) → TRIGGER LEVEL 3.1
```

**Level 3.1:** Cross-set TOC search
```python
# Domain keywords: none (generic query)
# → Search all doc sets
grep -r -i "design philosophy" md_docs/*/*/docTOC.md
# Output: (no matches) → TRIGGER LEVEL 3.2
```

**Level 3.2:** Content search with context
```bash
grep -r -i -B 10 "design philosophy" md_docs/*/*/docContent.md
```

**Bash output:**
```
md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md-Agent Skills are a powerful feature that extends Claude Code's capabilities...
md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md-
md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md-## Design Philosophy
md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md-Agent Skills follow a design philosophy focused on...
```

**Parse and format results:**
```markdown
Found 1 relevant document(s) via Level 3.2 content search:

1. **Agent Skills** (Claude_Code_Docs:latest)
   - Relevance: Content contains "design philosophy" in section context
   - Context: "## Design Philosophy\nAgent Skills follow a design philosophy focused on..."
   - TOC Path: `md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md`

**Note:** Use `/md-doc-reader "Agent Skills"` to view full TOC and document structure.

### 文档来源

1. **Agent Skills**
   - 原文链接: https://code.claude.com/docs/en/agent-skills
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md`
```

---

## Example 5: Multi-Set Search with Domain Filtering

**Scenario:** User query requires searching multiple documentation sets

**Input query:** "Claude Code 中关于 security 的文档"

**Step 1:** List and filter doc sets
```bash
SearchHelpers.get_list_command()
# All doc sets: Claude_Code_Docs:latest, Python_Docs:3.11, React_Docs:v18

# Intent filtering:
# - "Claude Code" → Filter to *Claude* sets
# - "security" → Generic term, but within Claude Code context
# Target: Claude_Code_Docs:latest only
```

**Step 2:** Search within filtered set
```
Query: "security"
Results:
  - Security best practices
  - Authentication configuration
  - API security
```

**Return with coverage notes:**
```markdown
Found 3 relevant document(s) in Claude_Code_Docs:latest:

1. **Security best practices** - Relevance: Matched by "security"
2. **Authentication configuration** - Relevance: Security-related authentication
3. **API security** - Relevance: API-specific security

**Coverage:**
- ✅ Covered: Security best practices and authentication
- ⚠️  Partially covered: API security (only overview)
- ❌ Not covered: Network security, firewall configuration

### 文档来源

1. **Security best practices**
   - 原文链接: https://code.claude.com/docs/en/security-best-practices
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Security best practices/docTOC.md
```

---

## Example 6: Coverage Completeness Check

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
- Hooks best practices
- Deployment hooks guide

Coverage check:
- ✅ Covered: Hooks best practices
- ❌ Not covered: Testing hooks (may exist in other docs)
```

**Step 3:** Expand search if gaps found
```
Since "testing hooks" gap identified, search with additional query:
- "testing hooks" → Found: "Testing with hooks"

Final coverage: Complete
```

**Return with comprehensive coverage notes:**
```markdown
Found 3 relevant document(s) in Claude_Code_Docs:latest:

1. **Hooks best practices** - Relevance: Direct match for best practices
2. **Deployment hooks guide** - Relevance: Contains deployment-specific best practices
3. **Testing with hooks** - Relevance: Testing best practices (found via coverage gap expansion)

**Coverage:**
- ✅ Covered: Hooks best practices, deployment best practices, testing best practices
- ✅ Coverage complete: All aspects of hooks best practices covered

### 文档来源

1. **Hooks best practices**
   - 原文链接: https://code.claude.com/docs/en/hooks-best-practices
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Hooks best practices/docTOC.md`

2. **Deployment hooks guide**
   - 原文链接: https://code.claude.com/docs/en/deployment-hooks
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Deployment hooks guide/docTOC.md`

3. **Testing with hooks**
   - 原文链接: https://code.claude.com/docs/en/testing-hooks
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Testing with hooks/docTOC.md`
```

---

## Example 7: Intent-Based Redundancy Filtering (Step 6)

**Scenario:** After coverage verification, apply intent-based filtering to improve precision

**Input query:** "Claude Code hooks的最佳实践"

**Step 1-5:** Standard search process
```
Search Results After Coverage Verification:
1. "Hooks best practices" - Found via semantic matching
2. "Get started with Claude Code hooks" - Found via expansion
3. "Hooks reference" - Found via Level 2 fallback
4. "API reference" - Found via cross-set search
5. "Claude Code overview" - Found via generic matching
```

**Step 6:** Intent-based filtering

**Step 6.1:** Query intent analysis
```python
intent = SearchHelpers.analyze_query_intent("Claude Code hooks的最佳实践")
# Returns:
# {
#   "primary_intent": "LEARN",
#   "scope": "SPECIFIC", 
#   "depth": "DETAILED",
#   "specificity_keywords": ["hooks", "最佳实践", "Claude Code"]
# }
```

**Step 6.2:** Document relevance scoring
```python
# For each document, calculate relevance
results = [
    {
        "title": "Hooks best practices",
        "score": 0.95,
        "rationale": "Direct match for hooks best practices learning"
    },
    {
        "title": "Get started with Claude Code hooks", 
        "score": 0.75,
        "rationale": "Provides foundational knowledge for best practices"
    },
    {
        "title": "Hooks reference",
        "score": 0.65,
        "rationale": "Technical reference, less focused on best practices"
    },
    {
        "title": "API reference",
        "score": 0.25,
        "rationale": "Different topic (API vs hooks best practices)"
    },
    {
        "title": "Claude Code overview",
        "score": 0.15,
        "rationale": "Too general for specific hooks best practices query"
    }
]
```

**Step 6.3:** Apply filtering thresholds
```
High Relevance (≥0.8): 
- "Hooks best practices" (0.95)

Medium Relevance (0.5-0.79):
- "Get started with Claude Code hooks" (0.75)
- "Hooks reference" (0.65)

Filtered Out (<0.5):
- "API reference" (0.25)
- "Claude Code overview" (0.15)
```

**Final filtered results:**
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=3 | doc_sets=Claude_Code_Docs:latest ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

## 精准检索结果 (Intent-Filtered Results)

### 高相关性文档 (High Relevance ≥0.8)
1. **Hooks best practices** - Relevance: 0.95
   - Intent Match: Direct answer to hooks best practices learning need
   - TOC Path: `md_docs/Claude_Code_Docs:latest/Hooks best practices/docTOC.md`

### 相关文档 (Medium Relevance 0.5-0.79)
2. **Get started with Claude Code hooks** - Relevance: 0.75
   - Intent Match: Provides foundational knowledge for understanding best practices
   - Note: Introductory content, complements best practices
   - TOC Path: `md_docs/Claude_Code_Docs:latest/Get started with Claude Code hooks/docTOC.md`

3. **Hooks reference** - Relevance: 0.65
   - Intent Match: Technical reference supporting best practices understanding
   - Note: Reference material, not practice-focused
   - TOC Path: `md_docs/Claude_Code_Docs:latest/Hooks reference/docTOC.md`

### 已过滤文档 (Filtered Out <0.5)
- "API reference" - Reason: Different topic (API vs hooks best practices)
- "Claude Code overview" - Reason: Too general for specific best practices query

**Filtering Summary:**
- Original results: 5 documents
- High relevance: 1 document
- Medium relevance: 2 documents
- Filtered out: 2 documents
- Precision improvement: 40% → 100% (high relevance focus)

**Coverage:**
- ✅ Covered: Hooks best practices, foundational knowledge, technical reference
- ✅ Coverage complete: All aspects of hooks best practices covered

---

### 文档来源 (Sources)

1. **Hooks best practices**
   - 原文链接: https://code.claude.com/docs/en/hooks-best-practices
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Hooks best practices/docTOC.md`

2. **Get started with Claude Code hooks**
   - 原文链接: https://code.claude.com/docs/en/get-started-hooks
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Get started with Claude Code hooks/docTOC.md`

3. **Hooks reference**
   - 原文链接: https://code.claude.com/docs/en/hooks-reference
   - TOC 路径: `md_docs/Claude_Code_Docs:latest/Hooks reference/docTOC.md`

=== END-AOP-FINAL ===
```

---

## Key Workflow Patterns

### Pattern 1: Multi-Query Aggregation
```python
# Search with all optimized queries
for query in optimized_queries:
    results = semantic_search(query)
    aggregated_results.extend(results)

# Deduplicate by document title
unique_results = deduplicate(aggregated_results)

# Sort by match count
sorted_results = sort_by_match_count(unique_results)
```

### Pattern 2: Progressive Fallback
```python
# Level 1: Semantic matching
results = semantic_search(query)
if not results or max_similarity(results) < 0.7:
    # Level 2: TOC grep
    results = toc_grep_search(keywords, doc_set)
    if not results:
        # Level 3.1: Cross-set search
        results = cross_set_search(keywords, filtered_sets)
        if not results:
            # Level 3.2: Content search
            results = content_search_with_context(keywords, doc_sets)
```

### Pattern 3: Coverage Verification
```python
# After search, verify coverage
coverage = assess_coverage(query, results)
if coverage.has_gaps():
    expanded_results = search_for_gaps(coverage.gaps)
    results.extend(expanded_results)
```

---

## Using Helper Functions in Workflows

### Quick Helper Usage Examples

```python
from doc4llm.tool.md_doc_retrieval import SearchHelpers

# Build patterns
pattern = SearchHelpers.build_toc_glob_pattern("Claude_Code_Docs:latest")

# Extract and format
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
```
