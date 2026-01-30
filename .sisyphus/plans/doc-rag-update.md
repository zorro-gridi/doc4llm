# 更新 doc-rag.md 文档约束

## TL;DR

> **快速摘要**: 更新 `.opencode/agents/doc-rag.md` 文档，在 Rules 部分添加严禁分批查询的硬性规则，并说明分批查询会增加性能开销
>
> **交付物**: 更新后的 `.opencode/agents/doc-rag.md` 文件
>
> **预估工作量**: 简单（一次性修改）
> **并行执行**: 否（顺序执行）
> **关键路径**: 读取当前文档 → 编辑添加规则 → 验证更新

---

## Context

### 原始请求
用户明确要求：
- ✅ **更新**: 文档正文约束部分（不是 description 字段）
- ✅ **语气**: 硬性规则（严禁分批查询）
- ✅ **原因**: 分批查询会增加性能开销

### 访谈总结

**关键讨论**：
- **不更新**: description 字段保持原样
- **更新位置**: Rules 部分（在现有3条规则后添加新规则）
- **语气风格**: 警告式硬性规则
- **原因说明**: 性能开销原因

### Metis 缺口分析

由于任务相对简单（仅更新文档约束），且用户需求已通过问题明确，以下为自动识别的处理方式：

**自动解决**（无需用户确认）：
- 规则格式：遵循现有 Rules 部分的中文风格
- 位置选择：在现有3条规则后顺序添加
- 措辞风格：与现有规则保持一致的简洁中文表达

---

## Work Objectives

### 核心目标
在 `.opencode/agents/doc-rag.md` 的 Rules 部分添加严禁分批查询的硬性规则，并解释性能开销原因。

### 具体交付物
- 更新后的文件: `.opencode/agents/doc-rag.md`

### 完成定义
- [ ] 新规则添加到 Rules 部分
- [ ] 规则内容包含"严禁分批查询"的硬性表述
- [ ] 包含性能开销的原因说明

### 必须包含（Must Have）
- 新增第4条规则：严禁分批查询
- 性能开销的原因说明

### 必须不包含（Must NOT Have）- 护栏
- ❌ 不修改 description 字段
- ❌ 不改变 CLI 命令示例部分
- ❌ 不修改 CLI 参数表
- ❌ 不添加与约束无关的其他内容

---

## Verification Strategy

### 测试决策
- **基础设施存在**: 不适用（文档更新任务）
- **用户需要测试**: 不适用
- **QA方式**: 人工验证文件更新是否正确

### 验证步骤
1. 读取更新后的文件 `.opencode/agents/doc-rag.md`
2. 确认 Rules 部分新增了第4条规则
3. 确认规则内容包含"严禁分批查询"表述
4. 确认包含性能开销原因说明

---

## Execution Strategy

### 顺序执行

由于任务极其简单（仅一个文件的一次性编辑），无需并行或分波执行：

```
步骤 1: 读取当前文档
步骤 2: 编辑 Rules 部分添加新规则
步骤 3: 验证更新内容
```

### 依赖关系

无依赖关系，所有步骤顺序执行。

---

## TODOs

- [ ] 1. 读取当前 `.opencode/agents/doc-rag.md` 文档内容

  **What to do**:
  - 读取完整文件内容，确认 Rules 部分位置和现有格式

  **Must NOT do**:
  - 任何修改操作

  **Recommended Agent Profile**:
  > 这是一个简单的读取任务，可以使用任意具有 Read 权限的 agent
  - **Category**: `quick` - 简单文件读取任务
  - **Skills**: 无特殊技能需求

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 2
  - **Blocked By**: None (can start immediately)

  **References**:
  - `.opencode/agents/doc-rag.md` - 需要读取的目标文件

  **Acceptance Criteria**:
  - [ ] 成功读取文件全部内容
  - [ ] 确认 Rules 部分在第21-24行
  - [ ] 记录现有3条规则的格式风格

- [ ] 2. 编辑 Rules 部分，添加严禁分批查询的新规则

  **What to do**:
  - 在现有 Rules 部分（第21-24行后）添加第4条规则
  - 规则内容需包含：
    1. "严禁分批查询"的硬性表述
    2. 性能开销的原因说明

  **Must NOT do**:
  - 不修改 description 字段
  - 不删除或修改现有规则
  - 不修改 CLI 命令示例和参数表

  **Recommended Agent Profile**:
  > 简单的文档编辑任务
  - **Category**: `quick` - 简单文件编辑
  - **Skills**: 无特殊技能需求

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 3
  - **Blocked By**: Task 1

  **References**:
  - `.opencode/agents/doc-rag.md` - 编辑目标文件
  - 现有 Rules 部分（第21-24行） - 格式参考

  **Acceptance Criteria**:
  - [ ] 文件成功更新
  - [ ] Rules 部分包含4条规则
  - [ ] 新规则包含"严禁分批查询"表述
  - [ ] 新规则包含性能开销原因说明

  **Commit**: NO
  - 这是简单的文档更新，无需自动提交

- [ ] 3. 验证更新内容正确性

  **What to do**:
  - 重新读取更新后的文件
  - 验证新规则是否正确添加

  **Must NOT do**:
  - 任何破坏性操作

  **Recommended Agent Profile**:
  > 验证任务，确保更新正确
  - **Category**: `quick` - 简单验证任务
  - **Skills**: 无特殊技能需求

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None (final)
  - **Blocked By**: Task 2

  **References**:
  - `.opencode/agents/doc-rag.md` - 验证目标文件

  **Acceptance Criteria**:
  - [ ] 文件存在且可读取
  - [ ] Rules 部分有4条规则
  - [ ] 新规则符合要求（严禁分批查询 + 性能说明）

  **Commit**: NO
  - 文档更新验证，无需提交

---

## Success Criteria

### 验证命令
```bash
# 读取文件并检查 Rules 部分
cat .opencode/agents/doc-rag.md | grep -A 10 "## Rules"
```

**预期输出**:
```
## Rules
1. 保留用户完整的查询输入文本，作为"query"参数
2. Complete Example 中的其它 CLI 参数调用时都要传递，保持与参数值一致
3. 调用这个 skill 时，tiemout 超时时间设置为 5 分钟
4. 严禁分批查询，必须一次性在 query 中输入所有查询需求。分批查询会增加性能开销。
```

### 最终检查清单
- [ ] Rules 部分包含4条规则
- [ ] 新规则包含"严禁分批查询"硬性表述
- [ ] 新规则包含"分批查询会增加性能开销"原因说明
- [ ] 不修改 description 字段
- [ ] CLI 命令示例和参数表保持不变
