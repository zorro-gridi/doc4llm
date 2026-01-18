"""
Search helper functions for md-doc-searcher skill.

This module provides lightweight helper functions for document search operations.
These helpers perform deterministic operations (path construction, formatting)
and do NOT replace LLM semantic understanding capabilities.

Core Principle:
- Helpers: Deterministic operations (path building, command construction)
- LLM: Semantic understanding (intent analysis, concept matching)
"""
import re
from typing import List, Optional


class SearchHelpers:
    """Helper functions for document search operations.

    These functions assist with repetitive formatting and construction tasks
    while preserving LLM's semantic understanding for core matching logic.
    """

    # Pattern for extracting original URL from docTOC.md
    ORIGINAL_URL_PATTERN = re.compile(
        r'>\s*\*\*原文链接\*\*\s*:\s*(https?://[^\s]+)',
        re.IGNORECASE
    )

    # Stop words to remove when extracting keywords
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
        'to', 'for', 'with', 'by', 'from', 'at', 'on', 'in', 'about',
        'how', 'what', 'where', 'when', 'why', 'which', 'that', 'this',
        'these', 'those', 'use', 'using', 'can', 'will', 'would'
    }

    # Technical terms to preserve during keyword extraction
    TECHNICAL_TERMS = {
        'api', 'cli', 'sdk', 'http', 'https', 'jwt', 'oauth', 'ssh',
        'webhook', 'middleware', 'endpoint', 'token', 'auth', 'config',
        'deploy', 'hooks', 'async', 'sync', 'json', 'xml', 'yaml', 'yml'
    }

    @staticmethod
    def build_toc_glob_pattern(doc_set: str) -> str:
        """Build Glob pattern for finding TOC files in a documentation set.

        Args:
            doc_set: Documentation set name (e.g., "Claude_Code_Docs:latest")

        Returns:
            Glob pattern string for finding docTOC.md files

        Examples:
            >>> SearchHelpers.build_toc_glob_pattern("Claude_Code_Docs:latest")
            'md_docs/Claude_Code_Docs:latest/*/docTOC.md'
        """
        return f"md_docs/{doc_set}/*/docTOC.md"

    @staticmethod
    def build_content_glob_pattern(doc_set: str) -> str:
        """Build Glob pattern for finding content files in a documentation set.

        Args:
            doc_set: Documentation set name (e.g., "Claude_Code_Docs:latest")

        Returns:
            Glob pattern string for finding docContent.md files

        Examples:
            >>> SearchHelpers.build_content_glob_pattern("Claude_Code_Docs:latest")
            'md_docs/Claude_Code_Docs:latest/*/docContent.md'
        """
        return f"md_docs/{doc_set}/*/docContent.md"

    @staticmethod
    def build_toc_path(doc_set: str, page_title: str) -> str:
        """Build the full path to a docTOC.md file.

        Args:
            doc_set: Documentation set name (e.g., "Claude_Code_Docs:latest")
            page_title: Page title (e.g., "Agent Skills")

        Returns:
            Full path to the docTOC.md file

        Examples:
            >>> SearchHelpers.build_toc_path("Claude_Code_Docs:latest", "Agent Skills")
            'md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md'
        """
        return f"md_docs/{doc_set}/{page_title}/docTOC.md"

    @staticmethod
    def build_content_path(doc_set: str, page_title: str) -> str:
        """Build the full path to a docContent.md file.

        Args:
            doc_set: Documentation set name (e.g., "Claude_Code_Docs:latest")
            page_title: Page title (e.g., "Agent Skills")

        Returns:
            Full path to the docContent.md file

        Examples:
            >>> SearchHelpers.build_content_path("Claude_Code_Docs:latest", "Agent Skills")
            'md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md'
        """
        return f"md_docs/{doc_set}/{page_title}/docContent.md"

    @staticmethod
    def build_level2_grep_command(keywords: List[str], doc_set: str) -> str:
        """Build Level 2 TOC grep command.

        Constructs a grep command for searching keywords in TOC files.
        This helper only constructs the command string; execution is left to the LLM.

        Args:
            keywords: List of keywords to search for
            doc_set: Documentation set name

        Returns:
            Grep command string

        Examples:
            >>> SearchHelpers.build_level2_grep_command(
            ...     ["configure", "hooks"], "Claude_Code_Docs:latest"
            ... )
            "grep -r -iE '(configure|hooks)' md_docs/Claude_Code_Docs:latest/*/docTOC.md"
        """
        if not keywords:
            return ""
        pattern = "|".join(keywords)
        return f"grep -r -iE '({pattern})' md_docs/{doc_set}/*/docTOC.md"

    @staticmethod
    def build_level3_content_grep_command(
        keywords: List[str],
        doc_sets: List[str],
        context_lines: int = 10
    ) -> str:
        """Build Level 3.2 content grep command with context.

        Constructs a grep command for searching keywords in content files
        with context lines before the match (for traceback).

        Args:
            keywords: List of keywords to search for
            doc_sets: List of documentation set names to search
            context_lines: Number of context lines before match (default: 10)

        Returns:
            Grep command string with -B flag for context

        Examples:
            >>> SearchHelpers.build_level3_content_grep_command(
            ...     ["design"], ["Claude_Code_Docs:latest"], 10
            ... )
            "grep -r -i -B 10 'design' md_docs/Claude_Code_Docs:latest/*/docContent.md"
        """
        if not keywords or not doc_sets:
            return ""

        # Build search paths for multiple doc sets
        search_paths = " ".join([
            f"md_docs/{doc_set}/*/docContent.md" for doc_set in doc_sets
        ])

        pattern = keywords[0] if len(keywords) == 1 else f"({'|'.join(keywords)})"
        return f"grep -r -i -B {context_lines} '{pattern}' {search_paths}"

    @staticmethod
    def extract_original_url(toc_content: str) -> Optional[str]:
        """Extract original URL from docTOC.md content.

        Args:
            toc_content: Content of a docTOC.md file

        Returns:
            Original URL if found, None otherwise

        Examples:
            >>> toc = "> **原文链接**: https://code.claude.com/docs/en/agent-skills"
            >>> SearchHelpers.extract_original_url(toc)
            'https://code.claude.com/docs/en/agent-skills'
        """
        match = SearchHelpers.ORIGINAL_URL_PATTERN.search(toc_content)
        return match.group(1).strip() if match else None

    @staticmethod
    def extract_keywords(query: str) -> List[str]:
        """Extract core keywords from a query for Level 2/3 fallback.

        This helper performs basic keyword extraction by removing stop words
        and preserving technical terms. However, LLM semantic understanding
        should be used for final keyword selection.

        Args:
            query: User query string

        Returns:
            List of extracted keywords

        Examples:
            >>> SearchHelpers.extract_keywords("how to configure hooks for deployment")
            ['configure', 'hooks', 'deployment']
        """
        # Tokenize and clean
        words = re.findall(r'\b\w+\b', query.lower())

        # Remove stop words but preserve technical terms
        keywords = [
            word for word in words
            if word not in SearchHelpers.STOP_WORDS or word in SearchHelpers.TECHNICAL_TERMS
        ]

        # Remove duplicates while preserving order
        seen = set()
        result = []
        for word in keywords:
            if word not in seen:
                seen.add(word)
                result.append(word)

        return result

    @staticmethod
    def format_sources_section(
        titles_and_urls: List[tuple[str, str, str]]
    ) -> str:
        """Format the Sources section for search results.

        Args:
            titles_and_urls: List of (title, original_url, toc_path) tuples

        Returns:
            Formatted Sources section in markdown

        Examples:
            >>> SearchHelpers.format_sources_section([
            ...     ("Agent Skills", "https://example.com/skills", "md_docs/.../docTOC.md")
            ... ])
            '### 文档来源...
    1. **Agent Skills**
       - 原文链接: https://example.com/skills
       ...'
        """
        if not titles_and_urls:
            return ""

        lines = ["\n---\n\n### 文档来源\n"]

        for i, (title, url, toc_path) in enumerate(titles_and_urls, 1):
            lines.append(f"{i}. **{title}**")
            lines.append(f"   - 原文链接: {url}")
            lines.append(f"   - TOC 路径: `{toc_path}`")

        return "\n".join(lines) + "\n"

    @staticmethod
    def format_coverage_section(
        covered: List[str],
        partial: List[str],
        not_covered: List[str],
        suggestion: Optional[str] = None
    ) -> str:
        """Format the Coverage section for search results.

        Args:
            covered: List of covered aspects
            partial: List of partially covered aspects
            not_covered: List of not covered aspects
            suggestion: Optional suggestion for further search

        Returns:
            Formatted Coverage section in markdown

        Examples:
            >>> SearchHelpers.format_coverage_section(
            ...     ["Configuration", "Setup"],
            ...     ["Advanced patterns"],
            ...     ["Performance"],
            ...     "Search 'performance' for optimization tips"
            ... )
            '**Coverage:**\\n- ✅ Covered: Configuration, Setup...'
        """
        lines = ["\n**Coverage:**"]

        if covered:
            lines.append(f"- ✅ Covered: {', '.join(covered)}")

        if partial:
            lines.append(f"- ⚠️  Partially covered: {', '.join(partial)}")

        if not_covered:
            lines.append(f"- ❌ Not covered: {', '.join(not_covered)}")

        if suggestion:
            lines.append(f"- 💡 Suggestion: {suggestion}")

        return "\n".join(lines)

    @staticmethod
    def build_doc_set_filter_pattern(intent_keywords: List[str]) -> str:
        """Build a filter pattern for documentation sets based on intent keywords.

        Args:
            intent_keywords: List of keywords for filtering doc sets

        Returns:
            Glob pattern for filtering documentation sets

        Examples:
            >>> SearchHelpers.build_doc_set_filter_pattern(["Claude", "Code"])
            'md_docs/*Claude* md_docs/*Code*'
        """
        patterns = [f"md_docs/*{keyword}*" for keyword in intent_keywords]
        return " ".join(patterns)

    @staticmethod
    def get_list_command(base_dir: str = "md_docs") -> str:
        """Get the command to list all available documentation sets.

        Args:
            base_dir: Base directory containing documentation sets

        Returns:
            Bash command string to list documentation sets

        Note:
            Actual execution should be done via Bash tool.

        Examples:
            >>> SearchHelpers.get_list_command()
            'ls -1 md_docs/'
        """
        return f"ls -1 {base_dir}/"

    @staticmethod
    def build_title_extraction_command(content_path: str, max_lines: int = 5) -> str:
        """Build command to extract title from docContent.md.

        Args:
            content_path: Path to docContent.md file
            max_lines: Maximum number of lines to check for title (default: 5)

        Returns:
            Head command string

        Examples:
            >>> SearchHelpers.build_title_extraction_command(
            ...     "md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md"
            ... )
            'head -5 md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md'
        """
        return f"head -{max_lines} {content_path}"
