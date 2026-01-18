"""
Agentic Document Matcher

Multi-stage progressive retrieval with self-reflective re-ranking.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .doc_extractor import MarkdownDocExtractor
from . import utils


@dataclass
class MatchResult:
    """Enhanced match result with metadata."""
    title: str
    similarity: float
    match_type: str
    doc_name_version: str
    source: str  # "title", "toc", "preview", "expanded"
    content_preview: Optional[str] = None
    sections_matched: Optional[List[str]] = None  # 匹配到的章节标题

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "similarity": self.similarity,
            "match_type": self.match_type,
            "doc_name_version": self.doc_name_version,
            "source": self.source,
            "content_preview": self.content_preview,
            "sections_matched": self.sections_matched or []
        }


class ProgressiveRetriever:
    """Multi-stage progressive retrieval with adaptive strategy."""

    def __init__(self, extractor: MarkdownDocExtractor, config: Optional[Dict[str, Any]] = None):
        self.extractor = extractor
        self.config = config or self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        return {
            "max_turns": 3,
            "min_results": 3,
            "min_similarity": 0.6,
            "high_quality_threshold": 0.7,  # Threshold for triggering Level 2 fallback
            "title_max_results": 5,
            "toc_max_results": 10,
            "preview_max_results": 8,
        }

    def retrieve(self, query: str, doc_set: Optional[str] = None) -> List[MatchResult]:
        """
        Multi-stage retrieval with adaptive expansion.

        Stages:
        1. Title matching (fast)
        2. TOC section matching (if needed)
        3. Content preview matching (if needed)
        """
        all_results: List[MatchResult] = []
        query_lower = query.lower()

        # Stage 1: Title matching (always)
        self._debug_print(f"[Stage 1] Searching titles for: '{query}'")
        title_results = self._search_titles(query, doc_set)
        all_results.extend(title_results)
        self._debug_print(f"  → Found {len(title_results)} title matches")

        # Evaluate: Do we need more?
        if not self._is_satisfied(all_results):
            # Stage 2: TOC section matching
            self._debug_print("[Stage 2] Expanding to TOC sections")
            toc_results = self._search_tocs(query, doc_set)
            all_results.extend(toc_results)
            self._debug_print(f"  → Found {len(toc_results)} TOC matches")

        # Evaluate again
        if not self._is_satisfied(all_results):
            # Stage 3: Content preview matching
            self._debug_print("[Stage 3] Searching content previews")
            preview_results = self._search_previews(query, doc_set)
            all_results.extend(preview_results)
            self._debug_print(f"  → Found {len(preview_results)} preview matches")

        return all_results

    def _search_titles(self, query: str, doc_set: Optional[str] = None) -> List[MatchResult]:
        """Stage 1: Search document titles."""
        raw_results = self.extractor.semantic_search_titles(
            query,
            doc_set=doc_set,
            max_results=self.config["title_max_results"]
        )
        return [
            MatchResult(
                title=r["title"],
                similarity=r["similarity"],
                match_type=r["match_type"],
                doc_name_version=r["doc_name_version"],
                source="title"
            )
            for r in raw_results
        ]

    def _search_tocs(self, query: str, doc_set: Optional[str] = None) -> List[MatchResult]:
        """
        Stage 2: Search TOC sections within documents.

        Finds documents whose TOC contains sections matching the query.
        """
        results: List[MatchResult] = []

        try:
            doc_structure = self.extractor._get_doc_structure()
        except Exception:
            return results

        # Filter by doc_set if specified
        if doc_set:
            if doc_set not in doc_structure:
                return results
            docs_to_search = {doc_set: doc_structure[doc_set]}
        else:
            docs_to_search = doc_structure

        query_lower = query.lower()

        for doc_key, titles in docs_to_search.items():
            for title in titles:
                # Try to read TOC
                toc_content = self._read_toc(doc_key, title)
                if not toc_content:
                    continue

                # Search for matching sections
                sections = utils.extract_toc_sections(toc_content, query if query else "")
                if sections:
                    # Calculate similarity based on best section match
                    best_section = max(
                        sections,
                        key=lambda s: s.get("relevance_score", 0),
                        default=None
                    )

                    if best_section:
                        similarity = best_section.get("relevance_score", 0.5)
                        # Boost if multiple sections match
                        if len(sections) > 1:
                            similarity = min(1.0, similarity + 0.1)

                        results.append(MatchResult(
                            title=title,
                            similarity=similarity,
                            match_type="toc_section",
                            doc_name_version=doc_key,
                            source="toc",
                            sections_matched=[s["title"] for s in sections[:3]]
                        ))

        # Sort and limit
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:self.config["toc_max_results"]]

    def _search_previews(self, query: str, doc_set: Optional[str] = None) -> List[MatchResult]:
        """
        Stage 3: Search content previews.

        Reads first N lines of documents to find content-level matches.
        """
        results: List[MatchResult] = []

        try:
            doc_structure = self.extractor._get_doc_structure()
        except Exception:
            return results

        # Filter by doc_set if specified
        if doc_set:
            if doc_set not in doc_structure:
                return results
            docs_to_search = {doc_set: doc_structure[doc_set]}
        else:
            docs_to_search = doc_structure

        query_lower = query.lower()
        query_terms = query_lower.split()

        for doc_key, titles in docs_to_search.items():
            for title in titles:
                # Skip if already found by title/TOC
                # (this will be handled by deduplication later)

                # Read preview
                preview = self._read_preview(doc_key, title, max_lines=50)
                if not preview:
                    continue

                # Check if query terms appear in preview
                preview_lower = preview.lower()
                matched_terms = [t for t in query_terms if t in preview_lower]

                if matched_terms:
                    # Calculate similarity based on term coverage
                    term_coverage = len(matched_terms) / len(query_terms)
                    similarity = 0.3 + (term_coverage * 0.4)  # Base 0.3, max 0.7

                    results.append(MatchResult(
                        title=title,
                        similarity=similarity,
                        match_type="content_preview",
                        doc_name_version=doc_key,
                        source="preview",
                        content_preview=preview[:200] + "..." if len(preview) > 200 else preview
                    ))

        # Sort and limit
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:self.config["preview_max_results"]]

    def _read_toc(self, doc_key: str, title: str) -> Optional[str]:
        """Read TOC content for a document."""
        try:
            if ":" in doc_key:
                doc_name, doc_version = doc_key.split(":", 1)
            else:
                doc_name = doc_key
                doc_version = "latest"

            # Try docTOC.md first
            toc_path = utils.build_doc_path(
                self.extractor.base_dir, doc_name, doc_version, title
            ).replace("docContent.md", "docTOC.md")

            toc_path_obj = __import__('pathlib').Path(toc_path)
            if toc_path_obj.exists():
                return toc_path_obj.read_text(encoding="utf-8")

        except Exception:
            pass

        return None

    def _read_preview(self, doc_key: str, title: str, max_lines: int = 50) -> Optional[str]:
        """Read content preview for a document."""
        try:
            if ":" in doc_key:
                doc_name, doc_version = doc_key.split(":", 1)
            else:
                doc_name = doc_key
                doc_version = "latest"

            doc_path = utils.build_doc_path(
                self.extractor.base_dir, doc_name, doc_version, title
            )

            path_obj = __import__('pathlib').Path(doc_path)
            if path_obj.exists():
                content = path_obj.read_text(encoding="utf-8")
                lines = content.split('\n')
                return '\n'.join(lines[:max_lines])

        except Exception:
            pass

        return None

    def _is_satisfied(self, results: List[MatchResult]) -> bool:
        """
        Evaluate if current results are satisfactory.

        Satisfaction criteria:
        1. Have at least min_results
        2. At least one result with high similarity (>= high_quality_threshold for Level 1)
        3. Have diverse match types

        Returns False to trigger Level 2: TOC Grep Fallback when:
        - No results found, OR
        - Max similarity below high_quality_threshold (0.7)
        """
        if not results:
            return False

        # Criterion 1: Minimum count
        if len(results) < self.config.get("min_results", 2):
            return False

        # Criterion 2: Quality check
        max_sim = max(r.similarity for r in results)

        # Use high_quality_threshold (0.7) for Level 1 satisfaction check
        # If max_sim < 0.7, trigger Level 2 fallback for better matching
        high_quality_threshold = self.config.get("high_quality_threshold", 0.7)
        if max_sim < high_quality_threshold:
            return False

        # Criterion 3: Diversity check (optional)
        match_types = set(r.match_type for r in results)
        if len(match_types) >= 2:
            return True  # Diverse sources = good

        # If only one source type, need higher quality
        return max_sim >= 0.8

    def _debug_print(self, msg: str):
        if hasattr(self.extractor, '_debug_mode') and self.extractor._debug_mode:
            print(f"[ProgressiveRetriever] {msg}")


class ReflectiveReRanker:
    """Self-reflective re-ranking with quality assessment."""

    def __init__(self, extractor: MarkdownDocExtractor, config: Optional[Dict[str, Any]] = None):
        self.extractor = extractor
        self.config = config or self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        return {
            "diversity_boost": 0.1,
            "source_weights": {
                "title": 1.0,
                "toc": 0.95,
                "preview": 0.8
            },
            "dedup_threshold": 0.85
        }

    def rerank(self, query: str, results: List[MatchResult]) -> List[MatchResult]:
        """
        Re-rank results with multi-factor scoring.

        Factors:
        1. Original similarity
        2. Source type weight
        3. Query term coverage
        4. Diversity boost
        """
        if not results:
            return results

        # Step 1: Deduplicate by title similarity
        deduped = self._deduplicate_results(results)

        # Step 2: Re-score with multiple factors
        for result in deduped:
            result.similarity = self._calculate_final_score(
                query, result, deduped
            )

        # Step 3: Sort by final score
        deduped.sort(key=lambda r: r.similarity, reverse=True)

        # Step 4: Apply diversity boost
        deduped = self._apply_diversity_boost(deduped)

        return deduped

    def _deduplicate_results(
        self,
        results: List[MatchResult]
    ) -> List[MatchResult]:
        """
        Remove duplicate documents (by title similarity).

        Keeps the highest-quality version of each document.
        """
        if not results:
            return results

        # Group by exact title
        title_groups: Dict[str, List[MatchResult]] = {}
        for r in results:
            if r.title not in title_groups:
                title_groups[r.title] = []
            title_groups[r.title].append(r)

        # For each title, keep the best result
        deduped: List[MatchResult] = []
        for title, group in title_groups.items():
            # Prefer: highest source weight, then highest similarity
            best = max(
                group,
                key=lambda r: (
                    self.config["source_weights"].get(r.source, 0.5),
                    r.similarity
                )
            )
            deduped.append(best)

        return deduped

    def _calculate_final_score(
        self,
        query: str,
        result: MatchResult,
        all_results: List[MatchResult]
    ) -> float:
        """Calculate final relevance score with multiple factors."""

        # Base score
        base_score = result.similarity

        # Factor 1: Source weight
        source_weight = self.config["source_weights"].get(result.source, 0.5)

        # Factor 2: Query term coverage
        query_terms = set(query.lower().split())
        title_lower = result.title.lower()
        coverage = len(query_terms & set(title_lower.split())) / max(len(query_terms), 1)

        # Factor 3: Section matches (for TOC results)
        section_boost = 0.0
        if result.sections_matched:
            section_boost = min(0.15, len(result.sections_matched) * 0.05)

        # Combine factors
        final_score = (
            base_score * 0.6 +  # Original similarity
            source_weight * 0.2 +  # Source reliability
            coverage * 0.1 +  # Term coverage
            section_boost  # Section match bonus
        )

        return min(1.0, final_score)

    def _apply_diversity_boost(
        self,
        results: List[MatchResult]
    ) -> List[MatchResult]:
        """
        Apply diversity boost to promote varied result types.

        Slightly boosts results that come from different sources.
        """
        if len(results) <= 1:
            return results

        seen_sources = set()
        adjusted_results = []

        for r in results:
            boost = 0.0
            if r.source not in seen_sources:
                # First result from this source gets small boost
                boost = self.config.get("diversity_boost", 0.05)
                seen_sources.add(r.source)

            adjusted = MatchResult(
                title=r.title,
                similarity=min(1.0, r.similarity + boost),
                match_type=r.match_type,
                doc_name_version=r.doc_name_version,
                source=r.source,
                content_preview=r.content_preview,
                sections_matched=r.sections_matched
            )
            adjusted_results.append(adjusted)

        return adjusted_results

    def critique_results(
        self,
        query: str,
        results: List[MatchResult]
    ) -> Dict[str, Any]:
        """
        Critique result quality and suggest improvements.

        Returns:
            Dict with critique metrics and suggestions
        """
        if not results:
            return {
                "satisfactory": False,
                "reason": "no_results",
                "suggestion": "expand_search"
            }

        # Calculate metrics
        metrics = {
            "count": len(results),
            "max_similarity": max(r.similarity for r in results),
            "avg_similarity": sum(r.similarity for r in results) / len(results),
            "source_diversity": len(set(r.source for r in results)),
            "match_type_diversity": len(set(r.match_type for r in results))
        }

        # Evaluate
        satisfactory = (
            metrics["count"] >= 3 and
            metrics["max_similarity"] >= 0.7 and
            metrics["source_diversity"] >= 1
        )

        suggestion = None
        if not satisfactory:
            if metrics["max_similarity"] < 0.5:
                suggestion = "lower_threshold"
            elif metrics["count"] < 3:
                suggestion = "expand_search"

        return {
            "satisfactory": satisfactory,
            "metrics": metrics,
            "suggestion": suggestion
        }


class AgenticDocMatcher:
    """
    Agentic document matcher combining progressive retrieval
    and reflective re-ranking.

    This is the main entry point for agentic document matching.
    """

    def __init__(
        self,
        extractor: MarkdownDocExtractor,
        config: Optional[Dict[str, Any]] = None,
        debug_mode: bool = False
    ):
        """
        Initialize the agentic matcher.

        Args:
            extractor: MarkdownDocExtractor instance
            config: Optional configuration dict
            debug_mode: Enable debug output
        """
        self.extractor = extractor
        self.config = config or {}
        self.debug_mode = debug_mode

        self.retriever = ProgressiveRetriever(extractor, config)
        self.reranker = ReflectiveReRanker(extractor, config)

    def match(
        self,
        query: str,
        doc_set: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform agentic document matching.

        Args:
            query: Search query
            doc_set: Optional document set filter
            max_results: Maximum number of results to return

        Returns:
            List of result dicts with enhanced metadata

        Example:
            >>> matcher = AgenticDocMatcher(extractor)
            >>> results = matcher.match("skills")
            >>> for r in results:
            ...     print(f"{r['title']} ({r['source']}, sim={r['similarity']:.2f})")
        """
        self._debug_print(f"=== Agentic Matching for: '{query}' ===")

        # Phase 1: Progressive retrieval
        self._debug_print("Phase 1: Progressive Retrieval")
        raw_results = self.retriever.retrieve(query, doc_set)
        self._debug_print(f"  → Retrieved {len(raw_results)} candidates")

        if not raw_results:
            self._debug_print("  → No results found")
            return []

        # Phase 2: Reflective re-ranking
        self._debug_print("Phase 2: Reflective Re-ranking")
        reranked = self.reranker.rerank(query, raw_results)
        self._debug_print(f"  → After dedup: {len(reranked)} results")

        # Phase 3: Quality critique
        critique = self.reranker.critique_results(query, reranked)
        self._debug_print(f"Phase 3: Quality Assessment")
        self._debug_print(f"  → Satisfactory: {critique['satisfactory']}")
        if "metrics" in critique:
            m = critique["metrics"]
            self._debug_print(f"  → Max sim: {m['max_similarity']:.2f}, Sources: {m['source_diversity']}")

        # Phase 4: Auto-expansion if needed (agentic behavior)
        if not critique["satisfactory"] and critique.get("suggestion") == "expand_search":
            self._debug_print("Phase 4: Auto-expansion (results unsatisfactory)")
            # Lower threshold and expand
            expanded = self._expand_search(query, doc_set)
            reranked.extend(expanded)
            reranked = self.reranker.rerank(query, reranked)
            self._debug_print(f"  → Expanded to {len(reranked)} results")

        # Limit results
        final_results = reranked[:max_results]

        self._debug_print(f"=== Final: {len(final_results)} results ===\n")

        # Convert to dict format
        return [r.to_dict() for r in final_results]

    def _expand_search(
        self,
        query: str,
        doc_set: Optional[str] = None
    ) -> List[MatchResult]:
        """Expand search with lower threshold and alternative queries."""
        results: List[MatchResult] = []

        # Generate alternative queries
        alt_queries = self._generate_alternative_queries(query)

        for alt_q in alt_queries[:2]:  # Try up to 2 alternatives
            alt_results = self.retriever.retrieve(alt_q, doc_set)
            results.extend(alt_results)

        return results

    def _generate_alternative_queries(self, query: str) -> List[str]:
        """Generate alternative search queries."""
        alternatives = []

        # Extract key terms (simple heuristic)
        terms = query.split()
        if len(terms) > 1:
            # Add individual terms
            alternatives.extend(terms)

            # Add bigrams
            for i in range(len(terms) - 1):
                alternatives.append(f"{terms[i]} {terms[i+1]}")

        # Remove duplicates and original
        alternatives = [a for a in alternatives if a.lower() != query.lower()]
        return list(set(alternatives))

    def _debug_print(self, msg: str):
        if self.debug_mode:
            print(f"[AgenticDocMatcher] {msg}")


# Convenience function for quick usage
def agentic_search(
    query: str,
    base_dir: str = "md_docs",
    max_results: int = 10,
    debug_mode: bool = False
) -> List[Dict[str, Any]]:
    """
    Convenience function for agentic document search.

    Example:
        >>> results = agentic_search("skills")
        >>> for r in results:
        ...     print(f"{r['title']} - {r['similarity']:.2f}")
    """
    extractor = MarkdownDocExtractor(base_dir=base_dir)
    matcher = AgenticDocMatcher(extractor, debug_mode=debug_mode)
    return matcher.match(query, max_results=max_results)
