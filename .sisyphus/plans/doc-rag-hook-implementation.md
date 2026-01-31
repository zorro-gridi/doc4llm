# doc_rag Claude Code Hook 完整实现方案

## TL;DR

> **快速摘要**: 通过创建 UserPromptSubmit Hook，在用户每次提交提示时自动调用 doc_rag 检索相关文档并将结果注入上下文，实现知识库的智能上下文增强。
> 
> **交付物**:
> - `.claude/hooks/doc_rag_context.py` - 主 Hook 脚本
> - `.claude/hooks/doc_rag_cache.py` - 缓存模块
> - `.claude/hooks/doc_rag_config.py` - 配置模块
> - `.claude/settings.json` - Hook 配置文件
> 
> **预估工作量**: 约 2-3 小时
> **并行执行**: YES - 3 个核心模块可以并行开发
> **关键路径**: 配置模块 → 缓存模块 → 主脚本 → 测试验证

---

## Context

### 原始需求
用户希望利用 Claude Code 的 hook 机制，将 `doc4llm/doc_rag/main.py` 代码执行结果注入到上下文中，实现每次对话时自动检索和注入相关文档。

### 研究结论
通过分析 Claude Code 官方 Hook 机制和现有插件实现，发现最佳方案是使用 `UserPromptSubmit` Hook：
- **注入方式**: 通过 `systemMessage` JSON 字段向上下文注入内容
- **触发时机**: 用户每次提交提示时自动触发
- **性能考虑**: 需要缓存机制避免重复检索

---

## Work Objectives

### Core Objective
创建一个完整的 UserPromptSubmit Hook 系统，实现：
1. 用户提示提交时自动触发 doc_rag 检索
2. 智能判断是否需要检索（触发条件）
3. 缓存机制优化性能
4. 上下文大小控制
5. 完善的错误处理和日志

### Concrete Deliverables
| 文件 | 描述 |
|------|------|
| `.claude/hooks/doc_rag_config.py` | 配置模块：加载和管理配置 |
| `.claude/hooks/doc_rag_cache.py` | 缓存模块：LRU 缓存 + TTL 过期 |
| `.claude/hooks/doc_rag_context.py` | 主 Hook 脚本 |
| `.claude/settings.json` | Hook 注册配置 |
| `.claude/.doc_rag_cache/` | 缓存存储目录 |

### Definition of Done
- [ ] Hook 脚本能正确解析用户输入
- [ ] 触发条件能准确判断何时需要检索
- [ ] doc_rag 检索成功并返回结果
- [ ] 检索结果能正确注入到 Claude 上下文
- [ ] 缓存机制正常工作
- [ ] 上下文大小得到控制
- [ ] 错误不会导致对话中断
- [ ] 日志记录完整可追溯

### Must Have
- 自动检索相关文档
- 缓存机制（TTL 支持）
- 上下文截断保护
- 完善的错误处理
- 详细的日志记录

### Must NOT Have (Guardrails)
- 不修改 doc4llm 核心代码
- 不阻塞用户提示的提交
- 不在没有触发条件时触发检索
- 不注入过大的上下文（最大 8000 字符）

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: NO (new project)
- **User wants tests**: Manual verification
- **Framework**: N/A (new Python scripts)
- **QA approach**: Manual testing with sample queries

### Manual Verification Commands

**Test 1: Syntax Check**
```bash
python3 -m py_compile .claude/hooks/doc_rag_config.py
python3 -m py_compile .claude/hooks/doc_rag_cache.py
python3 -m py_compile .claude/hooks/doc_rag_context.py
# Expected: No syntax errors
```

**Test 2: Module Import**
```bash
cd .claude/hooks
python3 -c "from doc_rag_config import DocRAGConfig; print('Config OK')"
python3 -c "from doc_rag_cache import DocRAGCache; print('Cache OK')"
# Expected: Both modules import successfully
```

**Test 3: Hook Execution**
```bash
echo '{"user_input": "如何创建 ray cluster?"}' | python3 .claude/hooks/doc_rag_context.py
# Expected: JSON output with systemMessage field
```

**Test 4: Claude Code Integration**
1. Restart Claude Code to load new Hook
2. Submit a query like "如何创建 ray cluster?"
3. Verify that doc_rag context is injected in the response
4. Check logs in `.claude/hooks/doc_rag_context.log`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: doc_rag_config.py - 配置模块
└── Task 2: doc_rag_cache.py - 缓存模块

Wave 2 (After Wave 1):
└── Task 3: doc_rag_context.py - 主 Hook 脚本

Wave 3 (After Wave 2):
├── Task 4: settings.json - Hook 配置文件
└── Task 5: 测试验证 - Manual verification
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 (config) | None | 3 | 2 |
| 2 (cache) | None | 3 | 1 |
| 3 (main) | 1, 2 | 4, 5 | None |
| 4 (settings) | 3 | None | 5 |
| 5 (test) | 3, 4 | None | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2 | `delegate_task(category="quick", ...)` - Simple file creation |
| 2 | 3 | `delegate_task(category="unspecified-medium", ...)` - Complex logic |
| 3 | 4, 5 | `delegate_task(category="quick", ...)` - Simple config + manual test |

---

## TODOs

> Implementation + Test = ONE Task. Never separate.

- [ ] 1. 创建配置模块 (doc_rag_config.py)

  **What to do**:
  - 创建 `DocRAGConfig` 类
  - 支持从环境变量加载配置
  - 支持从项目配置文件加载
  - 提供合理的默认值

  **Must NOT do**:
  - 不修改现有 doc4llm 代码
  - 不依赖外部配置（除环境变量外）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple configuration class, straightforward implementation
  - **Skills**: `[]`
    - No special skills needed for config module

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:
  - `/Users/zorro/project/doc4llm/doc4llm/doc_rag/orchestrator.py:85-110` - DocRAGConfig pattern reference
  - Environment variable pattern from `/Users/zorro/.claude/plugins/marketplaces/claude-plugins-official/plugins/security-guidance/hooks/security_reminder_hook.py:220` - ENV-based config

  **Acceptance Criteria**:
  - [ ] Config class can be imported without errors
  - [ ] `from_env()` returns valid config with env vars
  - [ ] `from_project()` returns valid config from JSON file
  - [ ] Default values work when no config provided

  **Evidence to Capture**:
  - [ ] Terminal output from `python3 -c "from doc_rag_config import DocRAGConfig; print(DocRAGConfig().to_dict())"`

- [ ] 2. 创建缓存模块 (doc_rag_cache.py)

  **What to do**:
  - 创建 `CacheEntry` 数据类
  - 创建 `DocRAGCache` 缓存管理器
  - 实现 `get()` 和 `set()` 方法
  - 实现 TTL 过期机制
  - 实现缓存清理功能

  **Must NOT do**:
  - 不修改 doc4llm 核心缓存逻辑
  - 不使用外部缓存系统（如 Redis）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Cache implementation is straightforward with standard patterns
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:
  - `/Users/zorro/.claude/plugins/marketplaces/claude-plugins-official/plugins/security-guidance/hooks/security_reminder_hook.py:129-181` - State file pattern for session persistence
  - Standard Python pickle/json caching patterns

  **Acceptance Criteria**:
  - [ ] Cache class can be imported without errors
  - [ ] `get()` returns None for non-existent key
  - [ ] `set()` and `get()` roundtrip works correctly
  - [ ] TTL expiration works (test with short TTL)
  - [ ] `cleanup_expired()` removes expired entries
  - [ ] `get_stats()` returns valid statistics

  **Evidence to Capture**:
  - [ ] Terminal output from cache test script

- [ ] 3. 创建主 Hook 脚本 (doc_rag_context.py)

  **What to do**:
  - 实现 `main()` 函数作为入口点
  - 实现 `should_trigger()` 触发条件判断
  - 实现 `truncate_context()` 上下文截断
  - 实现 `format_context_for_claude()` 结果格式化
  - 实现 `safe_retrieve()` 安全检索封装
  - 集成配置模块和缓存模块
  - 完善的错误处理和日志记录

  **Must NOT do**:
  - 不修改 doc4llm/orchestrator.py
  - 不在错误时阻塞用户操作
  - 不输出敏感信息到日志

  **Recommended Agent Profile**:
  - **Category**: `unspecified-medium`
    - Reason: Complex integration script with multiple responsibilities
  - **Skills**: `["python"]`
    - Python skill for complex logic implementation

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2)
  - **Blocks**: Tasks 4, 5
  - **Blocked By**: Tasks 1, 2

  **References**:
  - `/Users/zorro/.claude/plugins/marketplaces/claude-plugins-official/plugins/hookify/hooks/userpromptsubmit.py:27-54` - UserPromptSubmit hook pattern
  - `/Users/zorro/.claude/plugins/marketplaces/claude-plugins-official/plugins/security-guidance/hooks/security_reminder_hook.py:217-281` - Complete hook example with error handling
  - `/Users/zorro/project/doc4llm/doc4llm/doc_rag/main.py:1-34` - doc_rag usage pattern

  **Acceptance Criteria**:
  - [ ] Script can be executed with stdin input
  - [ ] `should_trigger()` correctly identifies trigger conditions
  - [ ] `safe_retrieve()` returns valid result dict
  - [ ] `format_context_for_claude()` produces readable output
  - [ ] JSON output contains `systemMessage` field when successful
  - [ ] Script exits with code 0 always
  - [ ] Error messages are logged to `.claude/hooks/doc_rag_context.log`

  **Evidence to Capture**:
  - [ ] Terminal output from `echo '{"user_input": "测试查询"}' | python3 .claude/hooks/doc_rag_context.py`
  - [ ] Log file contents from `.claude/hooks/doc_rag_context.log`

- [ ] 4. 创建 Hook 配置文件 (settings.json)

  **What to do**:
  - 在 `.claude/` 目录创建 `settings.json`
  - 注册 UserPromptSubmit Hook
  - 配置环境变量
  - 设置超时时间

  **Must NOT do**:
  - 不覆盖现有的 `.claude/settings.json`（如有）
  - 不设置过长的超时时间

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple JSON configuration file
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3)
  - **Blocks**: Task 5
  - **Blocked By**: Task 3

  **References**:
  - `/Users/zorro/.claude/plugins/marketplaces/claude-plugins-official/plugins/hookify/hooks/hooks.json:37-47` - UserPromptSubmit hook config pattern
  - `/Users/zorro/.claude/plugins/marketplaces/claude-plugins-official/plugins/claude-code-setup/skills/claude-automation-recommender/references/hooks-patterns.md:219-226` - Hook placement reference

  **Acceptance Criteria**:
  - [ ] `settings.json` is valid JSON
  - [ ] UserPromptSubmit hook is registered
  - [ ] Command path uses `${CLAUDE_HOOK_ROOT}` variable
  - [ ] Timeout is set to 60 seconds

  **Evidence to Capture**:
  - [ ] File contents verification with `cat .claude/settings.json`

- [ ] 5. 测试验证 (Manual Testing)

  **What to do**:
  - 执行所有单元测试
  - 手动测试 Hook 集成
  - 验证上下文注入效果
  - 性能测试和优化

  **Must NOT do**:
  - 不修改任何生产代码
  - 不在主项目目录外创建测试文件

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Manual testing and verification
  - **Skills**: `["python"]`
    - Python for running test commands

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final task)
  - **Blocks**: None
  - **Blocked By**: Tasks 3, 4

  **References**:
  - All previous tasks' acceptance criteria

  **Acceptance Criteria**:
  - [ ] All 4 previous tasks' acceptance criteria met
  - [ ] Claude Code can load the new Hook
  - [ ] Query with trigger keyword injects doc_rag context
  - [ ] Query without trigger keyword does not inject
  - [ ] Cache works (second same query is faster)
  - [ ] Error handling does not break conversation
  - [ ] Logs are created in `.claude/hooks/`

  **Evidence to Capture**:
  - [ ] Screenshot or log showing context injection in Claude Code
  - [ ] Performance comparison (first vs cached query)
  - [ ] All test command outputs

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1-4 | `feat: Add doc_rag UserPromptSubmit hook for context injection` | `.claude/hooks/*.py`, `.claude/settings.json` | `ls -la .claude/` |

---

## Success Criteria

### Verification Commands
```bash
# 1. 语法检查
python3 -m py_compile .claude/hooks/*.py

# 2. 模块导入测试
cd .claude/hooks
python3 -c "from doc_rag_config import DocRAGConfig; from doc_rag_cache import DocRAGCache; print('All modules OK')"

# 3. Hook 执行测试
echo '{"user_input": "测试查询"}' | python3 .claude/hooks/doc_rag_context.py

# 4. 查看日志
cat .claude/hooks/doc_rag_context.log
```

### Final Checklist
- [ ] 所有 5 个任务完成
- [ ] 所有验收标准满足
- [ ] Claude Code 中测试通过
- [ ] 日志文件生成
- [ ] 缓存正常工作
- [ ] 上下文注入成功
