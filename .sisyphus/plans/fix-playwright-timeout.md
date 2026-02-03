# 工作计划：修复 Playwright 页面加载等待策略

## TL;DR

> **问题**：`wait_until='networkidle'` 导致 Playwright 超时，现代 SPA 有持续后台活动，永远不会真正空闲
> 
> **解决方案**：将等待策略改为 `wait_until='domcontentloaded'` 或 `load`
> 
> **修改文件**：`doc4llm/crawler/DocUrlCrawler.py` 和 `doc4llm/crawler/DocContentCrawler.py`

---

## 问题分析

### 当前问题
```python
# DocUrlCrawler.py 第 509 行
page.goto(url, wait_until='networkidle')
```

### 问题原因
- `networkidle`：等待 500ms 内网络请求少于 2 个
- 现代 SPA（React/Vue/Next.js）：可能有 WebSocket、心跳包、长轮询
- 导致：永远等待网络空闲 → 超时失败

### 正确策略
| 策略 | 行为 | 适用场景 |
|------|------|---------|
| `domcontentloaded` | DOM 解析完成即返回 | 最快，适合大多数场景 |
| `load` | 页面完全加载（包括图片） | 需要等待资源 |
| `networkidle` | 网络空闲 500ms | 静态页面，不适合 SPA |

**推荐**：`wait_until='domcontentloaded'` + 额外等待

---

## 工作任务

### 任务 1：修改 DocUrlCrawler.py

**文件**: `doc4llm/crawler/DocUrlCrawler.py`

**修改位置**: 第 509 行

**当前代码**:
```python
page.goto(url, wait_until='networkidle')
```

**修改为**:
```python
page.goto(url, wait_until='domcontentloaded')

# 等待 SPA 渲染（特别是 Mintlify/Docusaurus）
page.wait_for_load_state('networkidle', timeout=5000)
```

**或者更稳定的方案**:
```python
page.goto(url, wait_until='domcontentloaded')

# 等待内容区域出现（SPA 渲染完成）
page.wait_for_selector('main, [data-page], #content-area', timeout=15000)
```

### 任务 2：修改 DocContentCrawler.py

**文件**: `doc4llm/crawler/DocContentCrawler.py`

**修改位置**: 第 400 行（类似代码）

**同样修改**:
```python
# 当前
page.goto(url, wait_until='networkidle')

# 修改为
page.goto(url, wait_until='domcontentloaded')
page.wait_for_load_state('networkidle', timeout=5000)
```

### 任务 3：测试修复

**测试命令**:
```bash
cd /Users/zorro/project/md_docs_base/doc4llmMain

python -m doc4llm \
    -u "https://docs.langchain.com/oss/python/langchain/retrieval" \
    -mode 4 \
    -config "/Users/zorro/project/md_docs_base/doc4llmMain/Config/langchain.json" \
    -proxy "" \
    -debug 1
```

**预期结果**:
- Playwright 不再因 networkidle 超时
- 页面加载更快（不再等待后台活动）
- HTML 内容正常获取

---

## 验收标准

- [ ] `wait_until='networkidle'` 替换为 `wait_until='domcontentloaded'`
- [ ] 添加额外的等待逻辑确保 SPA 渲染完成
- [ ] 测试通过，Playwright 不再超时
- [ ] 两种爬虫文件都修复（DocUrlCrawler.py 和 DocContentCrawler.py）

---

## 执行命令

```bash
# 修改 DocUrlCrawler.py
sed -i '' "s/wait_until='networkidle'/wait_until='domcontentloaded'/" doc4llm/crawler/DocUrlCrawler.py

# 修改 DocContentCrawler.py  
sed -i '' "s/wait_until='networkidle'/wait_until='domcontentloaded'/" doc4llm/crawler/DocContentCrawler.py
```

然后运行测试验证。
