---
name: md-doc-sence-output
description: "The Document Processor is a post-retrieval module that formats and delivers retrieved documents based on the **query scene classification** produced by the Query Router. Its purpose is to apply different output strategies for different user intents, ensuring the final response matches the user’s precision, fidelity, and coverage needs."
context: fork
disable-model-invocation: true
---


#### Core Responsibilities

1. **Input Handling**

   * Accepts:

     * Classified `scene` (one of the seven types)
     * Routing parameters (`confidence`, `ambiguity`, `coverage_need`, `reranker_threshold`)
     * A ranked list of retrieved document chunks

2. **Scene-Specific Output Templates**
   The processor selects an output template and formatting strategy based on the scene:

   * **fact_lookup**

     * Output: Short, precise answer
     * Strategy: Extract exact facts, values, or definitions
     * Style: Minimal text, citation-first, no extra context

   * **faithful_reference**

     * Output: High-fidelity original text
     * Strategy: Preserve wording, structure, and paragraph layout
     * Style: Verbatim reproduction, minimal or no paraphrasing

   * **faithful_how_to**

     * Output: Original procedural steps
     * Strategy: Keep exact step sequence and formatting
     * Style: Verbatim instructions with prerequisites and ordered steps

   * **concept_learning**

     * Output: Structured educational explanation
     * Strategy: Synthesize multiple sources
     * Style: Definition → Principles → Relationships → Examples

   * **how_to**

     * Output: Practical step-by-step guide
     * Strategy: Normalize steps from multiple sources
     * Style: Clear, actionable, reproducible instructions

   * **comparison**

     * Output: Comparative analysis
     * Strategy: Aggregate multiple options
     * Style: Table or structured pros/cons + recommendation

   * **exploration**

     * Output: Deep multi-angle analysis
     * Strategy: Broaden context and connect ideas
     * Style: Long-form, research-oriented, trend + implication driven

3. **Adaptive Content Processing**

   * Applies different transformations per scene:

     * Compression (for long documents)
     * Fidelity preservation (for faithful_* scenes)
     * Synthesis and abstraction (for concept / exploration)
     * Normalization and step ordering (for how_to)

4. **Output Assembly**

   * Produces a final response that:

     * Matches the user’s intent precision level
     * Aligns with the scene’s information breadth
     * Avoids hallucination in high-fidelity scenes
     * Encourages insight and coverage in exploration scenes

5. **Safety and Quality Controls**

   * Enforces:

     * High relevance in faithful scenes
     * Low paraphrasing where exact text is required
     * Clear structure in educational and procedural outputs