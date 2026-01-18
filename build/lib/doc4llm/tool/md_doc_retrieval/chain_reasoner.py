"""
Chain Reasoner for Multi-Hop Document Retrieval

Decomposes complex queries into reasoning chains, executes multi-step
retrieval, and synthesizes comprehensive answers with source attribution.
"""
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ReasoningStep:
    """Represents a single reasoning step in the chain."""
    hop: int
    query: str
    documents_found: int
    key_info: List[str]
    sources: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hop": self.hop,
            "query": self.query,
            "documents_found": self.documents_found,
            "key_info": self.key_info,
            "sources": self.sources
        }


@dataclass
class ReasoningResult:
    """Complete reasoning result with synthesized answer."""
    original_query: str
    decomposition: Dict[str, Any]
    reasoning_steps: List[ReasoningStep]
    answer: Dict[str, Any]
    citations: List[Dict[str, Any]]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "decomposition": self.decomposition,
            "reasoning_steps": [s.to_dict() for s in self.reasoning_steps],
            "answer": self.answer,
            "citations": self.citations,
            "confidence": self.confidence
        }


class ChainReasoner:
    """
    Multi-hop reasoning for complex document queries.

    Decomposes complex queries, executes sequential retrieval,
    and synthesizes comprehensive answers.
    """

    # Conjunction patterns for decomposition
    CONJUNCTION_PATTERNS = [
        r'\s+[和与与以及]\s+',
        r'\s+and\s+',
        r'\s+,',
        r'；\s*',
        r'，\s*',
    ]

    # Comparison patterns
    COMPARISON_PATTERNS = [
        r'和.*的区别',
        r'和.*的差异',
        r'和.*对比',
        r'和.*比较',
        r' vs\.?',
        r' versus ',
    ]

    # Procedural patterns
    PROCEDURAL_PATTERNS = [
        r'如何.*并',
        r'怎样.*然后',
        r'步骤',
    ]

    def __init__(
        self,
        extractor,
        matcher,
        config: Optional[Dict[str, Any]] = None,
        debug_mode: bool = False
    ):
        """
        Initialize the chain reasoner.

        Args:
            extractor: MarkdownDocExtractor instance
            matcher: AgenticDocMatcher instance
            config: Optional configuration dict
            debug_mode: Enable debug output
        """
        self.extractor = extractor
        self.matcher = matcher
        self.config = config or self._default_config()
        self.debug_mode = debug_mode

    def _default_config(self) -> Dict[str, Any]:
        return {
            "max_hops": 3,
            "max_documents_per_hop": 5,
            "min_similarity_threshold": 0.6,
            "enable_citation_tracking": True,
            "enable_cross_hop_refinement": True,
            "synthesis_strategy": "comprehensive",
        }

    def reason(
        self,
        query: str,
        max_hops: Optional[int] = None,
        max_documents_per_hop: Optional[int] = None
    ) -> ReasoningResult:
        """
        Perform multi-hop reasoning on a complex query.

        Args:
            query: The user's query
            max_hops: Maximum reasoning steps (overrides config)
            max_documents_per_hop: Max docs per step (overrides config)

        Returns:
            ReasoningResult with synthesized answer
        """
        self._debug_print(f"=== Chain Reasoning for: '{query}' ===")

        max_hops = max_hops or self.config.get("max_hops", 3)
        max_docs = max_documents_per_hop or self.config.get("max_documents_per_hop", 5)

        # Step 1: Analyze query complexity
        analysis = self._analyze_query(query)
        self._debug_print(f"Analysis: complexity={analysis['complexity']}, "
                        f"estimated_hops={analysis['estimated_hops']}")

        # Step 2: Decompose query
        sub_queries = self._decompose_query(query)
        if not sub_queries:
            # Simple query, no decomposition needed
            sub_queries = [query]

        self._debug_print(f"Decomposed into {len(sub_queries)} sub-queries")

        # Step 3: Execute retrieval chain
        reasoning_steps = self._execute_retrieval_chain(
            sub_queries[:max_hops],
            max_docs
        )

        # Step 4: Synthesize answer
        answer = self._synthesize_answer(reasoning_steps, query)

        # Step 5: Generate citations
        citations = self._generate_citations(reasoning_steps)

        # Step 6: Calculate confidence
        confidence = self._calculate_confidence(reasoning_steps)

        result = ReasoningResult(
            original_query=query,
            decomposition={
                "num_hops": len(sub_queries),
                "sub_queries": sub_queries
            },
            reasoning_steps=reasoning_steps,
            answer=answer,
            citations=citations,
            confidence=confidence
        )

        self._debug_print(f"=== Reasoning complete, confidence={confidence:.2f} ===")

        return result

    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine reasoning requirements."""
        is_complex = False
        requires_comparison = False
        requires_procedural = False

        # Check for conjunctions
        for pattern in self.CONJUNCTION_PATTERNS:
            if re.search(pattern, query):
                is_complex = True
                break

        # Check for comparisons
        for pattern in self.COMPARISON_PATTERNS:
            if re.search(pattern, query):
                requires_comparison = True
                is_complex = True
                break

        # Check for procedural patterns
        for pattern in self.PROCEDURAL_PATTERNS:
            if re.search(pattern, query):
                requires_procedural = True
                is_complex = True
                break

        # Estimate required hops
        estimated_hops = 1
        if is_complex:
            # Count distinct concepts
            concepts = self._extract_concepts(query)
            estimated_hops = min(len(concepts), self.config.get("max_hops", 3))

        return {
            "complexity": "high" if is_complex else "low",
            "requires_comparison": requires_comparison,
            "requires_procedural": requires_procedural,
            "estimated_hops": estimated_hops
        }

    def _decompose_query(self, query: str) -> List[str]:
        """Decompose complex query into sub-queries."""
        sub_queries = []

        # Try conjunction patterns first
        for pattern in self.CONJUNCTION_PATTERNS:
            parts = re.split(pattern, query)
            if len(parts) > 1:
                sub_queries = [p.strip() for p in parts if p.strip()]
                break

        # If no conjunctions, try comparison
        if not sub_queries:
            for pattern in self.COMPARISON_PATTERNS:
                match = re.search(pattern, query)
                if match:
                    # Extract comparison terms
                    terms = self._extract_comparison_terms(query, match)
                    sub_queries = terms
                    break

        return sub_queries

    def _extract_concepts(self, query: str) -> List[str]:
        """Extract distinct concepts from query."""
        # Simple heuristic: split by common separators
        concepts = re.split(r'[,，;；和与与以及and]', query)
        return [c.strip() for c in concepts if c.strip()]

    def _extract_comparison_terms(self, query: str, match) -> List[str]:
        """Extract terms being compared."""
        # Remove comparison words and split
        cleaned = re.sub(r'[和与与以及的区别差异对比比较vs\.?versus]', ',', query)
        terms = [t.strip() for t in cleaned.split(',') if t.strip()]
        return terms[:2]  # Limit to 2 terms for comparison

    def _execute_retrieval_chain(
        self,
        sub_queries: List[str],
        max_docs: int
    ) -> List[ReasoningStep]:
        """Execute sequential retrieval for each sub-query."""
        reasoning_steps = []
        min_similarity = self.config.get("min_similarity_threshold", 0.6)

        for i, sub_query in enumerate(sub_queries, start=1):
            self._debug_print(f"[Hop {i}] Searching for: '{sub_query}'")

            # Search for documents
            try:
                results = self.matcher.match(
                    sub_query,
                    max_results=max_docs
                )

                # Filter by similarity threshold
                results = [r for r in results if r.get("similarity", 0) >= min_similarity]

                # Extract key information from results
                key_info = []
                sources = []
                for r in results:
                    key_info.append(f"Found in: {r['title']}")
                    sources.append({
                        "title": r["title"],
                        "similarity": r.get("similarity", 0),
                        "source": r.get("source", "unknown")
                    })

                step = ReasoningStep(
                    hop=i,
                    query=sub_query,
                    documents_found=len(results),
                    key_info=key_info,
                    sources=sources
                )

                reasoning_steps.append(step)

                self._debug_print(f"[Hop {i}] Found {len(results)} documents")

            except Exception as e:
                self._debug_print(f"[Hop {i}] Error: {e}")
                # Add failed step
                reasoning_steps.append(ReasoningStep(
                    hop=i,
                    query=sub_query,
                    documents_found=0,
                    key_info=[f"Search failed: {str(e)}"],
                    sources=[]
                ))

        return reasoning_steps

    def _synthesize_answer(
        self,
        reasoning_steps: List[ReasoningStep],
        original_query: str
    ) -> Dict[str, Any]:
        """Synthesize comprehensive answer from reasoning steps."""
        # Collect all sources
        all_sources = []
        for step in reasoning_steps:
            all_sources.extend(step.sources)

        # Generate summary
        summary = self._generate_summary(reasoning_steps, original_query)

        # Organize by reasoning hop/section
        sections = []
        for step in reasoning_steps:
            if step.documents_found > 0:
                sections.append({
                    "title": f"Information about: {step.query}",
                    "content": f"Found {step.documents_found} relevant documents",
                    "sources": [s["title"] for s in step.sources]
                })

        return {
            "summary": summary,
            "sections": sections,
            "total_sources": len(all_sources),
            "successful_hops": sum(1 for s in reasoning_steps if s.documents_found > 0)
        }

    def _generate_summary(
        self,
        reasoning_steps: List[ReasoningStep],
        original_query: str
    ) -> str:
        """Generate a summary of findings."""
        total_docs = sum(s.documents_found for s in reasoning_steps)
        successful_hops = sum(1 for s in reasoning_steps if s.documents_found > 0)

        if total_docs == 0:
            return f"No relevant documents found for: {original_query}"

        summary_parts = [
            f"Found {total_docs} document(s) across {successful_hops} search step(s)"
        ]

        # Add brief notes from each hop
        for step in reasoning_steps:
            if step.documents_found > 0:
                top_source = step.sources[0]["title"] if step.sources else "Unknown"
                summary_parts.append(
                    f"- Step {step.hop}: {step.query} → {top_source}"
                )

        return ". ".join(summary_parts) + "."

    def _generate_citations(
        self,
        reasoning_steps: List[ReasoningStep]
    ) -> List[Dict[str, Any]]:
        """Generate citation list from reasoning steps."""
        citations = []
        seen = set()

        for step in reasoning_steps:
            for source in step.sources:
                # Deduplicate by title
                title = source["title"]
                if title not in seen:
                    seen.add(title)
                    citations.append({
                        "source": title,
                        "hop": step.hop,
                        "relevance": source.get("similarity", 0),
                        "source_type": source.get("source", "unknown")
                    })

        # Sort by relevance
        citations.sort(key=lambda c: c["relevance"], reverse=True)

        return citations

    def _calculate_confidence(
        self,
        reasoning_steps: List[ReasoningStep]
    ) -> float:
        """Calculate overall confidence in the reasoning result."""
        if not reasoning_steps:
            return 0.0

        # Factor 1: Average similarity
        similarities = []
        for step in reasoning_steps:
            for source in step.sources:
                similarities.append(source.get("similarity", 0))

        avg_similarity = sum(similarities) / len(similarities) if similarities else 0

        # Factor 2: Success rate
        successful_hops = sum(1 for s in reasoning_steps if s.documents_found > 0)
        success_rate = successful_hops / len(reasoning_steps)

        # Factor 3: Source diversity
        unique_sources = len(set(
            s["title"] for step in reasoning_steps for s in step.sources
        ))
        total_sources = sum(len(s.sources) for s in reasoning_steps)
        diversity = unique_sources / total_sources if total_sources > 0 else 0

        # Combine factors
        confidence = (
            avg_similarity * 0.5 +
            success_rate * 0.3 +
            diversity * 0.2
        )

        return round(confidence, 2)

    def _debug_print(self, msg: str):
        if self.debug_mode:
            print(f"[ChainReasoner] {msg}")


def chain_reason(
    query: str,
    extractor=None,
    config: Optional[Dict[str, Any]] = None,
    debug_mode: bool = False
) -> Dict[str, Any]:
    """
    Convenience function for multi-hop reasoning.

    Args:
        query: The user's query
        extractor: MarkdownDocExtractor instance (created if None)
        config: Optional configuration
        debug_mode: Enable debug output

    Returns:
        Dictionary with reasoning result

    Example:
        >>> result = chain_reason("hooks 配置以及部署注意事项")
        >>> print(result['answer']['summary'])
    """
    from . import MarkdownDocExtractor, AgenticDocMatcher

    if extractor is None:
        extractor = MarkdownDocExtractor()

    matcher = AgenticDocMatcher(extractor)
    reasoner = ChainReasoner(extractor, matcher, config=config, debug_mode=debug_mode)

    result = reasoner.reason(query)
    return result.to_dict()
