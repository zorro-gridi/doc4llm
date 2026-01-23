# Scene Definitions - Detailed Reference

This file contains detailed definitions, patterns, and examples for all seven retrieval scenes.

---

## 1. Fact Lookup (fact_lookup)

**Base Threshold:** 0.85

### Definition
User wants a **specific, unique, locatable** fact or direct quote from the documentation.

### User Intent
"Tell me a specific answer / exact location / precise value"

### Typical Query Patterns

| Pattern | Example |
|---------|---------|
| Version/number questions | "What is the version number of X?" |
| Location questions | "In which chapter is Y mentioned?" |
| Definition questions | "What is the exact definition of Z in the docs?" |
| Parameter values | "What is the default timeout value?" |
| Boolean existence | "Does feature X support Y?" |

### Output Goals
- Short, accurate, with citations
- No long analysis needed
- Direct quote preferred

### Why High Threshold?
Precision matters - **better to miss than to hallucinate**. Only highly relevant content should be included.

---

## 2. Faithful Reference (faithful_reference)

**Base Threshold:** 0.90

### Definition
User requests **high-fidelity reproduction** of documentation content with minimal paraphrasing.

### User Intent
"I want to see exactly what the documentation says"

### Typical Query Patterns

| Pattern | Example |
|---------|---------|
| Direct text requests | "Show me the original text about X" |
| Quote requests | "Quote the section on Y" |
| Verbatim reproduction | "Output the relevant paragraphs word-for-word" |
| Preservation requests | "Keep the original wording and structure" |

### Output Goals
- Original text as primary content
- Preserve structure, wording, paragraph breaks
- Minimal summarization or rewording
- Compression only if content is extremely long

### Why Highest Threshold?
High-fidelity output requires **strong relevance** - avoid introducing any non-original or weakly related content.

---

## 3. Faithful How-To (faithful_how_to)

**Base Threshold:** 0.82

### Definition
User requests **high-fidelity reproduction** of documentation content that contains **procedural steps**, requiring both original text preservation AND actionable operational guidance.

### User Intent
"I want to see exactly what the documentation says about how to do this"

### Typical Query Patterns

| Pattern | Example |
|---------|---------|
| Exact steps requests | "Show me the exact documentation steps for X" |
| Quote + procedure | "Quote the deployment instructions for Y" |
| Verbatim tutorial | "Output the installation guide word-for-word" |
| Original procedure requests | "Keep the original wording for the setup process" |
| Reference how-to | "Show me the official docs on how to configure X" |

### Key Distinction from how_to

| Attribute | faithful_how_to | how_to |
|-----------|-----------------|--------|
| **Source Requirement** | Explicit source specified | No specific source |
| **Precision** | Exact original text | Usable steps acceptable |
| **Error Tolerance** | Low (deviation causes failure) | High (multiple approaches valid) |

### Output Goals
- Original text as primary content
- Preserve structure, wording, paragraph breaks
- Step-by-step format within the original text
- Actionable, reproducible content
- Include prerequisites as documented
- Minimal summarization or rewording

### Why Medium-Lower Threshold?
Need to both consider the faithful_reference & how_to retrieval output, so just lower the threshold to get more message to make a decision.

---

## 4. Concept Learning (concept_learning)

**Base Threshold:** 0.65

### Definition
User seeks **systematic understanding** of a concept: definition, composition, principles, relationships.

### User Intent
"Teach me about this concept thoroughly"

### Typical Query Patterns

| Pattern | Example |
|---------|---------|
| What-is questions | "What is X?" |
| How-works questions | "How does X work under the hood?" |
| Difference questions | "What's the difference between X and Y?" |
| Principle questions | "What are the core principles of X?" |
| Architecture questions | "Explain the architecture of X" |

### Output Goals
- Structured explanation
- Definition → Principles → Relationships → Examples
- Educational progression
- Multiple angles welcome

### Why Medium-Low Threshold?
Learning benefits from **multiple perspectives** - not a single correct answer. Allow moderately related context to enrich understanding.

---

## 5. How-To (how_to)

**Base Threshold:** 0.70

### Definition
User wants to know **how to execute an operation or follow a process**.

### User Intent
"What steps do I take to accomplish this?"

### Typical Query Patterns

| Pattern | Example |
|---------|---------|
| How-to questions | "How do I configure X?" |
| Step requests | "What are the steps to implement Y?" |
| Deployment questions | "How do I deploy Z to production?" |
| Setup questions | "Set up X for me" |
| Tutorial requests | "Walk me through using feature Y" |

### Classification Boundary

Use **how_to** when NONE of the following conditions are met:
- Information source is explicitly specified (Q1)
- Precision keywords are present (Q2)
- Operation has strict order/parameter dependencies (Q3)

When any condition above is met → classify as **faithful_how_to**

### Output Goals
- Step-by-step format
- Actionable, reproducible
- Clear sequence
- Include prerequisites

### Why Medium Threshold?
Steps should be accurate, but **multiple valid approaches may exist**. Don't require single-source exclusivity.

---

## 6. Comparison (comparison)

**Base Threshold:** 0.63

### Definition
User wants **comparative analysis** of multiple options with recommendations.

### User Intent
"Help me choose / decide between options"

### Typical Query Patterns

| Pattern | Example |
|---------|---------|
| Comparison questions | "Compare A vs B" |
| Choice questions | "Which is better for my use case: X or Y?" |
| Pros/cons requests | "What are the pros and cons of X?" |
| Trade-off questions | "What trade-offs exist between X and Y?" |
| Selection help | "Should I use X or Y for scenario Z?" |

### Output Goals
- Comparison table or structured list
- Highlight key differences
- Provide recommendation based on context
- Summarize with conclusion

### Why Medium-Low Threshold?
Comparisons require **covering multiple options** - cannot rely on single-answer matches. Emphasize information breadth.

---

## 7. Exploration (exploration)

**Base Threshold:** 0.55

### Definition
User wants **deep, multi-angle research** on a topic: underlying logic, trends, connections, future directions.

### User Intent
"I want to deeply understand and explore this topic"

### Typical Query Patterns

| Pattern | Example |
|---------|---------|
| Essence questions | "What is the essence of X?" |
| Deep-dive requests | "Explore X from first principles" |
| Trend questions | "What are the future trends of X?" |
| Connection questions | "How does X relate to Y and Z?" |
| Research requests | "Give me a comprehensive analysis of X" |
| Why questions | "Why was X designed this way?" |

### Output Goals
- Multi-perspective analysis
- Systematic and comprehensive
- Extensible and connective
- Include implications and patterns

### Why Lowest Threshold?
Encourage **exploration and association** - allow loosely related context into the candidate set for serendipitous discoveries.

---

## Quick Reference Table

| Scene | Precision | Breadth | Multiple Answers OK? | Threshold |
|-------|-----------|---------|---------------------|-----------|
| fact_lookup | Very High | Very Low | No | 0.80 |
| faithful_reference | Highest | Minimal | No | 0.75 |
| faithful_how_to | Very High | Low | No | 0.68 |
| concept_learning | Medium | Medium | Yes | 0.65 |
| how_to | High | Low-Medium | Sometimes | 0.70 |
| comparison | Medium | High | Yes | 0.63 |
| exploration | Low | Very High | Yes | 0.55 |
