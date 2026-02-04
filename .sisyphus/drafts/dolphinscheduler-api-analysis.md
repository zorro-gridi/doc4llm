# DolphinScheduler API 文档处理问题分析

## 问题现状

### 问题1：docToc.md 标题层次不对

当前 docToc.md 使用**扁平序号**结构：
```
## 3. Engine
## 4. Engine._get_attr()
## 5. Engine._set_deps()
...
## 36. Task
## 37. Task._get_attr()
...
```

**问题**：所有项目都是同级 `##`，没有体现自然的层级关系。

### 问题2：docContent.md 与 docToc.md 标题不匹配

**docTOC.md 中的标题**:
```
"Engine._get_attr()"
"Task.add_in()"
"Workflow.run()"
```

**docContent.md 中的标题**:
```
## _class _pydolphinscheduler.core.Engine(_name : str_, _task_type : str_, ...
## _get_attr() → set[str]
## _set_deps(_tasks : Task | Sequence[Task]_, _upstream : bool = True_) → None
```

**格式差异**：
1. docContent 标题包含完整路径 `pydolphinscheduler.core.Engine`
2. docContent 方法标题没有类名前缀
3. docContent 使用 RST/Sphinx 特殊格式 `[[source]]`, `→`, `` 等

## 根本原因

### 1. 爬虫未识别 API 文档的层级结构

Sphinx 生成的 API 文档有**固有层级**：
```
一级：模块 (Core, Models, Tasks)
二级：类 (Engine, Task, Workflow, Base...)
三级：方法和属性 (_get_attr(), add_in(), timeout...)
```

但爬虫将其全部提取为**同级标题**。

### 2. 标题格式转换逻辑缺失

- docToc.md 提取的是**语义化标题**：`"Engine._get_attr()"`
- docContent.md 保存的是**原始 HTML 标题**：`"## _get_attr() → set[str]"`

两者格式不兼容，导致 doc_reader_api.py 无法关联。

## 解决方案设计

### 方案A：优化 docContent.md 标题格式（推荐）

修改爬虫，使其在 docContent.md 中使用与 docTOC.md 一致的标题格式：

```markdown
# API

## Core

### Engine

#### Engine._get_attr()

Get final task task_params attribute.

Base on _task_default_attr, append attribute from _task_custom_attr...

#### Engine._set_deps()

Set parameter tasks dependent to current task.

...

### Task

#### Task._get_attr()
...
```

**优点**：
- docToc 和 docContent 标题完全对应
- doc_reader_api.py 无需修改即可工作
- 层级结构清晰

**需要修改的模块**：
1. `DocContentCrawler._convert_to_markdown()` - 生成层级标题
2. `DocUrlCrawler` - 提取时识别层级
3. 新增 `ApiDocTitleFormatter` 类 - 专门处理 API 文档标题

### 方案B：优化 docToc.md 标题格式

保持 docContent.md 不变，但修改 docToc.md 使其与 docContent.md 格式对齐：

```markdown
## _class _pydolphinscheduler.core.Engine...
### _get_attr() → set[str]
### _set_deps(_tasks : Task...
```

**优点**：
- 保留原始文档格式

**缺点**：
- doc_reader_api.py 仍需修改
- 标题可读性差

### 方案C：修改 doc_reader_api.py 的匹配逻辑

在 doc_reader_api.py 中添加智能标题匹配：
- 提取 docTOC.md 中的方法名（去除类名前缀）
- 在 docContent.md 中查找匹配的方法标题
- 支持模糊匹配

**优点**：
- 爬虫无需修改

**缺点**：
- 增加复杂度
- 可能出现匹配错误
- 性能较差

## 推荐方案：方案A 详解

### 核心思路

1. **爬虫端**（DocContentCrawler）：
   - 检测 Sphinx/API 文档特征
   - 识别文档层级结构
   - 生成层级化的 Markdown 标题

2. **TOC 提取端**（DocUrlCrawler）：
   - 使用相同层级识别逻辑
   - 生成对应的目录结构

3. **一致性保证**：
   - 两个模块使用相同的 `ApiDocTitleFormatter`
   - 确保标题格式 100% 对应

### 实现架构

```
┌─────────────────────────────────────────────────────────┐
│              ApiDocTitleFormatter                        │
│  ┌─────────────────────────────────────────────────────┐│
│  │ detect_doc_type() - 识别 Sphinx/API 文档            ││
│  │ parse_hierarchy() - 解析层级结构                    ││
│  │ format_toc_title() - 格式化 TOC 标题                ││
│  │ format_content_title() - 格式化内容标题             ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│DocUrlCrawler │  │DocContentCrawler│  │doc_reader_api│
│  (Mode 2)    │  │  (Mode 1)     │  │   (无需修改)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 关键代码设计

```python
class ApiDocTitleFormatter:
    """专门处理 Sphinx/API 文档标题格式化"""

    # API 文档特征
    API_DOC_PATTERNS = [
        r'^_\w+_\.(core|models|tasks)\.\w+',  # _class pydolphinscheduler.core.Engine
        r'^\w+\.\w+_\w+\(\)',                   # Engine._get_attr()
        r'^module-\w+\.\w+',                    # module-pydolphinscheduler.core
    ]

    # 层级定义
    LEVELS = {
        'module': 1,      # ## Core, ## Models, ## Tasks
        'class': 2,       # ### Engine, ### Task
        'member': 3,      # #### Engine._get_attr()
    }

    def parse_anchor_title(self, anchor_text: str) -> dict:
        """解析锚点文本，提取层级和标准化的标题"""
        # 输入: "pydolphinscheduler.core.Engine"
        # 输出: {'level': 'class', 'title': 'Engine', 'full_path': '...'}
    def format_content_title(self, level: str, title: str) -> str:
        """为 docContent.md 生成 Markdown 标题"""
        # ## Core
        # ### Engine
        # #### Engine._get_attr()

    def format_toc_title(self, level: str, title: str, number: str) -> str:
        """为 docTOC.md 生成带序号的标题"""
        # ## 1. Core
        # ### 1.1 Engine
        # #### 1.1.1 Engine._get_attr()
```

## 具体实施步骤

### 步骤1：检测 API 文档类型

在爬虫中添加 API 文档检测逻辑：

```python
def is_api_doc(self, soup: BeautifulSoup) -> bool:
    """检测是否为 API 文档"""
    # 检查常见特征
    return (
        self._has_sphinx_signature(soup) or
        self._has_pydocumenter_signature(soup) or
        self._matches_api_url_pattern(self.url)
    )
```

### 步骤2：解析文档层级结构

```python
def extract_api_hierarchy(self, soup: BeautifulSoup) -> list:
    """
    从 HTML 中提取 API 文档的层级结构
    返回: [{'level': 1, 'anchor': 'module-pydolphinscheduler.core', 'title': 'Core'}, ...]
    """
```

### 步骤3：格式化标题

在 `_convert_to_markdown()` 中：

```python
def _convert_to_markdown_with_hierarchy(self, html: str, url: str) -> str:
    """将 API 文档 HTML 转换为带层级标题的 Markdown"""

    # 1. 解析层级结构
    hierarchy = self._extract_api_hierarchy(soup)

    # 2. 生成 Markdown
    md_lines = []
    for item in hierarchy:
        prefix = '#' * (item['level'] + 1)  # # 用于页面标题
        md_lines.append(f"{prefix} {item['title']}\n")
        md_lines.append(item['content'])  # 方法/属性描述

    return '\n'.join(md_lines)
```

## 配置文件扩展

在 `dolphinscheduler.json` 中添加 API 文档配置：

```json
{
  "api_doc_config": {
    "enabled": true,
    "doc_type": "sphinx",
    "hierarchy": {
      "level_1_selectors": [".section > h2", "##[normalize-space(text())='Core']"],
      "level_2_selectors": [".py.class > h3", "##[contains(text(), '.Engine')]"],
      "level_3_selectors": [".py.method", "##[contains(., '()')]"]
    },
    "title_cleaning": {
      "remove_prefixes": ["pydolphinscheduler.core.", "pydolphinscheduler.tasks."],
      "remove_suffixes": ["[[source]]", "→", "", "()"],
      "extract_pattern": "(\\w+\\.\\w+(?:\\.\\w+)?)"
    }
  }
}
```

## 预期效果

### 优化后的 docTOC.md

```markdown
# API

## 1. Core
### 1.1 Engine
#### 1.1.1 Engine
##### 1.1.1.1 Engine._get_attr()
##### 1.1.1.2 Engine._set_deps()
#### 1.2 Task
##### 1.2.1 Task._get_attr()
##### 1.2.2 Task.add_in()
### 1.3 Workflow

## 2. Models
### 2.1 Base
### 2.2 Project
```

### 优化后的 docContent.md

```markdown
# API

## Core

### Engine

#### Engine

Task engine object, declare behavior for engine task to dolphinscheduler.

This is the parent class of spark, flink and mr tasks...

#### Engine._get_attr()

Get final task task_params attribute.

Base on _task_default_attr, append attribute...

#### Engine._set_deps()

Set parameter tasks dependent to current task.
```

### doc_reader_api.py 调用示例

```python
reader = DocReaderAPI(base_dir="/md_docs_base")

# 现在可以正确匹配
result = reader.extract_multi_by_headings(sections=[
    {
        "title": "API",
        "headings": ["Engine", "Engine._get_attr()", "Task"],
        "doc_set": "DolpinScheduler_Docs@latest"
    }
])

# result.contents["API::Engine._get_attr()"] 正确返回对应内容
```

## 验证方法

1. 运行爬虫处理 DolphinScheduler API 文档
2. 检查生成的 docTOC.md 和 docContent.md
3. 使用 doc_reader_api.py 提取指定章节
4. 验证提取的内容与预期一致
