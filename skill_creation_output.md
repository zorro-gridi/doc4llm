=== AOP-FINAL | agent=doc-retriever | format=markdown | lines=479 | source=OpenCode_Docs@latest ===

# OpenCode 技能创建完整指南

基于从 OpenCode 文档库中检索的信息，以下是创建技能的完整规范、目录结构、最佳实践和模板参考。

---

## 1. 技能 (Skills) 概述

在 OpenCode 中，**技能 (Skills)** 是通过 `SKILL.md` 文件定义的可加载模块。技能与插件 (Plugins) 和自定义工具 (Custom Tools) 有本质区别：

| 组件类型 | 技术栈 | 用途 | 配置文件 |
|---------|--------|------|----------|
| **Skills** | Markdown (SKILL.md) | 文档和知识库加载 | opencode.json (permission) |
| **Plugins** | JavaScript/TypeScript | 事件钩子和功能扩展 | .opencode/plugins/*.js/*.ts |
| **Custom Tools** | 任意语言 (Python, etc.) | 自定义命令执行 | .opencode/tools/*.py |

**核心概念：**
- 技能是**只读的知识模块**，用于向 AI 提供特定领域的专业知识和指令
- 技能通过 `skill` 工具加载到对话中
- 技能文件使用 Markdown 格式，包含前端matter元数据

---

## 2. 技能目录结构

```
.opencode/
├── skills/                          # 技能目录
│   ├── skill-name/
│   │   ├── SKILL.md                 # 必需：技能定义文件
│   │   ├── scripts/                 # 可选：脚本目录
│   │   │   ├── script1.py
│   │   │   └── script2.sh
│   │   └── assets/                  # 可选：资源目录
│   │       ├── image1.png
│   │       └── template.json
│   └── another-skill/
│       ├── SKILL.md
│       └── scripts/
└── opencode.json                    # 权限配置
```

**必需文件：**
- ✅ `SKILL.md` - 技能定义主文件（必需）
- ❌ `scripts/` - 目录（可选，但目录内文件必需）
- ❌ `assets/` - 目录（可选）

---

## 3. SKILL.md 前端matter格式

每个技能必须包含 YAML 前端matter，定义技能的元数据。以下是必需字段和推荐字段：

### 必需字段

```yaml
---
name: skill-name                    # 技能名称（小写字母，用连字符）
description: "简短描述"              # 技能用途说明
disable-model-invocation: true/false # 是否禁用自动调用
---
```

### 完整前端matter模板

```yaml
---
name: my-custom-skill               # 技能标识符
description: "提供 XXX 领域的专业能力和知识库"  # 描述（英文或目标语言）
disable-model-invocation: true      # 通常设为 true，避免自动触发
---

# 技能标题

> 技能详细说明和用途介绍

## 功能特性

- 特性1说明
- 特性2说明

## 使用方法

```
使用方法说明
```

## 示例

```代码示例
```
```

### 字段说明

| 字段 | 必需 | 说明 | 示例 |
|------|------|------|------|
| `name` | ✅ | 技能标识符（小写+连字符） | `my-custom-skill` |
| `description` | ✅ | 技能用途描述 | `"提供数据分析能力"` |
| `disable-model-invocation` | ✅ | 是否禁用自动调用 | `true` 或 `false` |

---

## 4. opencode.json 权限配置

使用技能需要在 `opencode.json` 中配置相应权限：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "skill": "allow"                // 必需：允许使用技能
  }
}
```

**权限配置规则：**
- 技能使用需要 `skill: "allow"` 权限
- 权限配置文件位于项目根目录的 `.opencode/opencode.json`

---

## 5. 现有技能模板参考

OpenCode 文档库中包含多个可参考的技能实现模式：

### 模板1：基础工具技能 (Tools)

**参考文档：** `Tools::3.10. skill`

```markdown
### skill

Load a [skill](https://opencode.ai/docs/skills) (a `SKILL.md` file) and return its content in the conversation.

opencode.json
    
{
  
  "$schema": "https://opencode.ai/config.json",
  
  "permission": {
  
    "skill": "allow"
  
  }
  
}
```

**特点：** 简单技能定义，专注单一功能（加载其他技能）

### 模板2：插件开发模式 (Plugins)

**参考文档：** `Plugins::3. Create a plugin` 和 `Plugins::4. Examples`

虽然插件不同于技能，但插件的开发模式可作为技能扩展的参考：

**基础插件结构：**
```javascript
// .opencode/plugins/example.js
export const MyPlugin = async ({ project, client, $, directory, worktree }) => {
  console.log("Plugin initialized!")
  
  return {
    // Hook implementations go here
  }
}
```

**插件功能：**
- 事件订阅系统
- 工具执行前后钩子
- 文件操作钩子
- 自定义工具定义
- 日志记录
- 会话压缩钩子

### 模板3：自定义工具模式 (Custom Tools)

**参考文档：** `Custom Tools::3. Examples`

**Python 工具示例：**
```python
# .opencode/tools/add.py
import sys

a = int(sys.argv[1])
b = int(sys.argv[2])
print(a + b)
```

```typescript
// .opencode/tools/python-add.ts
import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "Add two numbers using Python",
  args: {
    a: tool.schema.number().describe("First number"),
    b: tool.schema.number().describe("Second number"),
  },
  async execute(args) {
    const result = await Bun.$`python3 .opencode/tools/add.py ${args.a} ${args.b}`.text()
    return result.trim()
  },
})
```

**特点：** 支持多语言实现，通过 TypeScript 包装器暴露给 OpenCode

---

## 6. 技能创建最佳实践

### 6.1 设计原则

1. **单一职责：** 每个技能专注于一个领域
2. **清晰命名：** 使用描述性的技能名称（小写+连字符）
3. **完整文档：** 提供详细的使用说明和示例
4. **版本控制：** 在技能名称中包含版本号（如 `skill-name@v1.0`）

### 6.2 目录结构最佳实践

```
skill-name/
├── SKILL.md              # 主文件（必需）
├── README.md             # 详细文档（推荐）
├── scripts/              # 支撑脚本
│   ├── main.py
│   └── utils.sh
├── examples/             # 使用示例
│   └── example1.md
├── tests/                # 测试文件
│   └── test_skill.py
└── config/               # 配置文件
    └── settings.json
```

### 6.3 前端matter最佳实践

```yaml
---
name: domain-specific-skill        # 清晰的命名
description: "提供 XXX 领域的专业知识和操作能力"  # 明确的用途描述
disable-model-invocation: true     # 避免意外自动调用
---

# 技能名称

> 一句话概括技能的核心价值

## 概述

详细说明技能的用途、适用场景和使用前提

## 核心功能

### 功能1
说明和示例

### 功能2
说明和示例

## 使用方法

### 前置条件
列出使用该技能的前置条件

### 快速开始
提供最简单的使用示例

### 高级用法
提供复杂场景的使用示例

## 注意事项

列出使用中的注意事项和限制

## 相关资源

- 相关文档链接
- 示例项目链接
```

### 6.4 技能 vs 插件 vs 自定义工具的选择指南

| 需求 | 推荐选择 | 原因 |
|------|----------|------|
| 提供领域知识/文档 | **Skills** | 专为知识加载设计，支持 Markdown 格式 |
| 扩展运行时功能 | **Plugins** | 支持事件钩子，可拦截和修改运行时行为 |
| 执行外部命令 | **Custom Tools** | 支持任意语言，可调用系统命令 |
| 组合多种功能 | **Plugins + Tools** | 插件提供钩子，工具提供执行能力 |

---

## 7. 技能使用示例

### 7.1 在对话中加载技能

通过 `skill` 工具加载技能到当前对话：

```
Use the skill: my-custom-skill
```

### 7.2 技能配置示例

**完整 opencode.json 配置：**
```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "skill": "allow"
  }
}
```

---

## 8. 总结

创建 OpenCode 技能的核心要点：

1. **必需文件：** `SKILL.md`（带必需的前端matter）
2. **目录结构：** `skills/skill-name/SKILL.md`
3. **前端matter：** 必需包含 `name`、`description`、`disable-model-invocation`
4. **权限配置：** 在 `opencode.json` 中配置 `skill: "allow"`
5. **参考模板：** 从 Tools、Plugins、Custom Tools 章节获取实现灵感
6. **最佳实践：** 单一职责、清晰命名、完整文档

**重要提示：** 技能是只读的知识模块，如需运行时功能扩展，请使用插件系统。

---

### 文档来源 (Sources)

1. **Agent Skills**
   - 原文链接: https://opencode.ai/docs/skills
   - 路径: `md_docs_base/OpenCode_Docs@latest/Agent Skills/docContent.md`

2. **Tools**
   - 原文链接: https://opencode.ai/docs/tools
   - 路径: `md_docs_base/OpenCode_Docs@latest/Tools/docTOC.md`

3. **Plugins**
   - 原文链接: https://opencode.ai/docs/plugins
   - 路径: `md_docs_base/OpenCode_Docs@latest/Plugins/docTOC.md`

4. **Custom Tools**
   - 原文链接: https://opencode.ai/docs/custom-tools
   - 路径: `md_docs_base/OpenCode_Docs@latest/Custom Tools/docTOC.md`

=== END-AOP-FINAL ===
