"""
BM25-based document matcher for full-text content search.

This module provides BM25 (Best Matching 25) ranking for document relevance.
BM25 is a bag-of-words ranking function based on the probabilistic retrieval
framework, ideal for content-level matching where term frequency and document
length normalization are important.

Algorithm Reference:
https://en.wikipedia.org/wiki/Okapi_BM25
"""
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BM25Config:
    """Configuration for BM25 ranking parameters.

    Attributes:
        k1: Term frequency saturation parameter (default 1.2)
             - Higher k1 gives more weight to term frequency
             - k1 = 0 ignores term frequency (binary model)
             - Typical range: 1.2 - 2.0

        b: Length normalization parameter (default 0.75)
           - b = 1.0 fully normalizes by document length
           - b = 0.0 ignores document length
           - Typical range: 0.75

        min_token_length: Minimum token length to index (default 2)
        max_token_length: Maximum token length to index (default 30)
        lowercase: Whether to lowercase tokens (default True)
        stop_words: Set of stop words to ignore (optional)
    """
    k1: float = 1.2
    b: float = 0.75
    min_token_length: int = 2
    max_token_length: int = 30
    lowercase: bool = True
    stop_words: Optional[set] = None


class BM25Matcher:
    """BM25-based matcher for full-text content search.

    This matcher builds an inverted index over document contents and
    ranks documents using the BM25 ranking function. It is particularly
    effective for content-level matching where:

    - Multi-term queries need proper term-based scoring
    - Rare keywords should be boosted (IDF weighting)
    - Document length variance needs normalization
    - Term frequency matters but should saturate

    Example:
        >>> matcher = BM25Matcher()
        >>> documents = {
        ...     "doc1": "Machine learning is a subset of AI",
        ...     "doc2": "Deep learning uses neural networks"
        ... }
        >>> matcher.build_index(documents)
        >>> results = matcher.search("machine learning", top_k=2)
        >>> print(results[0].doc_id)  # "doc1"
    """

    # Default stop words for English
    DEFAULT_STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
        'to', 'for', 'with', 'by', 'from', 'at', 'on', 'in', 'about',
        'as', 'of', 'it', 'this', 'that', 'be', 'have', 'has', 'had'
    }

    def __init__(self, config: Optional[BM25Config] = None):
        """Initialize the BM25 matcher.

        Args:
            config: BM25 configuration (uses defaults if not provided)
        """
        self.config = config or BM25Config()
        if self.config.stop_words is None:
            self.config.stop_words = self.DEFAULT_STOP_WORDS

        # Index data structures
        self._doc_ids: List[str] = []
        self._doc_lengths: List[int] = []
        self._doc_vectors: List[Dict[str, int]] = []
        self._idf_cache: Dict[str, float] = {}
        self._avg_doc_length: float = 0.0
        self._total_docs: int = 0

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms.

        Args:
            text: Input text to tokenize

        Returns:
            List of tokens after filtering and normalization
        """
        # Extract word tokens (alphanumeric + underscore)
        tokens = re.findall(r'\b\w+\b', text)

        filtered = []
        for token in tokens:
            # Apply lowercase if configured
            if self.config.lowercase:
                token = token.lower()

            # Skip stop words
            if token in self.config.stop_words:
                continue

            # Length filtering
            if len(token) < self.config.min_token_length:
                continue
            if len(token) > self.config.max_token_length:
                continue

            filtered.append(token)

        return filtered

    def build_index(
        self,
        documents: Dict[str, str],
        pre_tokenized: bool = False
    ) -> None:
        """Build the BM25 index from documents.

        Args:
            documents: Dictionary mapping doc_id to document content
            pre_tokenized: If True, values are already tokenized lists

        Example:
            >>> docs = {"doc1": "content here", "doc2": "more content"}
            >>> matcher.build_index(docs)
        """
        # Clear existing index
        self._doc_ids = []
        self._doc_lengths = []
        self._doc_vectors = []
        self._idf_cache = {}

        total_length = 0

        # Process each document
        for doc_id, content in documents.items():
            self._doc_ids.append(doc_id)

            if pre_tokenized:
                tokens = content if isinstance(content, list) else content.split()
            else:
                tokens = self._tokenize(content)

            # Count term frequencies in document
            term_freq = Counter(tokens)
            self._doc_vectors.append(dict(term_freq))
            self._doc_lengths.append(len(tokens))
            total_length += len(tokens)

        # Calculate average document length
        self._total_docs = len(self._doc_ids)
        self._avg_doc_length = total_length / self._total_docs if self._total_docs > 0 else 0

        # Pre-compute IDF values for all terms
        self._compute_idf()

    def _compute_idf(self) -> None:
        """Compute IDF values for all terms in the corpus."""
        # Count document frequency for each term
        doc_freq = Counter()

        for doc_vector in self._doc_vectors:
            for term in doc_vector:
                doc_freq[term] += 1

        # Compute IDF using smoothed version: log((N - df + 0.5) / (df + 0.5))
        for term, df in doc_freq.items():
            self._idf_cache[term] = math.log(
                (self._total_docs - df + 0.5) / (df + 0.5) + 1.0
            )

    def _get_idf(self, term: str) -> float:
        """Get IDF value for a term.

        Returns 0 for unknown terms (terms not in the corpus).
        """
        if self.config.lowercase:
            term = term.lower()
        return self._idf_cache.get(term, 0.0)

    def _score_document(
        self,
        query_tokens: List[str],
        doc_idx: int
    ) -> float:
        """Calculate BM25 score for a document.

        Args:
            query_tokens: List of query tokens
            doc_idx: Index of document in the index

        Returns:
            BM25 relevance score
        """
        doc_vector = self._doc_vectors[doc_idx]
        doc_length = self._doc_lengths[doc_idx]

        score = 0.0
        for token in query_tokens:
            # Skip if term not in document
            if token not in doc_vector:
                continue

            # Get term frequency in document
            tf = doc_vector[token]

            # Get IDF
            idf = self._get_idf(token)

            # BM25 formula
            numerator = tf * (self.config.k1 + 1)
            denominator = tf + self.config.k1 * (
                1 - self.config.b +
                self.config.b * (doc_length / self._avg_doc_length)
            )
            score += idf * (numerator / denominator)

        return score

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Tuple[str, float]]:
        """Search for documents matching the query.

        Args:
            query: Search query string
            top_k: Maximum number of results to return
            min_score: Minimum score threshold (default 0.0)

        Returns:
            List of (doc_id, score) tuples sorted by score descending

        Example:
            >>> results = matcher.search("machine learning", top_k=5)
            >>> for doc_id, score in results:
            ...     print(f"{doc_id}: {score:.3f}")
        """
        if not self._doc_ids:
            return []

        # Tokenize query
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        # Score all documents
        scores = []
        for doc_idx in range(self._total_docs):
            score = self._score_document(query_tokens, doc_idx)
            if score >= min_score:
                scores.append((self._doc_ids[doc_idx], score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top-k results
        return scores[:top_k]

    def search_with_metadata(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
        return_query_tokens: bool = False
    ) -> Dict[str, Any]:
        """Search with detailed metadata about the results.

        Args:
            query: Search query string
            top_k: Maximum number of results
            min_score: Minimum score threshold
            return_query_tokens: Whether to return the query tokens used

        Returns:
            Dictionary with results and metadata:
            {
                "results": [(doc_id, score), ...],
                "query_tokens": [...],  # if return_query_tokens=True
                "total_docs": int,
                "avg_doc_length": float,
                "matched_terms": set  # unique terms that matched
            }
        """
        query_tokens = self._tokenize(query)

        results = self.search(query, top_k=top_k, min_score=min_score)

        # Find which query terms actually matched
        matched_terms = set()
        if query_tokens and results:
            for doc_id, _ in results[:5]:  # Check top 5 results
                doc_idx = self._doc_ids.index(doc_id)
                doc_vector = self._doc_vectors[doc_idx]
                matched_terms.update(set(query_tokens) & set(doc_vector.keys()))

        output = {
            "results": results,
            "total_docs": self._total_docs,
            "avg_doc_length": self._avg_doc_length,
            "matched_terms": matched_terms
        }

        if return_query_tokens:
            output["query_tokens"] = query_tokens

        return output

    def get_doc_stats(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific document.

        Args:
            doc_id: Document identifier

        Returns:
            Dictionary with document statistics or None if not found
        """
        try:
            doc_idx = self._doc_ids.index(doc_id)
        except ValueError:
            return None

        return {
            "doc_id": doc_id,
            "length": self._doc_lengths[doc_idx],
            "unique_terms": len(self._doc_vectors[doc_idx]),
            "top_terms": sorted(
                self._doc_vectors[doc_idx].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

    def get_index_stats(self) -> Dict[str, Any]:
        """Get overall index statistics.

        Returns:
            Dictionary with index statistics
        """
        return {
            "total_documents": self._total_docs,
            "avg_doc_length": self._avg_doc_length,
            "total_unique_terms": len(self._idf_cache),
            "config": {
                "k1": self.config.k1,
                "b": self.config.b,
                "min_token_length": self.config.min_token_length,
                "max_token_length": self.config.max_token_length,
            }
        }


def create_bm25_matcher_from_files(
    file_paths: Dict[str, str],
    config: Optional[BM25Config] = None,
    max_lines: int = 100
) -> BM25Matcher:
    """Create a BM25 matcher from file contents.

    Args:
        file_paths: Dictionary mapping doc_id to file path
        config: BM25 configuration
        max_lines: Maximum lines to read from each file

    Returns:
        Initialized BM25Matcher with indexed documents

    Example:
        >>> files = {"doc1": "/path/to/doc1.md", "doc2": "/path/to/doc2.md"}
        >>> matcher = create_bm25_matcher_from_files(files)
    """
    matcher = BM25Matcher(config)

    documents = {}
    for doc_id, file_path in file_paths.items():
        try:
            path = Path(file_path)
            if path.exists():
                content = path.read_text(encoding="utf-8")
                # Limit to max_lines
                if max_lines:
                    lines = content.split('\n')[:max_lines]
                    content = '\n'.join(lines)
                documents[doc_id] = content
        except Exception:
            # Skip files that can't be read
            continue

    matcher.build_index(documents)
    return matcher


def calculate_bm25_similarity(
    query: str,
    content: str,
    config: Optional[BM25Config] = None
) -> float:
    """Quick BM25 similarity calculation for a single document.

    This is a convenience function for calculating BM25 similarity
    between a query and a single document content without building
    a full index.

    Args:
        query: Query string
        content: Document content
        config: BM25 configuration

    Returns:
        BM25 similarity score

    Example:
        >>> score = calculate_bm25_similarity("search query", "document content")
        >>> print(f"Similarity: {score:.3f}")
    """
    if not query or not content:
        return 0.0

    # Create a temporary matcher with the single document
    matcher = BM25Matcher(config)
    matcher.build_index({"doc": content})

    # Search and return the score
    results = matcher.search(query, top_k=1)
    return results[0][1] if results else 0.0


# Convenience function for tokenization
def tokenize_text(
    text: str,
    lowercase: bool = True,
    stop_words: Optional[set] = None,
    min_length: int = 2
) -> List[str]:
    """Tokenize text with configurable options.

    Args:
        text: Input text to tokenize
        lowercase: Whether to lowercase tokens
        stop_words: Optional set of stop words to filter
        min_length: Minimum token length

    Returns:
        List of tokens

    Example:
        >>> tokens = tokenize_text("Hello world! This is a test.")
        >>> print(tokens)  # ['hello', 'world', 'this', 'test']
    """
    tokens = re.findall(r'\b\w+\b', text)

    filtered = []
    stop_words = stop_words or BM25Matcher.DEFAULT_STOP_WORDS

    for token in tokens:
        if lowercase:
            token = token.lower()

        if token in stop_words:
            continue

        if len(token) < min_length:
            continue

        filtered.append(token)

    return filtered
