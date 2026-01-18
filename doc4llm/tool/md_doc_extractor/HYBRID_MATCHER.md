# Hybrid Agentic Document Matcher

## 概述

`HybridMatcher` 采用**混合策略**：快速规则匹配优先，LLM 语义理解作为兜底增强。

---

## 设计理念

### 为什么选择混合方案？

| 方案 | 速度 | 成本 | 理解力 | 适用场景 |
|------|------|------|--------|----------|
| **纯规则** | ⚡ 快 | 💰 免费 | 关键词匹配 | 简单、精确查询 |
| **纯 LLM** | 🐌 慢 | 💸💸 高 | 语义理解 | 复杂、模糊查询 |
| **混合** | ⚡⚡ 快+ | 💰 低 | 智能+ | **所有场景** |

### 工作流程

```
用户查询
    │
    ▼
┌─────────────────────────────────┐
│  Phase 1: 快速规则匹配           │
│  • 标题匹配                       │
│  • TOC 搜索                       │
│  • 内容预览                       │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  质量评估                        │
│  ✓ 结果数量 >= 2                 │
│  ✓ 最高相似度 >= 0.7             │
│  ✓ 无开放性问题关键词            │
└─────────────────────────────────┘
    │
    ├─ 满意 → 返回结果 ⚡
    │
    └─ 不满意
        │
        ▼
    ┌─────────────────────────────────┐
    │  Phase 2: LLM 语义增强           │
    │  • 意图识别 (tutorial/api/...)   │
    │  • 查询优化                      │
    │  • 搜索词生成                    │
    │  • 预期章节预测                  │
    └─────────────────────────────────┘
        │
        ▼
    返回增强结果 🧠
```

---

## 使用方法

### 快速开始

```python
from doc4llm.tool.md_doc_extractor import hybrid_search

# 一行代码，自动选择策略
result = hybrid_search("skills", base_dir="md_docs")

print(f"Found {len(result['results'])} results")
for r in result['results']:
    print(f"  - {r['title']} (similarity: {r['similarity']:.2f})")

# 检查是否使用了 LLM
if result['enhancement'].triggered:
    print(f"LLM Intent: {result['enhancement'].intent}")
    print(f"Refined Query: {result['enhancement'].query_refinement}")
```

### 完整配置

```python
from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor, HybridMatcher

extractor = MarkdownDocExtractor(base_dir="md_docs")

matcher = HybridMatcher(
    extractor,
    api_key="your-anthropic-api-key",  # 或从环境变量读取
    config={
        # LLM 触发条件
        "llm_trigger_min_results": 2,        # 结果少于 2 个时触发
        "llm_trigger_max_similarity": 0.7,   # 最高相似度低于 0.7 时触发
        "llm_trigger_open_questions": [
            "how", "why", "explain", "best way"
        ],

        # LLM 配置
        "llm_model": "claude-3-5-haiku-20241022",  # 使用 Haiku 降低成本
        "llm_max_tokens": 1024,
        "llm_temperature": 0.3,

        # 混合策略
        "llm_max_refinements": 2,          # 最多优化查询次数
        "llm_merge_results": True,         # 合并原始和增强结果
    },
    debug_mode=True  # 查看决策过程
)

result = matcher.match("how do I create my first skill")
```

---

## LLM 触发条件

### 自动触发（任一满足）

| 条件 | 说明 | 示例 |
|------|------|------|
| **结果不足** | 结果数 < `llm_trigger_min_results` | 查询 "xyzabc" 找不到结果 |
| **质量低** | 最高相似度 < `llm_trigger_max_similarity` | 所有结果相似度 < 0.7 |
| **开放性问题** | 包含 "how", "why" 等关键词 | "how to use skills" |

### 手动触发

```python
# 强制使用 LLM（用于测试）
result = matcher.match("skills", force_llm=True)
```

---

## LLM 增强能力

### 1. 意图识别

```python
# LLM 识别用户意图
result = matcher.match("how do I create a skill")

result['enhancement'].intent
# → "tutorial"

result['enhancement'].query_refinement
# → "create custom skill tutorial"
```

支持的意图类型：
- `tutorial` - 用户想学习如何做某事
- `api_reference` - 用户想要 API 详情或语法
- `troubleshooting` - 用户有要解决的问题
- `concept` - 用户想理解某个概念
- `comparison` - 用户想比较事物
- `configuration` - 用户想要配置/设置帮助

### 2. 查询优化

```python
# 原始查询可能不够精确
original_query = "how to use the thing for skills"

# LLM 优化后
refined_query = result['enhancement'].query_refinement
# → "how to use agent skills"
```

### 3. 搜索词生成

LLM 会生成 2-3 个备选搜索词：

```python
# 内部调用
search_terms = llm_analysis.get("search_terms")
# ["agent skills", "create skills", "skills tutorial"]
```

---

## 返回结果格式

```python
{
    "results": [
        {
            "title": "Agent Skills",
            "similarity": 0.85,
            "match_type": "toc_section",
            "doc_name_version": "code_claude_com:latest",
            "source": "toc",
            "sections_matched": ["Create your first Skill"]
        },
        # ... 更多结果
    ],
    "enhancement": {
        "triggered": True,              # 是否触发了 LLM
        "reason": "insufficient_results",  # 触发原因
        "original_count": 1,            # 原始结果数
        "enhanced_count": 5,            # 增强后结果数
        "intent": "tutorial",           # LLM 识别的意图
        "query_refinement": "how to create agent skills"  # 优化后的查询
    },
    "query": "how to create agent skills"  # 最终使用的查询
}
```

---

## 性能与成本

### 性能对比

| 场景 | 纯规则 | 混合 | 纯 LLM |
|------|--------|------|--------|
| 简单查询 ("skills") | ~50ms | ~50ms | ~2000ms |
| 中等查询 ("configure") | ~100ms | ~100ms | ~2000ms |
| 复杂查询 ("how to create...") | ~150ms | ~2000ms | ~2500ms |

### 成本估算（基于 Haiku）

| 使用频率 | 月成本 |
|---------|-------|
| 10% 查询触发 LLM | ~$0.50 |
| 30% 查询触发 LLM | ~$1.50 |
| 100% 查询触发 LLM | ~$5.00 |

---

## 测试

```bash
# 运行测试套件
cd /Users/zorro/project/doc4llm
python tests/test_hybrid_matcher.py

# 设置 API key（如果未设置）
export ANTHROPIC_AUTH_TOKEN='your-key-here'
```

测试包括：
1. 快速路径（仅规则匹配）
2. LLM 回退（结果不佳时）
3. 强制 LLM（测试模式）
4. 对比表
5. 触发条件测试
6. 意图识别测试

---

## 架构

```
HybridMatcher
├── RuleMatcher (AgenticDocMatcher)
│   ├── ProgressiveRetriever
│   │   ├── Stage 1: 标题匹配
│   │   ├── Stage 2: TOC 搜索
│   │   └── Stage 3: 内容预览
│   └── ReflectiveReRanker
│
└── LLM Enhancer
    ├── 意图识别
    ├── 查询优化
    ├── 搜索词生成
    └── 结果合并
```

---

## 版本

- **v2.1.0** - 初始发布 HybridMatcher
- **v2.0.0** - AgenticDocMatcher（纯规则）
- **v1.0.0** - MarkdownDocExtractor（基础版）
