=== AOP-FINAL | agent=doc-retriever | format=markdown | lines=616 | source=Claude_Code_Docs@latest,OpenCode_Docs@latest ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

## Claude Code 与 OpenCode Subagent 创建机制对比分析

### 一、Subagent 类型和分类方式

#### Claude Code
**分类维度**：按作用域（Scope）分类
| 位置 | 作用域 | 优先级 | 创建方式 |
|------|--------|--------|----------|
| `--agents` CLI 标志 | 当前会话 | 1（最高） | 启动时传递 JSON |
| `.claude/agents/` | 当前项目 | 2 | 交互式或手动 |
| `~/.claude/agents/` | 所有项目 | 3 | 交互式或手动 |
| 插件 `agents/` 目录 | 插件启用范围 | 4（最低） | 插件安装 |

**特点**：
- Subagent 是 Markdown 文件 + YAML 前置元数据
- 支持临时定义的 CLI JSON 格式
- 内置多种 subagent：Explore、Plan、通用助手

#### OpenCode  
**分类维度**：按角色分类
| 类型 | 说明 | 特点 |
|------|------|------|
| **Primary agents** | 主要交互代理 | 内置 Build 和 Plan，可切换 |
| **Subagents** | 子代理 | 通过 Task 工具调用，用于特定任务 |

**特点**：
- 区分主要代理和子代理的概念
- 主要代理通过 Tab 键切换
- 子代理通过 Task 工具调用

---

### 二、Subagent 创建和调用机制

#### Claude Code
**创建方式**：
```bash
# 1. 交互式创建
/claude
→ Create new agent → User-level → Generate with Claude

# 2. 手动创建 Markdown 文件
# ~/.claude/agents/code-reviewer.md
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer...

# 3. CLI 临时定义
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer",
    "prompt": "You are a senior code reviewer...",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

**调用方式**：
- 自然语言触发：`Use the code-reviewer agent to review this file`
- Task 工具自动识别可用 subagents

#### OpenCode
**创建方式**：
```bash
# 交互式创建
opencode agent create
# 1. 选择保存位置：全局或项目级
# 2. 描述代理职责
# 3. 生成系统提示和标识符
# 4. 选择工具访问权限
# 5. 创建 Markdown 配置文件

# 手动创建文件
# ~/.config/opencode/agents/docs-agent.md 或 .opencode/agents/docs-agent.md
---
description: Writes and maintains project documentation
mode: subagent
tools:
  bash: false
---

You are a technical writer...
```

**调用方式**：
- 通过 Task 工具调用子代理
- 需要明确配置 Task permissions

---

### 三、Subagent 配置方式

#### Claude Code
**YAML 前置元数据字段**：

| 字段 | 必填 | 描述 |
|------|------|------|
| `name` | 是 | 唯一标识（小写字母和连字符） |
| `description` | 是 | 调用时机描述 |
| `tools` | 否 | 可用工具列表（默认继承所有工具） |
| `disallowedTools` | 否 | 禁用工具列表 |
| `model` | 否 | 模型选择：`sonnet`/`opus`/`haiku`/`inherit`，默认 `sonnet` |
| `permissionMode` | 否 | 权限模式 |
| `skills` | 否 | 注入的技能列表 |
| `hooks` | 否 | 生命周期钩子 |

**CLI JSON 格式**：
```json
{
  "name": "code-reviewer",
  "description": "Expert code reviewer",
  "prompt": "You are a senior code reviewer...",  // 对应 Markdown 主体
  "tools": ["Read", "Grep", "Glob", "Bash"],
  "model": "sonnet"
}
```

#### OpenCode
**Markdown 前置元数据**：

| 字段 | 类型 | 描述 |
|------|------|------|
| `description` | 必填 | 代理描述 |
| `mode` | 必填 | 模式：`subagent` 或 primary |
| `tools` | 可选 | 工具访问配置（对象形式） |
| `permission` | 可选 | 权限配置 |

**opencode.json 配置**：
```json
{
  "agent": {
    "code-reviewer": {
      "description": "Reviews code for best practices",
      "model": "anthropic/claude-sonnet-4-5",
      "prompt": "You are a code reviewer...",
      "tools": {
        "write": false,
        "edit": false
      }
    }
  }
}
```

**默认代理配置**：
```json
{
  "default_agent": "plan"  // 必须是 primary agent，不能是 subagent
}
```

---

### 四、工具访问权限控制

#### Claude Code
**三级权限控制体系**：

1. **工具列表控制**
   ```yaml
   tools: Read, Grep, Glob, Bash  # 白名单
   disallowedTools: Write, Edit   # 黑名单
   ```

2. **权限模式（permissionMode）**
   | 模式 | 行为 |
   |------|------|
   | `default` | 标准权限检查和提示 |
   | `acceptEdits` | 自动接受文件编辑 |
   | `dontAsk` | 自动拒绝权限提示（显式允许的工具仍可用） |
   | `bypassPermissions` | 跳过所有权限检查（危险⚠️） |
   | `plan` | 计划模式（只读探索） |

3. **条件规则（Hooks）**
   ```yaml
   hooks:
     PreToolUse:
       - matcher: "Bash"
         hooks:
           - type: command
             command: "./scripts/validate-readonly-query.sh"
   ```

**禁用特定 subagent**：
```json
{
  "permissions": {
    "deny": ["Task(Explore)", "Task(my-custom-agent)"]
  }
}
```

#### OpenCode
**基于 Task 的权限控制**：

```json
{
  "agent": {
    "orchestrator": {
      "mode": "primary",
      "permission": {
        "task": {
          "*": "deny",              // 默认拒绝所有
          "orchestrator-*": "allow", // 允许特定模式
          "code-reviewer": "ask"     // 询问模式
        }
      }
    }
  }
}
```

**按代理覆盖技能权限**：
```yaml
# 自定义代理
---
permission:
  skill:
    "documents-*": "allow"
---

# 内置代理
{
  "agent": {
    "plan": {
      "permission": {
        "skill": {
          "internal-*": "allow"
        }
      }
    }
  }
}
```

**禁用技能工具**：
```yaml
# 自定义代理
---
tools:
  skill: false
---

# 内置代理
{
  "agent": {
    "plan": {
      "tools": {
        "skill": false
      }
    }
  }
}
```

---

### 五、生命周期管理

#### Claude Code
**1. 暂停和恢复机制**
- 每个 subagent 调用创建新实例
- 支持恢复已有 subagent 的工作
- 保留完整的对话历史和工具调用记录
- 转录文件保存在 `~/.claude/projects/{project}/{sessionId}/subagents/`

**2. 自动压缩**
- 默认在约 95% 容量时触发
- 可通过 `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` 环境变量调整
- 压缩事件记录在转录文件中

**3. Hooks 生命周期管理**
```yaml
# Subagent 级别（前置元数据）
hooks:
  PreToolUse:    # 工具使用前触发
  PostToolUse:   # 工具使用后触发
  Stop:          # Subagent 完成时触发（自动转为 SubagentStop）

# 项目级别（settings.json）
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "db-agent",
        "hooks": [
          { "type": "command", "command": "./scripts/setup-db.sh" }
        ]
      }
    ],
    "SubagentStop": [...]
  }
}
```

**4. 清理策略**
- 转录文件根据 `cleanupPeriodDays` 设置自动清理（默认 30 天）

#### OpenCode
**1. 代理类型管理**
- 主要代理：直接交互，通过 Tab 切换
- 子代理：通过 Task 工具调用

**2. 持久化存储**
- 全局配置：`~/.config/opencode/`
- 项目配置：`.opencode/`
- Markdown 文件格式便于版本控制

**3. 配置继承**
- 内置代理不可直接修改
- 支持通过配置覆盖和扩展行为

---

### 六、技能（Skills）访问控制

#### Claude Code
- Subagent **不自动继承**主对话的技能
- 需要在 `skills` 字段中显式列出
- 完整技能内容在启动时注入到 subagent 上下文
- 内置代理无技能访问权限

```yaml
skills: pr-review, security-check
```

#### OpenCode
- 支持按代理覆盖技能权限
- 可完全禁用技能工具
- 使用通配符模式匹配

---

### 七、核心差异总结

| 特性 | Claude Code | OpenCode |
|------|-------------|----------|
| **分类方式** | 按作用域（4 级） | 按角色（Primary/Subagent） |
| **配置格式** | YAML 前置元数据 + JSON CLI | Markdown 前置元数据 + JSON 配置 |
| **权限控制** | 工具列表 + 权限模式 + Hooks | Task 权限 + 技能覆盖 |
| **生命周期** | 暂停/恢复/压缩/转录 | 简单的配置驱动 |
| **创建方式** | `/agents` 命令或 CLI | `opencode agent create` 命令 |
| **工具访问** | 白名单/黑名单/条件规则 | 对象配置 + 通配符模式 |
| **默认行为** | 继承所有工具 | 需要显式配置 |
| **Hooks 支持** | 丰富的生命周期钩子 | 无明确 Hooks 机制 |

---

### 八、适用场景建议

**选择 Claude Code 当需要**：
- 精细的工具访问控制
- 复杂的条件权限规则
- Subagent 暂停和恢复能力
- 项目级的生命周期管理
- 插件分发的 subagent

**选择 OpenCode 当需要**：
- 简单的代理配置
- 主要代理和子代理的清晰分离
- 全局/项目级别的配置管理
- 基于 Task 的权限控制
- 轻量级的代理定义

=== END-AOP-FINAL ===
