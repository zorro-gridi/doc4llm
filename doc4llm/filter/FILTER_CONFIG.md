# 内容过滤器配置文档
# Content Filter Configuration Guide

本文档详细说明 doc4llm 内容过滤器的配置选项和使用方法。

---

## 目录

- [概述](#概述)
- [配置结构](#配置结构)
- [选择器类型说明](#选择器类型说明)
- [config.json 配置](#configjson-配置)
- [文档框架预设](#文档框架预设)
- [编程配置](#编程配置)

---

## 概述

内容过滤器负责从网页中提取正文内容，移除导航栏、侧边栏、页脚等非正文元素。过滤器使用 CSS 选择器来识别和移除这些元素。

### 两种合并模式

1. **extend（扩展模式，默认）**：保留默认选择器，并将自定义选择器追加到列表中
2. **replace（替换模式）**：完全使用自定义选择器，忽略默认选择器

---

## 配置结构

### 核心配置项

| 配置项 | 类型 | 描述 |
|--------|------|------|
| `non_content_selectors` | `List[str]` | 非正文内容的 CSS 选择器列表 |
| `fuzzy_keywords` | `List[str]` | 用于模糊匹配 class/id 的关键词列表 |
| `log_levels` | `List[str]` | 日志级别正则表达式列表 |
| `meaningless_content` | `List[str]` | 需要移除的无意义文本列表 |
| `content_end_markers` | `List[str]` | 标记正文结束的正则表达式 |
| `content_preserve_selectors` | `List[str]` | 需要优先保留的正文内容选择器 |
| `code_container_selectors` | `List[str]` | 代码块容器选择器 |

---

## 选择器类型说明

### 1. 语义化选择器（SEMANTIC_NON_CONTENT_SELECTORS）

高置信度非正文内容选择器，基于 HTML5 语义化标签和 ARIA 角色：

```python
SEMANTIC_NON_CONTENT_SELECTORS = [
    'aside',      # 侧边栏
    'nav',        # 导航菜单
    'footer',     # 页脚
    'header',     # 页头
    '[role="navigation"]',
    '[role="banner"]',
    '[role="complementary"]',
]
```

### 2. 通用选择器（GENERAL_NON_CONTENT_SELECTORS）

基于常见命名规范的 CSS 选择器，适用于大多数网站：

```python
GENERAL_NON_CONTENT_SELECTORS = [
    # Sidebar 相关
    '.sidebar', '.side-bar', '[class*="sidebar"]',

    # 导航相关
    '.nav', '.navigation', '.navbar',
    '[class*="navigation"]', '[class*="menu"]',

    # TOC（目录）
    '.toc', '.table-of-contents', '[class*="toc"]',

    # 页脚
    '.footer', '[class*="footer"]',

    # 广告和弹窗
    '.ad', '.popup', '.modal', '.banner',

    # 分页导航
    '.pagination', '.prev', '.next',
]
```

### 3. 模糊匹配关键词（FUZZY_KEYWORDS）

用于匹配 class 或 id 属性中包含特定关键词的元素：

```python
FUZZY_KEYWORDS = [
    'sidebar', 'navigation', 'navbar', 'menu', 'modal',
    'cookie', 'notification', 'popup', 'tooltip',
    'pagination', 'breadcrumb', 'footer', 'header',
]
```

### 4. 内容保留选择器（CONTENT_PRESERVE_SELECTORS）

标记需要优先保留的正文内容：

```python
CONTENT_PRESERVE_SELECTORS = [
    'article',
    'main',
    '[role="main"]',
    '.content',
    '.post-content',
    '.markdown-body',
]
```

### 5. 日志级别标识（LOG_LEVELS）

用于识别和过滤代码块中的日志输出：

```python
LOG_LEVELS = [
    r'INFO:', r'info:', r'Info:',
    r'DEBUG:', r'debug:', r'Debug:',
    r'WARNING:', r'warning:', r'Warning:',
    r'ERROR:', r'error:', r'Error:',
    r'CRITICAL:', r'critical:', r'Critical:',
]
```

---

## config.json 配置

在项目根目录的 `config.json` 文件中添加 `content_filter` 配置段：

```json
{
  "start_url": "https://example.com",
  "max_workers": 30,

  "content_filter": {
    "merge_mode": "extend",

    "non_content_selectors": [
      ".custom-sidebar",
      "[class*=\"custom-nav\"]",
      ".special-ad"
    ],

    "fuzzy_keywords": [
      "custommenu",
      "specialpopup"
    ],

    "log_levels": [
      r"TRACE:",
      r"VERBOSE:"
    ],

    "meaningless_content": [
      "Custom skip text",
      "Special back to top"
    ]
  }
}
```

### 配置字段说明

| 字段 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `merge_mode` | `string` | `"extend"` | 合并模式：`extend` 或 `replace` |
| `documentation_preset` | `string` | `null` | 文档框架预设：`null`/`mintlify`/`docusaurus`/`vitepress`/`gitbook` |
| `non_content_selectors` | `array` | `[]` | 自定义非正文选择器（会扩展默认选择器） |
| `fuzzy_keywords` | `array` | `[]` | 自定义模糊关键词（会扩展默认关键词） |
| `log_levels` | `array` | `[]` | 自定义日志级别（会扩展默认级别） |
| `meaningless_content` | `array` | `[]` | 自定义无意义内容（会扩展默认内容） |
| `content_end_markers` | `array` | `[]` | 自定义内容结束标识（空数组时使用默认值） |
| `content_preserve_selectors` | `array` | `[]` | 自定义内容保留选择器（空数组时使用默认值） |
| `code_container_selectors` | `array` | `[]` | 自定义代码容器选择器（空数组时使用默认值） |

---

## 文档框架预设

过滤器内置了针对常见文档框架的预设配置：

### Mintlify

现代 API 文档站点，常见于技术产品的文档网站。

```python
'mintlify': {
    'content_selectors': ['article', '[class*="markdown"]'],
    'exclude_selectors': ['[class*="sidebar"]', '[class*="mintlify-"]']
}
```

### Docusaurus

Meta 开源的文档平台，广泛用于开源项目文档。

```python
'docusaurus': {
    'content_selectors': ['article', '[class*="docMainContainer"]'],
    'exclude_selectors': ['[class*="sidebar"]', '.menu']
}
```

### VitePress

Vue 驱动的静态网站生成器，用于 Vue 生态文档。

```python
'vitepress': {
    'content_selectors': ['.VPDoc', '[class*="content"]'],
    'exclude_selectors': ['.VPNav', '.VPSidebar', '.VPFooter']
}
```

### GitBook

流行的文档托管平台。

```python
'gitbook': {
    'content_selectors': ['.gitbook-content'],
    'exclude_selectors': ['.gitbook-sidebar', '.gitbook-navigation']
}
```

---

## 编程配置

### 使用配置模块

```python
from filter.config import (
    get_filter_config,
    FilterConfigLoader,
    SEMANTIC_NON_CONTENT_SELECTORS,
    FUZZY_KEYWORDS
)

# 获取默认配置
config = get_filter_config()

# 获取特定预设配置
config = get_filter_config(preset='mintlify')

# 从 config.json 加载配置
import json
with open('config.json', 'r') as f:
    project_config = json.load(f)
config = FilterConfigLoader.load_from_config(project_config, preset='docusaurus')
```

### 使用过滤器工厂

```python
from filter import create_filter_for_url, FilterFactory

# 自动检测并创建合适的过滤器
filter_obj = create_filter_for_url("https://docs.example.com")

# 指定预设创建过滤器
filter_obj = FilterFactory.create(force_preset='mintlify')

# 使用标准过滤器
from filter import ContentFilter
filter_obj = ContentFilter(
    NON_CONTENT_SELECTORS=['.custom-nav'],
    FUZZY_KEYWORDS=['custommenu']
)
```

### 直接实例化增强版过滤器

```python
from filter import EnhancedContentFilter

# 使用默认配置
filter_obj = EnhancedContentFilter()

# 使用预设配置
filter_obj = EnhancedContentFilter(preset='vitepress')

# 使用自定义配置
filter_obj = EnhancedContentFilter(
    non_content_selectors=['.my-sidebar'],
    fuzzy_keywords=['my-menu', 'my-popup'],
    preset='mintlify',
    auto_detect_framework=True
)
```

---

## 配置最佳实践

### 1. 选择器优先级

1. **优先使用语义化标签**：`<nav>`, `<aside>`, `<footer>`
2. **其次使用属性选择器**：`[role="navigation"]`
3. **最后使用类选择器**：`.sidebar`, `.nav`

### 2. 模糊匹配注意事项

模糊匹配会匹配 class 或 id 中包含关键词的元素，可能误删正文内容。建议：

- 在明确知道网站结构时使用精确选择器
- 模糊关键词应选择具有明确语义的词汇
- 避免使用常见词汇（如 `content`, `main`）作为模糊关键词

### 3. 合并模式选择

- **extend（推荐）**：适用于大多数场景，保留默认过滤规则并添加自定义规则
- **replace**：仅在需要完全自定义过滤行为时使用

### 4. 针对特定网站优化

```python
# 针对特定网站的自定义配置
from filter import EnhancedContentFilter

filter_obj = EnhancedContentFilter(
    non_content_selectors=[
        # 添加该网站特有的侧边栏选择器
        '.site-specific-sidebar',
        '[class*="custom-nav"]',
    ],
    fuzzy_keywords=[
        # 添加该网站特有的导航关键词
        'sitemenu',
        'special-nav',
    ]
)
```

---

## 示例场景

### 场景 1：提取技术博客正文

```python
from filter import ContentFilter

# 技术博客通常有简单的结构
filter_obj = ContentFilter()

# 使用过滤器
cleaned_soup = filter_obj.filter_non_content_blocks(soup)
```

### 场景 2：提取 Mintlify 文档

```python
from filter import EnhancedContentFilter

# 使用 Mintlify 预设
filter_obj = EnhancedContentFilter(
    preset='mintlify',
    auto_detect_framework=True
)

cleaned_soup = filter_obj.filter_non_content_blocks(soup)
```

### 场景 3：从配置文件加载

```python
import json
from filter.config import FilterConfigLoader

# 加载项目配置
with open('config.json', 'r') as f:
    config = json.load(f)

# 获取过滤器配置
filter_config = FilterConfigLoader.load_from_config(
    config,
    preset='docusaurus'
)

# 使用配置创建过滤器
from filter import EnhancedContentFilter
filter_obj = EnhancedContentFilter(
    non_content_selectors=filter_config['non_content_selectors'],
    fuzzy_keywords=filter_config['fuzzy_keywords'],
    log_levels=filter_config['log_levels'],
    meaningless_content=filter_config['meaningless_content']
)
```

### 高级配置示例

使用高级配置参数（覆盖默认值）：

```json
{
  "content_filter": {
    "merge_mode": "extend",
    "documentation_preset": "mintlify",
    "non_content_selectors": [".custom-nav"],
    "fuzzy_keywords": ["custommenu"],
    "log_levels": ["TRACE:", "VERBOSE:"],
    "meaningless_content": ["Custom skip text"],
    "content_end_markers": [
      "Next steps",
      "Further reading",
      "See also"
    ],
    "content_preserve_selectors": [
      ".main-content",
      "[class*=\"article-body\"]"
    ],
    "code_container_selectors": [
      "code",
      "pre",
      "[class*=\"highlight\"]"
    ]
  }
}
```

---

## 文档内容后处理模板

### 概述

v2.1.0 版本引入了统一的内容后处理模板 `filter_by_end_markers()`，用于在 Markdown 文档保存之前清除指定分隔符及其后的所有内容。

### 工作原理

1. **纯文本自动转换**：用户只需填写纯文本，系统自动转换为灵活的正则表达式
2. **智能匹配**：支持变长空白字符、Markdown 标题前缀和数字编号
3. **区分大小写**：精确匹配文本大小写（"Next steps" 不会匹配 "next steps"）

### 自动转换规则

| 用户输入 | Markdown 模式 | TOC 模式 |
|----------|---------------|----------|
| `"Next steps"` | `^(##+\s*)?(?:\d+\.\s*)?Next\s+steps` | `^\s*Next\s+steps` |
| `"See also"` | `^(##+\s*)?(?:\d+\.\s*)?See\s+also` | `^\s*See\s+also` |

**转换特性**：
- **空白字符灵活匹配**：`"Next steps"` 可匹配 `"Next  steps"`（多个空格）
- **Markdown 标题前缀**：自动支持 `##`, `###` 等标题符号
- **数字编号支持**：自动支持 `"6. Next steps"` 格式
- **特殊字符转义**：自动转义正则表达式特殊字符（`.`, `*`, `?` 等）
- **区分大小写**：精确匹配，不忽略大小写

### content_end_markers 配置

**作用**：过滤 `DocContentCrawler.py` 生成的 Markdown 文档内容

**默认值**：
```python
CONTENT_END_MARKERS = [
    r"##?\s*\n*\s*Next steps?",
    r"##?\s*\n*\s*Further reading",
    r"##?\s*\n*\s*See also",
    r"##?\s*\n*\s*References",
    r"##?\s*\n*\s*Related",
    r"---+\s*\n*\s*Next steps?",
    r"Was this (page|article|doc) helpful\?",
    r"Did you (find|like) this",
]
```

**配置示例**：
```json
{
  "content_filter": {
    "content_end_markers": [
      "Next steps",
      "Further reading",
      "See also",
      "References"
    ]
  }
}
```

**匹配示例**：
- `"Next steps"` → 匹配 `## Next steps`、`## 6. Next steps：https://...`
- `"Further reading"` → 匹配 `### Further reading`
- `"See also"` → 匹配 `## See also`

### toc_end_markers 配置

**作用**：过滤 `DocUrlCrawler.py` 生成的 TOC markdown 文件中的锚点链接

**配置位置**：`config.json` → `toc_filter` → `toc_end_markers`

**默认值**：
```python
TOC_END_MARKERS = [
    'See also',
    'Related articles',
    'Further reading',
    'External links',
    'References',
    'Related skills',
    'Next steps',
    'Next up'
]
```

**配置示例**：
```json
{
  "toc_filter": {
    "merge_mode": "extend",
    "toc_end_markers": [
      "See also",
      "Related articles",
      "Further reading",
      "Next steps"
    ]
  }
}
```

**匹配示例**：
- `"See also"` → 匹配锚点链接文本为 "See also"
- `"Related articles"` → 匹配锚点链接文本为 "Related articles"
- `"Next steps"` → 匹配锚点链接文本为 "Next steps"

### 大小写敏感性

⚠️ **重要**：匹配是区分大小写的！

| 配置 | 匹配 | 不匹配 |
|------|------|--------|
| `"Next steps"` | `"Next steps"` | `"next steps"`, `"NEXT STEPS"` |
| `"See also"` | `"See also"` | `"see also"`, `"SEE ALSO"` |

如果需要匹配不同大小写的变体，请添加多个配置项：
```json
{
  "content_end_markers": [
    "Next steps",
    "next steps",
    "NEXT STEPS"
  ]
}
```

---

## 常见问题

### Q: 为什么有些内容没有被过滤？

A: 检查以下几点：
1. 确认目标元素的 class/id 是否匹配配置的选择器
2. 使用浏览器开发者工具检查元素的实际属性
3. 考虑添加自定义选择器到配置中

### Q: 为什么正文内容被误删了？

A: 可能的原因：
1. 模糊关键词匹配到了正文元素的 class/id
2. 使用了 `replace` 模式导致必要的选择器被移除
3. 建议：使用 `extend` 模式，并精确配置选择器

### Q: 如何针对新网站配置过滤器？

A: 步骤如下：
1. 使用浏览器访问目标网站
2. 打开开发者工具，检查需要移除的元素
3. 记录这些元素的 class、id 或其他属性
4. 将对应的选择器添加到配置中
5. 测试并调整配置

---

## 技术说明

### HTML 转 Markdown 的标题换行问题

某些 HTML 结构在转换为 Markdown 时，标题符号和文字之间会出现多余的换行符：

```html
<h2>
  Next steps
</h2>
```

可能被转换为：

```markdown
##


Next steps
```

**解决方案**：

1. **自动修复**：`MarkdownConverter` 现在包含后处理功能，自动清理标题中的多余换行符
2. **正则表达式增强**：`content_end_markers` 的默认正则表达式已更新，可以匹配包含换行符的情况

您也可以在 `config.json` 中使用正则表达式来匹配这种情况：

```json
{
  "content_filter": {
    "content_end_markers": [
      "##\\s*\\n*\\s*Next steps?"
    ]
  }
}
```

注意：在 JSON 中需要使用双反斜杠 `\\` 来转义正则表达式中的反斜杠。

---

## 版本历史

### v2.0.0 (2025-01-16) - 内容过滤器重大更新

**核心改进**：

1. **统一配置模块** (`filter/config.py`)
   - 集中管理所有预定义标签列表和配置参数
   - 支持从 `config.json` 加载自定义配置
   - 提供 `merge_selectors()` 和 `get_filter_config()` 工具函数

2. **标准化命名**
   - `SEMANTIC_NON_CONTENT_SELECTORS` - 语义化选择器（高优先级）
   - `GENERAL_NON_CONTENT_SELECTORS` - 通用选择器
   - `FUZZY_KEYWORDS` - 模糊匹配关键词
   - `LOG_LEVELS` - 日志级别
   - `MEANINGLESS_CONTENT` - 无意义内容
   - `CONTENT_PRESERVE_SELECTORS` - 内容保留选择器
   - `CONTENT_END_MARKERS` - 内容结束标识
   - `CODE_CONTAINER_SELECTORS` - 代码容器选择器

3. **两种合并模式**
   - `extend`（默认）：保留默认选择器并追加自定义选择器
   - `replace`：完全使用自定义选择器

4. **HTML 转 Markdown 修复**
   - 清理零宽空格（U+200B）和其他不可见 Unicode 字符
   - 修复标题符号和文字之间的多余换行符
   - 修复标题符号和文字之间的多余空格
   - 压缩连续的空行

5. **`content_end_markers` 配置生效**
   - 修改 `DocContentCrawler` 支持从 `config.json` 加载配置
   - 添加 `filter_content_end_markers()` 调用
   - 正确截断 "Next steps" 等结束标识后的内容

**新增文件**：
- `filter/config.py` - 统一配置模块
- `filter/FILTER_CONFIG.md` - 配置文档

**修改文件**：
- `filter/standard.py` - 使用 extend 模式和统一配置
- `filter/enhanced.py` - 引入统一配置
- `filter/__init__.py` - 导出配置常量和工具类
- `MarkdownConverter.py` - 添加格式清理功能
- `WebContentExtractor.py` - 支持从 config.json 加载配置
- `WebTextCrawler.py` - 支持从 config.json 加载配置
- `DocContentCrawler.py` - 支持从 config.json 加载配置和调用 filter_content_end_markers
- `config.json` - 添加 content_filter 配置段

---

### v1.0.0 (2025-01-16) - 初始版本

- 创建内容过滤器基类和实现
- 支持标准版和增强版过滤器
- 支持文档框架预设（Mintlify、Docusaurus、VitePress、GitBook）
