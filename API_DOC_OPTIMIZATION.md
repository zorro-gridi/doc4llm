# API文档优化方案

## 问题分析

DolphinScheduler API文档页面存在以下问题：

1. **正文内容缺少标题结构**：API文档中每个类、方法、属性都没有对应的HTML标题标签（h1-h6）
2. **docTOC.md与docContent.md不匹配**：TOC爬虫提取到导航中的锚点链接，但正文爬虫无法找到对应的标题来分段内容
3. **doc_reader_api.py按标题提取失败**：由于正文没有标准的Markdown标题格式，按标题提取功能无法正确工作

## 解决方案

### 1. API文档格式化器 (`api_doc_formatter.py`)

**功能**：
- 自动检测API文档中的类、方法、属性等结构
- 为这些结构生成对应的Markdown标题
- 支持多种API文档格式（Sphinx、JSDoc、OpenAPI等）

**核心特性**：
- **智能结构检测**：识别Python类、方法、属性等API元素
- **标题层级生成**：自动为API元素生成合适的标题层级
- **DolphinScheduler专用优化**：针对DolphinScheduler的HTML结构进行特殊处理

### 2. 增强的文档爬虫 (`DocContentCrawler.py`)

**改进**：
- 集成API文档格式化器
- 在HTML转Markdown过程中自动检测和增强API文档
- 保持与现有功能的兼容性

**处理流程**：
1. 检测页面是否为API文档
2. 如果是，使用API格式化器增强HTML结构
3. 转换为Markdown时保留增强的标题结构
4. 生成与TOC一致的标题层级

### 3. API文档读取器 (`api_doc_reader.py`)

**功能**：
- 继承自现有的`DocReaderAPI`
- 专门处理API文档的内容提取
- 支持按API项目名称提取内容

**核心特性**：
- **智能标题匹配**：生成多种可能的标题变体进行匹配
- **API结构分析**：分析文档中的类、方法、属性结构
- **模糊搜索支持**：当精确匹配失败时使用模糊搜索

## 使用方法

### 1. 配置文件

使用专门的DolphinScheduler配置文件：

```json
{
  "start_url": "https://dolphinscheduler.apache.org/python/main/api.html",
  "doc_name": "DolphinScheduler_API_Docs",
  "content_filter": {
    "documentation_preset": "sphinx",
    "content_preserve_selectors": [
      "dl.py", "dl.class", "dl.method", "dl.function", "dl.attribute"
    ]
  },
  "api_enhancement": {
    "enabled": true,
    "python_api_support": true,
    "auto_generate_headings": true
  }
}
```

### 2. 爬取API文档

```python
from doc4llm.crawler.DocContentCrawler import DocContentCrawler
from doc4llm.scanner.config import ScannerConfig

# 加载配置
config = ScannerConfig.from_file("doc4llm/config/dolphinscheduler_config.json")

# 创建爬虫
crawler = DocContentCrawler(config)

# 爬取API文档
crawler.process_documentation_site()
```

### 3. 使用API文档读取器

```python
from doc4llm.doc_rag.reader.api_doc_reader import APIDocReaderAPI

# 创建API文档读取器
reader = APIDocReaderAPI(
    base_dir="md_docs",
    search_mode="fuzzy",
    fuzzy_threshold=0.6
)

# 按API名称提取内容
api_content = reader.extract_api_by_names(
    api_names=["Engine", "Task", "Workflow"],
    doc_set="DolphinScheduler_API_Docs@latest"
)

# 分析API结构
api_structure = reader.analyze_api_structure()
```

### 4. 运行演示

```bash
# 激活conda环境
conda activate k8s

# 运行演示脚本
python demo/dolphinscheduler_api_demo.py
```

## 技术实现

### API结构检测

使用多种模式检测API文档结构：

```python
api_patterns = {
    'python_class': {
        'selector': 'dt[id*="class"], dt[id*="Class"]',
        'title_selector': 'code.descname, .sig-name',
        'level': 2,
        'prefix': 'class'
    },
    'python_method': {
        'selector': 'dt[id*="method"], dt[id*="Method"]',
        'title_selector': 'code.descname, .sig-name', 
        'level': 3,
        'prefix': 'method'
    }
}
```

### 标题层级映射

生成合适的Markdown标题层级：

- **类 (Class)**: `## ClassName` (h2)
- **方法 (Method)**: `### method_name` (h3)  
- **属性 (Property)**: `#### property_name` (h4)

### 智能标题匹配

生成多种标题变体进行匹配：

```python
def _generate_heading_variants(self, heading: str, api_type: str) -> List[str]:
    variants = [heading]  # 原始标题
    
    if api_type == 'class':
        variants.extend([
            f"class {clean_heading}",
            f"Class: {clean_heading}",
            f"{clean_heading} class"
        ])
    
    return variants
```

## 优势

1. **自动化处理**：无需手动修改HTML或Markdown文件
2. **保持兼容性**：不影响现有的非API文档处理
3. **灵活配置**：支持不同类型的API文档格式
4. **智能匹配**：多种策略确保内容提取成功
5. **结构化输出**：生成标准的Markdown标题层级

## 扩展性

该方案可以轻松扩展到其他类型的API文档：

- **JavaScript API文档**：添加JSDoc模式
- **REST API文档**：添加OpenAPI/Swagger模式
- **其他语言API文档**：添加相应的检测模式

## 测试验证

使用演示脚本验证功能：

1. **爬取测试**：验证API文档是否正确爬取和增强
2. **结构分析**：验证API结构是否正确识别
3. **内容提取**：验证按标题提取是否正常工作

## 总结

这个优化方案通过智能检测和增强API文档结构，解决了DolphinScheduler API文档标题缺失的问题，使得docTOC.md和docContent.md能够正确对应，doc_reader_api.py能够按标题正确提取内容。

该方案具有良好的扩展性和兼容性，可以应用到其他类似的API文档处理场景中。