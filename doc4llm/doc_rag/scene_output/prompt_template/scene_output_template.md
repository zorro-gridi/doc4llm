
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
| concept_learning   | 教学式结构化讲解                    |
| how_to             | 规范化可执行步骤                    |
| comparison         | 表格 + 优缺点 + 推荐                |
| exploration        | 多角度深度分析                      |

---

## Output Assembly Rules

### 1. Main Content

Format content based on scene:

* faithful_* → minimal paraphrasing
* concept / exploration → structured explanation
* how_to → ordered, actionable steps
* comparison → table + recommendation

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

---

# The Related Raw Docs Data Info
## 1. Oringal Query Sence
### {scene}

## 2. Raw Content Input
```json
{READER_OUTPUT_CONTENT}
````

## Your Task
Base on the Specific Query Sence Out Requirements and Rules, output a proper format of the docs content for users. Let's Start!