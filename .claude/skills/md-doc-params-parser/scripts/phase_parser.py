"""
Phase Parsers for Doc-RAG Pipeline

This module implements parsers that convert output from upstream phases
to input format required by downstream phases.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class PhaseParser(ABC):
    """Base class for all phase parsers."""

    @abstractmethod
    def parse(self, upstream_output: Dict[str, Any], target_skill: str) -> Dict[str, Any]:
        """
        Parse upstream output for downstream skill.

        Args:
            upstream_output: Output from the upstream phase
            target_skill: Target skill name (e.g., "phase_1")

        Returns:
            Input dict for the downstream skill
        """
        raise NotImplementedError


class Phase0aToPhase1Parser(PhaseParser):
    """Phase 0a (query-optimizer) → Phase 1 (searcher)"""

    def parse(self, optimizer_output: Dict[str, Any], target_skill: str) -> Dict[str, Any]:
        """
        Convert query-optimizer output to searcher CLI config.

        Args:
            optimizer_output: Output from md-doc-query-optimizer
            target_skill: Target skill name

        Returns:
            CLI config dict for md-doc-searcher
        """
        query_analysis = optimizer_output.get("query_analysis", {})
        optimized_queries = optimizer_output.get("optimized_queries", [])

        # Extract queries (sorted by rank)
        queries = sorted(
            [q["query"] for q in optimized_queries if "query" in q],
            key=lambda x: next(
                (q["rank"] for q in optimized_queries if q.get("query") == x),
                999
            )
        )

        # Extract doc_set array and convert to CLI format
        doc_sets = query_analysis.get("doc_set", [])
        doc_sets_cli = ",".join(doc_sets) if doc_sets else ""

        # Extract domain_nouns and predicate_verbs
        domain_nouns = query_analysis.get("domain_nouns", [])
        predicate_verbs = query_analysis.get("predicate_verbs", [])

        return {
            "query": queries,
            "doc_sets": doc_sets_cli,
            "domain_nouns": domain_nouns,
            "predicate_verbs": predicate_verbs
        }


class Phase0bToPhase1Parser(PhaseParser):
    """Phase 0b (query-router) → Phase 1 (searcher)"""

    def parse(self, router_output: Dict[str, Any], target_skill: str) -> Dict[str, Any]:
        """
        Convert query-router output to searcher parameters.

        Args:
            router_output: Output from md-doc-query-router
            target_skill: Target skill name

        Returns:
            Dict with reranker_threshold and scene
        """
        return {
            "reranker_threshold": router_output.get("reranker_threshold", 0.63),
            "scene": router_output.get("scene", "fact_lookup")
        }


class MultiPhaseToPhase1Parser(PhaseParser):
    """Phase 0a + Phase 0b → Phase 1 (Merge outputs from both phases)"""

    def parse(self, upstream_outputs: List[Dict[str, Any]], target_skill: str) -> Dict[str, Any]:
        """
        Merge outputs from Phase 0a and Phase 0b into Phase 1 config.

        Args:
            upstream_outputs: List of outputs from both phases
                [
                    {"phase": "0a", "output": {...}},  # query-optimizer output
                    {"phase": "0b", "output": {...}}   # query-router output
                ]
            target_skill: Target skill name

        Returns:
            Phase 1 (searcher) CLI config
        """
        # Separate 0a and 0b outputs
        phase_0a_output = None
        phase_0b_output = None

        for item in upstream_outputs:
            phase = item.get("phase")
            if phase == "0a":
                phase_0a_output = item.get("output", {})
            elif phase == "0b":
                phase_0b_output = item.get("output", {})

        # Parse 0a output
        result_0a = Phase0aToPhase1Parser().parse(
            phase_0a_output or {},
            target_skill
        )

        # Parse 0b output
        result_0b = Phase0bToPhase1Parser().parse(
            phase_0b_output or {},
            target_skill
        )

        # Merge results
        return {
            **result_0a,  # query, doc_sets, domain_nouns, predicate_verbs
            **result_0b,  # reranker_threshold, scene
        }


class Phase1ToPhase1_5Parser(PhaseParser):
    """Phase 1 (searcher) → Phase 1.5 (llm-reranker)"""

    def parse(self, searcher_output: Dict[str, Any], target_skill: str) -> Dict[str, Any]:
        """
        Check if results need LLM reranking.

        Args:
            searcher_output: Output from md-doc-searcher
            target_skill: Target skill name

        Returns:
            Dict with needs_rerank flag and results
        """
        results = searcher_output.get("results", [])

        # Check if any heading lacks rerank_sim (needs LLM reranking)
        needs_rerank = False
        for result in results:
            headings = result.get("headings", [])
            for heading in headings:
                if heading.get("rerank_sim") is None:
                    needs_rerank = True
                    break
            if needs_rerank:
                break

        return {
            "needs_rerank": needs_rerank,
            "results": results,
            "success": searcher_output.get("success", False)
        }


class Phase1_5ToPhase2Parser(PhaseParser):
    """Phase 1.5 (llm-reranker) → Phase 2 (reader)"""

    def parse(self, reranker_output: Dict[str, Any], target_skill: str) -> Dict[str, Any]:
        """
        Convert LLM reranker output to reader CLI config.

        Args:
            reranker_output: Output from md-doc-llm-reranker
            target_skill: Target skill name

        Returns:
            CLI config dict for md-doc-reader
        """
        results = reranker_output.get("results", [])

        # Build page_titles config for reader CLI
        page_titles_config = []
        for result in results:
            headings = result.get("headings", [])
            page_titles_config.append({
                "title": result.get("page_title", ""),
                "headings": [self._normalize_heading(h.get("text", "")) for h in headings],
                "doc_set": result.get("doc_set", "")
            })

        return {
            "page_titles": page_titles_config,
            "with_metadata": True,
            "format": "json"
        }

    def _normalize_heading(self, heading: str) -> str:
        """
        Normalize heading by removing markdown prefix and extra whitespace.

        Args:
            heading: Heading text, may include ## prefix

        Returns:
            Clean heading without ## prefix
        """
        return heading.lstrip("# ").strip()


class Phase2ToPhase3Parser(PhaseParser):
    """Phase 2 (reader) → Phase 3 (processor)"""

    def parse(self, reader_output: Dict[str, Any], target_skill: str) -> Dict[str, Any]:
        """
        Convert reader output to processor input.

        Args:
            reader_output: Output from md-doc-reader
            target_skill: Target skill name

        Returns:
            Input dict for md-doc-processor
        """
        return {
            "contents": reader_output.get("contents", {}),
            "line_count": reader_output.get("total_line_count", 0),
            "requires_processing": reader_output.get("requires_processing", False),
            "metadata": reader_output.get("metadata", {})
        }


class Phase3ToPhase4Parser(PhaseParser):
    """Phase 3 (processor) → Phase 4 (sence-output)"""

    def parse(self, processor_output: Dict[str, Any], target_skill: str) -> Dict[str, Any]:
        """
        Convert processor output to sence-output input.

        Args:
            processor_output: Output from md-doc-processor
            target_skill: Target skill name

        Returns:
            Input dict for md-doc-sence-output
        """
        return {
            "processed_doc": processor_output.get("processed_doc", ""),
            "compression_meta": {
                "compression_applied": processor_output.get("compression_applied", False),
                "original_line_count": processor_output.get("original_line_count", 0),
                "output_line_count": processor_output.get("output_line_count", 0)
            },
            "doc_meta": processor_output.get("doc_meta", {})
        }


class Phase1ToPhase2Parser(PhaseParser):
    """Phase 1 (searcher) → Phase 2 (reader) - Direct pass-through (no reranker)"""

    def parse(self, searcher_output: Dict[str, Any], target_skill: str) -> Dict[str, Any]:
        """
        Convert searcher output directly to reader input (skipping reranker).

        Args:
            searcher_output: Output from md-doc-searcher
            target_skill: Target skill name

        Returns:
            CLI config dict for md-doc-reader
        """
        results = searcher_output.get("results", [])

        # Build page_titles config for reader CLI
        page_titles_config = []
        for result in results:
            headings = result.get("headings", [])
            page_titles_config.append({
                "title": result.get("page_title", ""),
                "headings": [self._normalize_heading(h.get("text", "")) for h in headings],
                "doc_set": result.get("doc_set", "")
            })

        return {
            "page_titles": page_titles_config,
            "with_metadata": True,
            "format": "json"
        }

    def _normalize_heading(self, heading: str) -> str:
        """
        Normalize heading by removing markdown prefix and extra whitespace.

        Args:
            heading: Heading text, may include ## prefix

        Returns:
            Clean heading without ## prefix
        """
        return heading.lstrip("# ").strip()
