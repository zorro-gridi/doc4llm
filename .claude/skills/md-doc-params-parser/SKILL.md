---
name: md-doc-params-parser
description: "Parse doc-rag workflow data interface parameters between phases"
context: exec
allowed-tools:
  - Read
  - Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: 'python "$SCRIPT_PATH" --validate'
---

# md-doc-params-parser

## Overview

`md-doc-params-parser` is a parameter parsing tool that standardizes data interfaces between phases in the doc-rag retrieval workflow. It converts output from upstream skills into the input format required by downstream skills.

## Doc-RAG Pipeline

```
User Query
    │
    ├─── Phase 0a: md-doc-query-optimizer ──┐
    │                                       │
    └─── Phase 0b: md-doc-query-router ─────┤
                                            │
                                            ▼
                              Phase 1: md-doc-searcher ──┐
                                                         │
                                                         ▼
                                             Phase 1.5: md-doc-llm-reranker
                                                            │
                                                            ▼
                                                    Phase 2: md-doc-reader
                                                            │
                                                            ▼
                                                   Content Output
```

## Supported Phase Transitions

| From | To | Description |
|------|-----|-------------|
| 0a | 1 | Parse query-optimizer output for searcher CLI |
| 0b | 1 | Extract router config (threshold, scene) |
| **0a+0b** | **1** | **Merge outputs from both phases into searcher config** |
| 1 | 1.5 | Check if LLM reranking is needed |
| 1 | 2 | Direct pass-through (skip reranker) |
| 1.5 | 2 | Convert reranker output to reader config |

## Usage

### CLI Usage

```bash
# Phase 0a → Phase 1
conda run -n k8s python .claude/skills/md-doc-params-parser/scripts/params_parser_cli.py \
  --from-phase 0a \
  --to-phase 1 \
  --input '{"query_analysis": {"doc_set": ["OpenCode_Docs@latest"], "domain_nouns": ["hooks"], "predicate_verbs": ["create"]}, "optimized_queries": [{"rank": 1, "query": "create hooks", "strategy": "translation"}]}' \
  --knowledge-base .claude/knowledge_base.json

# Phase 0b → Phase 1
conda run -n k8s python .claude/skills/md-doc-params-parser/scripts/params_parser_cli.py \
  --from-phase 0b \
  --to-phase 1 \
  --input '{"scene": "fact_lookup", "reranker_threshold": 0.63}'

# Merge mode: Phase 0a+0b → Phase 1
# Accepts an array of outputs from both phases
conda run -n k8s python .claude/skills/md-doc-params-parser/scripts/params_parser_cli.py \
  --from-phase 0a+0b \
  --to-phase 1 \
  --input '[{"phase": "0a", "output": {"query_analysis": {"doc_set": ["OpenCode_Docs@latest"], "domain_nouns": ["hooks"], "predicate_verbs": ["create"]}, "optimized_queries": [{"rank": 1, "query": "create hooks"}]}}, {"phase": "0b", "output": {"scene": "fact_lookup", "reranker_threshold": 0.63}}]' \
  --knowledge-base .claude/knowledge_base.json

# Read input from stdin
echo '{"query_analysis": {...}}' | python params_parser_cli.py --from-phase 0a --to-phase 1 --input -
```

## Output Format

All CLI outputs are JSON with the following structure:

```json
{
  "data": {
    "query": ["create hooks"],
    "doc_sets": "OpenCode_Docs@latest",
    "domain_nouns": ["hooks"],
    "predicate_verbs": ["create"]
  },
  "from_phase": "0a",
  "to_phase": "1",
  "status": "success"
}
```

## Phase-Specific Examples

### Phase 0a → Phase 1 (query-optimizer → searcher)

**Input (optimizer output):**
```json
{
  "query_analysis": {
    "doc_set": ["OpenCode_Docs@latest", "API_Reference@latest"],
    "domain_nouns": ["hooks", "function"],
    "predicate_verbs": ["create", "register"]
  },
  "optimized_queries": [
    {"rank": 1, "query": "create hooks", "strategy": "translation"},
    {"rank": 2, "query": "register function hooks", "strategy": "expansion"}
  ]
}
```

**Output (searcher CLI config):**
```json
{
  "query": ["create hooks", "register function hooks"],
  "doc_sets": "OpenCode_Docs@latest,API_Reference@latest",
  "domain_nouns": ["hooks", "function"],
  "predicate_verbs": ["create", "register"]
}
```

### Phase 0a+0b → Phase 1 (merge outputs → searcher)

**Input (array of outputs from both phases):**
```json
[
  {
    "phase": "0a",
    "output": {
      "query_analysis": {
        "doc_set": ["OpenCode_Docs@latest"],
        "domain_nouns": ["hooks"],
        "predicate_verbs": ["create"]
      },
      "optimized_queries": [
        {"rank": 1, "query": "create hooks"}
      ]
    }
  },
  {
    "phase": "0b",
    "output": {
      "scene": "fact_lookup",
      "reranker_threshold": 0.63
    }
  }
]
```

**Output (merged searcher CLI config):**
```json
{
  "query": ["create hooks"],
  "doc_sets": "OpenCode_Docs@latest",
  "domain_nouns": ["hooks"],
  "predicate_verbs": ["create"],
  "reranker_threshold": 0.63,
  "scene": "fact_lookup"
}
```

## Validation

The parser validates upstream output against expected schemas:

```bash
# Run with validation (default)
python params_parser_cli.py --from-phase 0a --to-phase 1 --input '...'

# Skip validation
python params_parser_cli.py --from-phase 0a --to-phase 1 --input '...' --no-validate
```

## Files

```
.claude/skills/md-doc-params-parser/
├── SKILL.md                   # This file
├── scripts/
│   ├── __init__.py
│   ├── config_schema.py       # Phase I/O schema definitions
│   ├── phase_parser.py        # Phase-specific parsers
│   ├── parser_factory.py      # Factory for creating parsers
│   └── params_parser_cli.py   # CLI entry point
└── reference/
    └── DATA_INTERFACE.md      # Data interface specification
```

## Dependencies

- Python 3.10+
- Standard library only (json, argparse, pathlib)
