# DocUrlCrawler Mode 4 实现计划

## TL;DR

> **快速摘要**：新增 Mode 4 单页面模式，直接爬取单个 URL（`-u` 或 `config.start_url`），不递归、不提取其他链接，直接保存页面内容为 Markdown。

> **Deliverables**:
> - `DocUrlCrawler.py` 新增 `process_single()` 方法
> - `cli.py` 新增 `execute_mode_4()` 执行器
> - 文档更新（README.md）

> **Estimated Effort**: Short
> **Parallel Execution**: NO - sequential
> **Critical Path**: DocUrlCrawler.py 修改 → cli.py 修改 → README 更新

---

## Context

### 原始请求
用户想要给 DocUrlCrawler.py 增加一个 mode 4，只爬取 -u 参数或 config 中的 start_url 链接，不递归爬取，也不去爬取该url正文中任何其它url。

### 现有模式分析
| Mode | 行为 | 依赖 |
|------|------|------|
| 0 | 仅扫描 CSV URL 文件 | 无 |
| 1 | 抓取文档内容（需要先扫描 CSV） | CSV 文件 |
| 2 | 抓取锚点链接（需要先扫描 CSV） | CSV 文件 |
| 3 | 先内容爬取，再锚点提取（需要先扫描 CSV） | CSV 文件 |
| **4（新增）** | **直接爬取单个 URL，不递归** | **仅 start_url** |

### 核心差异
- Mode 1/2/3 需要先通过 `UltimateURLScanner` 扫描生成 CSV 文件
- **Mode 4 不需要扫描，直接对单个 URL 进行内容爬取**

---

## Work Objectives

### Core Objective
实现 Mode 4：单页面直接爬取模式，绕过 URL 扫描步骤。

### Concrete Deliverables
1. `doc4llm/crawler/DocUrlCrawler.py`:
   - 新增 `process_single(url)` 方法
   - 直接爬取单个 URL 并保存内容
   
2. `doc4llm/cli.py`:
   - 新增 `execute_mode_4()` 方法
   - ModeExecutor 添加 Mode 4 处理器
   
3. `README.md`:
   - 更新 Modes of Operation 表格
   - 添加 Mode 4 使用示例

### Definition of Done
- [ ] `python -m doc4llm -u https://example.com -mode 4` 能正确运行
- [ ] 仅爬取指定 URL，不递归
- [ ] 页面内容保存为 Markdown 文件
- [ ] 不产生 CSV 文件（无 URL 扫描步骤）

### Must Have
- 直接使用 `-u` 或 `config.start_url` 作为唯一输入
- 页面内容保存到 `md_docs/<doc_name>@<doc_version>/<PageTitle>/docContent.md`
- 正确应用内容过滤（navigation、footer 等移除）

### Must NOT Have (Guardrails)
- **不执行 URL 扫描**（UltimateURLScanner）
- **不生成 CSV 文件**
- **不提取锚点链接**
- **不递归爬取任何链接**

---

## Technical Approach

### DocUrlCrawler.py 修改

新增 `process_single()` 方法，参考 `DocContentCrawler.process_documentation_site()` 的逻辑：

```python
def process_single(self, url: str):
    """
    单页面爬取模式：直接爬取单个 URL，不递归
    
    Args:
        url: 目标 URL
    """
    # 1. 获取页面内容
    fetch_result = self._fetch_page_content(url)
    if not fetch_result:
        print(f"获取页面失败: {url}")
        return
    
    html_content, page_title = fetch_result
    
    # 2. 使用 ContentFilter 提取正文内容
    from doc4llm.filter import ContentFilter
    content_filter = ContentFilter()
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 应用内容过滤
    content = content_filter.filter_content(url, soup)
    
    # 3. 转换为 Markdown
    from doc4llm.convertor import MarkdownConverter
    converter = MarkdownConverter()
    markdown_content = converter.convert(content)
    
    # 4. 保存文件
    self._save_page_content(page_title, markdown_content, url)
```

需要复用或新增的辅助方法：
- `_save_page_content()` - 保存页面内容（类似 DocContentCrawler 的逻辑）

### cli.py 修改

在 `ModeExecutor` 类中新增：

```python
def execute_mode_4(self):
    """Mode 4: 单页面直接爬取（不递归，不生成CSV）"""
    self._print_doc_mode_info("单页面爬取模式已启用")
    
    # 获取起始 URL
    if not self.config.start_url:
        if self.args.start_url:
            self.config.start_url = self.args.start_url
        else:
            print(f"{Fore.RED}错误：Mode 4 必须指定 -u 参数或 config.start_url{Style.RESET_ALL}")
            sys.exit(1)
    
    # 设置 doc_name（如果未设置）
    if not self.config.doc_name and self.config.start_url:
        from doc4llm.cli import CSVHelper
        self.config.doc_name = CSVHelper.auto_detect_doc_name(self.config.start_url)
    
    # 直接爬取单个页面
    from doc4llm.crawler import DocUrlCrawler
    crawler = DocUrlCrawler(self.config)
    crawler.process_single(self.config.start_url)
```

### ModeExecutor 模式注册

在 `CLI.run()` 中添加：

```python
mode_handlers = {
    0: executor.execute_mode_0,
    1: executor.execute_mode_1,
    2: executor.execute_mode_2,
    3: executor.execute_mode_3,
    4: executor.execute_mode_4,  # 新增
}
```

---

## 验证策略 (MANUAL-ONLY)

### Test Decision
- **Infrastructure exists**: NO（项目无测试框架）
- **User wants tests**: NO
- **Framework**: manual verification only

### Manual Verification Commands

```bash
# 测试 Mode 4 基本功能
python -m doc4llm -u https://example.com -mode 4

# 验证：
# 1. 不生成 results/实时输出文件.csv
# 2. 生成 md_docs/example_com@latest/<PageTitle>/docContent.md
# 3. 查看文件内容是否正确提取

# 对比 Mode 1（需要先生成CSV）
python -m doc4llm -u https://example.com -mode 1 -force-scan 1
```

### Acceptance Criteria

| 检查项 | 验证方法 |
|--------|----------|
| 不生成 CSV 文件 | `ls results/` - 确认无 CSV |
| 正确保存 Markdown | `ls md_docs/<doc_name>@<doc_version>/` - 存在目录 |
| 内容过滤生效 | `cat <page>/docContent.md` - 无导航/页脚 |

---

## Execution Strategy

### Sequential Execution (无并行)

```
Task 1: DocUrlCrawler.py 新增 process_single() 方法
    ↓
Task 2: cli.py 新增 execute_mode_4() 方法  
    ↓
Task 3: README.md 更新文档
    ↓
Task 4: 手动验证测试
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|------------|--------|
| 1 | None | 2, 3 |
| 2 | 1 | 3, 4 |
| 3 | 2 | 4 |
| 4 | 2, 3 | None |

---

## TODOs

- [ ] 1. DocUrlCrawler.py 新增 `process_single()` 方法
  - 直接爬取单个 URL
  - 使用 ContentFilter 提取正文
  - 使用 MarkdownConverter 转换
  - 保存为 docContent.md
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: 简单的单文件修改，逻辑清晰
  - **Skills**: `[]`
    - 无特殊技能需求
  
  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 2, 3

  **References**:
  - `doc4llm/crawler/DocContentCrawler.py:process_documentation_site()` - 单页面爬取逻辑参考
  - `doc4llm/filter/standard.py:ContentFilter.filter_content()` - 内容过滤逻辑
  - `doc4llm/convertor/MarkdownConverter.py` - Markdown 转换逻辑
  
  **Acceptance Criteria**:
  - [ ] 方法存在且签名正确
  - [ ] 复用现有 `_fetch_page_content()` 方法
  - [ ] 调用 ContentFilter 过滤内容
  - [ ] 调用 MarkdownConverter 转换
  - [ ] 保存到正确位置

- [ ] 2. cli.py 新增 `execute_mode_4()` 方法
  - 获取 start_url（从 args 或 config）
  - 设置 doc_name（如果未设置）
  - 调用 `DocUrlCrawler.process_single()`
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: 简单的 CLI 修改，遵循现有模式
  - **Skills**: `[]`
  
  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 3, 4

  **References**:
  - `cli.py:ModeExecutor.execute_mode_1()` - 现有模式执行器参考
  - `cli.py:ModeExecutor.execute_mode_2()` - 模式执行器参考
  
  **Acceptance Criteria**:
  - [ ] 方法存在且签名正确
  - [ ] 处理 start_url 为空的情况
  - [ ] 正确调用 DocUrlCrawler
  - [ ] 更新 mode_handlers 字典

- [ ] 3. README.md 更新文档
  - Modes of Operation 表格添加 Mode 4
  - 添加 Mode 4 使用示例
  
  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 文档更新
  - **Skills**: `[]`
  
  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 4

  **References**:
  - `README.md:Modes of Operation` - 现有表格格式
  - `README.md:Usage Examples` - 现有示例格式
  
  **Acceptance Criteria**:
  - [ ] Modes of Operation 表格包含 Mode 4
  - [ ] 添加 Mode 4 使用示例
  - [ ] 说明与 Mode 1/3 的区别

- [ ] 4. 手动验证测试
  - 运行 Mode 4 命令
  - 验证输出文件位置和内容
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的验证测试
  - **Skills**: `[]`
  
  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: Task 2, 3

  **Acceptance Criteria**:
  - [ ] `python -m doc4llm -u https://example.com -mode 4` 成功执行
  - [ ] 无 CSV 文件生成
  - [ ] 正确生成 md_docs 目录结构
  - [ ] docContent.md 内容正确

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 4 | `feat(crawler): add mode 4 single-page crawl mode` | DocUrlCrawler.py, cli.py, README.md | 手动测试通过 |

---

## Success Criteria

### Verification Commands
```bash
# Mode 4 测试
python -m doc4llm -u https://example.com -mode 4

# 验证
ls results/*.csv 2>/dev/null || echo "无CSV文件 ✓"
ls md_docs/example_com@latest/ 2>/dev/null || echo "无文档目录 ✗"
cat md_docs/example_com@latest/*/docContent.md | head -20
```

### Final Checklist
- [ ] 所有 "Must Have" 满足
- [ ] 所有 "Must NOT Have" 排除（无 CSV，无递归）
- [ ] 代码符合项目风格
- [ ] README 文档更新完成
