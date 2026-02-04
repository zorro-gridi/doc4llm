# API 文档锚点标题注入方案

## 问题背景

### 现状分析

**Sphinx autodoc 生成的 API 页面结构**（如 dolphinscheduler api.html）:

```html
<!-- 只有锚点 ID，没有标题 -->
<dt id="pydolphinscheduler.core.Engine">
  <span class="sig-name">Engine</span>
</dt>
<dd>
  <p>Class docstring here...</p>
</dd>

<dt id="pydolphinscheduler.core.Engine._get_attr">
  <span class="sig-name">_get_attr() → set[str]</span>
</dt>
<dd>
  <p>Method docstring here...</p>
</dd>
```

**当前 `docContent.md` 转换结果**:

```markdown
# API

## API

[锚点注释]

<p>Class docstring here...</p>

[锚点注释]

<p>Method docstring here...</p>
```

**期望的 `docContent.md` 格式**:

```markdown
# API

## API

### Engine           # 类级别标题
Class docstring here...

#### Engine._get_attr()  # 方法级别标题
Method docstring here...
```

**docTOC.md 格式**（已正确提取）:

```markdown
## 1. pydolphinscheduler.core
### 1.1. pydolphinscheduler.core.Engine
#### 1.1.1. Engine._get_attr()
```

### 核心问题

`doc_reader_api.py` 依赖 `extract_section_by_title()` 按标题提取文档片段：
- 输入：从 docTOC.md 获取的标题（如 `Engine._get_attr()`）
- 期望：在 docContent.md 中找到对应的 `#### Engine._get_attr()` 标题
- 实际：docContent.md 中没有这个标题 → 提取失败

---

## 解决方案

### 方案概述

在 `DocContentCrawler._convert_to_markdown()` 中新增 `_inject_api_anchor_headings()` 方法：

```
流程：
HTML → BeautifulSoup 解析 → 识别 API 锚点 → 解析命名空间 → 注入 Markdown 标题 → 输出
```

### 实现设计

#### 1. 自动检测 Sphinx autodoc 页面

```python
def _is_sphinx_autodoc_page(self, soup: BeautifulSoup) -> bool:
    """
    检测是否为 Sphinx autodoc 生成的 API 文档页面
    
    特征检测：
    1. 存在 dt[id] 或 dl[id] 元素（类/方法定义）
    2. id 符合 Python 命名空间格式
    3. 存在 .sig 或 .sig-name 类名（Sphinx 签名样式）
    """
```

**检测特征**:
| 特征 | 说明 |
|------|------|
| `dt[id*="."]` | 描述列表项包含点（命名空间特征） |
| `.sig-name` | Sphinx 生成的签名样式类 |
| `dl.python` | Python 描述列表 |
| `py-method`, `py-class` | Sphinx 特定 class |

#### 2. 解析 Python 命名空间

```python
def _parse_python_namespace(self, anchor_id: str) -> dict:
    """
    解析锚点 ID 中的 Python 命名空间
    
    输入: "pydolphinscheduler.core.Engine._get_attr"
    输出: {
        "module": "pydolphinscheduler.core",
        "class": "Engine",
        "method": "_get_attr",
        "level": 3  # 命名空间层级
    }
    
    层级映射:
    - level 1: 简单 id（如 "Engine"）
    - level 2: module.Class（如 "core.Engine"）
    - level 3: module.Class.method（如 "core.Engine._get_attr"）
    - level 4: 完整命名空间（如 "pydolphinscheduler.core.Engine._get_attr"）
    """
```

#### 3. 注入 Markdown 标题

```python
def _inject_api_anchor_headings(
    self, 
    html_content: str, 
    soup: BeautifulSoup,
    base_url: str
) -> str:
    """
    为 API 元素注入 Markdown 标题
    
    标题格式:
    - 类: ### ClassName
    - 方法: #### ClassName.method()
    - 属性: #### ClassName.attr
    
    注入位置:
    - 标题注入到 <dd> 元素之前（方法/属性）
    - 或 <dt> 元素之前（类定义）
    """
```

#### 4. 配置增强

在 `dolphinscheduler.json` 中添加 API 文档配置：

```json
{
  "content_filter": {
    "api_doc_mode": "auto",      // auto | enabled | disabled
    "api_anchor_selectors": [    // API 锚点选择器
      "dt[id]",
      "section[id]",
      ".py-class > dt[id]",
      ".py-method > dt[id]"
    ],
    "api_title_patterns": {      // 标题格式模式
      "class": "### {class_name}",
      "method": "#### {class_name}.{method_name}",
      "property": "#### {class_name}.{property_name}"
    }
  }
}
```

---

## 详细实现

### 文件修改

**`doc4llm/crawler/DocContentCrawler.py`**

新增方法：

```python
class DocContentCrawler:
    # 现有方法...
    
    # 新增：API 文档处理
    def _convert_to_markdown(self, html_content: str, url: str, page_title: str) -> str:
        # 现有逻辑...
        
        # 新增：API 锚点标题注入
        markdown_content = self._inject_api_anchor_headings(
            markdown_content, soup, url
        )
        
        return header + markdown_content
    
    def _is_sphinx_autodoc_page(self, soup: BeautifulSoup) -> bool:
        """检测是否为 Sphinx autodoc 页面"""
        pass
    
    def _inject_api_anchor_headings(
        self, 
        markdown_content: str, 
        soup: BeautifulSoup,
        base_url: str
    ) -> str:
        """为 API 元素注入 Markdown 标题"""
        pass
    
    def _parse_python_namespace(self, anchor_id: str) -> dict:
        """解析 Python 命名空间"""
        pass
    
    def _format_api_heading(self, namespace_info: dict) -> str:
        """格式化 API 标题"""
        pass
```

---

## 验收标准

### 测试用例

**测试 1: 基本类名识别**

```html
<dt id="Engine">
  <span class="sig-name">Engine</span>
</dt>
```

**预期输出**:
```markdown
### Engine
```

**测试 2: 完整命名空间**

```html
<dt id="pydolphinscheduler.core.Engine._get_attr">
  <span class="sig-name">_get_attr() → set[str]</span>
</dt>
```

**预期输出**:
```markdown
#### Engine._get_attr()
```

**测试 3: 嵌套方法**

```html
<dt id="pydolphinscheduler.tasks.Condition.add_in">
  <span class="sig-name">add_in(...)</span>
</dt>
```

**预期输出**:
```markdown
#### Condition.add_in(...)
```

---

## 影响范围

### 修改文件

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `DocContentCrawler.py` | 修改 | 新增 API 锚点注入方法 |
| `config.json` | 新增配置 | API 文档模式配置项 |

### 兼容考虑

- **向后兼容**: 默认 `api_doc_mode: "auto"`，不影响现有功能
- **自动检测**: 只对 Sphinx autodoc 页面生效
- **可配置**: 用户可通过配置启用/禁用

---

## 执行计划

1. **实现检测逻辑** `_is_sphinx_autodoc_page()`
2. **实现解析逻辑** `_parse_python_namespace()`
3. **实现注入逻辑** `_inject_api_anchor_headings()`
4. **配置集成** 添加 API 文档配置项
5. **测试验证** 验证 dolphinscheduler 文档

---

## 相关模块

| 模块 | 作用 |
|------|------|
| `DocContentCrawler.py` | 文档内容爬取（修改点） |
| `doc_reader_api.py` | 文档读取 API（使用方） |
| `dolphinscheduler.json` | 配置示例 |
