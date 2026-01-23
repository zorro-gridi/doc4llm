# Claude Code 与 OpenCode 代理设计哲学深度对比分析报告

## 概述

本报告对比分析两个主流AI编程助手——Claude Code（Anthropic）和OpenCode（opencode.ai）——在代理（Agent）设计理念上的核心差异。通过对官方文档的深入研究，从架构模式、工具调用、自主性控制、请求处理、上下文管理和执行模型等六个维度进行全面剖析。

---

## 1. 核心架构差异：代理行为的根本分歧

### 1.1 Claude Code：权限驱动的事件型架构

Claude Code采用了**基于权限的严格分层架构**，其核心设计理念是将安全性置于所有操作的核心位置。根据官方文档，"Claude Code uses strict read-only permissions by default"。

**事件驱动的生命周期管理**：Claude Code通过Hooks系统实现了完整的事件生命周期管理。Hooks可以响应多种事件类型：

| 事件类型 | 触发时机 | 作用 |
|---------|---------|------|
| `PreToolUse` | 工具使用前 | 参数创建后、调用处理前执行 |
| `PostToolUse` | 工具使用后 | 工具执行完成后执行 |
| `UserPromptSubmit` | 用户提示提交时 | 处理用户输入时触发 |
| `Stop` | 停止时 | 会话停止时执行 |
| `SubagentStop` | 子代理停止时 | 子代理结束时触发 |
| `SessionStart` | 会话开始时 | 新会话初始化时执行 |
| `SessionEnd` | 会话结束时 | 会话关闭时执行 |

**权限渗透的设计原则**：权限不是孤立存在的，而是渗透到整个系统的每个层面。从主会话到子代理，从Skills到Hooks，权限规则形成了完整的继承链。文档明确指出："Subagents inherit all tools from the main conversation, including MCP tools. To restrict tools, use the `tools` field (allowlist) or `disallowedTools` field (denylist)"。

**源文档章节**：
- [Permission-based architecture - Claude Code](https://code.claude.com/docs/en/security)
- [Control subagent capabilities - Claude Code](https://code.claude.com/docs/en/sub-agents)
- [Hook Events - Claude Code](https://code.claude.com/docs/en/hooks)

### 1.2 OpenCode：配置驱动的分层代理架构

OpenCode采用了**基于配置的代理分层架构**，其核心设计理念是通过显式配置实现灵活的行为控制。官方文档描述："Agents are specialized AI assistants that can be configured for specific tasks and workflows. They allow you to create focused tools with custom prompts, models, and tool access"。

**Primary-Subagent的双层结构**：OpenCode的架构核心是Primary Agents和Subagents的明确区分：

- **Primary Agents**：用户直接交互的主要助手，可通过Tab键循环切换
- **Subagents**：主要代理可以为特定任务调用的专门助手

**配置即代码的理念**：OpenCode将所有行为定义都转化为配置项。从代理定义到工具权限，从模型选择到温度控制，一切都可以通过JSON配置或Markdown文件进行管理。

**源文档章节**：
- [Agents - OpenCode](https://opencode.ai/docs/agents)
- [Types - OpenCode](https://opencode.ai/docs/agents)

---

## 2. 工具使用与调用机制的本质差异

### 2.1 Claude Code：声明式工具控制与动态权限协商

Claude Code的工具调用系统体现了**声明式控制与动态协商**的结合：

**工具访问的声明式限制**：通过`allowed-tools`元数据字段，Skills可以声明其可用的工具集。文档描述："Use the `allowed-tools` frontmatter field to limit which tools Claude can use when a Skill is active. You can specify tools as a comma-separated string or a YAML list"。

**运行时权限协商机制**：Claude Code在运行时实现了精细的权限协商，通过Permission Modes实现：

| 权限模式 | 行为描述 |
|---------|---------|
| `default` | 标准权限检查 |
| `acceptEdits` | 自动接受文件编辑 |
| `dontAsk` | 自动拒绝权限提示 |
| `bypassPermissions` | 跳过所有权限检查 |
| `plan` | 计划模式，只读探索 |

**Hooks作为工具调用的拦截器**：Claude Code的Hooks系统提供了对工具调用的深度拦截能力。文档描述PreToolUse钩子："Runs after Claude creates tool parameters and before processing the tool call. Use PreToolUse decision control to allow, deny, or ask for permission to use the tool"。

**源文档章节**：
- [Restrict tool access with allowed-tools - Claude Code](https://code.claude.com/docs/en/skills)
- [Permission modes - Claude Code](https://code.claude.com/docs/en/sub-agents)
- [PreToolUse - Claude Code](https://code.claude.com/docs/en/hooks)

### 2.2 OpenCode：编程式工具定义与静态配置

OpenCode的工具系统采用了**TypeScript/JavaScript编程定义与JSON静态配置**的结合：

**基于TypeScript的工具定义**：OpenCode的工具使用TypeScript定义，通过`@opencode-ai/plugin`包提供的`tool()`辅助函数创建：

```typescript
export default tool({
  description: "Query the project database",
  args: {
    query: tool.schema.string().describe("SQL query to execute"),
  },
  async execute(args) {
    // Your database logic here
    return `Executed query: ${args.query}`
  },
})
```

**工具的静态配置控制**：在代理配置中，工具通过`tools`配置节进行控制，支持布尔值开关和通配符模式。文档说明："You can also use wildcards to control multiple tools at once. For example, to disable all tools from an MCP server"。

**源文档章节**：
- [Creating a tool - OpenCode](https://opencode.ai/docs/custom-tools)
- [Tools - OpenCode](https://opencode.ai/docs/agents)

---

## 3. 自主性与控制权的设计哲学

### 3.1 Claude Code：精细化控制与渐进式信任

Claude Code的设计哲学体现了**"安全第一，渐进式信任"**的理念：

**多层次的权限控制体系**：Claude Code实现了从全局到局部的五级权限控制：

1. 企业级托管设置（Managed Settings）
2. 用户级设置（User Settings）
3. 项目级设置（Project Settings）
4. 技能级限制（Skill-level restrictions）
5. 运行时钩子（Runtime hooks）

**权限模式作为信任级别映射**：不同的权限模式对应不同的信任级别。文档将`bypassPermissions`标记为需要谨慎使用："Use `bypassPermissions` with caution. It skips all permission checks, allowing the subagent to execute any operation without approval"。

**条件规则的高级控制**：通过PreToolUse Hooks，Claude Code支持基于上下文的动态权限决策。

**源文档章节**：
- [Permission-based architecture - Claude Code](https://code.claude.com/docs/en/security)
- [Permission modes - Claude Code](https://code.claude.com/docs/en/sub-agents)
- [Conditional rules with hooks - Claude Code](https://code.claude.com/docs/en/sub-agents)

### 3.2 OpenCode：显式配置与可预测的行为边界

OpenCode的设计哲学强调**"显式配置，可预测行为"**：

**代理能力边界**：每个代理都有明确的工具访问边界，这个边界在配置时就被固定。文档说明："Control which tools are available in this agent with the `tools` config. You can enable or disable specific tools by setting them to `true` or `false`"。

**最大步骤限制**：OpenCode提供了`maxSteps`配置来限制代理的迭代次数："Control the maximum number of agentic iterations an agent can perform before being forced to respond with text only. This allows users who wish to control costs to set a limit on agentic actions"。

**温度作为确定性控制**：通过`temperature`配置，OpenCode允许用户控制代理输出的随机性和创造性："Lower values make responses more focused and deterministic, while higher values increase creativity and variability"。

**源文档章节**：
- [Tools - OpenCode](https://opencode.ai/docs/agents)
- [Max steps - OpenCode](https://opencode.ai/docs/agents)
- [Temperature - OpenCode](https://opencode.ai/docs/agents)

---

## 4. 用户请求处理与任务执行流程

### 4.1 Claude Code：事件驱动的请求处理管道

Claude Code的处理流程体现了**事件驱动架构**的特征：

**请求接收与上下文匹配**：当用户提交请求时，Claude Code首先进行上下文匹配。文档描述："Skills are model-invoked: Claude decides which Skills to use based on your request. You don't need to explicitly call a Skill. Claude automatically applies relevant Skills when your request matches their description"。

**多阶段执行流程**：

1. **发现阶段（Discovery）**：启动时，仅加载每个Skill的名称和描述
2. **激活阶段（Activation）**：请求匹配Skill描述时，Claude请求使用该Skill
3. **执行阶段（Execution）**：Claude遵循Skill的指令，加载引用的文件或运行捆绑的脚本

**工具调用的生命周期管理**：每次工具调用都经过完整的生命周期：PreToolUse → 工具执行 → PostToolUse。

**源文档章节**：
- [How Skills work - Claude Code](https://code.claude.com/docs/en/skills)
- [Hook Execution Details - Claude Code](https://code.claude.com/docs/en/hooks)

### 4.2 OpenCode：代理路由与任务委派模型

OpenCode的处理流程体现了**代理路由与任务委派**的特征：

**主代理循环机制**：OpenCode使用Tab键循环切换主代理，每个主代理有明确的定位。文档描述："Primary agents are the main assistants you interact with directly...Tool access is configured via permissions — for example, Build has all tools enabled while Plan is restricted"。

**子代理的@提及调用**：子代理可以通过@提及被显式调用："Subagents can be invoked: Automatically by primary agents for specialized tasks based on their descriptions. Manually by @ mentioning a subagent in your message"。

**会话导航与状态管理**：OpenCode支持父子会话的导航："When subagents create their own child sessions, you can navigate between the parent session and all child sessions using <Leader>+Right"。

**源文档章节**：
- [Primary agents - OpenCode](https://opencode.ai/docs/agents)
- [Usage - OpenCode](https://opencode.ai/docs/agents)

---

## 5. 上下文管理与状态处理的差异

### 5.1 Claude Code：渐进式披露与上下文优化

Claude Code的上下文管理体现了**渐进式披露（Progressive Disclosure）**的设计原则：

**技能内容的渐进式加载**：文档描述了保持`SKILL.md`文件精简的策略："Keep `SKILL.md` under 500 lines for optimal performance. If your content exceeds this, split detailed reference material into separate files"。

**上下文窗口的智能管理**：
- 技能元数据仅在需要时加载
- 支持文件级引用（`{file:./path}`语法）
- 支持变量替换（`$ARGUMENTS`、`${CLAUDE_SESSION_ID}`）

**会话状态的钩子传递**：Hooks系统提供了会话状态的访问能力，包含`session_id`、`transcript_path`、`cwd`、`permission_mode`等上下文信息。

**源文档章节**：
- [Add supporting files with progressive disclosure - Claude Code](https://code.claude.com/docs/en/skills)
- [Hook Input - Claude Code](https://code.claude.com/docs/en/hooks)

### 5.2 OpenCode：配置驱动的上下文与独立会话模型

OpenCode的上下文管理采用了**配置驱动与独立会话**的模式：

**指令的配置文件管理**：通过`instructions`字段，OpenCode支持从多个文件加载上下文指令："The recommended approach is to use the `instructions` field in `opencode.json`"。

**工具的上下文访问**：OpenCode的工具系统通过`context`参数提供会话信息：

```typescript
async execute(args, context) {
  const { agent, sessionID, messageID } = context
  return `Agent: ${agent}, Session: ${sessionID}, Message: ${messageID}`
}
```

**源文档章节**：
- [Using opencode.json - OpenCode](https://opencode.ai/docs/rules)
- [Context - OpenCode](https://opencode.ai/docs/custom-tools)

---

## 6. 执行模型：脚本驱动 vs 提示驱动

### 6.1 Claude Code：提示驱动的工作流编排

Claude Code的执行模型是**提示驱动（Prompt-driven）**的：

**Skills作为提示工程载体**：每个Skill本质上是一个系统提示的增强，定义了代理的行为模式和响应策略。文档明确指出："A Skill is a markdown file that teaches Claude how to do something specific: reviewing PRs using your team's standards, generating commit messages in your preferred format, or querying your company's database schema"。

**Hooks作为脚本干预点**：虽然Hooks可以执行外部脚本，但设计目的是作为提示驱动流程的干预机制。

**源文档章节**：
- [Create your first Skill - Claude Code](https://code.claude.com/docs/en/skills)
- [PreToolUse Decision Control - Claude Code](https://code.claude.com/docs/en/hooks)

### 6.2 OpenCode：脚本驱动的工具执行

OpenCode的执行模型更接近**脚本驱动（Script-driven）**：

**工具作为可执行单元**：OpenCode的工具定义明确包含`execute`函数，这是一个可以执行任意代码的可调用单元。

**外部脚本的集成能力**：OpenCode的工具可以调用任何语言编写的脚本。文档示例："You can write your tools in any language you want. Here's an example that adds two numbers using Python"。

**源文档章节**：
- [Write a tool in Python - OpenCode](https://opencode.ai/docs/custom-tools)
- [Creating a tool - OpenCode](https://opencode.ai/docs/custom-tools)

---

## 综合对比分析表

| 维度 | Claude Code | OpenCode |
|------|-------------|----------|
| **核心架构** | 权限驱动的事件型架构 | 配置驱动的分层代理架构 |
| **工具调用** | 声明式控制 + 动态权限协商 | 编程式定义 + 静态配置 |
| **自主性控制** | 多层次权限 + 运行时Hooks | 显式配置边界 + 最大步骤限制 |
| **请求处理** | 事件驱动的生命周期管道 | 代理路由 + 任务委派模型 |
| **上下文管理** | 渐进式披露 + 动态上下文注入 | 配置驱动 + 独立会话模型 |
| **执行模型** | 提示驱动的工作流编排 | 脚本驱动的工具执行 |
| **设计哲学** | 安全第一，渐进式信任 | 显式配置，可预测行为 |
| **扩展机制** | Skills + Hooks | Agents + Custom Tools |
| **状态持久化** | 会话快照 + Hook输入/输出 | 独立会话 + 父子导航 |

---

## 结论与选型建议

### 设计哲学总结

| 特性 | Claude Code | OpenCode |
|------|-------------|----------|
| 安全机制 | 多层权限 + 运行时拦截 | 配置边界 + 步骤限制 |
| 扩展方式 | Skills（提示模板） | Custom Tools（可执行脚本） |
| 控制粒度 | 事件级Hooks拦截 | 配置级工具开关 |
| 学习曲线 | 较陡（Hooks系统复杂） | 较平（配置即代码） |

### 选型建议

**选择 Claude Code 的场景**：
- 需要精细的运行时控制和复杂的安全策略
- 重视渐进式披露和上下文优化
- 需要动态权限决策和条件规则
- 团队已有Anthropic生态依赖

**选择 OpenCode 的场景**：
- 需要灵活的代理配置和强大的脚本集成能力
- 重视配置的版本控制和可复用性
- 偏好TypeScript/JavaScript生态
- 需要多主代理协作的工作流

---

## 文档来源

### Claude Code 文档
| 模块 | 原文链接 | 本地路径 |
|-----|---------|---------|
| Agent Skills | https://code.claude.com/docs/en/skills | `Claude_Code_Docs@latest/Agent Skills/docContent.md` |
| Hooks Reference | https://code.claude.com/docs/en/hooks | `Claude_Code_Docs@latest/Hooks reference/docContent.md` |
| Security | https://code.claude.com/docs/en/security | `Claude_Code_Docs@latest/Security/docContent.md` |
| Create Custom Subagents | https://code.claude.com/docs/en/sub-agents | `Claude_Code_Docs@latest/Create custom subagents/docContent.md` |

### OpenCode 文档
| 模块 | 原文链接 | 本地路径 |
|-----|---------|---------|
| Agents | https://opencode.ai/docs/agents | `OpenCode_Docs@latest/Agents/docContent.md` |
| Custom Tools | https://opencode.ai/docs/custom-tools | `OpenCode_Docs@latest/Custom Tools/docContent.md` |
| Config | https://opencode.ai/docs/config | `OpenCode_Docs@latest/Config/docContent.md` |
| Rules | https://opencode.ai/docs/rules | `OpenCode_Docs@latest/Rules/docContent.md` |

---

*报告生成日期：2026-01-23*
*数据来源：doc-retriever 知识库检索*
