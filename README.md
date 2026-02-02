# doc4llm

> A powerful documentation crawler for LLM training data collection

## Overview

doc4llm is a documentation crawler designed for collecting and converting web documentation into structured Markdown format for LLM training data. It features recursive URL scanning, intelligent path concatenation, content filtering, and HTML-to-Markdown conversion with multi-threaded concurrent execution.

## Features

### Core Capabilities

- **Recursive URL Scanning**: Automatically discovers and scans all reachable URLs with duplicate detection
- **Smart Path Concatenation**: Handles relative/absolute paths, API routes, and custom base URL concatenation
- **Content Filtering**: Removes navigation, footers, and non-content blocks from documentation
- **HTML to Markdown**: Converts web pages to clean Markdown format
- **Multi-threaded Execution**: Concurrent scanning for improved performance
- **Sensitive Data Detection**: Regex-based detection of sensitive information (API keys, credentials, etc.)
- **Framework Presets**: Built-in support for Mintlify, Docusaurus, VitePress, and GitBook

### Modes of Operation

| Mode | Description |
|------|-------------|
| **0** | URL scan only - outputs to CSV file |
| **1** | Document content crawling - saves Markdown files |
| **2** | Anchor link extraction - extracts TOC links |
| **3** | Combined mode - executes content crawl and anchor extraction |
| **4** | Single page crawl - crawls only the specified URL (no recursion, no CSV) |

### URL Scope Modes

| Mode | Behavior |
|------|----------|
| **0** | Main domain only - records external URLs |
| **1** | External links visited once (no recursion on external domains) |
| **2** | Unlimited - scans all links recursively |
| **3** | Whitelist mode - only scans domains in `whitelist_domains` |

## Installation

```bash
pip install -r requirements.txt
```

### Requirements

- Python 3.7+
- requests
- beautifulsoup4
- tldextract
- colorama
- html2text

## Quick Start

### Basic URL Scan

```bash
python -m doc4llm -u https://example.com -workers 20 -delay 1 -timeout 8 -depth 3
```

### Document Crawling (Mode 3 - Recommended)

```bash
python -m doc4llm -u https://docs.example.com -mode 3 -force-scan 1
```

### Batch URL File

```bash
python -m doc4llm -f urls.txt -workers 20 -delay 1 -timeout 8 -depth 3
```

### With Proxy

```bash
python -m doc4llm -u https://example.com -proxy http://127.0.0.1:8080
```

### Fuzz Mode (Custom URL Concatenation)

```bash
python -m doc4llm -f urls.txt -fuzz 1 -scope 3
```

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-u` | Starting URL | - |
| `-f` | Batch URL file path | - |
| `-config` | Config file path | `doc4llm/config/config.json` |
| `-workers` | Max thread count | 30 |
| `-delay` | Delay between requests (seconds) | 0.1 |
| `-timeout` | Request timeout (seconds) | 20 |
| `-depth` | Max recursion depth | 5 |
| `-out` | Real-time output file path | `results/实时输出文件.csv` |
| `-proxy` | Proxy URL | - |
| `-debug` | Debug mode (1=on, 0=off) | 0 |
| `-scope` | URL scope mode (0/1/2/3) | 0 |
| `-danger` | Dangerous API filter (1=on, 0=off) | 1 |
| `-fuzz` | Enable custom URL concatenation (1=on, 0=off) | 0 |
| `-mode` | Crawl mode (0/1/2/3) | 0 |
| `-force-scan` | Force URL scan refresh (mode 1/2/3) | 0 |
| `-doc-dir` | Document output directory | `md_docs` |
| `-doc-name` | Document name (overrides auto-detect) | - |
| `-doc-version` | Document version tag | `latest` |
| `-doc-depth` | Max document crawl depth | 10 |
| `-doc-toc-selector` | TOC CSS selector (e.g., `.toc`, `#navigation`) | - |

## Configuration

First run generates `doc4llm/config/config.json` automatically:

```json
{
  "start_url": null,
  "max_workers": 30,
  "timeout": 20,
  "max_depth": 5,
  "delay": 0.1,
  "proxy": null,
  "blacklist_domains": ["www.w3.org", "www.baidu.com", "github.com"],
  "whitelist_domains": [],
  "extension_blacklist": [".css", ".mp4"],
  "max_urls": 10000,
  "url_scope_mode": 0,
  "danger_filter_enabled": 1,
  "danger_api_list": ["del", "delete", "insert", "logout"],
  "is_duplicate": 0,
  "fuzz": 0,
  "custom_base_url": [],
  "path_route": [],
  "api_route": [],
  "mode": 0,
  "force_scan": 0,
  "doc_dir": "md_docs",
  "doc_name": null,
  "doc_version": "latest",
  "doc_max_depth": 10,
  "doc_timeout": 30,
  "output_file": "results/实时输出文件.csv",
  "results_dir": "results",
  "output_log_file": "results/output.out",
  "debug_log_file": "results/debug.log",
  "log_max_lines": 10000,
  "content_filter": {
    "merge_mode": "extend",
    "documentation_preset": null,
    "non_content_selectors": [],
    "fuzzy_keywords": [],
    "log_levels": [],
    "meaningless_content": [],
    "content_end_markers": [],
    "content_preserve_selectors": [],
    "code_container_selectors": []
  },
  "toc_filter": {
    "merge_mode": "extend",
    "toc_class_patterns": [],
    "toc_link_class_patterns": [],
    "toc_parent_class_patterns": [],
    "content_area_patterns": [],
    "non_toc_link_patterns": [],
    "toc_end_markers": []
  }
}
```

### Content Filter Configuration

The `content_filter` section allows customization of content extraction:

| Option | Description |
|--------|-------------|
| `merge_mode` | `"extend"` to add to defaults, `"replace"` to override |
| `documentation_preset` | Framework preset: `"mintlify"`, `"docusaurus"`, `"vitepress"`, `"gitbook"` |
| `non_content_selectors` | CSS selectors to remove (nav, footer, etc.) |
| `fuzzy_keywords` | Keywords for fuzzy matching class/id |
| `content_end_markers` | Patterns marking end of main content (e.g., "Next steps") |

## Output Structure

### URL Scan Results

```
results/
├── 实时输出文件.csv          # Main scan results
├── all_results_YYYYMMDD.csv  # Batch scan summary
├── output.out                # Console output log
└── debug.log                 # Debug log (when debug_mode=1)
```

### Document Output (Mode 1/3)

```
md_docs/
└── <doc_name>@<doc_version>/
    ├── Page 1 Title/
    │   └── docContent.md
    ├── Page 2 Title/
    │   └── docContent.md
    └── ...
```

## Architecture

### Package Structure

```
doc4llm/
├── __init__.py           # Package exports
├── __main__.py           # Entry point for `python -m doc4llm`
├── cli.py               # Main CLI interface
├── main.py              # Alternative entry point
├── scanner/             # URL scanning module
│   ├── config.py        # ScannerConfig
│   ├── scanner.py       # UltimateURLScanner
│   ├── url_matcher.py   # URLMatcher
│   ├── url_utils.py     # URLConcatenator
│   ├── sensitive_detector.py  # SensitiveDetector
│   ├── output_handler.py      # OutputHandler
│   └── utils.py         # Utilities
├── crawler/             # Document crawling
│   ├── DocUrlCrawler.py       # Anchor link extraction
│   └── DocContentCrawler.py   # Content crawling
├── extractor/           # Web content extraction
│   └── WebContentExtractor.py
├── link_processor/      # Link processing
│   └── LinkProcessor.py
├── convertor/           # HTML to Markdown
│   └── MarkdownConverter.py
└── filter/              # Content filtering
    ├── base.py          # BaseContentFilter
    ├── standard.py      # ContentFilter
    ├── enhanced.py      # EnhancedContentFilter
    ├── config.py        # Filter configurations
    └── factory.py       # FilterFactory
```

### Key Classes

| Class | Purpose |
|-------|---------|
| `UltimateURLScanner` | Main URL scanner with connection pooling |
| `ScannerConfig` | Configuration management |
| `DocContentCrawler` | Document content crawler |
| `DocUrlCrawler` | Anchor/TOC link extractor |
| `ContentFilter` | Standard content filter |
| `EnhancedContentFilter` | Advanced filter with framework detection |
| `MarkdownConverter` | HTML to Markdown conversion |

## Usage Examples

### Scan a Documentation Site

```bash
# Full pipeline: scan URLs, extract content, extract TOC
python -m doc4llm -u https://docs.example.com -mode 3 -force-scan 1 -workers 20
```

### Reuse Existing CSV

```bash
# Skip URL scan if CSV exists and has content
python -m doc4llm -u https://docs.example.com -mode 3 -force-scan 0
```

### Custom Document Name

```bash
python -m doc4llm -u https://docs.example.com -mode 1 -doc-name mydocs -doc-version v1.0
```

### Single Page Crawl (Mode 4)

```bash
# Crawl only the specified URL, no recursion, no CSV generation
python -m doc4llm -u https://docs.example.com/page -mode 4
```

### Scope-Limited Scanning

```bash
# Only scan main domain
python -m doc4llm -u https://example.com -scope 0

# Scan with external links (no recursion)
python -m doc4llm -u https://example.com -scope 1

# Whitelist mode
python -m doc4llm -u https://example.com -scope 3
```

## Development

### Entry Points

- `python -m doc4llm` - Main CLI entry point
- `python doc4llm/cli.py` - Direct CLI execution
- `python doc4llm/main.py` - Alternative entry point

### Testing

```bash
# Run with debug mode
python -m doc4llm -u https://example.com -debug 1

# Check debug log
cat results/debug.log
```

## License

MIT License

## Author

Zorro - [GitHub](https://github.com/zorro-gridi/doc4llm)
