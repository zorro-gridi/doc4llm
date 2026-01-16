# WhiteURLScan 配置参数说明文档

本文档详细说明 `config.json` 中所有配置参数的作用、应用场景和配置方法。

---

## 目录

- [基础配置](#基础配置)
- [域名与URL范围](#域名与url范围)
- [请求配置](#请求配置)
- [过滤规则](#过滤规则)
- [文档爬取模式](#文档爬取模式)
- [TOC选择器详解](#toc选择器详解)
- [TOC URL过滤配置](#toc-url过滤配置)
- [内联提取优化](#内联提取优化)

---

## 基础配置

### `start_url`

| 参数 | 类型 | 默认值 | 必填 |
|------|------|--------|------|
| 起始URL | string | `null` | 否 |

**作用**：扫描的起始URL地址

**配置示例**：
```json
"start_url": "https://example.com"
```

**应用场景**：
- 单URL扫描：指定要扫描的目标网站
- 批量扫描：配合 `-f` 参数使用时，此参数可省略

---

### `max_workers`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 最大线程数 | int | `30` |

**作用**：并发爬取的最大线程数量

**配置示例**：
```json
"max_workers": 50
```

**应用场景**：
- 高性能扫描：可设置为 50-100
- 低带宽环境：设置为 10-20
- 避免被封：设置为 5-10

---

### `delay`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 请求延迟（秒） | float | `0.1` |

**作用**：每个请求之间的延迟时间

**配置示例**：
```json
"delay": 1.0
```

**应用场景**：
- 避免触发反爬：设置为 1-3 秒
- 快速扫描：设置为 0.1-0.5 秒
- 友好爬取：设置为 2-5 秒

---

### `timeout`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 请求超时（秒） | int | `20` |

**作用**：单个HTTP请求的超时时间

**配置示例**：
```json
"timeout": 30
```

**应用场景**：
- 慢速网站：设置为 30-60 秒
- 快速扫描：设置为 10-15 秒

---

### `max_depth`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 最大递归深度 | int | `5` |

**作用**：URL递归爬取的最大深度

**配置示例**：
```json
"max_depth": 3
```

**应用场景**：
- 浅层扫描：设置为 2-3
- 深度扫描：设置为 5-10
- 全站扫描：设置为 10+

---

### `max_urls`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 最大URL数量 | int | `10000` |

**作用**：最多扫描的URL总数限制

**配置示例**：
```json
"max_urls": 5000
```

---

## 域名与URL范围

### `url_scope_mode`

| 参数 | 类型 | 默认值 | 可选值 |
|------|------|--------|--------|
| URL扫描范围模式 | int | `0` | `0` / `1` / `2` / `3` |

**作用**：控制URL扫描的范围策略

**模式说明**：

| 模式值 | 名称 | 行为说明 | 应用场景 |
|--------|------|----------|----------|
| `0` | 主域名模式 | 仅扫描目标主域名，外部URL记录到文件但不递归 | 常规扫描 |
| `1` | 外部一次模式 | 扫描目标域名 + 访问外部链接一次（外部域名不递归） | 扩展发现 |
| `2` | 无限制模式 | 扫描所有链接，仅受深度和URL数量限制 | 全面扫描 |
| `3` | 白名单模式 | 仅扫描 `whitelist_domains` 中的域名 | 精确目标 |

**配置示例**：
```json
"url_scope_mode": 0
```

---

### `blacklist_domains`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 黑名单域名 | array | `["www.w3.org", "www.baidu.com", "github.com"]` |

**作用**：禁止扫描的域名列表

**配置示例**：
```json
"blacklist_domains": [
  "www.w3.org",
  "www.baidu.com",
  "github.com",
  "google.com",
  "facebook.com"
]
```

**应用场景**：
- 排除大型CDN：如 `google.com`, `facebook.com`
- 排除广告域名：如 `doubleclick.net`
- 排除社交媒体：如 `twitter.com`, `linkedin.com`

---

### `whitelist_domains`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 白名单域名 | array | `[]` |

**作用**：配合 `url_scope_mode=3` 使用，仅扫描白名单中的域名

**配置示例**：
```json
"whitelist_domains": [
  "docs.python.org",
  "api.example.com"
]
```

---

## 请求配置

### `proxy`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 代理地址 | string | `null` |

**作用**：HTTP/HTTPS代理服务器地址

**配置示例**：
```json
"proxy": "http://127.0.0.1:7890"
```

**支持格式**：
- HTTP代理：`http://127.0.0.1:8080`
- SOCKS5代理：`socks5://127.0.0.1:1080`

---

### `headers_path`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| HTTP头文件路径 | string | `"headers.json"` |

**作用**：指定包含HTTP请求头的JSON文件路径

**配置示例**：
```json
"headers_path": "headers.json"
```

**headers.json 文件格式**：
```json
{
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
  "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
  "Authorization": "Bearer your_token_here"
}
```

**应用场景**：
- 模拟浏览器：设置 `User-Agent`
- API访问：添加 `Authorization` 头
- 语言设置：配置 `Accept-Language`
- 自定义路径：可指定其他位置的 headers 文件

**路径说明**：
- 支持相对路径：相对于项目根目录
- 支持绝对路径：如 `/path/to/custom_headers.json`

---

### `extension_blacklist`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 扩展名黑名单 | array | `[".css", ".mp4", ".js", ...]` |

**作用**：跳过指定扩展名的文件

**配置示例**：
```json
"extension_blacklist": [
  ".css", ".js", ".svg",
  ".jpg", ".png", ".gif",
  ".mp4", ".mp3", ".avi",
  ".zip", ".rar", ".tar",
  ".pdf", ".doc", ".docx"
]
```

**过滤规则说明**：

1. **自动处理查询参数**：扩展名过滤会自动处理带查询参数的 URL
   - ✅ `image.png` → 被过滤
   - ✅ `image.png?v=1` → 被过滤
   - ✅ `image.png?timestamp=1234567890&quality=high` → 被过滤
   - ✅ `script.js?version=1.2.3` → 被过滤

2. **实现原理**：使用 `urllib.parse.urlparse()` 解析 URL，只检查路径部分（path），忽略查询参数（query）和片段（fragment）

3. **大小写不敏感**：扩展名匹配不区分大小写
   - ✅ `file.PNG` → 被过滤（匹配 `.png`）
   - ✅ `file.JPG?v=test` → 被过滤（匹配 `.jpg`）

4. **支持的扩展名类型**：
   - 样式文件：`.css`, `.scss`, `.less`, `.sass`
   - 脚本文件：`.js`, `.map`, `.json`
   - 图片文件：`.jpg`, `.jpeg`, `.png`, `.gif`, `.svg`, `.webp`, `.bmp`, `.ico`
   - 字体文件：`.woff`, `.woff2`, `.ttf`, `.eot`, `.otf`
   - 视频文件：`.mp4`, `.avi`, `.mov`, `.wmv`, `.flv`, `.mkv`, `.webm`
   - 音频文件：`.mp3`, `.wav`, `.ogg`, `.aac`, `.flac`
   - 文档文件：`.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`
   - 压缩文件：`.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.bz2`
   - 其他文件：`.swf`, `.exe`, `.dll`, `.bin`, `.dmg`, `.apk`, `.iso`

---

## 过滤规则

### `danger_filter_enabled`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 危险接口过滤开关 | int | `1` |

**作用**：是否启用危险API接口过滤

**配置**：
```json
"danger_filter_enabled": 1  // 1=启用, 0=禁用
```

---

### `danger_api_list`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 危险API关键词列表 | array | `[...]` |

**作用**：包含危险操作的关键词列表

**配置示例**：
```json
"danger_api_list": [
  "del", "delete", "drop",
  "truncate", "shutdown", "stop",
  "deactivate", "disable", "remove"
]
```

---

### `exclude_fuzzy`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 模糊排除路径 | array | `["/blog/", "/news/", ...]` |

**作用**：排除包含特定关键词的URL路径

**配置示例**：
```json
"exclude_fuzzy": [
  "/blog/",
  "/news/",
  "/community/",
  "/forum/",
  "download",
  "_modules",
  "/product/"
]
```

---

### `title_filter_list`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 标题过滤列表 | array | `["Page Not Found", "404 Not Found"]` |

**作用**：根据页面标题过滤无效页面

**配置示例**：
```json
"title_filter_list": [
  "Page Not Found",
  "404 Not Found",
  "Access Denied",
  "Service Unavailable"
]
```

---

### `status_code_filter`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 状态码过滤列表 | array | `[404, 503, 502, ...]` |

**作用**：过滤掉特定HTTP状态码的响应

**配置示例**：
```json
"status_code_filter": [
  404,   // Not Found
  503,   // Service Unavailable
  502,   // Bad Gateway
  504,   // Gateway Timeout
  403,   // Forbidden
  401,   // Unauthorized
  500    // Internal Server Error
]
```

---

## 文档爬取模式

### `mode`

| 参数 | 类型 | 默认值 | 可选值 |
|------|------|--------|--------|
| 爬取模式 | int | `0` | `0` / `1` / `2` / `3` |

**作用**：控制文档爬取的行为模式

**模式说明**：

| 模式值 | 名称 | 行为说明 | 应用场景 |
|--------|------|----------|----------|
| `0` | 仅爬取CSV | 只执行URL扫描，结果保存到CSV | 常规扫描 |
| `1` | 抓取文档内容 | 扫描URL + 爬取文档正文内容 | 内容采集 |
| `2` | 抓取锚点链接 | 扫描URL + 提取TOC锚点链接 | 文档索引 |
| `3` | 组合模式 | 依次执行文档内容爬取和锚点链接提取 | 完整采集 |

**配置示例**：
```json
"mode": 3
```

**命令行使用**：
```bash
python -m doc4llm -u https://docs.example.com -mode 3
```

---

### `force_scan`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 强制扫描开关 | int | `0` |

**作用**：在 mode 1/2 时，是否强制执行URL扫描以刷新CSV文件

**行为说明**：
- `0`（默认）：如果CSV文件已存在且有内容，跳过URL扫描步骤，直接使用现有CSV文件
- `1`：强制执行URL扫描，刷新CSV文件内容

**配置**：
```json
"force_scan": 1  // 1=强制扫描, 0=智能跳过
```

**命令行使用**：
```bash
# 使用现有CSV文件（如果存在）
python -m doc4llm -u https://docs.example.com -mode 2

# 强制刷新CSV文件
python -m doc4llm -u https://docs.example.com -mode 2 -force-scan 1
```

**应用场景**：
- 增量更新：CSV文件已存在时，跳过扫描直接使用现有结果
- 全量更新：需要获取最新URL时，强制刷新CSV文件

---

### `doc_dir`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 文档输出目录 | string | `"documentation_output"` |

**作用**：文档内容的保存目录

**配置示例**：
```json
"doc_dir": "my_docs"
```

---

### `doc_name`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 文档名称 | string | `null` |

**作用**：覆盖自动检测的文档名称

**配置示例**：
```json
"doc_name": "MyAPI_Documentation"
```

---

### `doc_version`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 文档版本 | string | `"latest"` |

**作用**：指定文档的版本号

**配置示例**：
```json
"doc_version": "v2.5.0"
```

---

### `doc_max_depth`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 文档爬取最大深度 | int | `10` |

**作用**：文档内容爬取的最大深度

**配置示例**：
```json
"doc_max_depth": 15
```

---

### `doc_timeout`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 文档请求超时（秒） | int | `30` |

**作用**：文档爬取时的HTTP请求超时时间

**配置示例**：
```json
"doc_timeout": 60
```

---

## TOC选择器详解

### `doc_toc_selector`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| TOC区域CSS选择器 | string / null | `null` |

**作用**：指定文档页面中目录（TOC）区域的CSS选择器

**默认行为**：
- 设置为 `null` 时，使用内置的白名单/黑名单策略自动检测TOC

**配置方式**：

#### 场景1：使用默认自动检测

```json
"doc_toc_selector": null
```

适用于：Claude Code Docs、Ray Docs等已适配的文档站点

---

#### 场景2：ID选择器

**页面HTML**：
```html
<nav id="toc">
  <a href="#section1">Section 1</a>
</nav>
```

**配置**：
```json
"doc_toc_selector": "#toc"
```

---

#### 场景3：单个class

**页面HTML**：
```html
<nav class="toc">
  <a href="#section1">Section 1</a>
</nav>
```

**配置**：
```json
"doc_toc_selector": ".toc"
```

---

#### 场景4：多个class（精确匹配，推荐）

**页面HTML**：
```html
<nav class="bd-toc-nav page-toc">
  <a href="#section1">Section 1</a>
</nav>
```

**配置（推荐）**：
```json
"doc_toc_selector": ".bd-toc-nav.page-toc"
```

**说明**：
- ✅ **推荐使用**：class之间无空格，表示**同时包含**这两个class
- ✅ **精确匹配**：避免匹配到其他不相关元素
- ✅ **避免冗余**：只匹配真正的TOC容器

---

#### 场景5：多个class（OR逻辑，慎用）

**配置**：
```json
"doc_toc_selector": ".toc, .sidebar-nav"
```

**说明**：
- ⚠️ **慎用**：逗号分隔表示OR逻辑
- ⚠️ **可能冗余**：会匹配所有包含任一class的元素
- ❌ **不推荐**：除非非常确定不会有其他元素使用这些class

---

#### 场景6：标签+class组合

**页面HTML**：
```html
<nav class="toc">
  <a href="#section1">Section 1</a>
</nav>
```

**配置**：
```json
"doc_toc_selector": "nav.toc"
```

---

#### 场景7：层级选择器

**页面HTML**：
```html
<div class="sidebar">
  <nav class="toc">
    <a href="#section1">Section 1</a>
  </nav>
</div>
```

**配置**：
```json
"doc_toc_selector": ".sidebar .toc"
```

---

### 常见文档框架的选择器

| 文档框架 | 推荐选择器 |
|----------|------------|
| **Sphinx** (Python官方文档) | `.bd-toc-nav.bd-sidebar` |
| **MkDocs** | `.md-nav` |
| **Docusaurus** | `.table-of-contents` |
| **GitBook** | `.page-toc` |
| **VitePress** | `.VPDocAside` |
| **Mintlify** (Claude Code Docs) | `null` (使用自动检测) |
| **Ray Docs** | `null` (使用自动检测) |

---

### 如何找到页面的TOC选择器

#### 步骤：

1. **打开浏览器开发者工具**
   - Chrome/Edge: 按 `F12` 或 `Ctrl+Shift+I`
   - Firefox: 按 `F12`

2. **使用元素选择器**
   - 点击元素选择器图标（或按 `Ctrl+Shift+C`）
   - 鼠标悬停在页面TOC区域
   - 点击选中TOC容器元素

3. **查看元素的class或id**
   - 在HTML代码中找到对应的容器标签
   - 记录下 `class="xxx"` 或 `id="xxx"` 属性

4. **根据HTML结构配置选择器**

#### 示例：

```
开发者工具显示的HTML：
┌─────────────────────────────────────┐
│ <nav class="bd-toc-nav page-toc">  │
│   <ul>                              │
│     <li><a href="#intro">...</a></li>│
│   </ul>                              │
│ </nav>                              │
└─────────────────────────────────────┘

提取信息：class="bd-toc-nav page-toc"

配置：.bd-toc-nav.page-toc（无空格）
```

---

### CSS选择器快速参考

| 选择器语法 | 说明 | 示例 |
|------------|------|------|
| `.classname` | class选择器 | `.toc` |
| `#idname` | ID选择器 | `#navigation` |
| `tagname` | 标签选择器 | `nav` |
| `.class1.class2` | 多class AND（同时包含） | `.bd-toc-nav.page-toc` |
| `.class1, .class2` | 多class OR（匹配任一） | `.toc, .sidebar` |
| `.parent .child` | 层级选择器（后代） | `.sidebar .toc` |
| `tag.class` | 标签+class | `nav.toc` |
| `[attr*='value']` | 属性包含某值 | `[class*='toc']` |
| `[attr^='value']` | 属性以某值开头 | `[class^='toc-']` |
| `[attr$='value']` | 属性以某值结尾 | `[class$='-nav']` |

---

### 命令行使用

```bash
# 使用默认自动检测
python -m doc4llm -csv urls.csv -mode 2

# 指定TOC选择器
python -m doc4llm -csv urls.csv -mode 2 -doc-toc-selector ".bd-toc-nav.page-toc"

# 使用ID选择器
python -m doc4llm -csv urls.csv -mode 2 -doc-toc-selector "#toc"

# 使用多个选择器（OR逻辑）
python -m doc4llm -csv urls.csv -mode 2 -doc-toc-selector ".toc, .sidebar-nav"
```

---

## TOC URL过滤配置

### `toc_filter`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| TOC URL 过滤规则 | object | `{...}` |

**作用**：配置 `DocUrlCrawler` 模块提取 TOC 锚点链接时的标签过滤规则

**默认行为**：
- 使用预定义的白名单/黑名单策略自动识别 TOC 容器和链接
- 支持通过配置文件自定义或扩展过滤规则

**配置示例**：
```json
"toc_filter": {
  "merge_mode": "extend",
  "toc_class_patterns": [
    "custom-toc",
    "special-directory"
  ],
  "toc_link_class_patterns": [
    "custom-toc-item",
    "custom-nav-link"
  ],
  "toc_parent_class_patterns": [
    "custom-menu-item"
  ],
  "content_area_patterns": [
    "custom-content-area"
  ],
  "non_toc_link_patterns": [
    "custom-exclude-link"
  ]
}
```

### 配置字段说明

| 字段 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `merge_mode` | `string` | `"extend"` | 合并模式：`extend` 或 `replace` |
| `toc_class_patterns` | `array` | `[...]` | TOC 容器的 class/id 匹配模式（白名单） |
| `toc_link_class_patterns` | `array` | `[...]` | TOC 链接的 class 匹配模式（白名单） |
| `toc_parent_class_patterns` | `array` | `[...]` | TOC 链接父元素的 class 匹配模式（白名单） |
| `content_area_patterns` | `array` | `[...]` | 正文内容区域的 class 匹配模式（黑名单） |
| `non_toc_link_patterns` | `array` | `[...]` | 非 TOC 链接的 class 匹配模式（黑名单） |
| `toc_end_markers` | `array` | `[...]` | TOC 内容结束标识（纯文本，自动转换为正则） |

### 默认配置值

#### `toc_end_markers`（默认）

TOC 内容结束标识，遇到这些文本后停止提取后续锚点链接：
- `See also` - 另请参阅
- `Related articles` - 相关文章
- `Further reading` - 延伸阅读
- `External links` - 外部链接
- `References` - 参考资料
- `Related skills` - 相关技能
- `Next steps` - 下一步
- `Next up` - 接下来

**特性**：
- **纯文本配置**：用户只需填写纯文本，系统自动转换为正则表达式
- **区分大小写**：精确匹配（"Next steps" 不会匹配 "next steps"）
- **灵活空白**：自动支持变长的空白字符

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

#### `toc_class_patterns`（默认）

TOC 容器的 CSS 类名/ID 模式（白名单）：
- `toc` - 目录通用 class
- `table-of-contents` - 完整目录名称
- `navigation` - 导航
- `sidebar` - 侧边栏
- `menu` - 菜单
- `directory` - 目录索引
- `index` - 索引
- `content-side-layout` - 侧边栏布局容器
- `table-of-contents-` - TOC 相关前缀

#### `toc_link_class_patterns`（默认）

TOC 锚点链接的类名模式（白名单）：
- `toc-item` - 目录项
- `toc-link` - 目录链接
- `nav-item` - 导航项
- `nav-link` - 导航链接
- `menu-item` - 菜单项
- `menu-link` - 菜单链接
- `directory-item` - 目录项

#### `toc_parent_class_patterns`（默认）

TOC 锚点链接的直接父元素类名（白名单）：
- `toc-item` - 目录项（如 `<li class="toc-item">`）
- `toc-item relative` - 带有相对定位的目录项
- `nav-item` - 导航项
- `menu-item` - 菜单项

#### `content_area_patterns`（默认）

正文内容区域的类名模式（黑名单）：
- `mdx-content` - MDX 内容区域
- `content-area` - 通用内容区域
- `prose` - Prose 正文
- `content-container` - 内容容器

#### `non_toc_link_patterns`（默认）

非目录链接的类名模式（黑名单）：
- `link` - 正文相关链接
- `opacity-0` - 隐藏的锚点按钮
- `group-hover:opacity-100` - 悬停显示的锚点按钮
- `header-link` - 标题链接
- `anchor` - 锚点符号

### 合并模式说明

#### `extend`（扩展模式，默认）

保留默认配置，并将自定义配置追加到列表中：

```json
{
  "toc_filter": {
    "merge_mode": "extend",
    "toc_class_patterns": ["my-custom-toc"]
  }
}
```

**结果**：默认的 `toc_class_patterns` + `["my-custom-toc"]`

#### `replace`（替换模式）

完全使用自定义配置，忽略默认配置：

```json
{
  "toc_filter": {
    "merge_mode": "replace",
    "toc_class_patterns": ["my-custom-toc"]
  }
}
```

**结果**：仅使用 `["my-custom-toc"]`

### 应用场景

#### 场景 1：处理特殊文档站点

某些文档站点使用自定义的 class 名称：

```json
{
  "toc_filter": {
    "merge_mode": "extend",
    "toc_class_patterns": [
      "docs-sidebar",
      "api-navigation",
      "my-doc-index"
    ]
  }
}
```

#### 场景 2：排除干扰元素

某些站点的正文区域使用特定的 class：

```json
{
  "toc_filter": {
    "merge_mode": "extend",
    "content_area_patterns": [
      "main-content",
      "article-body",
      "post-content"
    ]
  }
}
```

#### 场景 3：精确匹配 TOC 链接

某些站点的 TOC 链接有特定的父元素结构：

```json
{
  "toc_filter": {
    "merge_mode": "extend",
    "toc_parent_class_patterns": [
      "my-toc-list-item",
      "nav-list-item active"
    ]
  }
}
```

### 与 `doc_toc_selector` 的区别

| 配置项 | 作用范围 | 使用场景 |
|--------|----------|----------|
| `doc_toc_selector` | 直接指定 TOC 容器的 CSS 选择器 | 精确定位单个 TOC 容器 |
| `toc_url_filter` | 定义识别 TOC 的标签匹配规则 | 自动识别多个可能的 TOC 元素 |

**配合使用**：
```json
{
  "doc_toc_selector": ".bd-toc-nav.page-toc",
  "toc_filter": {
    "merge_mode": "extend",
    "non_toc_link_patterns": ["exclude-this-link"]
  }
}
```

---

## 输出配置

### `results_dir`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 结果文件保存目录 | string | `"results"` |

**作用**：所有扫描结果文件的保存目录

**配置示例**：
```json
"results_dir": "results"
```

**应用场景**：
- 统一管理：集中管理所有扫描结果文件
- 动态文件名：批量扫描时动态生成的汇总文件也会保存到此目录
- 目录自定义：可根据需要修改为其他目录名

**说明**：
- 批量扫描的汇总文件格式：`{results_dir}/all_results_YYYYMMDD_HHMMSS.csv`
- CSV 输出文件、日志文件等都保存在此目录或其子目录

---

### `output_file`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 输出文件路径 | string | `"results/实时输出文件.csv"` |

**作用**：实时扫描结果的CSV输出文件路径

**配置示例**：
```json
"output_file": "results/my_scan.csv"
```

---

### `output_log_file`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 输出日志文件路径 | string | `"results/output.out"` |

**作用**：控制台输出的日志文件路径（同时输出到终端和文件）

**配置示例**：
```json
"output_log_file": "results/output.out"
```

**应用场景**：
- 保存扫描过程日志：记录所有终端输出
- 调试分析：查看扫描过程中的详细信息
- 历史记录：保留扫描历史供后续查看

---

### `debug_log_file`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 调试日志文件路径 | string | `"results/debug.log"` |

**作用**：调试模式下的详细日志文件路径（仅在 debug_mode=1 时生效）

**配置示例**：
```json
"debug_log_file": "results/debug.log"
```

**应用场景**：
- 问题排查：记录详细的调试信息
- 性能分析：跟踪程序执行流程
- 开发调试：开发阶段的详细日志

---

### `color_output`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 彩色输出开关 | bool | `true` |

**作用**：是否在终端输出彩色日志

**配置**：
```json
"color_output": true
```

---

### `verbose`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 详细输出开关 | bool | `true` |

**作用**：是否输出详细的日志信息

**配置**：
```json
"verbose": true
```

---

### `debug_mode`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 调试模式 | int | `0` |

**作用**：启用调试模式，输出更详细的调试信息

**配置**：
```json
"debug_mode": 1  // 1=开启, 0=关闭
```

---

## 自定义URL拼接配置

### `fuzz`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| Fuzz模式开关 | int | `0` |

**作用**：是否启用自定义URL拼接功能

**配置**：
```json
"fuzz": 1  // 1=启用, 0=禁用
```

---

### `custom_base_url`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 自定义基础URL列表 | array | `[]` |

**作用**：Fuzz模式使用的基础URL列表

**配置示例**：
```json
"custom_base_url": [
  "https://api.example.com"
]
```

---

### `path_route`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| 路径路由列表 | array | `[]` |

**作用**：Fuzz模式拼接的路径列表

**配置示例**：
```json
"path_route": [
  "/api/v1/users",
  "/api/v1/products",
  "/admin/dashboard"
]
```

---

### `api_route`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| API路由列表 | array | `[]` |

**作用**：Fuzz模式拼接的API路由列表

**配置示例**：
```json
"api_route": [
  "/api/v1/user/login",
  "/api/v1/user/logout"
]
```

---

## TOC URL过滤配置

### `toc_url_filters`

| 参数 | 类型 | 默认值 |
|------|------|--------|
| TOC URL过滤规则 | object | `{...}` |

**作用**：配置文档爬取时的URL过滤规则

**配置示例**：
```json
"toc_url_filters": {
  "subdomains": ["docs.", "api.", "developer."],
  "fuzzy_match": ["/docs/", "/guide/", "/tutorial/", "/api/"],
  "exclude_fuzzy": ["/blog/", "/news/", "/community/"]
}
```

**子字段说明**：

| 字段 | 作用 | 示例 |
|------|------|------|
| `subdomains` | 匹配指定子域名 | `["docs.", "api."]` |
| `fuzzy_match` | URL路径包含关键词 | `["/docs/", "/api/"]` |
| `exclude_fuzzy` | 排除包含关键词的URL | `["/blog/", "/news/"]` |

---

## 内联提取优化

### `enable_inline_extraction`

| 参数 | 类型 | 默认值 | 可选值 |
|------|------|--------|--------|
| 内联提取开关 | int | `1` | `0` / `1` |

**作用**：控制在 mode 1/2/3 时是否启用内联提取优化

**功能说明**：

当启用内联提取时（默认），系统会在扫描过程中直接使用已获取的HTML响应进行内容和TOC提取，避免重复的HTTP请求。这可以显著提高性能，减少网络流量。

| 设置值 | 行为说明 | 适用场景 |
|--------|----------|----------|
| `1`（默认） | 启用内联提取，在扫描时实时提取内容/TOC | 推荐使用，性能更优 |
| `0` | 禁用内联提取，使用传统爬虫流程 | 兼容旧版本，调试用途 |

**性能对比**：

| 指标 | 传统模式（mode 3） | 内联提取模式 | 提升 |
|------|-------------------|-------------|------|
| HTTP请求数（100个URL） | 300 | 100 | 66% ↓ |
| 执行时间 | ~3x | ~1x | 66% ↓ |
| 服务器负载 | 3x | 1x | 66% ↓ |

**配置示例**：
```json
{
  "mode": 3,
  "enable_inline_extraction": 1
}
```

**命令行使用**：
```bash
# 使用内联提取（默认）
python -m doc4llm -u https://docs.example.com -mode 3

# 禁用内联提取，使用传统流程
python -m doc4llm -u https://docs.example.com -mode 3 -enable-inline-extraction 0
```

**工作原理**：

```
传统模式（mode 3）：
┌─────────────┐    HTTP请求1    ┌──────────────┐
│ UltimateURL │ ──────────────> │ 目标服务器    │
│   Scanner   │                 │              │
└─────────────┘                 └──────────────┘
       ↓                                   ↓
   写入CSV                            返回HTML
       ↓                                   ↓
┌─────────────┐    HTTP请求2    ┌──────────────┐
│ DocContent  │ <────────────── │ 目标服务器    │
│  Crawler    │                 │              │
└─────────────┘                 └──────────────┘
       ↓
┌─────────────┐    HTTP请求3    ┌──────────────┐
│ DocUrl      │ <────────────── │ 目标服务器    │
│  Crawler    │                 │              │
└─────────────┘                 └──────────────┘

内联提取模式：
┌─────────────┐    HTTP请求    ┌──────────────┐
│ UltimateURL │ ──────────────> │ 目标服务器    │
│   Scanner   │                 │              │
│             │ ──────────────> │              │
│  + Content  │  （内存处理）   │              │
│  Extractor  │                 └──────────────┘
└─────────────┘
       ↓
   写入CSV
       ↓
   提取内容 ──→ 保存 docContent.md
       ↓
   提取TOC ──→ 保存 docTOC.md
```

**输出结果**：

两种模式的输出文件结构完全相同：

```
documentation_output/
└── <doc_name>:<doc_version>/
    ├── <页面1标题>/
    │   ├── docContent.md    # 文档正文内容
    │   └── docTOC.md        # 目录锚点链接
    ├── <页面2标题>/
    │   ├── docContent.md
    │   └── docTOC.md
    └── ...
```

**注意事项**：

1. **线程安全**：内联提取使用线程锁保证并发安全
2. **错误处理**：提取失败不会影响扫描流程，传统爬虫仍可作为备选
3. **向后兼容**：禁用内联提取后，完全回退到传统爬虫流程
4. **内存占用**：内联提取在内存中处理HTML，不额外增加磁盘占用

---

## 完整配置示例

```json
{
  "start_url": "https://docs.example.com",
  "proxy": "http://127.0.0.1:7890",
  "delay": 0.5,
  "max_workers": 20,
  "timeout": 30,
  "max_depth": 5,
  "blacklist_domains": [
    "www.w3.org",
    "www.baidu.com",
    "github.com"
  ],
  "whitelist_domains": [
    "docs.example.com",
    "api.example.com"
  ],
  "headers_path": "headers.json",
  "output_file": "results/scan_results.csv",
  "color_output": true,
  "verbose": true,
  "extension_blacklist": [
    ".css", ".mp4", ".js", ".svg",
    ".jpg", ".png", ".gif", ".zip"
  ],
  "max_urls": 10000,
  "smart_concatenation": true,
  "debug_mode": 0,
  "url_scope_mode": 0,
  "danger_filter_enabled": 1,
  "fuzz": 0,
  "exclude_fuzzy": [
    "/blog/", "/news/", "/forum/"
  ],
  "title_filter_list": [
    "Page Not Found",
    "404 Not Found",
    "Access Denied"
  ],
  "status_code_filter": [
    404, 503, 502, 504, 403, 401, 500
  ],
  "mode": 2,
  "force_scan": 0,
  "results_dir": "results",
  "doc_dir": "documentation_output",
  "doc_name": null,
  "doc_version": "latest",
  "toc_url_filters": {
    "subdomains": ["docs.", "api."],
    "fuzzy_match": ["/docs/", "/api/"],
    "exclude_fuzzy": ["/blog/", "/news/"]
  },
  "doc_max_depth": 10,
  "doc_timeout": 30,
  "doc_toc_selector": ".bd-toc-nav.page-toc",
  "toc_filter": {
    "merge_mode": "extend",
    "toc_class_patterns": ["custom-toc"],
    "toc_link_class_patterns": ["custom-toc-item"],
    "toc_parent_class_patterns": ["custom-menu-item"],
    "content_area_patterns": ["custom-content-area"],
    "non_toc_link_patterns": ["custom-exclude-link"]
  },
  "content_filter": {
    "merge_mode": "extend",
    "documentation_preset": null,
    "non_content_selectors": [".custom-sidebar"],
    "fuzzy_keywords": ["custommenu"],
    "log_levels": ["TRACE:", "VERBOSE:"],
    "meaningless_content": ["Custom skip text"],
    "content_end_markers": ["Next steps"],
    "content_preserve_selectors": [],
    "code_container_selectors": []
  },
  "output_log_file": "results/output.out",
  "debug_log_file": "results/debug.log"
}
```

---

## 常见问题

### Q1: 如何选择合适的 `url_scope_mode`？

**A**：
- 常规扫描：使用 `0`（主域名模式）
- 需要发现外部链接：使用 `1`（外部一次模式）
- 全站深度扫描：使用 `2`（无限制模式）
- 精确目标扫描：使用 `3`（白名单模式）

### Q2: `doc_toc_selector` 什么时候需要配置？

**A**：
- Claude Code Docs、Ray Docs：使用 `null`（自动检测）
- 其他文档站点：先尝试 `null`，如果提取效果不好，再配置CSS选择器

### Q3: 如何避免被封禁？

**A**：
- 设置合理的 `delay`（建议 1-3 秒）
- 降低 `max_workers`（建议 10-20）
- 配置 `proxy` 使用代理
- 设置 `User-Agent` 模拟真实浏览器

### Q4: 多个class如何精确匹配？

**A**：
- ✅ 正确：`.bd-toc-nav.page-toc`（无空格，AND逻辑）
- ❌ 错误：`.bd-toc-nav, .page-toc`（逗号分隔，OR逻辑，可能冗余）

---

## 命令行参数快速参考

```bash
# 基础扫描
python -m doc4llm -u https://example.com

# 批量扫描
python -m doc4llm -f urls.txt

# 使用代理
python -m doc4llm -u https://example.com -proxy http://127.0.0.1:7890

# 调整线程和延迟
python -m doc4llm -u https://example.com -workers 20 -delay 1

# 设置深度
python -m doc4llm -u https://example.com -depth 3

# 文档爬取模式
python -m doc4llm -u https://docs.example.com -mode 2

# 强制刷新CSV文件（mode 1/2）
python -m doc4llm -u https://docs.example.com -mode 2 -force-scan 1

# 指定TOC选择器
python -m doc4llm -csv urls.csv -mode 2 -doc-toc-selector ".toc"

# 调试模式
python -m doc4llm -u https://example.com -debug 1

# URL范围模式
python -m doc4llm -u https://example.com -scope 3
```

---

**文档版本**: v1.2
**更新日期**: 2026-01-16
**项目**: WhiteURLScan

## 更新日志

### v1.4 (2026-01-16)
- 新增 `enable_inline_extraction` 配置参数（mode 1/2/3 时的内联提取优化）
- 新增 `ContentExtractor` 模块（扫描过程中实时提取内容/TOC）
- mode 3 新增组合模式（依次执行文档内容爬取和锚点链接提取）
- 优化 HTTP 请求次数，mode 3 性能提升约 66%
- 支持向后兼容，禁用内联提取可回退到传统爬虫流程

### v1.3 (2026-01-16)
- 将 `headers` 配置参数更改为 `headers_path`（指向 JSON 格式的 headers 文件）
- 删除 `headers.txt` 文件，统一使用 `headers.json` 格式
- 支持自定义 headers 文件路径（相对路径或绝对路径）

### v1.2 (2026-01-16)
- 新增 `toc_filter` 配置参数（管理 DocUrlCrawler 模块的预定义标签过滤规则）
- 将 `DocUrlCrawler.py` 的预定义配置整合到 `filter/config.py` 统一配置模块
- 支持 `extend` 和 `replace` 两种合并模式
- 新增 `TocFilterConfigLoader` 工具类用于从 config.json 加载配置
- 更新 `filter` 包导出，新增 TOC URL 过滤相关常量和工具类
- `filter` 包版本更新至 v2.1.0

### v1.1 (2026-01-16)
- 删除 `filter_404` 参数（已被 `status_code_filter` 替代）
- 新增 `force_scan` 参数（mode 1/2时控制是否强制刷新CSV）
- 新增 `results_dir` 参数（结果文件保存目录，支持动态文件名）
- 新增 `output_log_file` 参数（控制台输出日志文件路径）
- 新增 `debug_log_file` 参数（调试日志文件路径）
- 新增 `-config` 命令行参数（自定义配置文件路径）
- 新增 `-force-scan` 命令行参数（强制扫描刷新CSV）
