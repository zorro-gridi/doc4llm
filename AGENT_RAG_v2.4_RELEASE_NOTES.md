# doc-retriever Agent v2.4 更新说明

## 概述

本次更新对 `doc-retriever` agent 进行了全面的现代化改造，从传统的基于规则的检索系统升级为具有 Agentic RAG 能力的智能文档问答系统。

**版本**: v2.4.0
**发布日期**: 2025-01-18
**更新类型**: Major Feature Release

---

## 核心改进

### 1. 智能检索引擎 (AgenticDocMatcher)

**新增功能**:
- **4阶段渐进式检索**: Title → TOC → Content Preview → 自动扩展
- **反思式重排序**: 多因子相关性评分（相似度 + 来源权重 + 查询覆盖）
- **质量自评估**: 自动判断结果质量，不满意时自动扩展搜索
- **去重机制**: 跨检索阶段智能去重

**技术指标**:
```
检索阶段: 3层渐进回退
质量阈值: 0.7 (可配置)
最大扩展轮数: 3
去重相似度: 0.85
```

### 2. 查询优化系统 (QueryOptimizer)

**新增功能**:
- **查询分解**: 复杂查询自动拆分为子查询
- **查询扩展**: 同义词替换和相关术语添加
- **查询重写**: 口语化转正式表达
- **多查询生成**: 并行多个查询变体

**支持模式**:
```python
# 输入: "如何配置 hooks"
# 输出: ["hooks configuration", "setup hooks", "hooks settings"]

# 输入: "hooks 配置以及部署注意事项"
# 输出: ["hooks configuration", "deployment hooks注意事项"]
```

### 3. 多跳推理引擎 (ChainReasoner)

**新增功能**:
- **复杂查询分解**: 识别连接词、比较词、程序链
- **顺序检索**: 执行多步骤文档检索
- **信息合成**: 整合多来源信息
- **引用追踪**: 完整的来源追溯

**推理类型**:
| 类型 | 示例 | 分解方式 |
|------|------|----------|
| 连接 (AND) | "A 以及 B" | ["A", "B"] |
| 比较 | "A 和 B 的区别" | ["A", "B", "comparison"] |
| 程序链 | "如何做 A 然后 B" | ["A", "B"] |

### 4. 持久化会话记忆 (ConversationMemory)

**新增功能**:
- **会话历史存储**: JSON 格式持久化存储
- **延续查询检测**: 自动识别 "那X呢？" 等模式
- **上下文查询重写**: 基于历史优化新查询
- **文档去重**: 避免重复检索已访问文档

**存储结构**:
```
.claude/memory/
├── session_20250118_123456_abc123.json
└── ...
```

### 5. 新增问答 Agent (doc-qa-agentic)

**定位**: 独立的文档问答 Agent，专注于复杂问题的推理和合成

**能力**:
- 自动判断使用简单搜索还是多跳推理
- 整合所有优化组件
- 生成带引用的综合答案
- 提供置信度评分

---

## 架构变更

### 旧架构 (v2.1)

```
doc-retriever agent
├── Phase 1: md-doc-searcher (手动 bash/grep)
├── Phase 2: md-doc-reader (MarkdownDocExtractor)
└── Phase 3: md-doc-processor (条件压缩)
```

### 新架构 (v2.4)

```
doc-retriever system
├── doc-retriever agent (文档检索)
│   ├── Phase 1: Discovery (AgenticDocMatcher)
│   ├── Phase 2: Extraction (MarkdownDocExtractor)
│   ├── Phase 3: Post-processing (md-doc-processor)
│   └── Conversation Memory (上下文追踪)
│
└── doc-qa-agentic agent (智能问答)
    ├── Query Optimizer (查询优化)
    ├── Chain Reasoner (多跳推理)
    ├── AgenticDocMatcher (智能检索)
    └── Citation Tracking (引用追踪)
```

---

## 新增文件清单

### Skills (技能定义)

| 文件 | 用途 |
|------|------|
| `.claude/skills/md-doc-searcher/SKILL.md` | 文档搜索 (已更新) |
| `.claude/skills/md-doc-query-optimizer/SKILL.md` | 查询优化 |
| `.claude/skills/md-doc-chain-reasoner/SKILL.md` | 多跳推理 |
| `.claude/skills/md-doc-conversation-memory/SKILL.md` | 会话记忆 |

### Agents (智能体)

| 文件 | 用途 |
|------|------|
| `.claude/agents/doc-retriever.md` | 文档检索 (原有) |
| `.claude/agents/doc-qa-agentic.md` | 智能问答 (新增) |

### Python 实现

| 文件 | 说明 |
|------|------|
| `doc4llm/tool/md_doc_extractor/agentic_matcher.py` | 渐进式检索器 (已存在，现已集成) |
| `doc4llm/tool/md_doc_extractor/query_optimizer.py` | 查询优化器 (新增) |
| `doc4llm/tool/md_doc_extractor/chain_reasoner.py` | 多跳推理器 (新增) |
| `doc4llm/tool/md_doc_extractor/conversation_memory.py` | 会话记忆 (新增) |

---

## API 使用示例

### 1. 智能文档搜索

```python
from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor, AgenticDocMatcher

# 初始化
extractor = MarkdownDocExtractor()
matcher = AgenticDocMatcher(extractor, debug_mode=True)

# 执行智能搜索
results = matcher.match("hooks configuration", max_results=5)

# 结果包含增强元数据
for r in results:
    print(f"{r['title']} (source: {r['source']}, sim: {r['similarity']:.2f})")
    if r.get('sections_matched'):
        print(f"  匹配章节: {r['sections_matched']}")
```

### 2. 查询优化

```python
from doc4llm.tool.md_doc_extractor import QueryOptimizer

optimizer = QueryOptimizer()

# 优化查询
optimized = optimizer.optimize("如何配置 hooks", max_queries=3)

for opt in optimized:
    print(f"[{opt.strategy}] {opt.query} (confidence: {opt.confidence})")
```

### 3. 多跳推理

```python
from doc4llm.tool.md_doc_extractor import ChainReasoner

reasoner = ChainReasoner(extractor, matcher)

# 复杂查询推理
result = reasoner.reason(
    "hooks 配置以及部署注意事项",
    max_hops=3,
    max_documents_per_hop=5
)

print(f"置信度: {result.confidence}")
print(f"推理步骤: {len(result.reasoning_steps)}")
```

### 4. 会话记忆

```python
from doc4llm.tool.md_doc_extractor import ConversationMemory

memory = ConversationMemory()
memory.create_session(domain="claude")

# 添加对话轮次
memory.add_turn(
    query="如何配置 hooks",
    optimized_query="hooks configuration",
    results=search_results
)

# 获取上下文
context = memory.get_context_for_query("那部署呢？")
print(f"建议查询: {context['suggested_rewrites']}")
```

### 5. 完整的问答流程

```python
from doc4llm.tool.md_doc_extractor import (
    MarkdownDocExtractor, AgenticDocMatcher,
    QueryOptimizer, ChainReasoner, ConversationMemory
)

# 初始化组件
extractor = MarkdownDocExtractor()
matcher = AgenticDocMatcher(extractor)
optimizer = QueryOptimizer()
reasoner = ChainReasoner(extractor, matcher)
memory = ConversationMemory()
memory.create_session()

# 用户问题
user_query = "hooks 配置以及部署注意事项"

# 1. 检查会话上下文
context = memory.get_context_for_query(user_query)
query = context["suggested_rewrites"] or user_query

# 2. 判断复杂度
if "以及" in query or "和" in query:
    # 复杂查询，使用多跳推理
    result = reasoner.reason(query)
    answer = result.answer
else:
    # 简单查询，直接搜索
    results = matcher.match(query)
    answer = synthesize_answer(results)

# 3. 存储到会话记忆
memory.add_turn(query, query, results)

# 4. 返回答案
return answer
```

---

## 配置说明

### AgenticDocMatcher 配置

```python
config = {
    "max_turns": 3,              # 最大检索阶段
    "min_results": 3,            # 满意度最小结果数
    "min_similarity": 0.6,       # 包含最小相似度
    "high_quality_threshold": 0.7,  # 高质量阈值
    "title_max_results": 5,      # 标题匹配最大结果
    "toc_max_results": 10,       # TOC 匹配最大结果
    "preview_max_results": 8,    # 预览匹配最大结果
    "diversity_boost": 0.1,      # 多样性提升
    "source_weights": {          # 来源权重
        "title": 1.0,
        "toc": 0.95,
        "preview": 0.8
    }
}

matcher = AgenticDocMatcher(extractor, config=config)
```

### QueryOptimizer 配置

```python
config = {
    "max_optimized_queries": 5,   # 最大优化查询数
    "min_confidence_threshold": 0.6,  # 最小置信度
    "enable_decomposition": True,  # 启用查询分解
    "enable_expansion": True,      # 启用查询扩展
    "enable_rewriting": True,      # 启用查询重写
    "language_priority": ["zh", "en"],  # 语言优先级
}

optimizer = QueryOptimizer(config=config)
```

### ChainReasoner 配置

```python
config = {
    "max_hops": 3,                      # 最大推理步数
    "max_documents_per_hop": 5,         # 每步最大文档数
    "min_similarity_threshold": 0.6,    # 最小相似度阈值
    "enable_citation_tracking": True,   # 启用引用追踪
    "enable_cross_hop_refinement": True,  # 启用跨步优化
    "synthesis_strategy": "comprehensive",  # 合成策略
}

reasoner = ChainReasoner(extractor, matcher, config=config)
```

### ConversationMemory 配置

```python
config = {
    "storage_dir": ".claude/memory",  # 存储目录
    "max_sessions": 100,               # 最大会话数
    "max_turns_per_session": 50,       # 每会话最大轮次
}

memory = ConversationMemory(**config)
```

---

## 向后兼容性

### 保持兼容

- `MarkdownDocExtractor` API 完全兼容
- 现有的 `doc-retriever` agent 工作流保持不变
- 所有新增功能均为可选增强

### 升级路径

**无需修改** 的场景:
- 使用 `MarkdownDocExtractor.extract_by_title()`
- 使用简单的文档标题匹配

**建议升级** 的场景:
- 需要更智能的检索 → 使用 `AgenticDocMatcher`
- 需要处理复杂查询 → 使用 `ChainReasoner`
- 需要保持会话上下文 → 使用 `ConversationMemory`

---

## 性能考量

### 检索性能

| 场景 | 旧方法 | 新方法 (AgenticDocMatcher) |
|------|--------|---------------------------|
| 简单查询 (精确匹配) | ~100ms | ~150ms |
| 复杂查询 (模糊匹配) | 需多次手动尝试 | ~300ms (一次完成) |
| 低质量结果 | 需重新查询 | 自动扩展 (~500ms) |

### 存储占用

- 会话记忆: ~1-5 KB per session
- 默认保留 100 个会话: ~500 KB 总占用

---

## 已知限制

1. **向量检索**: 未集成嵌入模型，依赖关键词和规则匹配
2. **跨语言支持**: 主要支持中英文，其他语言支持有限
3. **查询重写**: 基于模式匹配，可能无法处理非常规表达
4. **多跳推理**: 复杂度受限于 `max_hops` 配置

---

## 未来规划

### 短期 (v2.5)

- [ ] 增强多语言支持
- [ ] 改进查询重写的自然语言理解
- [ ] 添加结果质量可视化

### 中期 (v3.0)

- [ ] 集成轻量级嵌入模型（可选）
- [ ] 实现自适应阈值学习
- [ ] 添加用户反馈机制

### 长期 (v3.5+)

- [ ] 完整的向量检索能力
- [ ] 跨文档引用关系图谱
- [ ] 主动学习用户偏好

---

## 问题反馈

如有问题或建议，请通过以下方式反馈:

- GitHub Issues: [项目地址]
- 文档: `CLAUDE.md`
- 配置指南: `CONFIG_GUIDE.md`

---

## 致谢

本次更新参考了以下现代 Agentic RAG 系统的最佳实践:

- Multi-Stage Retrieval (MSMARCO)
- Query Decomposition (DSPy)
- Re-ranking (Cohere Reranker)
- Citation Tracking (Attributed QA)

---

**版权所有 © 2025 doc4llm 项目**
