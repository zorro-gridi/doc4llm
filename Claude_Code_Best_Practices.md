# Claude Code 最佳实践、技巧和工作流全面指南

本文档汇总了 Claude Code 的最佳实践、使用技巧、工作模式和推荐方法，内容来源于官方文档。

## 目录

1. [初学者专业技巧](#初学者专业技巧)
2. [常见工作流最佳实践](#常见工作流最佳实践)
3. [成本管理优化](#成本管理优化)
4. [Agent Skills 使用模式](#agent-skills-使用模式)
5. [安全最佳实践](#安全最佳实践)
6. [高级技巧和模式](#高级技巧和模式)
7. [故障排除提示](#故障排除提示)

---

## 初学者专业技巧

### 1. 具体化您的请求

**❌ 避免：** "修复 bug"
**✅ 推荐：** "修复登录错误，即用户输入错误凭证后看到空白屏幕的问题"

**原因：** 具体的描述帮助 Claude 更准确地定位和理解问题。

### 2. 使用逐步指导

将复杂任务分解为多个步骤：

```bash
> 1. 为用户配置文件创建新的数据库表

> 2. 创建 API 端点来获取和更新用户配置文件

> 3. 构建一个网页，允许用户查看和编辑他们的信息
```

**优势：**
- 更容易跟踪进度
- 每个步骤可以独立验证
- 更容易调试问题

### 3. 让 Claude 先探索

在进行更改之前，让 Claude 理解您的代码：

```bash
> 分析数据库架构

> 构建一个仪表板，显示英国客户最常退回的产品
```

### 4. 节省时间的快捷键

- 按 `?` 查看所有可用的键盘快捷键
- 使用 Tab 进行命令补全
- 按 ↑ 查看命令历史
- 输入 `/` 查看所有斜杠命令

### 5. 理解 Claude Code 的工作原理

**关键特性：**
- Claude Code 根据需要读取文件 - 您无需手动添加上下文
- Claude 有权访问自己的文档，可以回答有关其功能和能力的问题
- 始终询问权限后才修改文件
- 可以启用"全部接受"模式进行会话

---

## 常见工作流最佳实践

### 1. 理解新代码库

#### 快速代码库概览

```bash
# 1. 导航到项目根目录
cd /path/to/project

# 2. 启动 Claude Code
claude

# 3. 请求高层概览
> 给我这个代码库的概览

# 4. 深入研究特定组件
> 解释这里使用的主要架构模式

> 关键数据模型是什么？

> 如何处理身份验证？
```

**技巧：**
- 从广泛的问题开始，然后缩小到特定领域
- 询问项目中使用的编码约定和模式
- 请求项目特定术语的词汇表

#### 查找相关代码

```bash
# 1. 让 Claude 查找相关文件
> 查找处理用户身份验证的文件

# 2. 获取组件如何交互的上下文
> 这些身份验证文件如何协同工作？

# 3. 理解执行流程
> 跟踪从前端到数据库的登录过程
```

**技巧：**
- 具体说明您要查找的内容
- 使用项目中的领域语言

### 2. 高效修复 Bug

```bash
# 1. 与 Claude 分享错误
> 我运行 npm test 时看到错误

# 2. 请求修复建议
> 建议几种修复 user.ts 中 @ts-ignore 的方法

# 3. 应用修复
> 按照您的建议更新 user.ts 添加空值检查
```

**技巧：**
- 告诉 Claude 重现问题的命令并获取堆栈跟踪
- 提及重现错误的任何步骤
- 让 Claude 知道错误是间歇性的还是一致的

### 3. 代码重构

```bash
# 1. 识别要重构的遗留代码
> 在我们的代码库中查找已弃用的 API 使用

# 2. 获取重构建议
> 建议如何重构 utils.js 以使用现代 JavaScript 特性

# 3. 安全地应用更改
> 在保持相同行为的同时重构 utils.js 以使用 ES2024 特性

# 4. 验证重构
> 运行重构代码的测试
```

**技巧：**
- 请求 Claude 解释现代方法的好处
- 在需要时请求保持向后兼容性
- 以小的、可测试的增量进行重构

### 4. 使用专业子代理

```bash
# 1. 查看可用的子代理
> /agents

# 2. 自动使用子代理
> 审查我的最近代码更改的安全问题

> 运行所有测试并修复任何失败

# 3. 显式请求特定子代理
> 使用 code-reviewer 子代理检查身份验证模块

> 让 debugger 子代理调查为什么用户无法登录
```

**技巧：**
- 在 `.claude/agents/` 中创建项目特定的子代理以供团队共享
- 使用描述性的 `description` 字段以启用自动委托
- 将工具访问权限限制在每个子代理实际需要的范围内

### 5. 使用 Plan Mode 进行安全代码分析

**何时使用 Plan Mode：**
- **多步骤实现：** 当您的功能需要编辑许多文件时
- **代码探索：** 当您想在更改任何内容之前彻底研究代码库时
- **交互式开发：** 当您想与 Claude 一起迭代方向时

**如何在会话期间启用 Plan Mode：**
- 使用 **Shift+Tab** 循环切换权限模式
- Normal Mode → Auto-Accept Mode (⏵⏵) → Plan Mode (⏸)

**在 Plan Mode 中启动新会话：**
```bash
claude --permission-mode plan
```

**运行"无头"查询：**
```bash
claude --permission-mode plan -p "分析身份验证系统并建议改进"
```

**配置 Plan Mode 为默认：**
```json
// .claude/settings.json
{
  "permissions": {
    "defaultMode": "plan"
  }
}
```

### 6. 让 Claude 面试您

对于大型功能，从最小规范开始，让 Claude 面试您以填写细节：

```bash
> 在开始之前面试我关于这个功能：用户通知系统

> 通过提出问题帮助我思考身份验证的要求

> 询问澄清问题以构建这个规范：支付处理
```

**优势：**
- 产生更好的规范
- 协作方法
- 识别边缘情况
- 阐明歧义

### 7. 处理测试

```bash
# 1. 识别未测试的代码
> 查找 NotificationsService.swift 中未被测试覆盖的函数

# 2. 生成测试脚手架
> 为通知服务添加测试

# 3. 添加有意义的测试用例
> 为通知服务中的边缘条件添加测试用例

# 4. 运行和验证测试
> 运行新测试并修复任何失败
```

**最佳实践：**
- 具体说明您要验证的行为
- Claude 会检查您现有的测试文件以匹配样式、框架和断言模式
- 请求 Claude 识别您可能遗漏的边缘情况

### 8. 创建 Pull Requests

```bash
# 1. 总结您的更改
> 总结我对身份验证模块所做的更改

# 2. 使用 Claude 生成 PR
> 创建一个 PR

# 3. 审查和完善
> 使用更多关于安全改进的上下文增强 PR 描述

# 4. 添加测试详情
> 添加关于如何测试这些更改的信息
```

**技巧：**
- 直接要求 Claude 为您创建 PR
- 在提交之前审查 Claude 生成的 PR
- 请求 Claude 突出显示潜在风险或考虑因素

### 9. 处理文档

```bash
# 1. 识别未记录的代码
> 查找身份验证模块中没有适当 JSDoc 注释的函数

# 2. 生成文档
> 为 auth.js 中未记录的函数添加 JSDoc 注释

# 3. 审查和增强
> 使用更多上下文和示例改进生成的文档

# 4. 验证文档
> 检查文档是否遵循我们的项目标准
```

**技巧：**
- 指定您想要的文档样式（JSDoc、docstrings 等）
- 请求文档中的示例
- 为公共 API、接口和复杂逻辑请求文档

### 10. 处理图像

**添加图像到对话：**
1. 将图像拖放到 Claude Code 窗口中
2. 复制图像并使用 ctrl+v 粘贴到 CLI 中（不要使用 cmd+v）
3. 向 Claude 提供图像路径。例如，"分析此图像：/path/to/your/image.png"

**分析图像：**
```bash
> 此图像显示什么？

> 描述此屏幕截图中的 UI 元素

> 此图中是否有问题的元素？
```

**使用图像作为上下文：**
```bash
> 这是错误的屏幕截图。是什么导致的？

> 这是我们当前的数据库架构。我们应该如何为新功能修改它？
```

**从视觉内容获取代码建议：**
```bash
> 生成与此设计模型匹配的 CSS

> 什么 HTML 结构将重新创建此组件？
```

**技巧：**
- 当文本描述不清楚或繁琐时使用图像
- 包含错误、UI 设计或图表的屏幕截图以获得更好的上下文
- 您可以在对话中使用多个图像
- 当 Claude 引用图像（例如，`[Image #1]`）时，Cmd+Click（Mac）或 Ctrl+Click（Windows/Linux）链接可在默认查看器中打开图像

### 11. 引用文件和目录

**引用单个文件：**
```bash
> 解释 @src/utils/auth.js 中的逻辑
```

**引用目录：**
```bash
> @src/components 的结构是什么？
```

**引用 MCP 资源：**
```bash
> 显示来自 @github:repos/owner/repo/issues 的数据
```

**技巧：**
- 文件路径可以是相对的或绝对的
- @ 文件引用将文件目录和父目录中的 `CLAUDE.md` 添加到上下文
- 目录引用显示文件列表，而不是内容
- 您可以在单个消息中引用多个文件（例如，"@file1.js and @file2.js"）

### 12. 使用扩展思考（思考模式）

**什么是扩展思考：**
- 默认启用
- 为 Claude 分配最多 31,999 个输出令牌用于逐步推理
- 对于复杂的架构决策、具有挑战性的 bug、多步骤实施规划和评估不同方法之间的权衡特别有价值

**配置思考模式：**

| 范围 | 如何配置 | 详情 |
|------|----------|------|
| **切换快捷键** | 按 `Option+T` (macOS) 或 `Alt+T` (Windows/Linux) | 切换当前会话的思考开/关。可能需要终端配置来启用 Option 键快捷键 |
| **全局默认** | 使用 `/config` 切换思考模式 | 在所有项目中设置您的默认值。保存在 `~/.claude/settings.json` 中作为 `alwaysThinkingEnabled` |
| **限制令牌预算** | 设置 `MAX_THINKING_TOKENS` 环境变量 | 将思考预算限制为特定数量的令牌。例如：`export MAX_THINKING_TOKENS=10000` |

**查看思考过程：**
- 按 `Ctrl+O` 切换详细模式
- 查看显示为灰色斜体文本的内部推理

**思考令牌预算：**
- 启用思考时：Claude 可以使用最多 **31,999 个令牌**进行内部推理
- 禁用思考时：Claude 使用 **0 个令牌**进行思考
- **重要：** 即使 Claude 4 模型显示总结的思考，您也要为所有使用的思考令牌付费

### 13. 恢复以前的对话

**命令：**
- `claude --continue` - 继续当前目录中最近的对话
- `claude --resume` - 打开对话选择器或按名称恢复

**命名您的会话：**
```bash
# 命名当前会话
> /rename auth-refactor

# 稍后按名称恢复
claude --resume auth-refactor

# 或从活动会话内
> /resume auth-refactor
```

**使用会话选择器：**

**选择器中的键盘快捷键：**

| 快捷键 | 操作 |
|--------|------|
| `↑` / `↓` | 在会话之间导航 |
| `→` / `←` | 展开或折叠分组的会话 |
| `Enter` | 选择并恢复突出显示的会话 |
| `P` | 预览会话内容 |
| `R` | 重命名突出显示的会话 |
| `/` | 搜索以过滤会话 |
| `A` | 在当前目录和所有项目之间切换 |
| `B` | 过滤到当前 git 分支的会话 |
| `Esc` | 退出选择器或搜索模式 |

**会话组织：**
- 会话名称或初始提示
- 自上次活动以来经过的时间
- 消息计数
- Git 分支（如果适用）

**技巧：**
- **尽早命名会话：** 在开始处理不同任务时使用 `/rename` - 以后更容易找到"payment-integration"而不是"解释这个函数"
- 使用 `--continue` 快速访问当前目录中最近的对话
- 使用 `--resume session-name` 当您知道需要哪个会话时
- 使用 `--resume`（不带名称）当您需要浏览和选择时
- 对于脚本，使用 `claude --continue --print "prompt"` 以非交互模式恢复
- 在选择器中按 `P` 在恢复之前预览会话

### 14. 使用 Git Worktrees 运行并行 Claude Code 会话

```bash
# 1. 创建一个新的 worktree
git worktree add ../project-feature-a -b feature-a

# 或使用现有分支创建 worktree
git worktree add ../project-bugfix bugfix-123

# 2. 在每个 worktree 中运行 Claude Code
cd ../project-feature-a
claude

# 3. 在另一个 worktree 中运行 Claude
cd ../project-bugfix
claude

# 4. 管理您的 worktrees
# 列出所有 worktrees
git worktree list

# 完成后删除 worktree
git worktree remove ../project-feature-a
```

**技巧：**
- 每个 worktree 都有自己的独立文件状态，非常适合并行 Claude Code 会话
- 在一个 worktree 中所做的更改不会影响其他 worktree，防止 Claude 实例互相干扰
- 所有 worktree 共享相同的 Git 历史记录和远程连接
- 对于长时间运行的任务，您可以让 Claude 在一个 worktree 中工作，而您在另一个 worktree 中继续开发
- 使用描述性目录名称以轻松识别每个 worktree 用于什么任务
- 记住根据项目的设置过程在每个新 worktree 中初始化开发环境

### 15. 将 Claude 用作 Unix 风格实用程序

**添加到您的验证过程：**

```json
// package.json
{
    ...
    "scripts": {
        ...
        "lint:claude": "claude -p 'you are a linter. please look at the changes vs. main and report any issues related to typos. report the filename and line number on one line, and a description of the issue on the second line. do not return any other text.'"
    }
}
```

**技巧：**
- 将 Claude 用于 CI/CD 管道中的自动代码审查
- 自定义提示以检查与您的项目相关的特定问题
- 考虑创建多个脚本用于不同类型的验证

**管道输入，管道输出：**

```bash
cat build-error.txt | claude -p '简要解释此构建错误的根本原因' > output.txt
```

**技巧：**
- 使用管道将 Claude 集成到现有的 shell 脚本中
- 与其他 Unix 工具结合以实现强大的工作流
- 考虑使用 --output-format 进行结构化输出

**控制输出格式：**

**1. 使用文本格式（默认）：**
```bash
cat data.txt | claude -p '总结此数据' --output-format text > summary.txt
```

**2. 使用 JSON 格式：**
```bash
cat code.py | claude -p '分析此代码的错误' --output-format json > analysis.json
```

**3. 使用流式 JSON 格式：**
```bash
cat log.txt | claude -p '解析此日志文件的错误' --output-format stream-json
```

**技巧：**
- 使用 `--output-format text` 进行简单的集成，您只需要 Claude 的响应
- 使用 `--output-format json` 当您需要完整的对话日志时
- 使用 `--output-format stream-json` 实时输出每个对话轮次

### 16. 创建自定义斜杠命令

**创建项目特定命令：**

```bash
# 1. 在项目中创建命令目录
mkdir -p .claude/commands

# 2. 为每个命令创建 Markdown 文件
echo "分析此代码的性能并建议三个具体的优化：" > .claude/commands/optimize.md

# 3. 在 Claude Code 中使用您的自定义命令
> /optimize
```

**技巧：**
- 命令名称源自文件名（例如，`optimize.md` 变成 `/optimize`）
- 您可以在子目录中组织命令（例如，`.claude/commands/frontend/component.md` 创建带有"(project:frontend)"显示在描述中的 `/component`）
- 项目命令对克隆存储库的每个人都可用
- Markdown 文件内容变成调用命令时发送给 Claude 的提示

**使用 $ARGUMENTS 添加命令参数：**

```bash
# 1. 创建带有 $ARGUMENTS 占位符的命令文件
echo '查找并修复问题 #$ARGUMENTS。按照以下步骤：1. 理解票据中描述的问题 2. 定位我们代码库中的相关代码 3. 实现解决根本原因的解决方案 4. 添加适当的测试 5. 准备简洁的 PR 描述' > .claude/commands/fix-issue.md

# 2. 使用带问题编号的命令
> /fix-issue 123
```

**技巧：**
- `$ARGUMENTS` 占位符替换为命令后面的任何文本
- 您可以将 `$ARGUMENTS` 定位在命令模板中的任何位置
- 其他有用的应用程序：为特定函数生成测试用例、创建组件文档、审查特定文件中的代码或将内容翻译为指定语言

**创建个人斜杠命令：**

```bash
# 1. 在主文件夹中创建命令目录
mkdir -p ~/.claude/commands

# 2. 为每个命令创建 Markdown 文件
echo "审查此代码的安全漏洞，重点关注：" > ~/.claude/commands/security-review.md

# 3. 使用您的个人自定义命令
> /security-review
```

**技巧：**
- 个人命令在用 `/help` 列出时在描述中显示"(user)"
- 个人命令仅对您可用，不与您的团队共享
- 个人命令适用于您的所有项目
- 您可以使用这些在不同代码库之间实现一致的工作流

---

## 成本管理优化

### 平均成本
- **每个开发者每天：** $6
- **90% 的用户：** 每日成本保持在 $12 以下
- **团队使用：** 平均每个开发者每月 ~$100-200（使用 Sonnet 4.5），但差异很大

### 跟踪成本

**使用 `/cost` 命令：**
```
Total cost:            $0.55
Total duration (API):  6m 19.7s
Total duration (wall): 6h 33m 10.2s
Total code changes:    0 lines added, 0 lines removed
```

**注意：** `/cost` 命令不适用于 Claude Max 和 Pro 订阅者。

**其他跟踪选项：**
- 查看 Claude Console 中的[历史使用情况](https://support.claude.com/en/articles/9534590-cost-and-usage-reporting-in-console)（需要 Admin 或 Billing 角色）
- 为 Claude Code 工作区设置[工作区支出限制](https://support.claude.com/en/articles/9796807-creating-and-managing-workspaces)（需要 Admin 角色）

### 团队成本管理

**每用户速率限制建议：**

| 团队规模 | 每用户 TPM | 每用户 RPM |
|---------|-----------|-----------|
| 1-5 用户 | 200k-300k | 5-7 |
| 5-20 用户 | 100k-150k | 2.5-3.5 |
| 20-50 用户 | 50k-75k | 1.25-1.75 |
| 50-100 用户 | 25k-35k | 0.62-0.87 |
| 100-500 用户 | 15k-20k | 0.37-0.47 |
| 500+ 用户 | 10k-15k | 0.25-0.35 |

**示例：** 如果您有 200 个用户，您可能会请求每个用户 20k TPM，或 400 万总 TPM (200*20,000 = 400 万)。

**注意：**
- 这些速率限制适用于组织级别，而不是每个个人用户
- 个人用户可以在其他用户不主动使用服务时临时消耗超过其计算份额
- 如果您预计异常高并发使用场景（例如与大群体的实时培训会话），您可能需要每个用户更高的 TPM 分配

### 减少令牌使用

**紧凑对话：**
- Claude 在上下文达到约 95% 容量时默认使用自动紧凑
- 更早触发紧凑：设置 `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` 为较低的百分比（例如，`50`）
- 切换自动紧凑：运行 `/config` 并导航到"Auto-compact enabled"
- 手动使用 `/compact` 当上下文变大时
- 添加自定义说明：`/compact Focus on code samples and API usage`
- 通过添加到 CLAUDE.md 自定义紧凑：
  ```markdown
  # Summary instructions

  When you are using compact, please focus on test output and code changes
  ```

**其他策略：**
- **编写具体的查询：** 避免触发不必要扫描的模糊请求
- **分解复杂任务：** 将大型任务拆分为专注的交互
- **在任务之间清除历史：** 使用 `/clear` 重置上下文

**成本变化因素：**
- 正在分析的代码库大小
- 查询复杂性
- 正在搜索或修改的文件数量
- 对话历史长度
- 紧凑对话的频率

### 后台令牌使用

Claude Code 在空闲时为某些后台功能使用令牌：
- **对话总结：** 为 `claude --resume` 功能总结以前对话的后台作业
- **命令处理：** 某些命令如 `/cost` 可能生成请求以检查状态

**注意：** 这些后台过程即使在没有主动交互的情况下也消耗少量令牌（每个会话通常低于 $0.04）。

### 跟踪版本更改和更新

**检查当前版本：**
```bash
claude doctor
```

**了解 Claude Code 行为的变化：**
- **版本跟踪：** 使用 `claude doctor` 查看您的当前版本
- **行为变化：** 功能如 `/cost` 可能跨版本显示不同的信息
- **文档访问：** Claude 始终有权访问最新的文档，这可以帮助解释当前功能行为

**团队部署建议：**
建议从小型试点组开始，在更广泛推出之前建立使用模式。

---

## Agent Skills 使用模式

### 什么是 Skills

Skill 是一个 markdown 文件，教导 Claude 如何做特定的事情：使用您团队的标准审查 PR、以您首选的格式生成提交消息、或查询您公司的数据库架构。当您问 Claude 与 Skill 目的匹配的问题时，Claude 会自动应用它。

### 创建您的第一个 Skill

**1. 检查可用的 Skills：**
```bash
What Skills are available?
```

**2. 创建 Skill 目录：**
```bash
mkdir -p ~/.claude/skills/explaining-code
```

**3. 编写 SKILL.md：**
```markdown
---
name: explaining-code
description: Explains code with visual diagrams and analogies. Use when explaining how code works, teaching about a codebase, or when the user asks "how does this work?"
---

When explaining code, always include:

1. **Start with an analogy**: Compare the code to something from everyday life
2. **Draw a diagram**: Use ASCII art to show the flow, structure, or relationships
3. **Walk through the code**: Explain step-by-step what happens
4. **Highlight a gotcha**: What's a common mistake or misconception?

Keep explanations conversational. For complex concepts, use multiple analogies.
```

**4. 加载并验证 Skill：**
```bash
What Skills are available?
```

**5. 测试 Skill：**
```bash
How does this code work?
```

### Skills 如何工作

**1. 发现：**
- 在启动时，Claude 仅加载每个可用 Skill 的名称和描述
- 这使启动快速，同时给 Claude 足够的上下文以知道每个 Skill 何时可能相关

**2. 激活：**
- 当您的请求与 Skill 的描述匹配时，Claude 请求使用 Skill
- 在加载完整的 `SKILL.md` 之前，您会看到确认提示
- 由于 Claude 读取这些描述以查找相关的 Skills，请编写包含用户自然会说的关键词的描述

**3. 执行：**
- Claude 遵循 Skill 的说明，根据需要加载引用的文件或运行捆绑的脚本

### Skills 存放位置

| 位置 | 路径 | 适用于 |
|------|------|--------|
| **Enterprise** | See [managed settings](https://code.claude.com/docs/en/iam#managed-settings) | 组织中的所有用户 |
| **Personal** | `~/.claude/skills/` | 您，跨所有项目 |
| **Project** | `.claude/skills/` | 在此存储库中工作的任何人 |
| **Plugin** | Bundled with [plugins](https://code.claude.com/docs/en/plugins) | 安装了插件的任何人 |

**优先级：** 如果两个 Skills 具有相同的名称，更高的行获胜：managed 覆盖 personal，personal 覆盖 project，project 覆盖 plugin。

**嵌套目录的自动发现：**
- 当您在子目录中处理文件时，Claude Code 自动从嵌套的 `.claude/skills/` 目录发现 Skills
- 例如，如果您在 `packages/frontend/` 中编辑文件，Claude Code 也会在 `packages/frontend/.claude/skills/` 中查找 Skills
- 这支持具有自己 Skills 的包的 monorepo 设置

### 何时使用 Skills 与其他选项

| 使用此 | 当您想要... | 何时运行 |
|--------|------------|----------|
| **Skills** | 给 Claude 专门知识（例如，"使用我们的标准审查 PR"） | Claude 选择何时相关 |
| **Slash commands** | 创建可重用的提示（例如，`/deploy staging`） | 您输入 `/command` 来运行它 |
| **CLAUDE.md** | 设置项目范围说明（例如，"使用 TypeScript 严格模式"） | 加载到每个对话中 |
| **Subagents** | 将任务委托给具有自己工具的单独上下文 | Claude 委托，或您显式调用 |
| **Hooks** | 在事件上运行脚本（例如，文件保存时 lint） | 在特定工具事件上触发 |
| **MCP servers** | 将 Claude 连接到外部工具和数据源 | Claude 根据需要调用 MCP 工具 |

**Skills vs. 子代理：** Skills 为当前对话添加知识。子代理在具有自己工具的单独上下文中运行。对指导和标准使用 Skills；当您需要隔离或不同的工具访问时使用子代理。

**Skills vs. MCP：** Skills 告诉 Claude _如何_ 使用工具；MCP _提供_ 工具。例如，MCP 服务器将 Claude 连接到您的数据库，而 Skill 教导 Claude 您的数据模型和查询模式。

### 编写 SKILL.md

**可用元数据字段：**

| 字段 | 必需 | 描述 |
|------|------|------|
| `name` | 是 | Skill 名称。必须仅使用小写字母、数字和连字符（最多 64 个字符）。应与目录名称匹配。 |
| `description` | 是 | Skill 的作用以及何时使用它（最多 1024 个字符）。Claude 使用它来决定何时应用 Skill。 |
| `allowed-tools` | 否 | 当此 Skill 处于活动状态时，Claude 可以在未经许可的情况下使用的工具。支持逗号分隔的值或 YAML 样式的列表。 |
| `model` | 否 | 当此 Skill 处于活动状态时使用的模型（例如，`claude-sonnet-4-20250514`）。默认为对话的模型。 |
| `context` | 否 | 设置为 `fork` 以在具有自己对话历史的分叉子代理上下文中运行 Skill。 |
| `agent` | 否 | 指定当设置 `context: fork` 时使用哪个代理类型（例如，`Explore`、`Plan`、`general-purpose` 或来自 `.claude/agents/` 的自定义代理名称）。如果未指定，默认为 `general-purpose`。仅在与 `context: fork` 结合时适用。 |
| `hooks` | 否 | 定义为此 Skill 的生命周期作用域的钩子。支持 `PreToolUse`、`PostToolUse` 和 `Stop` 事件。 |
| `user-invocable` | 否 | 控制 Skill 是否出现在斜杠命令菜单中。不影响 `Skill` 工具或自动发现。默认为 `true`。 |

**可用字符串替换：**

| 变量 | 描述 |
|------|------|
| `$ARGUMENTS` | 调用 Skill 时传递的所有参数。如果 `$ARGUMENTS` 不存在于内容中，参数将附加为 `ARGUMENTS: <value>`。 |
| `${CLAUDE_SESSION_ID}` | 当前会话 ID。对于日志记录、创建会话特定文件或关联 Skill 输出与会话很有用。 |

**示例：**
```markdown
---
name: session-logger
description: Log activity for this session
---

Log the following to logs/${CLAUDE_SESSION_ID}.log:

$ARGUMENTS
```

### 使用渐进式披露添加支持文件

**保持 SKILL.md 在 500 行以下**以获得最佳性能。如果您的内容超过此，将详细的参考材料拆分为单独的文件。

**示例：多文件 Skill 结构：**
```
my-skill/
├── SKILL.md (required - overview and navigation)
├── reference.md (detailed API docs - loaded when needed)
├── examples.md (usage examples - loaded when needed)
└── scripts/
    └── helper.py (utility script - executed, not loaded)
```

**在 SKILL.md 中引用：**
```markdown
## Overview

[Essential instructions here]

## Additional resources

- For complete API details, see [reference.md](reference.md)
- For usage examples, see [examples.md](examples.md)

## Utility scripts

To validate input files, run the helper script. It checks for required fields and returns any validation errors:
```bash
python scripts/helper.py input.txt
```
```

**技巧：**
- 保持引用一级深度。直接从 `SKILL.md` 链接到参考文件
- 深度嵌套的引用（文件 A 链接到文件 B，文件 B 链接到文件 C）可能导致 Claude 部分读取文件
- 捆绑实用程序脚本以进行零上下文执行。Skill 目录中的脚本可以在不将其内容加载到上下文的情况下执行。Claude 运行脚本，只有输出消耗令牌

### 使用 allowed-tools 限制工具访问

```markdown
---
name: reading-files-safely
description: Read files without making changes. Use when you need read-only file access.
allowed-tools: Read, Grep, Glob
---
```

或使用 YAML 样式的列表以获得更好的可读性：

```markdown
---
name: reading-files-safely
description: Read files without making changes. Use when you need read-only file access.
allowed-tools:
  - Read
  - Grep
  - Glob
---
```

**用途：**
- 不应修改文件的只读 Skills
- 范围有限的 Skills：例如，仅数据分析，不写文件
- 安全敏感的工作流，您希望限制功能

### 在分叉上下文中运行 Skills

```markdown
---
name: code-analysis
description: Analyze code quality and generate detailed reports
context: fork
---
```

这会在隔离的子代理上下文中运行 Skill，该上下文具有自己的对话历史。这对于执行复杂的多步骤操作而不使主对话混乱的 Skills 很有用。

### 定义 Skills 的钩子

```markdown
---
name: secure-operations
description: Perform operations with additional security checks
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh $TOOL_INPUT"
          once: true
---
```

`once: true` 选项每个会话仅运行钩子一次。第一次成功执行后，钩子被删除。Skill 中定义的钩子作用于该 Skill 的执行，并在 Skill 完成时自动清理。

### 控制 Skill 可见性

Skills 可以通过三种方式调用：

1. **手动调用：** 您在提示中输入 `/skill-name`
2. **编程调用：** Claude 通过 `Skill` 工具调用它
3. **自动发现：** Claude 读取 Skill 的描述，并在与对话相关时加载它

`user-invocable` 字段仅控制手动调用。设置为 `false` 时，Skill 从斜杠命令菜单中隐藏，但 Claude 仍可以通过编程方式调用它或自动发现它。

**何时使用每个设置：**

| 设置 | Slash 菜单 | `Skill` 工具 | 自动发现 | 用例 |
|------|-----------|-------------|----------|------|
| `user-invocable: true` (默认) | 可见 | 允许 | 是 | 您希望用户直接调用的 Skills |
| `user-invocable: false` | 隐藏 | 允许 | 是 | Claude 可以使用但用户不应手动调用的 Skills |
| `disable-model-invocation: true` | 可见 | 阻止 | 是 | 您希望用户调用但不以编程方式调用的 Skills |

### Skills 和子代理

**给子代理访问 Skills：**

子代理不会自动从主对话继承 Skills。要给自定义子代理访问特定 Skills，请在子代理的 `skills` 字段中列出它们：

```markdown
# .claude/agents/code-reviewer.md
---
name: code-reviewer
description: Review code for quality and best practices
skills: pr-review, security-check
---
```

**注意：** 每个列出的 Skill 的完整内容在启动时注入到子代理的上下文中，而不仅仅是使其可用于调用。如果省略 `skills` 字段，则不会为该子代理加载 Skills。

内置代理（Explore、Plan、general-purpose）无权访问您的 Skills。只有您在 `.claude/agents/` 中定义的自定义子代理具有显式 `skills` 字段才能使用 Skills。

### 分发 Skills

**项目 Skills：** 将 `.claude/skills/` 提交到版本控制。克隆存储库的任何人都获得 Skills。

**插件：** 要在多个存储库之间共享 Skills，在您的插件中创建 `skills/` 目录，其中包含包含 `SKILL.md` 文件的 Skill 文件夹。通过插件市场分发。

**托管：** 管理员可以通过托管设置在整个组织中部署 Skills。

### 故障排除

**Skill 未触发：**

`description` 字段是 Claude 决定是否使用您的 Skill 的方式。像"Helps with documents"这样模糊的描述不会给 Claude 足够的信息来将您的 Skill 与相关请求匹配。一个好的描述回答两个问题：

1. **这个 Skill 做什么？** 列出特定功能。
2. **Claude 应该何时使用它？** 包括用户会提到的触发术语。

**好的描述示例：**
```markdown
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
```

**Skill 不加载：**

**检查文件路径。** Skills 必须在正确的目录中，具有确切的文件名 `SKILL.md`（区分大小写）：

| 类型 | 路径 |
|------|------|
| Personal | `~/.claude/skills/my-skill/SKILL.md` |
| Project | `.claude/skills/my-skill/SKILL.md` |
| Enterprise | See Where Skills live for platform-specific paths |
| Plugin | `skills/my-skill/SKILL.md` inside the plugin directory |

**检查 YAML 语法。** frontmatter 中的无效 YAML 会阻止 Skill 加载。frontmatter 必须在第 1 行以 `---` 开始（前面没有空行），在 Markdown 内容之前以 `---` 结束，并使用空格进行缩进（而不是制表符）。

**运行调试模式。** 使用 `claude --debug` 查看 Skill 加载错误。

**多个 Skills 冲突：**

如果 Claude 使用错误的 Skill 或在类似的 Skills 之间混淆，描述可能太相似了。通过使用特定的触发术语使每个描述不同。例如，不要在两个描述中都有"data analysis"，而是区分它们：一个用于"sales data in Excel files and CRM exports"，另一个用于"log files and system metrics"。您使用的触发术语越具体，Claude 就越容易将正确的 Skill 与您的请求匹配。

---

## 安全最佳实践

### 安全基础

您的代码安全至关重要。Claude Code 的核心构建安全，根据 Anthropic 的综合安全程序开发。

### 基于权限的架构

Claude Code 默认使用严格的只读权限。当需要其他操作（编辑文件、运行测试、执行命令）时，Claude Code 请求明确权限。用户控制是批准一次还是自动允许它们。

**内置保护：**

- **沙盒化 bash 工具：** 沙盒 bash 命令，具有文件系统和网络隔离，在保持安全性的同时减少权限提示。使用 `/sandbox` 启用以定义 Claude Code 可以自主工作的边界
- **写访问限制：** Claude Code 只能写入它启动的文件夹及其子文件夹 - 它不能在未经明确许可的情况下修改父目录中的文件
- **提示疲劳缓解：** 支持每个用户、每个代码库或每个组织允许频繁使用的安全命令
- **接受编辑模式：** 批量接受多个编辑，同时为具有副作用的命令维护权限提示

### 防止提示注入

**核心保护：**
- **权限系统：** 敏感操作需要明确批准
- **上下文感知分析：** 通过分析完整请求来检测潜在的有害指令
- **输入清理：** 通过处理用户输入来防止命令注入
- **命令阻止列表：** 默认阻止从 Web 获取任意内容的风险命令，如 `curl` 和 `wget`

**隐私保障：**
- 敏感信息的有限保留期
- 限制访问用户会话数据
- 用户控制数据训练偏好

**额外保障：**
- **网络请求批准：** 进行网络请求的工具默认需要用户批准
- **隔离的上下文窗口：** Web fetch 使用单独的上下文窗口以避免注入潜在的恶意提示
- **信任验证：** 首次代码库运行和新的 MCP 服务器需要信任验证
  - 注意：使用 `-p` 标志以非交互方式运行时，信任验证被禁用
- **命令注入检测：** 可疑的 bash 命令即使以前被允许也需要手动批准
- **失败关闭匹配：** 未匹配的命令默认需要手动批准
- **自然语言描述：** 复杂的 bash 命令包括用于用户理解的说明
- **安全凭据存储：** API 密钥和令牌已加密

### 处理不受信任内容的最佳实践

1. 在批准之前审查建议的命令
2. 避免将不受信任的内容直接管道传输到 Claude
3. 验证对关键文件的提议更改
4. 使用虚拟机 (VM) 运行脚本并进行工具调用，尤其是在与外部 Web 服务交互时
5. 使用 `/bug` 报告可疑行为

### MCP 安全

- Claude Code 允许用户配置模型上下文协议 (MCP) 服务器
- 允许的 MCP 服务器列表在您的源代码中配置，作为工程师签入源控制的 Claude Code 设置的一部分
- 我们鼓励编写自己的 MCP 服务器或使用您信任的提供商提供的 MCP 服务器
- 您能够为 MCP 服务器配置 Claude Code 权限
- Anthropic 不管理或审核任何 MCP 服务器

### 云执行安全

使用 Claude Code on the web时，额外的安全控制已就位：

- **隔离的虚拟机：** 每个云会话在隔离的、Anthropic 管理的 VM 中运行
- **网络访问控制：** 网络访问默认受限，可以配置为禁用或仅允许特定域
- **凭据保护：** 身份验证通过安全代理处理，该代理在沙盒中使用作用域凭据，然后转换为您的实际 GitHub 身份验证令牌
- **分支限制：** Git push 操作仅限于当前工作分支
- **审计日志记录：** 云环境中的所有操作都被记录以进行合规性和审计
- **自动清理：** 云环境在会话完成后自动终止

### 团队安全

- 使用托管设置强制执行组织标准
- 通过版本控制共享批准的权限配置
- 培训团队成员安全最佳实践
- 通过 OpenTelemetry 指标监控 Claude Code 使用情况

### 报告安全问题

如果您在 Claude Code 中发现安全漏洞：

1. 不要公开披露
2. 通过我们的 HackerOne 程序报告
3. 包括详细的重现步骤
4. 在公开披露之前留出时间让我们解决问题

---

## 高级技巧和模式

### 终端设置优化

**主题和外观：** 根据您的偏好自定义终端主题以获得更好的可读性。

**换行：** 配置终端以正确处理长行。

**通知设置：**
- **iTerm 2 系统通知：** 在长时间运行的命令完成时获取通知
- **自定义通知钩子：** 设置特定事件的自定义通知

**处理大输入：** 配置终端以有效地处理大文本块。

**Vim Mode：** 为喜欢 Vim 键绑定的用户启用 Vim 模式。

### 常见模式和反模式

**模式 1：迭代改进**
```bash
# ✅ 好的方法
> 为用户配置文件创建数据库架构
> 审查建议的架构并改进
> 根据审查实施架构
```

**❌ 反模式：** 一次性要求所有内容而无需迭代

**模式 2：上下文优先方法**
```bash
# ✅ 好的方法
> 分析现有代码库结构
> 基于此分析建议添加新功能的最佳位置
```

**❌ 反模式：** 在不了解现有结构的情况下要求更改

**模式 3：测试驱动开发**
```bash
# ✅ 好的方法
> 为新功能编写测试
> 实现功能以通过测试
> 运行测试并修复任何失败
```

**❌ 反模式：** 在没有测试的情况下实现功能

### 性能优化技巧

1. **使用 /compact 保持对话专注**
2. **在任务之间使用 /clear 清除历史**
3. **使用 @ 符号引用特定文件而不是让 Claude 搜索**
4. **对大型重复性任务使用自定义斜杠命令**
5. **为复杂操作使用专业子代理**

---

## 故障排除提示

### 常见安装问题

**Linux 和 Mac 安装问题：权限或命令未找到错误**

**推荐的解决方案：** 原生 Claude Code 安装

### 权限和身份验证

**重复的权限提示：**
- 审查您的权限设置
- 考虑允许频繁使用的安全命令

### 性能和稳定性

**高 CPU 或内存使用：**
- 检查是否有大型文件正在被读取
- 考虑使用 /compact 减少上下文大小
- 关闭未使用的会话

**命令挂起或冻结：**
- 检查网络连接
- 使用 Ctrl+C 中断命令
- 如果持续存在，使用 `/bug` 报告

**搜索和发现问题：**
- 确保您在项目根目录中
- 检查文件权限
- 尝试重新启动 Claude Code

### Markdown 格式问题

**最佳实践：**
- 确保代码块具有语言标签
- 保持一致的间距和格式
- 使用适当的标题级别

### 获取更多帮助

- **在 Claude Code 中：** 输入 `/help` 或询问"how do I…"
- **文档：** 您在这里！浏览其他指南
- **社区：** 加入我们的 Discord 获取技巧和支持

---

## 总结和关键要点

### Claude Code 最佳实践总结

1. **具体化您的请求** - 详细的描述产生更好的结果
2. **分解复杂任务** - 逐步方法更有效
3. **使用 Plan Mode** - 对于大型或多步骤任务
4. **利用自定义命令** - 为重复性任务创建斜杠命令
5. **管理上下文** - 使用 /compact 和 /clear 保持对话专注
6. **监控成本** - 使用 /cost 跟踪令牌使用
7. **安全第一** - 审查建议的命令和更改
8. **利用 Skills** - 为专门知识创建 Agent Skills
9. **使用子代理** - 为特定任务委托给专业代理
10. **命名会话** - 使用 /rename 以便以后查找

### 常见工作流程模式

- **理解代码库：** 从广泛的问题开始，缩小到特定领域
- **修复 Bug：** 提供错误详情、重现步骤和上下文
- **重构：** 分析、计划、实施、验证
- **测试：** 识别未测试的代码、生成测试、验证
- **文档：** 识别未记录的代码、生成文档、审查
- **PR 创建：** 总结更改、生成 PR、增强描述

### 成本优化策略

- 编写具体的查询
- 分解复杂任务
- 在任务之间清除历史
- 使用自动紧凑
- 监控使用情况

### 安全考虑

- 审查所有建议的更改
- 使用项目特定的权限设置
- 定期审计权限设置
- 报告可疑行为
- 保护敏感代码

---

## 文档来源 (Sources)

1. **Quickstart**
   - 原文链接: https://code.claude.com/docs/en/quickstart
   - 路径: `md_docs/Claude_Code_Docs:latest/Quickstart/docContent.md`
   - 行数: 358

2. **Common workflows**
   - 原文链接: https://code.claude.com/docs/en/common-workflows
   - 路径: `md_docs/Claude_Code_Docs:latest/Common workflows/docContent.md`
   - 行数: 1,136

3. **Manage costs effectively**
   - 原文链接: https://code.claude.com/docs/en/costs
   - 路径: `md_docs/Claude_Code_Docs:latest/Manage costs effectively/docContent.md`
   - 行数: 117

4. **Agent Skills**
   - 原文链接: https://code.claude.com/docs/en/skills
   - 路径: `md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md`
   - 行数: 583

5. **Security**
   - 原文链接: https://code.claude.com/docs/en/security
   - 路径: `md_docs/Claude_Code_Docs:latest/Security/docContent.md`
   - 行数: 128

6. **Troubleshooting**
   - 原文链接: https://code.claude.com/docs/en/troubleshooting
   - 路径: `md_docs/Claude_Code_Docs:latest/Troubleshooting/docTOC.md`

7. **Optimize your terminal setup**
   - 原文链接: https://code.claude.com/docs/en/terminal-config
   - 路径: `md_docs/Claude_Code_Docs:latest/Optimize your terminal setup/docTOC.md`

**总提取行数：** 2,322 行
**文档集合：** Claude_Code_Docs:latest
**提取日期：** 2025-01-18
