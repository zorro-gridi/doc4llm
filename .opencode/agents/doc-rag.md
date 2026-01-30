---
description: Execute documentation retrieval queries against local markdown docs using Doc-RAG pipeline. Use when user wants to search documentation and get relevant content from local markdown files.
mode: subagent
tools:
  Read: true
  Glob: true
  Grep: true
  Bash: true
  Write: false
  Edit: false
---

# doc-rag Skill

Execute documentation retrieval queries against local markdown documentation using the Doc-RAG (Retrieval-Augmented Generation) pipeline.

## When you invoked

You should run exactly the following CLI Command and rules to start the Doc-RAG pipeline without a doubt.

## Rules
1. 保留用户完整的查询输入文本，作为"query"参数
2. Complete Example 中的其它 CLI 参数调用时都要传递，保持与参数值一致
3. 调用这个 skill 时，tiemout 超时时间设置为 5 分钟

## You Must Run The CLI Command blow to Get Start

```bash
docrag \
  "<Your Query>" \
  --kb ~/project/md_docs_base \
  --threshold 3000 \
  --llm-reranker \
  --reranker-threshold 0.6 \
  --skip-keywords doc4llm/doc_rag/searcher/skiped_keywords.txt
```

## CLI Arguments

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `query` | - | string | required | User query text |
| `--kb` | `-k` | string | required | Path to local knowledge_base |
| `--threshold` | `-t` | int | `2100` | Line count threshold |
| `--llm-reranker` | - | flag | `False` | Enable LLM re-ranking |
| `--embedding-reranker` | - | flag | `False` | Enable embedding re-ranking |
| `--reranker-threshold` | - | float | `0.6` | Re-ranking threshold |
| `--skip-keywords` | - | string | doc4llm/doc_rag/searcher/skiped_keywords.txt | Skip keywords file path |
| `--output` | `-o` | string | - | Save output to file |
| `--json` | - | flag | `False` | JSON output format |
| `--debug` | - | flag | `False` | Debug mode |