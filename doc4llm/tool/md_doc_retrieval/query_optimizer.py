"""
Query Optimizer for Document Retrieval

Optimizes user queries through decomposition, expansion, rewriting,
and multi-query generation to improve document retrieval quality.
"""
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class OptimizedQuery:
    """Represents an optimized query with metadata."""
    query: str
    rank: int
    strategy: str  # "original", "decomposition", "expansion", "rewriting", "translation"
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "rank": self.rank,
            "strategy": self.strategy,
            "confidence": self.confidence
        }


@dataclass
class QueryAnalysis:
    """Analysis result of a user query."""
    original_query: str
    language: str  # "zh", "en", "mixed"
    complexity: str  # "low", "medium", "high"
    ambiguity: str  # "low", "medium", "high"
    is_colloquial: bool
    has_conjunctions: bool
    technical_terms: List[str]
    domain: Optional[str]


class QueryOptimizer:
    """
    Optimize user queries for better document retrieval.

    Supports:
    - Query decomposition for complex queries
    - Query expansion with synonyms
    - Query rewriting for colloquial language
    - Multi-query generation
    """

    # Conjunction patterns for decomposition (Chinese and English)
    CONJUNCTION_PATTERNS = [
        r'\s+[和与与以及]\s+',
        r'\s+and\s+',
        r'\s+,',
        r'\s+;\s+',
        r'，\s*',
        r'；\s*',
    ]

    # Chinese colloquial patterns
    COLLOQUIAL_PATTERNS = {
        r'咋[弄办做]': 'how to',
        r'怎么[弄办做]': 'how to',
        r'如何': 'how to',
        r'啥': 'what',
        r'那个': 'the',  # Context-dependent
        r'来着': '',  # Reminder marker, remove
    }

    # Expansion mappings (Chinese → English)
    EXPANSION_ZH = {
        '配置': ['configuration', 'setup', 'settings', 'configure'],
        '部署': ['deployment', 'deploy', 'production', 'release'],
        '安全': ['security', 'secure', 'authentication', 'authorization'],
        '文档': ['documentation', 'docs', 'guide', 'reference'],
        '安装': ['installation', 'install', 'setup'],
        '教程': ['tutorial', 'guide', 'how to'],
        '参考': ['reference', 'docs', 'documentation'],
        '示例': ['example', 'sample', 'demo'],
        '问题': ['issue', 'problem', 'troubleshooting'],
        '错误': ['error', 'exception', 'failure'],
        '方法': ['method', 'function', 'approach'],
        '功能': ['feature', 'capability', 'functionality'],
        '使用': ['usage', 'using', 'use'],
        '设置': ['settings', 'configuration', 'setup'],
    }

    # Expansion mappings (English → English)
    EXPANSION_EN = {
        'configuration': ['setup', 'settings', 'configure', 'config'],
        'deployment': ['deploy', 'production', 'release', 'deploying'],
        'security': ['secure', 'authentication', 'authorization', 'auth'],
        'documentation': ['docs', 'guide', 'reference', 'tutorial'],
        'installation': ['install', 'setup', 'getting started'],
        'tutorial': ['guide', 'how to', 'getting started'],
        'reference': ['docs', 'documentation', 'api'],
        'example': ['sample', 'demo', 'examples'],
        'issue': ['problem', 'troubleshooting', 'error'],
        'error': ['exception', 'failure', 'bug'],
        'method': ['function', 'approach', 'way'],
        'feature': ['capability', 'functionality'],
        'usage': ['using', 'use', 'how to use'],
        'settings': ['configuration', 'setup', 'config'],
    }

    # Domain-specific term mappings
    DOMAIN_TERMS = {
        'claude': ['Claude Code', 'Claude', 'claude'],
        'python': ['Python', 'python3', 'python'],
        'react': ['React', 'ReactJS', 'react'],
        'javascript': ['JavaScript', 'JS', 'javascript', 'js'],
        'typescript': ['TypeScript', 'TS', 'typescript', 'ts'],
    }

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        debug_mode: bool = False
    ):
        """
        Initialize the query optimizer.

        Args:
            config: Optional configuration dict
            debug_mode: Enable debug output
        """
        self.config = config or self._default_config()
        self.debug_mode = debug_mode

    def _default_config(self) -> Dict[str, Any]:
        return {
            "max_optimized_queries": 5,
            "min_confidence_threshold": 0.6,
            "enable_decomposition": True,
            "enable_expansion": True,
            "enable_rewriting": True,
            "language_priority": ["zh", "en"],
        }

    def optimize(
        self,
        query: str,
        max_queries: Optional[int] = None
    ) -> List[OptimizedQuery]:
        """
        Optimize a user query.

        Args:
            query: The original user query
            max_queries: Maximum number of optimized queries to return

        Returns:
            List of OptimizedQuery objects, ranked by confidence
        """
        self._debug_print(f"=== Optimizing query: '{query}' ===")

        max_queries = max_queries or self.config.get("max_optimized_queries", 5)

        # Analyze the query
        analysis = self._analyze_query(query)
        self._debug_print(f"Analysis: complexity={analysis.complexity}, "
                        f"ambiguity={analysis.ambiguity}, language={analysis.language}")

        # Start with original query
        optimized_queries: List[OptimizedQuery] = [
            OptimizedQuery(
                query=query,
                rank=1,
                strategy="original",
                confidence=1.0
            )
        ]

        # Apply strategies based on analysis
        if (analysis.has_conjunctions and
            self.config.get("enable_decomposition", True)):
            decomposed = self._decompose_query(query, analysis)
            optimized_queries.extend(decomposed)

        if analysis.ambiguity in ["medium", "high"] and self.config.get("enable_expansion", True):
            expanded = self._expand_query(query, analysis)
            optimized_queries.extend(expanded)

        if analysis.is_colloquial and self.config.get("enable_rewriting", True):
            rewritten = self._rewrite_query(query, analysis)
            optimized_queries.extend(rewritten)

        # Remove duplicates (case-insensitive)
        seen = set()
        unique_queries = []
        for q in optimized_queries:
            query_lower = q.query.lower().strip()
            if query_lower not in seen:
                seen.add(query_lower)
                unique_queries.append(q)

        # Re-rank by confidence
        unique_queries.sort(key=lambda q: q.confidence, reverse=True)

        # Update ranks
        for i, q in enumerate(unique_queries, start=1):
            q.rank = i

        # Limit results
        final_queries = unique_queries[:max_queries]

        self._debug_print(f"Generated {len(final_queries)} optimized queries")

        return final_queries

    def _analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze query characteristics."""
        query_lower = query.lower()

        # Detect language
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', query))
        english_chars = len(re.findall(r'[a-z]', query_lower))
        total_chars = chinese_chars + english_chars

        if total_chars == 0:
            language = "unknown"
        elif chinese_chars > english_chars * 0.5:
            language = "zh"
        elif english_chars > chinese_chars * 2:
            language = "en"
        else:
            language = "mixed"

        # Detect conjunctions
        has_conjunctions = any(
            re.search(pattern, query) for pattern in self.CONJUNCTION_PATTERNS
        )

        # Detect colloquialism (mainly Chinese)
        is_colloquial = any(
            re.search(pattern, query) for pattern in self.COLLOQUIAL_PATTERNS.keys()
        ) if language in ["zh", "mixed"] else False

        # Extract technical terms
        technical_terms = self._extract_technical_terms(query)

        # Infer domain
        domain = self._infer_domain(query)

        # Determine complexity
        complexity = "low"
        if has_conjunctions:
            complexity = "high"
        elif len(query.split()) > 10:
            complexity = "medium"

        # Determine ambiguity (heuristic)
        ambiguity = "low"
        if len(technical_terms) == 0 and complexity == "low":
            ambiguity = "high"
        elif len(technical_terms) == 1 and not has_conjunctions:
            ambiguity = "medium"

        return QueryAnalysis(
            original_query=query,
            language=language,
            complexity=complexity,
            ambiguity=ambiguity,
            is_colloquial=is_colloquial,
            has_conjunctions=has_conjunctions,
            technical_terms=technical_terms,
            domain=domain
        )

    def _decompose_query(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> List[OptimizedQuery]:
        """Decompose complex queries into simpler sub-queries."""
        decomposed: List[OptimizedQuery] = []

        # Try each conjunction pattern
        for pattern in self.CONJUNCTION_PATTERNS:
            parts = re.split(pattern, query)
            if len(parts) > 1:
                # Found a conjunction, create sub-queries
                for i, part in enumerate(parts, start=2):
                    part = part.strip()
                    if part:
                        decomposed.append(OptimizedQuery(
                            query=part,
                            rank=i,
                            strategy="decomposition",
                            confidence=0.9 - (i * 0.1)
                        ))
                break  # Only use first matching pattern

        return decomposed

    def _expand_query(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> List[OptimizedQuery]:
        """Expand query with synonyms and related terms."""
        expanded: List[OptimizedQuery] = []

        # Get appropriate expansion dictionary
        if analysis.language == "zh":
            expansion_dict = self.EXPANSION_ZH
        else:
            expansion_dict = self.EXPANSION_EN

        # Find expandable terms
        for term, synonyms in expansion_dict.items():
            if term.lower() in query.lower():
                # Generate variations
                for i, synonym in enumerate(synonyms[:2], start=1):  # Limit to 2 per term
                    # Replace term with synonym
                    variation = re.sub(
                        re.escape(term),
                        synonym,
                        query,
                        flags=re.IGNORECASE
                    )

                    if variation.lower() != query.lower():
                        expanded.append(OptimizedQuery(
                            query=variation,
                            rank=len(expanded) + 2,
                            strategy="expansion",
                            confidence=0.8 - (i * 0.1)
                        ))

        return expanded

    def _rewrite_query(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> List[OptimizedQuery]:
        """Rewrite colloquial or informal queries."""
        rewritten: List[OptimizedQuery] = []

        # Apply colloquial pattern replacements
        for pattern, replacement in self.COLLOQUIAL_PATTERNS.items():
            if re.search(pattern, query):
                # Replace colloquial pattern
                formal = re.sub(pattern, replacement, query)

                # Clean up extra whitespace
                formal = re.sub(r'\s+', ' ', formal).strip()

                if formal != query and formal:
                    # Translate Chinese to English if needed
                    translated = self._translate_to_english(formal)

                    if translated:
                        rewritten.append(OptimizedQuery(
                            query=translated,
                            rank=len(rewritten) + 2,
                            strategy="rewriting",
                            confidence=0.85
                        ))

        return rewritten

    def _translate_to_english(self, query: str) -> Optional[str]:
        """
        Simple translation from Chinese to English using pattern matching.

        This is a basic implementation. For production, consider using
        a proper translation service.
        """
        # Common patterns
        translations = [
            (r'如何\s*(.+)', r'\1 configuration'),
            (r'怎么\s*(.+)', r'how to \1'),
            (r'配置\s*(.+)', r'\1 setup'),
            (r'使用\s*(.+)', r'using \1'),
            (r'关于\s*(.+)', r'\1 overview'),
        ]

        for pattern, replacement in translations:
            if re.search(pattern, query):
                return re.sub(pattern, replacement, query)

        # No pattern matched, return None
        return None

    def _extract_technical_terms(self, query: str) -> List[str]:
        """Extract technical terms from query."""
        technical_terms = []

        # Common technical patterns
        patterns = [
            r'\b[A-Z]{2,}\b',  # Acronyms like API, CLI, SDK
            r'\b[a-z]+[A-Z][a-z]+\b',  # CamelCase like ClaudeCode
            r'\b\w+\.js\b',  # File extensions
            r'\b\w+\.py\b',
            r'\b\w+-\w+\b',  # Hyphenated terms
        ]

        for pattern in patterns:
            matches = re.findall(pattern, query)
            technical_terms.extend(matches)

        # Add known technical terms
        all_terms = set(self.EXPANSION_ZH.keys()) | set(self.EXPANSION_EN.keys())
        for term in all_terms:
            if term.lower() in query.lower():
                technical_terms.append(term)

        return list(set(technical_terms))

    def _infer_domain(self, query: str) -> Optional[str]:
        """Infer the domain from the query."""
        query_lower = query.lower()

        for domain, terms in self.DOMAIN_TERMS.items():
            if any(term.lower() in query_lower for term in terms):
                return domain

        return None

    def _debug_print(self, msg: str):
        if self.debug_mode:
            print(f"[QueryOptimizer] {msg}")


def optimize_query(
    query: str,
    config: Optional[Dict[str, Any]] = None,
    debug_mode: bool = False
) -> List[str]:
    """
    Convenience function for query optimization.

    Args:
        query: The user query to optimize
        config: Optional configuration
        debug_mode: Enable debug output

    Returns:
        List of optimized query strings

    Example:
        >>> queries = optimize_query("如何配置 hooks")
        >>> print(queries)
        ['如何配置 hooks', 'hooks configuration', 'setup hooks']
    """
    optimizer = QueryOptimizer(config=config, debug_mode=debug_mode)
    optimized = optimizer.optimize(query)
    return [q.query for q in optimized]
