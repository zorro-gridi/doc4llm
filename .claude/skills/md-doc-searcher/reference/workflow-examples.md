# md-doc-searcher Workflow Examples

## 概述

本文档提供md-doc-searcher技能的实践工作流程示例。完整策略说明请参考：
- **渐进回退策略**: `reference/progressive-fallback.md`
- **API函数**: `reference/search-helpers-api.md`
- **核心流程**: 参见技能主文档 `../SKILL.md`

---

## 示例1: 单查询搜索

**输入** (来自md-doc-query-optimizer):
```
Optimized Query: "hooks configuration"
```

**步骤**:
```bash
# Step 1: 列出文档集
ls -1 {knowledge_base}/
# → Claude_Code_Docs:latest, Python_Docs:3.11, React_Docs:v18

# Step 2: 过滤目标集
# Filter: "hooks" → Claude_Code_Docs:latest

# Step 3: 语义匹配PageTitle
# Results: Hooks reference (0.92), Get started (0.85), Testing (0.68)

# Step 4: 验证Level 1成功条件
# PageTitle≥2 ✅, 精准匹配≥0.7 ✅ → Level 1 SUCCESS

# Step 5: 提取并评分Heading
```

**输出**:
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=3 | doc_sets=Claude_Code_Docs:latest ===

## 检索结果摘要
- 文档集数量: 1
- 匹配PageTitle总数: 3
- 匹配Heading总数: 8
- 精准匹配(≥0.7)数量: 5

## 精准检索结果

### 高相关性文档 (≥0.8)

**Hooks reference** - PageTitle相关性: 0.92 ✅精准匹配
- **匹配Heading列表**:
  - ## 1. Hook Configuration (0.94) ✅精准匹配
  - ### 1.1. Configuration Options (0.91) ✅精准匹配
- **匹配统计**: ✅✅✅

### 中等相关性 (0.6-0.79)

**Get started with Claude Code hooks** - PageTitle相关性: 0.85
- **匹配Heading列表**:
  - ## 1. Introduction to hooks (0.87)
  - ## 2. Basic configuration (0.82)

## 匹配统计 (按文档集)
- **Claude_Code_Docs:latest**: ✅✅✅ 完整通过

### 文档来源
1. **Hooks reference** - https://code.claude.com/docs/en/hooks
   - TOC: `{knowledge_base}/Claude_Code_Docs:latest/Hooks reference/docTOC.md`

**Coverage:** ✅ Covered: hooks配置, 基础设置, 测试
=== END-AOP-FINAL ===
```

---

## 示例2: 多查询聚合

**输入** (来自md-doc-query-optimizer):
```
1. "skills" - direct match
2. "Agent Skills" - context-specific
3. "skills reference" - expansion
```

**步骤**:
```python
# 多查询语义匹配
# - "skills" → Agent Skills (0.95)
# - "Agent Skills" → Agent Skills (0.98) ✅
# - "skills reference" → Agent Skills (0.92)

# 聚合结果并验证
results = [{"Agent Skills", 0.95}, {"CLI Skills", 0.72}, {"Best Practices", 0.68}]
pt_valid, _ = SearchHelpers.check_page_title_requirement(results, min_count=2)
prec_valid, _ = SearchHelpers.check_precision_requirement(results, precision_threshold=0.7)
# → PageTitle≥2 ✅, 精准匹配≥0.7 ✅ → Level 1 SUCCESS
```

**输出**:
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=3 | doc_sets=Claude_Code_Docs:latest ===

## 检索结果摘要
- 文档集数量: 1
- 匹配PageTitle总数: 3
- 匹配Heading总数: 10
- 精准匹配(≥0.7)数量: 4

## 精准检索结果

### 高相关性 (≥0.8)

**Agent Skills** - 0.95 ✅精准匹配
- 匹配查询数: 3
- **匹配Heading列表**:
  - ## 1. Create your first Skill (0.96) ✅
  - ## 2. Configure Skills (0.91) ✅

### 中等相关性 (0.6-0.79)

**CLI Skills Integration** - 0.72
- **匹配Heading列表**: ## CLI-based Skills (0.75)

**Skills Best Practices** - 0.68
- **匹配Heading列表**: Best Practices (0.71), Common Patterns (0.65)

## 匹配统计 (按文档集)
- **Claude_Code_Docs:latest**: ✅✅✅

**Coverage:** ✅ Covered: skills设计哲学, 工作原理, 配置
=== END-AOP-FINAL ===
```

---

## 示例3: 渐进回退 - Level 1失败

**场景**: 语义匹配结果无精准匹配

| 策略 | 条件要求 | 结果 | 状态 |
|------|---------|------|------|
| Level 1 | PageTitle≥2 且 精准≥0.7 | PageTitle: 2, 精准: 0 | ❌ 失败 |
| Level 2 | Heading≥2 | Heading: 4 | ✅ 成功 |

**Level 1失败**: "deployment considerations" → Deployment guide (0.65), Production setup (0.68) 均<0.7

**Level 2成功**: TOC grep找到4个heading:
- Production Deployment (0.82)
- Production Considerations (0.78)
- Deployment Hooks (0.75)
- Production Security (0.72)

**完整回退流程**: 参见 `reference/progressive-fallback.md`

---

## 示例4: 完整回退链 - 所有策略

**场景**: 通用概念搜索 "design philosophy"

| 策略 | 条件 | 结果 | 状态 |
|------|------|------|------|
| Level 1 | PageTitle≥2, 精准≥0.7 | PageTitle: 0 | ❌ |
| Level 2 | Heading≥2 | Heading: 0 | ❌ |
| Level 3.1 | Heading≥2 (跨集) | Heading: 0 | ❌ |
| Level 3.2 | Heading≥2 + 归属 | Heading: 1 | ❌ |

**结果**: 所有策略失败

**失败报告**:
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=0 | doc_sets=1 ===

## 检索失败报告

| 策略 | 条件 | 验证结果 | 状态 |
|------|------|---------|------|
| Level 1 | PageTitle≥2, 精准≥0.7 | 0 | ❌ |
| Level 2 | Heading≥2 | 0 | ❌ |
| Level 3.1 | Heading≥2 | 0 | ❌ |
| Level 3.2 | Heading≥2 + 归属 | 1 | ❌ |

**建议:**
1. 使用更具体的查询关键词
2. 确认目标文档集是否包含相关内容
=== END-AOP-FINAL ===
```

---

## 示例5: 跨文档集搜索

**输入**: "Claude Code 和 Cursor 的 skills 功能对比"

**步骤**:
```python
# Step 1: 过滤目标集
target_sets = ["Claude_Code_Docs:latest", "Cursor_Docs:v1.0"]

# Step 2: 各自搜索
claude = search_with_validation("skills comparison", "Claude_Code_Docs:latest")
cursor = search_with_validation("skills comparison", "Cursor_Docs:v1.0")

# Step 3: 跨集覆盖度验证
coverage = SearchHelpers.validate_cross_docset_coverage(
    target_sets, ["Claude_Code_Docs:latest", "Cursor_Docs:v1.0"]
)
# → {"complete": True, "coverage_percentage": 100.0}
```

**输出**:
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=4 | doc_sets=2 ===

## 检索结果摘要
- 文档集数量: 2
- 匹配PageTitle总数: 4
- 匹配Heading总数: 12

## 精准检索结果

### Claude_Code_Docs:latest
**Agent Skills** - 0.94 ✅
- ## Skills Configuration (0.95) ✅, ### Write SKILL.md (0.92) ✅

### Cursor_Docs:v1.0
**Cursor Skills** - 0.91 ✅
- ## Skills Setup (0.93) ✅, ### Configure Skills (0.89) ✅

## 匹配统计 (按文档集)
- **Claude_Code_Docs:latest**: ✅✅✅
- **Cursor_Docs:v1.0**: ✅✅✅
**跨文档集覆盖度:** ✅ 100%

**Coverage:** ✅ 完整覆盖 skills 功能对比
=== END-AOP-FINAL ===
```

---

## 示例6: 覆盖度检查

**输入**: "best practices for hooks"

**步骤**:
```python
# 初始搜索
results = [{"Hooks best practices", 0.95}, {"Deployment hooks", 0.88}]
# → Level 1 SUCCESS ✅

# 覆盖度检查
coverage = assess_coverage("best practices for hooks", results)
# → Gap: testing hooks 未覆盖

# 补全搜索
gap_results = search_with_validation("testing hooks", "Claude_Code_Docs:latest")
# → {"Testing with hooks", 0.82}
```

**输出**:
```markdown
=== AOP-FINAL | agent=md-doc-searcher | results=3 | doc_sets=1 ===

## 检索结果摘要
- 匹配PageTitle总数: 3
- 匹配Heading总数: 9
- 精准匹配(≥0.7)数量: 6

## 精准检索结果

**Hooks best practices** - 0.95 ✅
- ## Best Practices Overview (0.96) ✅, ### Common Patterns (0.92) ✅

**Deployment hooks guide** - 0.88 ✅
- ## Deployment Best Practices (0.90) ✅

**Testing with hooks** - 0.82 ✅ (Coverage Gap补全)
- ## Testing Best Practices (0.85) ✅

## 匹配统计 (按文档集)
- **Claude_Code_Docs:latest**: ✅✅✅

**Coverage:** ✅ 完整覆盖 hooks 最佳实践
=== END-AOP-FINAL ===
```

---

## 核心工作流模式

| 模式 | 代码 | 详细说明 |
|------|------|----------|
| 多查询聚合 | `semantic_search(query)` × N → 聚合去重 | 示例2 |
| 渐进回退 | 验证失败 → 触发下一级 | 详见 progressive-fallback.md |
| 跨集验证 | `validate_cross_docset_coverage()` | 示例5 |
| 覆盖度检查 | `assess_coverage()` → 补全Gap | 示例6 |

---

## API Version

本文档描述 Workflow Examples v4.1.0
