---
name: md-doc-rag
description: Execute documentation retrieval queries against local markdown docs using Doc-RAG pipeline. Use when user wants to search documentation and get relevant content from local markdown files.
context: fork
---

# md-doc-rag Skill

Execute documentation retrieval queries against local markdown documentation using the Doc-RAG (Retrieval-Augmented Generation) pipeline.

## Rules
1. 保留用户完整的查询输入文本，作为"query"参数
2. Complete Example 中的其它 CLI 参数调用时都要传递，保持与参数值一致
3. 调用这个 skill 时，tiemout 超时时间设置为 5 分钟

## Quick Start
```bash
conda init
```

```bash
conda run -n k8s docrag "Your Query" [OPTIONS]
```

## Complete Example

```bash
conda run -n k8s docrag \
  "<Your Query>" \
  --kb .claude/knowledge_base.json \
  --threshold 3000 \
  --llm-reranker \
  --reranker-threshold 0.6 \
  --skip-keywords doc4llm/doc_rag/searcher/skiped_keywords.txt
```

## CLI Arguments

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `query` | - | string | required | User query text |
| `--kb` | `-k` | string | `.claude/knowledge_base.json` | Path to knowledge_base.json |
| `--knowledge-base` | `-k` | string | `.claude/knowledge_base.json` | Alias for --kb |
| `--threshold` | `-t` | int | `2100` | Line count threshold |
| `--llm-reranker` | - | flag | `False` | Enable LLM re-ranking |
| `--embedding-reranker` | - | flag | `False` | Enable embedding re-ranking |
| `--reranker-threshold` | - | float | `0.6` | Re-ranking threshold |
| `--skip-keywords` | - | string | doc4llm/doc_rag/searcher/skiped_keywords.txt | Skip keywords file path |
| `--output` | `-o` | string | - | Save output to file |
| `--json` | - | flag | `False` | JSON output format |
| `--debug` | - | flag | `False` | Debug mode |