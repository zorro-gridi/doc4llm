# 工作计划：DocContentCrawler Mode 4 Playwright 功能测试（使用自定义配置）

## TL;DR

> **测试目标**：使用自定义配置文件测试 playwright 有头模式下加载 URL 页面的能力
> 
> **配置文件**：`/Users/zorro/project/md_docs_base/doc4llmMain/Config/langchain.json`
> 
> **核心配置**：
> - Playwright: 启用 + 强制 + 有头模式（headless=false）
> - 代理: `http://127.0.0.1:7890`
> - 输出目录: `/Users/zorro/project/md_docs_base/LangChain_Docs@latest/`
> 
> **测试 URL**: `https://docs.langchain.com/oss/python/langchain/retrieval`
> **执行命令**: `python -m doc4llm -u <URL> -mode 4 -config /path/to/langchain.json`
> 
> **预计工作量**：小型测试任务
> **执行方式**：直接命令行测试

---

## 背景

### 用户需求
使用自定义配置文件 `/Users/zorro/project/md_docs_base/doc4llmMain/Config/langchain.json` 测试 playwright 有头模式下的页面加载能力。

### 配置文件分析

**配置文件位置**: `/Users/zorro/project/md_docs_base/doc4llmMain/Config/langchain.json`

**关键配置项**:

```json
{
  "start_url": "https://docs.langchain.com/oss/python/langchain/overview",
  "proxy": "http://127.0.0.1:7890",
  "doc_dir": "/Users/zorro/project/md_docs_base",
  "doc_name": "LangChain_Docs",
  "doc_version": "latest",
  "playwright": {
    "enabled": true,
    "force": true,
    "timeout": 30,
    "headless": false
  }
}
```

**Playwright 配置说明**：
- `enabled`: true - 启用 Playwright
- `force`: true - 强制使用 Playwright 获取所有页面
- `timeout`: 30 - 超时时间 30 秒
- `headless`: false - **有头模式**（显示浏览器窗口）

**内容过滤配置**：
- `non_content_selectors`: `["#content-side-layout"]` - 移除侧边栏
- `content_preserve_selectors`: 保留 `#content-area` 和 mermaid 容器
- `content_end_markers`: `["Next steps"]` - 过滤结束标识后的内容

**URL 过滤配置**：
- 白名单域名: `docs.langchain.com`
- 排除路径: `/blog/`, `/news/`, `/community/`, `/forum/`

### 目标 URL

**指定 URL**: `https://docs.langchain.com/oss/python/langchain/retrieval`

**测试目标**：
- 验证 Playwright 有头模式（headless=false）正确启动
- 验证通过代理（127.0.0.1:7890）访问
- 验证页面内容正确获取并转换为 Markdown
- 验证输出保存到正确位置

---

## 工作任务

### 任务 1：确认配置文件和环境

**配置文件路径**:
```
/Users/zorro/project/md_docs_base/doc4llmMain/Config/langchain.json
```

**验证步骤**：
```bash
# 1. 确认配置文件存在
ls -la /Users/zorro/project/md_docs_base/doc4llmMain/Config/langchain.json

# 2. 确认 headers 文件存在
ls -la /Users/zorro/project/md_docs_base/doc4llmMain/Config/headers.json

# 3. 确认 Playwright 可用
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
```

**预期结果**：
- 配置文件存在且有效
- headers.json 文件存在
- Playwright 可导入

**推荐代理**：category="quick"（环境检查任务）

---

### 任务 2：执行 Mode 4 测试命令

**执行命令**：
```bash
cd /Users/zorro/project/md_docs_base/doc4llmMain

# 使用自定义配置执行 Mode 4 测试
python -m doc4llm \
    -u "https://docs.langchain.com/oss/python/langchain/retrieval" \
    -mode 4 \
    -config "Config/langchain.json" \
    -debug 1
```

**参数说明**：
- `-u`: 目标 URL（覆盖配置的 start_url）
- `-mode 4`: 单页面爬取模式
- `-config`: 自定义配置文件路径（相对于工作目录）
- `-debug 1`: 启用调试模式，输出详细日志

**配置文件中的关键设置**：
```json
{
  "playwright": {
    "enabled": true,
    "force": true,
    "timeout": 30,
    "headless": false
  },
  "doc_dir": "/Users/zorro/project/md_docs_base",
  "doc_name": "LangChain_Docs",
  "doc_version": "latest",
  "proxy": "http://127.0.0.1:7890"
}
```

**预期行为**：
1. 加载配置文件中的 playwright 设置（headless=false）
2. 启动有头模式的 Chromium 浏览器（可以看到窗口）
3. 通过代理（127.0.0.1:7890）导航到 LangChain 文档页面
4. 使用 Playwright 获取渲染后的页面内容
5. 转换为 Markdown 格式
6. 保存到 `/Users/zorro/project/md_docs_base/LangChain_Docs@latest/<PageTitle>/docContent.md`

**验证要点**：
- [ ] 浏览器窗口可见启动（有头模式）
- [ ] 页面加载成功（通过代理）
- [ ] playwright 获取的 HTML 长度 > 0
- [ ] Markdown 文件成功生成在正确位置

**推荐代理**：category="unspecified-low"（执行测试验证）

---

### 任务 3：验证输出结果

**检查输出文件**：
```bash
# 查看生成的文档目录结构
ls -la /Users/zorro/project/md_docs_base/LangChain_Docs@latest/

# 检查生成的 Markdown 文件
find /Users/zorro/project/md_docs_base/LangChain_Docs@latest -name "*.md" -exec ls -lh {} \;

# 查看文件内容
cat /Users/zorro/project/md_docs_base/LangChain_Docs@latest/*/docContent.md | head -100
```

**预期输出目录结构**：
```
/Users/zorro/project/md_docs_base/
└── LangChain_Docs@latest/
    └── Retrieval/
        └── docContent.md
```

**验证内容**：
1. **文件存在性**：
   - [ ] `/Users/zorro/project/md_docs_base/LangChain_Docs@latest/` 目录存在
   - [ ] 包含页面标题命名的子目录（如 `Retrieval/`）
   - [ ] 子目录中包含 `docContent.md` 文件

2. **文件内容**：
   - [ ] 文件包含页面标题（# 标题）
   - [ ] 文件包含原文链接
   - [ ] 文件包含正文内容（非空）
   - [ ] 内容与 LangChain Retrieval 相关

3. **Playwright 验证**：
   - [ ] HTML 内容长度合理（> 10KB）
   - [ ] 包含 LangChain 相关内容
   - [ ] mermaid 图表容器被保留

**推荐代理**：category="quick"（验证输出结果）

---

### 任务 4：对比有头模式和无头模式（可选）

**无头模式对比测试**：
```bash
# 执行无头模式测试
python -m doc4llm \
    -u "https://docs.langchain.com/oss/python/langchain/retrieval" \
    -mode 4 \
    -playwright-force 1 \
    -playwright-headless 1 \
    -debug 1 \
    -doc-name "langchain_docs" \
    -doc-version "headless_v1"
```

**对比分析**：
- 有头模式和无头模式获取的 HTML 长度对比
- 内容完整性对比
- 执行时间对比

**预期**：
- 两种模式获取的内容应该相同
- 有头模式可能略慢（窗口渲染开销）

**推荐代理**：category="quick"（对比测试）

---

## 测试验证策略

### 执行命令详解

**工作目录**:
```bash
cd /Users/zorro/project/md_docs_base/doc4llmMain
```

**完整测试命令**:
```bash
# 使用自定义配置文件执行测试
python -m doc4llm \
    -u "https://docs.langchain.com/oss/python/langchain/retrieval" \
    -mode 4 \
    -config "Config/langchain.json" \
    -debug 1
```

**配置文件关键设置**:
```json
{
  "playwright": {
    "enabled": true,
    "force": true,
    "timeout": 30,
    "headless": false
  },
  "doc_dir": "/Users/zorro/project/md_docs_base",
  "doc_name": "LangChain_Docs",
  "doc_version": "latest",
  "proxy": "http://127.0.0.1:7890"
}
```

### 验证流程

| 步骤 | 操作 | 验证命令 | 预期结果 |
|-----|------|---------|---------|
| 1 | 确认环境 | `python -c "from playwright.sync_api import sync_playwright"` | 无报错 |
| 2 | 执行测试 | 运行上述命令 | 浏览器窗口显示（通过代理） |
| 3 | 检查输出 | `ls -la /Users/zorro/project/md_docs_base/LangChain_Docs@latest/` | 目录和文件生成 |
| 4 | 验证内容 | `cat /Users/zorro/project/md_docs_base/LangChain_Docs@latest/*/docContent.md` | 包含 LangChain 内容 |
| 5 | 清理 | `rm -rf /Users/zorro/project/md_docs_base/LangChain_Docs@latest/Retrieval` | 清理测试文件 |

### 注意事项

1. **有头模式**：测试时会弹出浏览器窗口，这是验证有头模式的必要手段
2. **代理设置**：使用配置的代理 `http://127.0.0.1:7890`
3. **工作目录**：需要在 `/Users/zorro/project/md_docs_base/doc4llmMain` 目录下执行
4. **输出位置**：`/Users/zorro/project/md_docs_base/LangChain_Docs@latest/<PageTitle>/docContent.md`

### 预期输出示例

```
======================================================
=== 单页面爬取模式已启用 ===
=== 文档输出目录: /Users/zorro/project/md_docs_base/LangChain_Docs@latest ===
=== 文档版本: latest ===
=== 最大爬取深度: 10 ===
=== 爬取单个页面: https://docs.langchain.com/oss/python/langchain/retrieval ===
======================================================

[DEBUG] 使用 Playwright 获取渲染后的页面: https://docs.langchain.com/oss/python/langchain/retrieval
[DEBUG] Playwright 获取成功，HTML 长度: 154320 字符
✓ Retrieval -> Retrieval/   # 页面标题
```

### 成功标准

- [ ] 浏览器窗口在有头模式下成功启动和显示（通过代理）
- [ ] 成功加载 LangChain 文档页面
- [ ] Playwright 获取的 HTML 长度 > 0（通常 > 50KB）
- [ ] Markdown 文件成功生成在 `/Users/zorro/project/md_docs_base/LangChain_Docs@latest/`
- [ ] Markdown 内容包含文档正文（不是空内容）
- [ ] 侧边栏 `#content-side-layout` 被正确过滤
- [ ] Mermaid 图表容器被正确保留

---

## 输出产物

### 测试结果

| 输出 | 描述 |
|-----|------|
| 控制台输出 | 执行日志和测试结果 |
| 浏览器窗口 | 有头模式下的可见浏览器（通过代理） |
| Markdown 文件 | 转换后的文档内容 |

### 预期文件结构

```
/Users/zorro/project/md_docs_base/
└── LangChain_Docs@latest/
    └── Retrieval/
        └── docContent.md
```

**docContent.md 内容预览**：
```markdown
# Retrieval

> **原文链接**: https://docs.langchain.com/oss/python/langchain/retrieval

---

## Overview
[文档内容...]
```

---

## 依赖检查

### 前置条件

1. **Playwright 安装**：
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. **项目依赖**：
   ```bash
   pip install -r /Users/zorro/project/doc4llm/requirements.txt
   ```

3. **Python 环境**：
   ```bash
   conda activate k8s
   ```

4. **工作目录**：
   ```bash
   cd /Users/zorro/project/md_docs_base/doc4llmMain
   ```

5. **配置文件**：
   ```bash
   ls -la /Users/zorro/project/md_docs_base/doc4llmMain/Config/langchain.json
   ls -la /Users/zorro/project/md_docs_base/doc4llmMain/Config/headers.json
   ```

---

## 风险和注意事项

### 潜在风险

1. **有头模式视觉干扰**：测试时会弹出浏览器窗口，但这是验证有头模式的必要手段
2. **代理问题**：确保代理 `http://127.0.0.1:7890` 可用
3. **网络不稳定**：测试依赖外部 URL，可能因网络问题失败
4. **浏览器安装**：首次运行可能需要安装 Chromium 浏览器

### 缓解措施

1. **代理检查**：确保代理服务正在运行
2. **网络问题**：检查网络连接，确保可以访问 docs.langchain.com
3. **浏览器问题**：提前安装 `playwright install chromium`
4. **内容过滤**：如果页面需要客户端渲染，Playwright 会自动获取动态内容

---

## 总结

本工作计划使用自定义配置文件测试 playwright 功能：

- **配置文件**: `/Users/zorro/project/md_docs_base/doc4llmMain/Config/langchain.json`
- **测试模式**: 单页面爬取（mode=4）
- **浏览器模式**: 有头模式（headless=false）
- **代理**: `http://127.0.0.1:7890`
- **输出目录**: `/Users/zorro/project/md_docs_base/LangChain_Docs@latest/`

测试将验证 playwright 在有头模式下通过代理正确加载 LangChain 文档页面的能力。
