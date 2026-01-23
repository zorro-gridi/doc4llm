---
name: md-doc-processor
description: >
  Document-level Content Filter & Compressor.
  Receives full markdown documentation and user query.
  Decides whether to bypass or perform query-relevant intelligent compression based on:
  (1) document line count threshold and
  (2) user intent and scene type.
  Outputs processed_doc plus compression metadata for downstream md-doc-sence-output.
context: fork
disable-model-invocation: true
allowed-tools:
  - Read
  - Bash
---

# Markdown Document Processor (Document-Level)

## Role

This skill is the **document-level processing phase** of the doc-retriever workflow.

It is responsible ONLY for:
- Deciding whether to compress/cut the document
- Performing query-relevant intelligent extraction
- Preserving code blocks, APIs, configs, and warnings
- Outputting processed markdown + compression metadata

It does NOT:
- Control output language
- Assemble Sources
- Decide scene-specific output style

---

## Input Contract

You receive the following fields:

```json
{
  "user_query": "string",
  "scene": "fact_lookup | faithful_reference | faithful_how_to | concept_learning | how_to | comparison | exploration",
  "full_doc_content": "string (markdown)",
  "line_count": 2850,
  "doc_meta": {
    "title": "string",
    "source_url": "string",
    "local_path": "string"
  }
}
````

---

## Decision Rules

### Rule 1: Bypass Compression

Bypass compression and return full content if:

* scene is one of:

  * faithful_reference
  * faithful_how_to

OR

* user_query contains any of:

  * Chinese: 不压缩, 完整内容, 原文, 全部内容, 不要压缩
  * English: full content, no compression, original, uncompressed

---

### Rule 2: Perform Intelligent Compression

Trigger compression if:

* line_count > 2100

OR

* user explicitly requests compression:

  * Chinese: 压缩, 总结, 精简
  * English: compress, summarize, condense

---

## Compression Principles

1. Semantic Fidelity

   * Do NOT change technical meaning
   * Do NOT alter code or configs

2. Query Relevance

   * Extract sections aligned with user_query intent

3. Smart Extraction (NOT truncation)

   * Keep full relevant sections
   * Remove unrelated chapters entirely

---

## Preservation Rules

| Content Type         | Strategy              |
| -------------------- | --------------------- |
| Code blocks          | Always preserve fully |
| API definitions      | Always preserve fully |
| Config examples      | Always preserve fully |
| Critical warnings    | Always preserve fully |
| Query-relevant parts | Preserve in full      |
| Repetitive examples  | Keep 1–2 only         |
| Unrelated sections   | Remove entirely       |

---

## Output Contract

You must return:

```json
{
  "processed_doc": "string (markdown)",
  "compression_applied": true,
  "original_line_count": 2850,
  "output_line_count": 1980,
  "doc_meta": {
    "title": "Hooks reference",
    "source_url": "https://code.claude.com/docs/en/hooks",
    "local_path": "md_docs/Claude_Code_Docs@latest/Hooks reference/docContent.md"
  }
}
```

---

## Output Rules

* Output must be raw markdown only
* Do NOT:

  * Add Sources
  * Translate language
  * Change structure for presentation
* Only modify content for compression / extraction

---

## Quality Standards

* ✅ Maintain technical accuracy
* ✅ Preserve code syntax
* ✅ Keep complete sections (not partial sentences)
* ❌ Do NOT cut sentences mid-way
* ❌ Do NOT rewrite in teaching style
* ❌ Do NOT change terminology
