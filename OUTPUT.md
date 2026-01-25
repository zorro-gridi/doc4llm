# OpenCode 技能创建指南

## 1. 技能文件结构与位置

技能文件需要放置在特定目录结构中。OpenCode 会搜索以下位置来发现技能：

### 项目级配置路径
- `.opencode/skills/<技能名称>/SKILL.md`
- `.claude/skills/<技能名称>/SKILL.md`

### 全局配置路径
- `~/.config/opencode/skills/<技能名称>/SKILL.md`
- `~/.claude/skills/<技能名称>/SKILL.md`

### 搜索机制
OpenCode 会在以下情况下发现技能：

1. **项目本地路径**：从当前工作目录向上遍历直到 git 工作树根目录
2. **全局定义**：从 `~/.config/opencode/skills/` 和 `~/.claude/skills/` 加载
3. **Claude 兼容性**：同时支持 `.claude/skills/` 路径以保持与 Claude 生态兼容

**文件结构示例：**
```
project/
├── .opencode/
│   └── skills/
│       └── git-release/
│           └── SKILL.md
└── .claude/
    └── skills/
        └── my-custom-skill/
            └── SKILL.md
```

## 2. SKILL.md 文件格式与前置元数据要求

每个技能必须包含 YAML 前置元数据（frontmatter），这是 OpenCode 识别和加载技能的关键。

### 必需字段

**name（必需）**
- 类型：字符串
- 长度：1-64 字符
- 格式：小写字母数字，允许单连字符分隔
- 规则：不能以连字符开头或结尾，不能包含连续 `--`
- 正则表达式：`^[a-z0-9]+(-[a-z0-9]+)*$`
- 必须与包含 `SKILL.md` 的目录名称一致

**description（必需）**
- 类型：字符串
- 长度：1-1024 字符
- 用途：帮助 Agent 选择正确的技能
- 建议：保持足够具体，使 Agent 能够正确区分不同技能

### 可选字段

**license**
- 类型：字符串
- 用途：指定技能的许可证类型

**compatibility**
- 类型：字符串
- 用途：指定技能的兼容性要求

**metadata**
- 类型：字符串到字符串的映射
- 用途：存储自定义元数据
- 示例：
  ```yaml
  metadata:
    audience: maintainers
    workflow: github
  ```

### 前置元数据示例

```yaml
---
name: git-release
description: Create consistent releases and changelogs
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: github
---
```

### 未知字段处理
OpenCode 会忽略未知的前置元数字段，因此可以安全地添加额外信息。

## 3. 技能配置选项详解

### 技能元数据配置

**name 配置规则**
- ✅ 有效示例：`git-release`、`my-skill`、`doc-helper-v2`
- ❌ 无效示例：`Git-Release`（大写）、`my--skill`（连续连字符）、`-myskill`（以连字符开头）

**description 最佳实践**
- 提供足够信息帮助 Agent 理解技能用途
- 避免过于笼统的描述
- 明确技能的使用场景和限制

### 技能调用配置

OpenCode 通过 `skill` 工具加载技能。Agent 可以看到可用技能列表，并在需要时加载完整内容：

```xml
<available_skills>
  <skill>
    <name>git-release</name>
    <description>Create consistent releases and changelogs</description>
  </skill>
</available_skills>
```

加载技能的方式：
```json
skill({ name: "git-release" })
```

### 权限控制配置

在 `opencode.json` 中可以控制技能的访问权限：

```json
{
  "permission": {
    "skill": {
      "*": "allow",
      "pr-review": "allow",
      "internal-*": "deny",
      "experimental-*": "ask"
    }
  }
}
```

**权限级别说明**

| 权限 | 行为 |
|------|------|
| `allow` | 技能立即加载 |
| `deny` | 技能对 Agent 隐藏，访问被拒绝 |
| `ask` | 加载前需要用户批准 |

**通配符支持**
- `internal-*` 匹配 `internal-docs`、`internal-tools` 等
- `experimental-*` 匹配所有以 `experimental-` 开头的技能

### 按 Agent 覆盖配置

**自定义 Agent 配置**（在 Agent 前置元数据中）：
```yaml
---
permission:
  skill:
    "documents-*": "allow"
---
```

**内置 Agent 配置**（在 `opencode.json` 中）：
```json
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

### 禁用技能工具

**禁用自定义 Agent 的技能工具：**
```yaml
---
tools:
  skill: false
---
```

**禁用内置 Agent 的技能工具：**
```json
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

禁用后，`<available_skills>` 部分将完全省略。

## 4. 技能创建完整示例

### 示例 1：Git 发布技能

创建文件：`.opencode/skills/git-release/SKILL.md`

```yaml
---
name: git-release
description: Create consistent releases and changelogs
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: github
---

## What I do

- Draft release notes from merged PRs
- Propose a version bump
- Provide a copy-pasteable `gh release create` command

## When to use me

Use this when you are preparing a tagged release.
Ask clarifying questions if the target versioning scheme is unclear.
```

### 示例 2：文档查询优化技能

创建文件：`.opencode/skills/md-doc-query-optimizer/SKILL.md`

```yaml
---
name: md-doc-query-optimizer
description: "Pure LLM prompt-based skill. Optimize and rewrite user queries for better document retrieval. Supports query decomposition, expansion, synonym replacement, and multi-query generation. Returns optimized queries for document search."
---

# Markdown Document Query Optimizer

Optimize user queries to improve document retrieval quality in the doc4llm system through pure prompt-based analysis and transformation.

## Purpose

Improve search relevance by:

- Detecting target documentation sets from local knowledge base
- Decomposing complex queries into simpler sub-queries
- Expanding queries with synonyms and related terms
- Generating multiple query variations for broader coverage
- Translating non-English queries to documentation language
```

## 5. 技能故障排除

如果技能没有显示在可用技能列表中，请按以下步骤排查：

1. **验证文件名**：确保文件名为 `SKILL.md`（全大写）
2. **检查前置元数据**：确认包含 `name` 和 `description` 字段
3. **确保技能名称唯一**：检查所有位置的技能名称是否重复
4. **检查权限设置**：带有 `deny` 权限的技能对 Agent 隐藏

## 6. 最佳实践建议

### 命名规范
- 使用描述性名称，准确反映技能功能
- 遵循 kebab-case 格式（小写字母和连字符）
- 避免使用过于通用的名称

### 描述撰写
- 清晰说明技能的主要功能
- 指定适用的使用场景
- 包含任何重要的限制或前提条件

### 文件组织
- 每个技能放在独立目录中
- 目录名称必须与 `name` 字段完全匹配
- 考虑使用全局路径来共享常用技能

### 权限配置
- 默认使用 `ask` 权限以确保安全
- 对可信技能使用 `allow`
- 使用通配符简化批量配置

---

### 文档来源 (Sources)

1. **Agent Skills**
   - 原文链接: https://opencode.ai/docs/skills
   - 路径: `/Users/zorro/project/md_docs_base/OpenCode_Docs@latest/Agent Skills/docContent.md`

2. **Tools**
   - 原文链接: https://opencode.ai/docs/tools
   - 路径: `/Users/zorro/project/md_docs_base/OpenCode_Docs@latest/Tools/docContent.md`

3. **Real Skill Examples from Repository**
   - 路径: `/Users/zorro/project/doc4llm/.opencode/skills/md-doc-query-optimizer/SKILL.md`
   - 路径: `/Users/zorro/project/doc4llm/.opencode/skills/md-doc-searcher/SKILL.md`
