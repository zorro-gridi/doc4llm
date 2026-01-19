# Configuration

Config location: `scripts/config.json`

## Config Loading Priority

The `MarkdownDocExtractor` loads configuration in the following order (highest to lowest priority):

1. **`--config` CLI argument** - Explicitly specified config file path
2. **`scripts/config.json`** - Skill's default config file
3. **Hardcoded defaults** - Built-in default values
4. **Package config** - Deprecated package-level config (shows warning)

## Config Structure

```json
{
  "base_dir": "md_docs",
  "default_search_mode": "exact",
  "case_sensitive": false,
  "max_results": 10,
  "fuzzy_threshold": 0.6,
  "enable_fallback": true,
  "fallback_modes": ["case_insensitive", "partial", "fuzzy"],
  "compress_threshold": 2000,
  "enable_compression": false,
  "debug_mode": 0
}
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `base_dir` | string | `"md_docs"` | Base documentation directory path |
| `default_search_mode` | string | `"exact"` | Search mode: `"exact"`, `"case_insensitive"`, `"fuzzy"`, `"partial"` |
| `case_sensitive` | bool | `false` | Whether exact matching is case sensitive |
| `max_results` | int | `10` | Max results for fuzzy/partial searches |
| `fuzzy_threshold` | float | `0.6` | Minimum similarity ratio (0.0 to 1.0) for fuzzy matching |
| `enable_fallback` | bool | `true` | Enable automatic fallback to other search modes on failure |
| `fallback_modes` | list | `["case_insensitive", "partial", "fuzzy"]` | List of fallback search modes to try |
| `compress_threshold` | int | `2000` | Line count threshold for content compression |
| `enable_compression` | bool | `false` | Enable automatic content compression for large documents |
| `debug_mode` | int | `0` | Debug output (0=off, 1=on) |

## Usage Examples

### Python API with Config

```python
# Load from default config file
extractor = MarkdownDocExtractor.from_config()

# Load from custom config file
extractor = MarkdownDocExtractor.from_config(config_path="/path/to/config.json")

# Load from config dict
config = {
    "base_dir": "md_docs",
    "default_search_mode": "fuzzy",
    "fuzzy_threshold": 0.7
}
extractor = MarkdownDocExtractor.from_config(config_dict=config)
```

### CLI with Config

```bash
# Use default config (scripts/config.json)
python scripts/extract_md_doc.py --title "Agent Skills"

# Use custom config file
python scripts/extract_md_doc.py --config /path/to/config.json --title "Agent Skills"
```

## Search Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `exact` | Requires exact title match | Known exact titles |
| `case_insensitive` | Case-insensitive exact match | Titles with uncertain casing |
| `fuzzy` | Fuzzy string matching with similarity threshold | Typos or approximate titles |
| `partial` | Matches titles containing query as substring | Searching for keywords in titles |

## See Also

- [CLI Reference](cli.md)
- [Python API Reference](python_api.md)
- [SKILL.md](../SKILL.md)
