"""
Basic document title matcher for md_doc_retrieval.

This module provides fundamental matching strategies without LLM dependency.
It is designed to be the foundational matcher that other matchers can extend.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .utils import calculate_similarity, normalize_title


@dataclass
class MatchResult:
    """Result of a title matching operation.

    Attributes:
        title: The matched document title
        similarity: Similarity score between 0.0 and 1.0
        doc_name_version: Document identifier (e.g., "code_claude_com@latest")
        match_type: Type of match ("exact", "partial", "fuzzy")
    """
    title: str
    similarity: float
    doc_name_version: str
    match_type: str  # "exact", "partial", "fuzzy"


class BasicDocMatcher:
    """Basic document title matcher without LLM dependency.

    This class provides three matching strategies:
    - Exact match (case-sensitive/insensitive)
    - Partial match (substring)
    - Fuzzy match (similarity-based)

    It is designed as the foundational matcher that other matchers can extend.
    All matching operations are self-contained and do not depend on external
    services or LLMs.

    Example:
        >>> matcher = BasicDocMatcher(search_mode="exact", case_sensitive=False)
        >>> result = matcher.match("Agent Skills", ["Agent Skills", "Slash Commands"])
        >>> print(result.title)  # "Agent Skills"
    """

    VALID_SEARCH_MODES = {"exact", "case_insensitive", "fuzzy", "partial"}

    def __init__(
        self,
        search_mode: str = "exact",
        case_sensitive: bool = False,
        fuzzy_threshold: float = 0.6,
        max_results: Optional[int] = None,
    ):
        """Initialize the matcher with configuration.

        Args:
            search_mode: One of "exact", "case_insensitive", "partial", "fuzzy"
            case_sensitive: Whether exact matching should be case sensitive
            fuzzy_threshold: Minimum similarity for fuzzy matching (0.0-1.0)
            max_results: Maximum results to return for fuzzy/partial searches

        Raises:
            ValueError: If search_mode is invalid or fuzzy_threshold is out of range
        """
        if search_mode not in self.VALID_SEARCH_MODES:
            raise ValueError(
                f"Invalid search_mode '{search_mode}'. "
                f"Must be one of {self.VALID_SEARCH_MODES}"
            )

        if not 0.0 <= fuzzy_threshold <= 1.0:
            raise ValueError(
                f"fuzzy_threshold must be between 0.0 and 1.0, got {fuzzy_threshold}"
            )

        self.search_mode = search_mode
        self.case_sensitive = case_sensitive
        self.fuzzy_threshold = fuzzy_threshold
        self.max_results = max_results

    def find_exact_match(
        self,
        title: str,
        titles: List[str]
    ) -> Optional[str]:
        """Find an exact title match.

        Args:
            title: The title to search for
            titles: List of available titles

        Returns:
            The matched title or None if not found

        Example:
            >>> matcher = BasicDocMatcher()
            >>> matcher.find_exact_match("Agent Skills", ["Agent Skills", "Slash"])
            'Agent Skills'
        """
        normalized_query = normalize_title(title)

        for available_title in titles:
            normalized_available = normalize_title(available_title)

            if self.case_sensitive:
                if normalized_query == normalized_available:
                    return available_title
            else:
                if normalized_query.lower() == normalized_available.lower():
                    return available_title

        return None

    def find_partial_match(
        self,
        title: str,
        titles: List[str]
    ) -> List[str]:
        """Find all partial (substring) matches.

        Args:
            title: The title to search for
            titles: List of available titles

        Returns:
            List of titles containing the query as a substring

        Example:
            >>> matcher = BasicDocMatcher()
            >>> matcher.find_partial_match("skill", ["Agent Skills", "Skill Guide"])
            ['Agent Skills', 'Skill Guide']
        """
        normalized_query = normalize_title(title).lower()
        matches: List[str] = []

        for available_title in titles:
            normalized_available = normalize_title(available_title).lower()
            if normalized_query in normalized_available:
                matches.append(available_title)

        return matches

    def find_fuzzy_match(
        self,
        title: str,
        titles: List[str]
    ) -> Optional[Tuple[str, float]]:
        """Find the best fuzzy match using similarity scoring.

        Args:
            title: The title to search for
            titles: List of available titles

        Returns:
            Tuple of (matched_title, similarity_score) or None if below threshold

        Example:
            >>> matcher = BasicDocMatcher(fuzzy_threshold=0.5)
            >>> result = matcher.find_fuzzy_match "agent skill", ["Agent Skills"])
            >>> print(result)  # ('Agent Skills', 0.92)
        """
        best_match: Optional[str] = None
        best_score = self.fuzzy_threshold

        for available_title in titles:
            score = calculate_similarity(title, available_title)
            if score > best_score:
                best_score = score
                best_match = available_title

        if best_match:
            return best_match, best_score
        return None

    def match(
        self,
        title: str,
        titles: List[str],
        mode: Optional[str] = None
    ) -> Optional[MatchResult]:
        """Match a title against available titles using configured strategy.

        This is the primary matching method. It uses the configured search_mode
        to find the best match and returns a MatchResult object with detailed
        information about the match.

        Args:
            title: The title to search for
            titles: List of available titles
            mode: Override the default search mode for this match

        Returns:
            MatchResult object or None if no match found

        Example:
            >>> matcher = BasicDocMatcher(search_mode="exact")
            >>> result = matcher.match("Agent Skills", ["Agent Skills", "Slash"])
            >>> print(result.title, result.match_type)  # "Agent Skills", "exact"
        """
        search_mode = mode or self.search_mode
        matched_title: Optional[str] = None
        match_type: Optional[str] = None
        similarity = 0.0

        if search_mode in ("exact", "case_insensitive"):
            matched_title = self.find_exact_match(title, titles)
            match_type = "exact"
            similarity = 1.0

        elif search_mode == "partial":
            matches = self.find_partial_match(title, titles)
            if matches:
                matched_title = matches[0]
                match_type = "partial"
                similarity = 0.8

        elif search_mode == "fuzzy":
            result = self.find_fuzzy_match(title, titles)
            if result:
                matched_title, similarity = result
                match_type = "fuzzy"

        if matched_title and match_type:
            return MatchResult(
                title=matched_title,
                similarity=similarity,
                doc_name_version="",  # To be filled by caller
                match_type=match_type
            )
        return None

    def search_all(
        self,
        title: str,
        titles_with_doc: List[Tuple[str, str]]
    ) -> List[MatchResult]:
        """Search for all matching documents.

        Returns all matching documents sorted by similarity. Useful for
        finding multiple candidates that match the query.

        Args:
            title: The title to search for
            titles_with_doc: List of (title, doc_name_version) tuples

        Returns:
            List of MatchResult objects, sorted by similarity descending

        Example:
            >>> matcher = BasicDocMatcher(search_mode="partial")
            >>> titles = [("Agent Skills", "docs@latest"), ("Skill Guide", "docs@latest")]
            >>> results = matcher.search_all("skill", titles)
            >>> for r in results:
            ...     print(f"{r.title}: {r.similarity}")
        """
        results: List[MatchResult] = []
        all_titles = [t for t, _ in titles_with_doc]

        if self.search_mode in ("exact", "case_insensitive"):
            match = self.find_exact_match(title, all_titles)
            if match:
                for t, doc_key in titles_with_doc:
                    if t == match:
                        results.append(MatchResult(
                            title=t,
                            similarity=1.0,
                            doc_name_version=doc_key,
                            match_type="exact"
                        ))
                        break

        elif self.search_mode == "partial":
            matches = self.find_partial_match(title, all_titles)
            for t, doc_key in titles_with_doc:
                if t in matches:
                    results.append(MatchResult(
                        title=t,
                        similarity=0.8,
                        doc_name_version=doc_key,
                        match_type="partial"
                    ))

        elif self.search_mode == "fuzzy":
            for t, doc_key in titles_with_doc:
                similarity = calculate_similarity(title, t)
                if similarity >= self.fuzzy_threshold:
                    results.append(MatchResult(
                        title=t,
                        similarity=similarity,
                        doc_name_version=doc_key,
                        match_type="fuzzy"
                    ))

        # Sort by similarity descending
        results.sort(key=lambda x: x.similarity, reverse=True)

        # Apply max_results limit
        if self.max_results and len(results) > self.max_results:
            results = results[:self.max_results]

        return results

    def semantic_search(
        self,
        query: str,
        titles_with_doc: List[Tuple[str, str]]
    ) -> List[MatchResult]:
        """Multi-strategy semantic search combining exact, partial, and fuzzy.

        This is an advanced search that combines all matching strategies:
        1. Exact match (similarity 1.0)
        2. Partial match (similarity 0.7-0.9)
        3. Fuzzy match (similarity based on calculation)

        Args:
            query: The search query
            titles_with_doc: List of (title, doc_name_version) tuples

        Returns:
            List of MatchResult objects, sorted by similarity

        Example:
            >>> matcher = BasicDocMatcher()
            >>> titles = [("Agent Skills", "docs@latest"), ("Slash Commands", "docs@latest")]
            >>> results = matcher.semantic_search("skill", titles)
            >>> for r in results:
            ...     print(f"{r.title}: {r.match_type} ({r.similarity})")
        """
        all_titles = [t for t, _ in titles_with_doc]
        results: List[MatchResult] = []

        # Strategy 1: Exact match (weight 1.0)
        exact_match = self.find_exact_match(query, all_titles)
        if exact_match:
            for t, doc_key in titles_with_doc:
                if t == exact_match:
                    results.append(MatchResult(
                        title=t,
                        similarity=1.0,
                        doc_name_version=doc_key,
                        match_type="exact"
                    ))
                    break

        # Strategy 2: Partial match (weight 0.7-0.9)
        partial_matches = self.find_partial_match(query, all_titles)
        for t, doc_key in titles_with_doc:
            if t in partial_matches and t != exact_match:
                # Calculate similarity based on substring position
                if t.lower().startswith(query.lower()):
                    similarity = 0.9
                else:
                    similarity = 0.7
                results.append(MatchResult(
                    title=t,
                    similarity=similarity,
                    doc_name_version=doc_key,
                    match_type="partial"
                ))

        # Strategy 3: Fuzzy match for remaining
        for t, doc_key in titles_with_doc:
            if t == exact_match or t in partial_matches:
                continue
            similarity = calculate_similarity(query, t)
            if similarity >= self.fuzzy_threshold:
                results.append(MatchResult(
                    title=t,
                    similarity=similarity,
                    doc_name_version=doc_key,
                    match_type="fuzzy"
                ))

        # Sort by similarity descending
        results.sort(key=lambda x: x.similarity, reverse=True)

        return results
