# 内容过滤器包 (Filter Package)

## 概述

此包提供网页内容过滤和清理功能，支持传统网站和现代文档站点（如 Mintlify、Docusaurus、VitePress 等）。

## 包结构

```
filter/
├── __init__.py       # 包初始化，导出所有公共 API
├── base.py           # BaseContentFilter 抽象基类
├── standard.py       # ContentFilter 标准实现
├── enhanced.py       # EnhancedContentFilter 增强实现
├── factory.py        # FilterFactory 工厂类
└── README.md         # 本文档
```

## 模块说明

### base.py

定义 `BaseContentFilter` 抽象基类，规定所有内容过滤器必须实现的方法：

- `get_page_title(url, soup)` - 获取页面标题
- `filter_non_content_blocks(soup)` - 过滤非正文内容
- `filter_logging_outputs(soup)` - 过滤日志输出
- `remove_meaningless_content(content)` - 移除无意义内容
- `sanitize_filename(filename)` - 清理文件名

### standard.py

提供 `ContentFilter` 类，适用于传统网站的原始实现：

```python
from filter import ContentFilter

filter = ContentFilter()
```

### enhanced.py

提供 `EnhancedContentFilter` 类，支持现代文档站点：

```python
from filter import EnhancedContentFilter, create_filter

# 自动检测文档框架
filter = create_filter(auto_detect_framework=True)

# 指定框架预设
filter = create_filter(preset='mintlify')
```

支持的文档框架：
- `mintlify` - Mintlify 文档站点
- `docusaurus` - Docusaurus 文档站点
- `vitepress` - VitePress 文档站点
- `gitbook` - GitBook 文档站点

### factory.py

提供 `FilterFactory` 工厂类，智能选择合适的过滤器：

```python
from filter import FilterFactory, create_filter_for_url

# 根据 URL 自动选择
filter = FilterFactory.create_for_url("https://docs.example.com")

# 便捷函数
filter = create_filter_for_url(url)
```

## 快速开始

### 方式 1: 直接导入

```python
from filter import ContentFilter, EnhancedContentFilter

# 使用标准过滤器
standard = ContentFilter()

# 使用增强版过滤器
enhanced = EnhancedContentFilter()
```

### 方式 2: 使用工厂

```python
from filter import FilterFactory

# 让工厂自动选择
filter = FilterFactory.create(
    url="https://code.claude.com/docs/en/skills",
    use_enhanced=True,
    auto_detect=True
)
```

### 方式 3: 在 WebContentExtractor 中使用

```python
from WebContentExtractor import WebContentExtractor
from filter import EnhancedContentFilter

# 方式 A: 直接传入过滤器实例
extractor = WebContentExtractor(
    content_filter=EnhancedContentFilter()
)

# 方式 B: 使用参数自动创建
extractor = WebContentExtractor(
    use_enhanced=True,
    doc_preset='mintlify'
)

# 方式 C: 使用工厂推荐的过滤器
from filter import FilterFactory
filter = FilterFactory.create_for_url(url)
extractor = WebContentExtractor(content_filter=filter)
```

## API 导出

从 `filter` 包可以直接导入：

```python
from filter import (
    # 基类
    BaseContentFilter,

    # 标准实现
    ContentFilter,

    # 增强实现
    EnhancedContentFilter,
    create_filter,

    # 工厂
    FilterFactory,
    create_filter_auto,
    create_filter_for_url,
)
```

## 版本历史

- **1.0.0** - 初始版本，包含标准过滤器和增强版过滤器
