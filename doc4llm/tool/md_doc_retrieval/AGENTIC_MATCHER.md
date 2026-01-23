# Agentic Document Matcher

## 概述

`AgenticDocMatcher` 是对文档检索系统的 agentic 优化，通过**多阶段渐进检索**和**自反思重排序**实现智能文档匹配。

---

## 核心设计

### 架构

```
                    ┌──────────────────────────────────────┐
                    │     AgenticDocMatcher (入口)          │
                    └──────────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
           ┌─────────────────┐             ┌─────────────────┐
           │  Progressive    │             │   Reflective    │
           │  Retriever      │────────────▶│   ReRanker      │
           │                 │  初步结果    │                 │
           │ • 标题匹配      │             │ • 质量评估      │
           │ • TOC搜索       │             │ • 语义去重      │
           │ • 预览匹配      │             │ • 重新排序      │
           └─────────────────┘             └─────────────────┘
                    │                                 │
                    └────────────────┬────────────────┘
                                     ▼
                            ┌─────────────────┐
                            │  Ranked Results │
                            └─────────────────┘
```

### Agentic 特征

| 特征 | 实现方式 |
|------|----------|
| **观察** | 分析初步检索结果的质量 |
| **决策** | 根据质量评估决定是否扩展搜索 |
| **行动** | 执行多阶段检索策略 |
| **反思** | 自我评估结果并重新排序 |

---

## 使用方法

### 快速开始

```python
from doc4llm.tool.md_doc_retrieval import agentic_search

# 一行代码完成 agentic 搜索
results = agentic_search("skills", base_dir="md_docs")

for r in results:
    print(f"{r['title']} - {r['similarity']:.2f} ({r['source']})")
```

### 完整配置

```python
from doc4llm.tool.md_doc_retrieval import (
    MarkdownDocExtractor,
    AgenticDocMatcher
)

# 创建 matcher
extractor = MarkdownDocExtractor(base_dir="md_docs")
matcher = AgenticDocMatcher(
    extractor,
    config={
        "min_results": 3,          # 最小结果数
        "min_similarity": 0.5,     # 最小相似度
        "title_max_results": 5,    # 标题匹配最大结果
        "toc_max_results": 10,     # TOC 搜索最大结果
    },
    debug_mode=True  # 启用调试输出
)

# 执行搜索
results = matcher.match("commit message", max_results=10)
```

---

## 检索阶段

### Stage 1: 标题匹配 (始终执行)

```python
# 快速、精确的标题匹配
title_results = extractor.semantic_search_titles(query)
# → 返回: {title, similarity, match_type, doc_name_version}
```

### Stage 2: TOC 章节匹配 (条件执行)

```python
# 如果 Stage 1 结果不足，搜索 TOC 章节
# → 返回: 匹配到相关章节的文档
# → boost: 多章节匹配 +0.1 相似度
```

### Stage 3: 内容预览匹配 (条件执行)

```python
# 如果仍不足，读取文档前 N 行进行匹配
# → 返回: 内容包含查询词的文档
```

### 满意度评估

每个阶段后评估是否继续：

```python
def _is_satisfied(results):
    # 1. 至少 min_results 个结果
    # 2. 最大相似度 >= min_similarity
    # 3. 有多样化的来源 (可选)
    return (
        len(results) >= 3 and
        max(r.similarity for r in results) >= 0.7
    )
```

---

## 结果格式

```python
{
    "title": "Agent Skills",
    "similarity": 0.85,          # 最终相似度分数
    "match_type": "toc_section", # 匹配类型
    "doc_name_version": "code_claude_com@latest",
    "source": "toc",             # 来源: title/toc/preview
    "content_preview": "...",    # 内容预览 (可选)
    "sections_matched": [        # 匹配的章节 (TOC)
        "Create your first Skill",
        "Configure Skills"
    ]
}
```

---

## 对比：传统 vs Agentic

### 传统搜索

```python
extractor = MarkdownDocExtractor()
results = extractor.semantic_search_titles("skills")

# 固定策略，单次返回
# ["Agent Skills" (sim=0.70)]
```

### Agentic 搜索

```python
matcher = AgenticDocMatcher(extractor)
results = matcher.match("skills")

# 多阶段，自适应扩展
# [
#   "Agent Skills" (sim=0.85, source=toc),
#   "How Skills work" (sim=0.78, source=preview),
#   "Configure Skills" (sim=0.72, source=toc)
# ]
```

---

## 配置选项

```python
config = {
    # Progressive Retriever
    "max_turns": 3,              # 最大检索轮数
    "min_results": 3,            # 最小结果数（触发扩展）
    "min_similarity": 0.5,       # 最小相似度（触发扩展）
    "title_max_results": 5,      # Stage 1 最大结果
    "toc_max_results": 10,       # Stage 2 最大结果
    "preview_max_results": 8,    # Stage 3 最大结果

    # Reflective ReRanker
    "diversity_boost": 0.1,      # 多样性提升权重
    "source_weights": {          # 来源可信度权重
        "title": 1.0,
        "toc": 0.95,
        "preview": 0.8
    },
    "dedup_threshold": 0.85      # 去重阈值
}
```

---

## 测试

```bash
# 运行测试脚本
cd /Users/zorro/project/doc4llm
python tests/test_agentic_matcher.py
```

测试包括：
1. 基本搜索
2. 自定义配置
3. 传统 vs Agentic 对比
4. 调试模式（决策过程）

---

## 文件结构

```
doc4llm/tool/md_doc_extractor/
├── agentic_matcher.py       # Agentic matcher 实现
├── doc_extractor.py         # 原始提取器
├── utils.py                 # 工具函数
├── exceptions.py            # 异常定义
└── __init__.py              # 导出接口
```

---

## 性能考虑

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| Stage 1: 标题匹配 | O(n) | n = 文档数量 |
| Stage 2: TOC 搜索 | O(m×k) | m = 文档数, k = 平均章节数 |
| Stage 3: 预览匹配 | O(p×l) | p = 文档数, l = 预览行数 |
| 去重重排序 | O(r²) | r = 结果数量 |

**优化**：大多数查询在 Stage 1 或 Stage 2 就能返回满意结果，避免昂贵的 Stage 3。

---

## 未来扩展

1. **意图感知**：根据查询类型（教程/API/故障排查）调整权重
2. **上下文记忆**：结合对话历史优化结果
3. **主动探索**：自动生成相关查询扩展搜索
4. **学习反馈**：根据用户选择学习偏好

---

## 版本

- **v2.0.0** - 初始发布 AgenticDocMatcher
