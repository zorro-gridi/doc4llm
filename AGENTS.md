# AGENT.md

This file provides guidance to OpenCode (opencode.ai) when working with code in this repository.

## Project Overview

doc4llm is a documentation crawler for LLM training data. It features recursive URL scanning, intelligent path concatenation, content filtering, and documentation conversion to markdown format with multi-threaded concurrent execution.

**Important:** This is a security testing tool. Only assist with authorized security testing, defensive security, CTF challenges, and educational contexts.

## Development Commands

### Environment Setup

**IMPORTANT:** All Python scripts must be executed within the `k8s` conda virtual environment.

```bash
# Activate the k8s conda environment
conda activate k8s

# Install dependencies (first time only)
pip install -r requirements.txt
```

### Running the Scanner

**IMPORTANT:** Always activate the `k8s` conda environment before running any Python scripts.

**Single URL:**
```bash
python doc4llm.py -u https://example.com -workers 20 -delay 1 -timeout 8 -depth 3
```

**Batch URL file:**
```bash
python doc4llm.py -f url.txt -workers 20 -delay 1 -timeout 8 -depth 3
```

**Fuzz mode (custom URL concatenation):**
```bash
python doc4llm.py -f url.txt -fuzz 1 -proxy http://127.0.0.1:8080
```

**Whitelist mode:**
```bash
python doc4llm.py -f url.txt -fuzz 1 -scope 3 -danger 1 -proxy http://127.0.0.1:8080
```

### Command-Line Arguments

| Argument | Description |
|----------|-------------|
| `-u` | Starting URL |
| `-f` | Batch URL file path |
| `-delay` | Delay between requests (seconds) |
| `-workers` | Max thread count |
| `-timeout` | Request timeout (seconds) |
| `-depth` | Max recursion depth |
| `-out` | Real-time output file path |
| `-proxy` | Proxy URL |
| `-debug` | Debug mode (1=on, 0=off) |
| `-scope` | URL scope: 0=main domain only, 1=external once, 2=unlimited, 3=whitelist |
| `-danger` | Dangerous API filter (1=on, 0=off) |
| `-fuzz` | Enable custom URL concatenation (0=off, 1=on) |

## Architecture

### Entry Point and Core Module

**`doc4llm/`** - The main package directory containing all core modules. The primary entry point is `doc4llm/cli.py`.

### Core Class Architecture

| Class | Purpose |
|-------|---------|
| `OutputLogger` | Redirects stdout/stderr to log file while preserving console output |
| `DebugMixin` | Mixin providing debug printing functionality |
| `ScannerConfig` | Configuration management for all scanner settings |
| `URLConcatenator` | Smart URL concatenation for relative/absolute paths, API routes, fuzz mode |
| `URLMatcher` | URL validation, domain filtering, extraction from content |
| `SensitiveDetector` | Regex-based sensitive information detection |
| `OutputHandler` | CSV output writing and result formatting |
| `UltimateURLScanner` | Main scanner with connection pooling and thread management |

### Supporting Modules

| File | Purpose |
|------|---------|
| `LinkProcessor.py` | Converts relative links to absolute links in HTML |
| `MarkdownConverter.py` | HTML to Markdown conversion using html2text with format cleaning |
| `WebContentExtractor.py` | Web page fetching, HTML processing, content extraction |
| `WebTextCrawler.py` | Entry point for web content extraction workflow |
| `DocContentCrawler.py` | Documentation crawler for scraping and converting doc sites |
| `filter/` | Content filtering package (removes nav, footer, and other non-content blocks) |

#### Filter Package Architecture

The `filter/` directory contains the content filtering system:

| File | Purpose |
|------|---------|
| `filter/base.py` | Abstract base class defining the filter interface |
| `filter/standard.py` | `ContentFilter` - Basic filter for most websites |
| `filter/enhanced.py` | `EnhancedContentFilter` - Advanced filter with smart detection |
| `filter/config.py` | Unified configuration module for all filter presets |
| `filter/factory.py` | Factory for creating filters based on URL or preset |
| `filter/__init__.py` | Package exports and version info |
| `filter/FILTER_CONFIG.md` | Detailed configuration guide |

### Configuration

**`config.json`** - Main configuration file (auto-generated on first run). Key settings:
- `start_url`, `max_workers`, `timeout`, `max_depth`
- `blacklist_domains`, `whitelist_domains`
- `extension_blacklist` (file extensions to skip)
- `url_scope_mode` (0=main domain, 1=external once, 2=unlimited, 3=whitelist)
- `danger_api_list`, `danger_filter_enabled`
- `fuzz`, `custom_base_url`, `path_route`, `api_route`
- **`content_filter`** - Content filter configuration (NEW in v2.0.0):
  - `merge_mode`: Configuration merge mode (`"extend"` or `"replace"`)
  - `documentation_preset`: Framework preset (`"mintlify"`, `"docusaurus"`, `"vitepress"`, `"gitbook"`)
  - `non_content_selectors`: Custom CSS selectors to remove
  - `fuzzy_keywords`: Keywords for fuzzy matching class/id
  - `log_levels`: Custom log levels to filter
  - `meaningless_content`: Custom meaningless text to remove
  - `content_end_markers`: Patterns that mark end of main content (e.g., "Next steps")
  - `content_preserve_selectors`: Selectors for content to prioritize
  - `code_container_selectors`: Selectors for code blocks

**`headers.json`** - Custom HTTP headers for requests (JSON format)

### Output

Results are saved to the `results/` directory:
- CSV files with scan results
- `output.out` log file

### Code Patterns

- **Mixin Pattern**: `DebugMixin` provides debug functionality
- **Threading**: Thread-safe operations with `threading.Lock()`
- **Connection Pooling**: `requests.Session` with `HTTPAdapter`
- **Decorator Pattern**: `@handle_exceptions` for error handling
- **Regex-based Detection**: Extensive patterns for sensitive data (Chinese ID cards, cloud API keys, JWT tokens, SSH keys, etc.)

## URL Scope Modes

- **0** (main domain): Only scans the target domain, records external URLs to file
- **1** (external once): Scans target domain + visits external links once (no recursion on external domains)
- **2** (unlimited): Scans all links recursively (limited only by depth and max_urls)
- **3** (whitelist): Only scans domains in `whitelist_domains` config

## Dependencies

- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `tldextract` - Domain extraction
- `colorama` - Colored console output
- `urllib3` - HTTP utilities
- `html2text` - HTML to Markdown conversion (used by filter module)

## OpenCode Interaction Guidelines

### General Behavior

- Be concise, direct, and to the point
- Minimize output tokens while maintaining helpfulness
- Answer concisely with fewer than 4 lines unless user asks for detail
- Avoid unnecessary preamble or postamble
- Only use emojis if explicitly requested

### Tool Usage

- **File Operations**: Use `Read` before `Write` or `Edit` on existing files
- **Bash Commands**: Avoid using `cd` - use `workdir` parameter instead
- **Search**: Use `grep` for content, `glob` for file patterns
- **Web Fetching**: Use `webfetch` for URL content retrieval

### Code Development

- Follow existing code conventions and patterns
- Mimic code style from existing files
- Never commit unless explicitly requested
- Run lint/typecheck commands if available
- Verify solutions with tests when possible

### Security Considerations

- Refuse malicious code requests
- Do not generate code for malware or attacks
- Never expose secrets or keys in code
