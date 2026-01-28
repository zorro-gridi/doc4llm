# Scene Definitions - Detailed Reference

This file contains detailed definitions, patterns, and examples for all seven retrieval scenes.

---

## 1. Fact Lookup (fact_lookup)

### Definition
User wants to retrieve a **simple, specific fact** from the documentation. The query targets concrete, verifiable information such as keyboard shortcuts, version numbers, configuration values, or other single-point facts.

### User Intent
"Tell me the specific answer/value for this question"

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

---

## 2. Faithful Reference (faithful_reference)

### Definition
User wants to view official documentation explanations about a specific topic or concept. The user is interested in seeing how the documentation describes and explains a subject, with the content being faithfully reproduced from the source.

### User Intent
"I want to see what the official documentation says about this topic/concept"

### Typical Query Patterns

| Pattern | Example |
|---------|---------|
| Topic explanation requests | "What does the documentation say about X?" |
| Concept description queries | "How is X defined in the official docs?" |
| Official reference requests | "Show me the docs for feature X" |
| Documentation overview | "Explain X based on the official documentation" |
| Subject matter queries | "What does the docs say about implementing X?" |

### Output Goals
- Reproduce documentation content faithfully
- Preserve original wording and structure from the source docs
- Focus on topic/concept explanations as presented in official documentation
- Minimal summarization or rewording

---

## 3. Faithful How-To (faithful_how_to)

### Definition
User is **actively implementing a project** and needs comprehensive official documentation to guide the implementation process. This scene is activated when the user explicitly requests documentation reference for completing their work. Compared to **how_to**, faithful_how_to requires **broader documentation coverage** with relatively **lower relevance threshold**, as the goal is to gather sufficient reference materials for project execution.

### User Intent
"Guide my project implementation using official documentation as reference"

### Activation Triggers
- User explicitly mentions being in an implementation/working context
- User requests official documentation or reference materials
- User needs comprehensive documentation to complete a project task
- Query involves following documented procedures for production work

### Key Distinction from how_to

| Attribute | faithful_how_to | how_to |
|-----------|-----------------|--------|
| **User Context** | Actively implementing a project | Learning how to accomplish a task |
| **Goal** | Complete project implementation | Understand the process |
| **Documentation Scope** | Broad coverage (more docs, lower relevance threshold) | Focused matching (relevant docs, higher relevance threshold) |
| **Source Requirement** | Explicit reference to official docs | No specific source requirement |
| **Detail Level** | Comprehensive, including edge cases and variations | Core steps and main流程 |

### Typical Query Patterns

| Pattern | Example |
|---------|---------|
| Implementation guidance | "What does the documentation say about deploying X in production?" |
| Project reference | "I need official docs to help implement feature X for my project" |
| Comprehensive how-to | "Show me all documentation related to configuring X for project use" |
| Detailed procedure | "Give me the detailed steps for X implementation based on official docs" |
| Reference-based how-to | "Based on the official documentation, how do I set up X?" |

### Output Goals
- Reproduce comprehensive content from official documentation
- Preserve original structure and wording from source docs
- Include edge cases, variations, and detailed configurations
- Support project implementation with thorough reference materials
- Higher recall, broader coverage over precision

---

## 4. Concept Learning (concept_learning)

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

---

## 5. How-To (how_to)

### Definition
User wants to understand the steps for **how to accomplish a task**. The focus is on learning the process of doing something, with retrieval targeting relevant documentation that describes the procedure. Precision matching is not strictly required.

### User Intent
"I want to learn how to do X"

### Typical Query Patterns

| Pattern | Example |
|---------|---------|
| How-to questions | "How do I configure X?" |
| Process learning | "What's the process for implementing Y?" |
| Operation guidance | "How to set up X environment?" |
| Procedure understanding | "How does one deploy Z?" |
| Step discovery | "What are the steps to accomplish X?" |

### Classification Boundary

Use **how_to** when the user primarily wants to **learn how to accomplish a task**, without the context of an ongoing implementation project requiring comprehensive documentation reference.

Use **faithful_how_to** when:
- User is actively working on an implementation project
- User explicitly requests official documentation as reference
- Comprehensive documentation coverage is needed for project execution

### Output Goals
- Summarize actionable steps from relevant documentation
- Clear, step-by-step guidance
- Focus on understanding how to accomplish the task
- May include prerequisites and dependencies

---

## 6. Comparison (comparison)

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

---

## 7. Exploration (exploration)

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
