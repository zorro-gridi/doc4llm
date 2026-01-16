# 内容过滤器兼容性指南

## 概述

项目现在提供了两种内容过滤器实现，它们完全兼容且可以互换使用：

| 过滤器 | 文件 | 用途 |
|--------|------|------|
| `ContentFilter` | `filter/standard.py` | 原始过滤器，适用于传统网站 |
| `EnhancedContentFilter` | `filter/enhanced.py` | 增强版过滤器，支持现代文档站点 |

所有过滤器都继承自 `BaseContentFilter` (`filter/base.py`)，确保了接口的一致性。

## 兼容性保证

### 1. 抽象基类 (`BaseContentFilter`)

两个过滤器都继承自 `filter.base.BaseContentFilter`，确保了接口的一致性：

```python
from filter import BaseContentFilter

class ContentFilter(BaseContentFilter):
    # 原始实现
    pass

class EnhancedContentFilter(BaseContentFilter):
    # 增强实现
    pass
```

### 2. 统一接口

所有过滤器都实现了以下方法：

| 方法 | 说明 | 两者都支持 |
|------|------|-----------|
| `get_page_title(url, soup)` | 获取页面标题 | ✅ |
| `filter_non_content_blocks(soup)` | 过滤非正文内容 | ✅ |
| `filter_logging_outputs(soup)` | 过滤日志输出 | ✅ |
| `remove_meaningless_content(content)` | 移除无意义内容 | ✅ |
| `sanitize_filename(filename)` | 清理文件名 | ✅ |
| `filter_content_end_markers(content)` | 过滤结束标识 | ✅ (默认为空实现) |
| `pre_process_html(soup, url)` | HTML预处理 | ✅ (默认为空实现) |
| `post_process_markdown(content)` | Markdown后处理 | ✅ (默认为空实现) |

### 3. WebContentExtractor 自动适配

`WebContentExtractor` 现在可以接受任何 `BaseContentFilter` 子类：

```python
from filter import ContentFilter, EnhancedContentFilter
from WebContentExtractor import WebContentExtractor

# 方式1: 使用原始过滤器
extractor1 = WebContentExtractor(
    content_filter=ContentFilter()
)

# 方式2: 使用增强版过滤器
extractor2 = WebContentExtractor(
    content_filter=EnhancedContentFilter()
)

# 方式3: 让 WebContentExtractor 自动创建
extractor3 = WebContentExtractor(
    use_enhanced=True  # 自动创建增强版
)
```

## 如何选择合适的过滤器

### 方式 1: 手动选择（明确控制）

```python
from filter import ContentFilter, EnhancedContentFilter
from WebContentExtractor import WebContentExtractor

# 对于传统网站
extractor = WebContentExtractor(
    content_filter=ContentFilter()
)

# 对于现代文档站点（Mintlify, Docusaurus 等）
extractor = WebContentExtractor(
    content_filter=EnhancedContentFilter()
)
```

### 方式 2: 使用参数自动创建（推荐）

```python
from WebContentExtractor import WebContentExtractor

# 默认使用原始过滤器
extractor = WebContentExtractor()

# 使用增强版过滤器（自动检测框架）
extractor = WebContentExtractor(use_enhanced=True)

# 指定文档框架预设
extractor = WebContentExtractor(
    use_enhanced=True,
    doc_preset='mintlify'  # 或 'docusaurus', 'vitepress', 'gitbook'
)
```

### 方式 3: 使用过滤器工厂（智能推荐）

```python
from filter import FilterFactory

# 根据 URL 自动选择最合适的过滤器
filter = FilterFactory.create_for_url("https://code.claude.com/docs/en/skills")

extractor = WebContentExtractor(content_filter=filter)
```

## 工厂模式详解

`filter.factory.FilterFactory` 提供了更智能的过滤器选择：

```python
from filter import FilterFactory, create_filter_for_url

# 方式1: 完全自动检测
filter = FilterFactory.create_for_url(url)

# 方式2: 指定选项
filter = FilterFactory.create(
    url=url,
    use_enhanced=True,
    auto_detect=True
)

# 方式3: 强制使用特定预设
filter = FilterFactory.create(
    force_preset='mintlify'
)
```

### URL 签名检测

工厂会根据 URL 中的特征自动检测文档框架：

| 框架 | URL 签名 |
|------|----------|
| Mintlify | `mintlify.app`, `mintlify.com`, `_mintlify` |
| Docusaurus | `docusaurus.io`, `/docs/` |
| VitePress | `vitepress.dev`, `vitepress` |
| GitBook | `gitbook.io`, `app.gitbook.com` |

## 迁移指南

### 旧代码（仍然兼容）

```python
# 旧的方式仍然有效
from filter import ContentFilter
from WebContentExtractor import WebContentExtractor

filter = ContentFilter()
extractor = WebContentExtractor(filter)
```

### 新代码（推荐）

```python
# 新的方式更简洁
from WebContentExtractor import WebContentExtractor

# 方式1: 默认（原始过滤器）
extractor = WebContentExtractor()

# 方式2: 增强版（自动检测）
extractor = WebContentExtractor(use_enhanced=True)
```

## 向后兼容性

| 方面 | 兼容性 |
|------|--------|
| 旧的 `ContentFilter` 用法 | ✅ 完全兼容 |
| 新的 `EnhancedContentFilter` | ✅ 可选使用 |
| `WebContentExtractor` API | ✅ 向后兼容，参数有默认值 |
| 自定义过滤器 | ✅ 继承 `BaseContentFilter` 即可 |

## 最佳实践

1. **对于新代码**：推荐使用 `WebContentExtractor(use_enhanced=True)` 以获得最佳兼容性

2. **对于已知文档站点**：使用 `doc_preset` 参数指定框架

3. **对于混合来源**：使用 `FilterFactory.create_for_url(url)` 自动选择

4. **对于自定义需求**：继承 `BaseContentFilter` 实现自己的过滤器

## 包导入

所有公共 API 都可以从 `filter` 包直接导入：

```python
from filter import (
    BaseContentFilter,      # 抽象基类
    ContentFilter,          # 标准实现
    EnhancedContentFilter,  # 增强实现
    create_filter,          # 创建增强过滤器的便捷函数
    FilterFactory,          # 工厂类
    create_filter_auto,     # 自动创建的便捷函数
    create_filter_for_url,  # 根据URL创建的便捷函数
)
```
