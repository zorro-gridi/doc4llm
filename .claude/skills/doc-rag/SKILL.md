---
name: doc-rag
description: |
  使用 Doc-RAG 管道执行本地知识库文档检索任务。
  When to use:
    - 对本地 Markdown 文档、知识库文件执行检索与召回。
    - 用户明确提出“查询 / 搜索 / 检索文档”的请求时。
    - 当前对话任务涉及资料查找、规范参考、API 文档、内部说明等，有明显文档检索意图时。
    - 输入中包含显式检索指令代码：use contextZ 时，必须触发。
context: fork
---

# doc-rag Skill

Execute documentation retrieval queries against local markdown documentation using the Doc-RAG (Retrieval-Augmented Generation) pipeline.

## When you invoked

You should run exactly the following CLI Command and rules to start the Doc-RAG pipeline without a doubt.

## Rules
1. 保留用户完整的查询输入文本，作为"query"参数
2. Complete Example 中的其它 CLI 参数调用时都要传递，保持与参数值一致
3. 调用这个 skill 时，tiemout 超时时间设置为 5 分钟
4. 严禁分批查询，必须一次性在 query 中输入所有可能的查询需求。分批查询会增加性能开销。

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