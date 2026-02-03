# Mermaid 流程图截图方案

## 问题背景

当前方案提取 mermaid SVG 时只能获取纯文本节点，丢失了流程图结构和连接关系。

## 解决方案

在 Playwright 页面渲染完成后，对 `.mermaid` 容器进行截图，保存为 PNG 图片，并在 Markdown 中引用。

## 实现方案

### 1. 新增截图功能

在 `DocContentCrawler` 中添加 `_screenshot_mermaid_elements()` 方法：

```python
def _screenshot_mermaid_elements(self, page, url: str) -> List[Dict[str, str]]:
    """
    对页面中的 mermaid 流程图进行截图
    
    Returns:
        List of screenshots: [{'path': 'path/to/image.png', 'alt': '流程图描述'}]
    """
    screenshots = []
    
    try:
        # 等待 mermaid 渲染完成
        page.wait_for_timeout(3000)
        
        # 获取所有 mermaid 容器
        mermaid_count = page.locator('.mermaid').count()
        
        for i in range(mermaid_count):
            try:
                # 滚动到元素并等待渲染
                mermaid_el = page.locator('.mermaid').nth(i)
                mermaid_el.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                
                # 生成文件名
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc.replace('.', '_')
                safe_path = parsed.path.strip('/').replace('/', '_')[:30]
                screenshot_name = f"{domain}_{safe_path}_mermaid_{i}.png"
                screenshot_path = os.path.join(self.output_dir, 'screenshots', screenshot_name)
                
                # 截图
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                mermaid_el.screenshot(path=screenshot_path)
                
                screenshots.append({
                    'path': f"screenshots/{screenshot_name}",
                    'alt': f"Mermaid 流程图 #{i+1}"
                })
                
                self._debug_print(f"Mermaid 截图已保存: {screenshot_path}")
                
            except Exception as e:
                self._debug_print(f"截图失败 #{i}: {e}")
                
    except Exception as e:
        self._debug_print(f"Mermaid 截图失败: {e}")
        
    return screenshots
```

### 2. 修改 HTML → Markdown 转换

在 `convert_to_markdown()` 中处理 mermaid 截图：

```python
def convert_to_markdown(self, html_content: str, mermaid_screenshots: List[Dict] = None) -> str:
    """将HTML内容转换为Markdown格式"""
    
    # 先使用 html2text 转换
    markdown = self.converter.handle(html_content)
    
    # 处理 mermaid 截图（插入到文档中）
    if mermaid_screenshots:
        for i, shot in enumerate(mermaid_screenshots):
            # 在文档末尾或适当位置插入截图
            markdown += f"\n\n## Mermaid 流程图 {i+1}\n\n"
            markdown += f"![{shot['alt']}]({shot['path']})\n"
    
    # 后处理清理格式问题
    markdown = self._clean_markdown(markdown)
    
    return markdown
```

### 3. 在爬取流程中集成

```python
def crawl_with_playwright(self, url: str) -> Optional[str]:
    """使用 Playwright 渲染并提取内容"""
    
    # ... 现有代码 ...
    
    # 等待页面加载
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(5000)
    
    # 获取 HTML 内容
    html_content = page.content()
    
    # 截图 mermaid 流程图（新增）
    mermaid_screenshots = self._screenshot_mermaid_elements(page, url)
    
    # 转换为 Markdown
    markdown = self.convert_to_markdown(html_content, mermaid_screenshots)
    
    return markdown
```

### 4. 目录结构

```
results/
├── screenshots/
│   ├── docs_langchain_com_oss_python_langchain_retrieval_mermaid_0.png
│   ├── docs_langchain_com_oss_python_langchain_retrieval_mermaid_1.png
│   └── ...
└── docContent.md
```

## 配置选项

```python
class ScannerConfig:
    # ... 现有配置 ...
    
    # Mermaid 截图配置
    mermaid_screenshot_enabled: bool = True  # 是否启用截图
    mermaid_screenshot_scale: int = 1        # 缩放比例 (1=标准, 2=高清)
    mermaid_screenshot_dir: str = "screenshots"  # 保存目录
```

## 优点

| 特性 | 说明 |
|-----|------|
| ✅ 保留完整结构 | 截图保留流程图的完整布局和连接关系 |
| ✅ 高清质量 | 可配置缩放比例，支持 1x/2x/3x |
| ✅ 简单可靠 | 不需要复杂的 SVG 解析 |
| ✅ 通用兼容 | 适用于所有使用 mermaid 的网站 |

## 注意事项

1. **文件大小**: 截图会增加存储空间，建议启用压缩
2. **相对路径**: 截图路径需要相对于 Markdown 文件
3. **懒加载**: 可以使用 `loading="lazy"` 优化页面加载
4. **Alt 文本**: 为截图添加描述性 alt 文本提升可访问性

## 可选增强

1. **截图压缩**: 使用 pillow 压缩 PNG
2. **格式转换**: 转存为 WebP 以减小体积
3. **智能插入**: 根据 mermaid 容器在 DOM 中的位置插入截图
4. **延迟截图**: 对不在视口中的 mermaid，先记录位置，滚动后再截图
