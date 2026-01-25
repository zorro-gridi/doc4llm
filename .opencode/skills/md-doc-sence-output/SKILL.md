---
name: md-doc-sence-output
description: >
  Scene-based Response Composer.
  Receives classified query scene, routing parameters,
  and processed markdown document from md-doc-processor.
  Produces the final user-facing answer using scene-specific
  output strategies (precision, fidelity, coverage, depth).
context: fork
disable-model-invocation: true
---

# Scene-Based Output Composer

## Role

This skill is the **final output phase** of the doc-retriever workflow.

It is responsible for:
- Formatting the final answer based on query scene
- Choosing fidelity vs synthesis vs analysis style
- Assembling Sources
- Applying default language rules
- Adding compression notices when applicable

It does NOT:
- Perform document compression
- Modify raw document content for size

---

## Input Contract

```json
{
  "scene": "fact_lookup | faithful_reference | faithful_how_to | concept_learning | how_to | comparison | exploration",
  "routing_params": {
    "confidence": 0.82,
    "ambiguity": 0.15,
    "coverage_need": 0.7,
    "reranker_threshold": 0.63
  },
  "processed_doc": "string (markdown)",
  "compression_meta": {
    "compression_applied": true,
    "original_line_count": 2850,
    "output_line_count": 1980
  },
  "doc_meta": {
    "title": "Hooks reference",
    "source_url": "https://code.claude.com/docs/en/hooks",
    "local_path": "md_docs/Claude_Code_Docs@latest/Hooks reference/docContent.md"
  }
}
````

---

## Default Output Rules

* Default language: Chinese (中文)
* Technical terms: English in parentheses on first appearance
* Code blocks: Never translated
* Always include Sources section

---

## Scene → Output Strategy

| Scene              | Output Strategy                  |
| ------------------ | -------------------------------- |
| fact_lookup        | Short, precise answer + citation |
| faithful_reference | Verbatim original paragraphs     |
| faithful_how_to    | Verbatim ordered steps           |
| concept_learning   | 教学式结构化讲解                         |
| how_to             | 规范化可执行步骤                         |
| comparison         | 表格 + 优缺点 + 推荐                    |
| exploration        | 多角度深度分析                          |

---

## Output Assembly Rules

### 1. Main Content

Format content based on scene:

* faithful_* → minimal paraphrasing
* concept / exploration → structured explanation
* how_to → ordered, actionable steps
* comparison → table + recommendation

---

### 2. Compression Notice (Conditional)

If `compression_meta.compression_applied == true`:

Append:

```markdown
---

**注意：源文档已被压缩输出；原文: {{original_line_count}} 行，当前输出: {{output_line_count}} 行**
```

---

### 3. Sources Section (REQUIRED)

Always append:

```markdown
---

### 文档来源 (Sources)

1. **{{doc_meta.title}}**
   - 原文链接: {{doc_meta.source_url}}
   - 路径: `{{doc_meta.local_path}}`
```

---

## Output Rules

* Output must be valid Markdown
* Do NOT hallucinate facts in faithful scenes
* Do NOT omit Sources
* Do NOT change code or configs

---

## Quality Controls

* High fidelity in faithful_* scenes
* Clear structure in concept/how_to
* Depth and insight in exploration
* Precision in fact_lookup
