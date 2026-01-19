"""
Search helper functions for md-doc-searcher skill.

This module provides lightweight helper functions for document search operations.
These helpers perform deterministic operations (path construction, formatting)
and do NOT replace LLM semantic understanding capabilities.

Core Principle:
- Helpers: Deterministic operations (path building, command construction, formatting)
- LLM: Semantic understanding (intent analysis, concept matching, relevance scoring)

Version 2.9.0 Features:
- Content language consistency constraints for result formatting
- TOC structure extraction from docTOC.md files
- Language-adaptive result formatting (Chinese/English/Mixed)
- Markdown heading extraction with hierarchy preservation

Version 2.8.0 Features:
- Intent analysis framework for query understanding
- Relevance scoring structure for document filtering
- Filtered results formatting for precision improvement
- Comprehensive filtering summary generation
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
            >>> SearchHelpers.extract_keywords("如何配置hooks用于测试")
            ['配置', 'hooks', '测试']
        """
        # Handle mixed language queries - preserve both Chinese and English words
        # Use a more inclusive pattern for Chinese characters
        words = re.findall(r'[\w\u4e00-\u9fff]+', query.lower())

        # Remove English stop words but preserve technical terms and Chinese words
        keywords = []
        for word in words:
            # Keep Chinese words (contains Chinese characters)
            if re.search(r'[\u4e00-\u9fff]', word):
                keywords.append(word)
            # Keep English technical terms
            elif word in SearchHelpers.TECHNICAL_TERMS:
                keywords.append(word)
            # Keep English words that are not stop words
            elif word not in SearchHelpers.STOP_WORDS:
                keywords.append(word)

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

    # ========================================================================
    # Content Language and TOC Processing Helpers (v2.9.0)
    # ========================================================================

    @staticmethod
    def extract_toc_headings(toc_content: str, max_headings: int = 10) -> str:
        """Extract markdown headings from docTOC.md content.

        This helper extracts the actual markdown headings from TOC content
        to be included in search results, preserving the original language
        and hierarchical structure.

        Args:
            toc_content: Content of a docTOC.md file
            max_headings: Maximum number of headings to extract (default: 10)

        Returns:
            Formatted string of markdown headings

        Examples:
            >>> toc = '''# Agent Skills
            ... ## 1. Create your first Skill
            ... ### 1.1. Where Skills live
            ... ## 2. Configure Skills'''
            >>> SearchHelpers.extract_toc_headings(toc)
            '# Agent Skills\\n## 1. Create your first Skill\\n### 1.1. Where Skills live\\n## 2. Configure Skills'
        """
        if not toc_content:
            return ""

        lines = toc_content.split('\n')
        headings = []
        count = 0

        for line in lines:
            line = line.strip()
            # Match markdown headings (# ## ### etc.)
            if line.startswith('#') and count < max_headings:
                # Remove URL links from headings for cleaner display
                # Pattern: "## 1. Title：https://example.com/link"
                if '：https://' in line:
                    line = line.split('：https://')[0]
                elif ': https://' in line:
                    line = line.split(': https://')[0]
                
                headings.append(line)
                count += 1

        return '\n'.join(headings)

    @staticmethod
    def detect_content_language(content: str) -> str:
        """Detect the primary language of content.

        This helper performs basic language detection to determine if content
        is primarily Chinese, English, or mixed language.

        Args:
            content: Text content to analyze

        Returns:
            Language code: 'zh' for Chinese, 'en' for English, 'mixed' for mixed

        Examples:
            >>> SearchHelpers.detect_content_language("Agent Skills")
            'en'
            >>> SearchHelpers.detect_content_language("代理技能")
            'zh'
            >>> SearchHelpers.detect_content_language("Agent Skills 代理技能")
            'mixed'
        """
        if not content:
            return 'en'

        # Count Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        # Count English letters
        english_chars = len(re.findall(r'[a-zA-Z]', content))
        
        total_chars = chinese_chars + english_chars
        if total_chars == 0:
            return 'en'

        chinese_ratio = chinese_chars / total_chars
        
        if chinese_ratio > 0.6:
            return 'zh'
        elif chinese_ratio < 0.2:
            return 'en'
        else:
            return 'mixed'

    @staticmethod
    def format_language_appropriate_results(
        results: List[dict], 
        detected_language: str
    ) -> str:
        """Format results using language-appropriate labels and structure.

        Args:
            results: List of result dictionaries with metadata
            detected_language: Detected language ('zh', 'en', 'mixed')

        Returns:
            Formatted results with appropriate language labels

        Examples:
            >>> results = [{"title": "Agent Skills", "score": 0.9, "toc_content": "# Agent Skills\\n## Create"}]
            >>> SearchHelpers.format_language_appropriate_results(results, 'en')
            '1. **Agent Skills** - Relevance: 0.9\\n   - Content:\\n     # Agent Skills\\n     ## Create'
        """
        if not results:
            return ""

        # Language-specific labels
        labels = {
            'zh': {
                'content': '正文内容',
                'relevance': '相关性',
                'intent_match': '意图匹配',
                'toc_path': 'TOC 路径'
            },
            'en': {
                'content': 'Content',
                'relevance': 'Relevance',
                'intent_match': 'Intent Match',
                'toc_path': 'TOC Path'
            },
            'mixed': {
                'content': '正文内容 (Content)',
                'relevance': '相关性 (Relevance)',
                'intent_match': '意图匹配 (Intent Match)',
                'toc_path': 'TOC 路径 (TOC Path)'
            }
        }

        current_labels = labels.get(detected_language, labels['en'])
        lines = []

        for i, doc in enumerate(results, 1):
            lines.append(f"{i}. **{doc['title']}** - {current_labels['relevance']}: {doc.get('score', 'N/A')}")
            
            if 'rationale' in doc:
                lines.append(f"   - {current_labels['intent_match']}: {doc['rationale']}")
            
            if 'path' in doc:
                lines.append(f"   - {current_labels['toc_path']}: `{doc['path']}`")
            
            # Add TOC content if available
            if 'toc_content' in doc and doc['toc_content']:
                lines.append(f"   - {current_labels['content']}:")
                # Indent each line of TOC content
                toc_lines = doc['toc_content'].split('\n')
                for toc_line in toc_lines:
                    if toc_line.strip():
                        lines.append(f"     {toc_line}")
            
            lines.append("")

        return '\n'.join(lines)

    @staticmethod
    def build_toc_content_extraction_command(toc_path: str, max_lines: int = 50) -> str:
        """Build command to extract TOC content for result formatting.

        Args:
            toc_path: Path to docTOC.md file
            max_lines: Maximum number of lines to extract (default: 50)

        Returns:
            Head command string to extract TOC content

        Examples:
            >>> SearchHelpers.build_toc_content_extraction_command(
            ...     "md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md"
            ... )
            'head -50 md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md'
        """
        return f"head -{max_lines} {toc_path}"

    # ========================================================================
    # Intent Analysis and Filtering Helpers (Step 6 - v2.8.0)
    # ========================================================================

    @staticmethod
    def analyze_query_intent(original_query: str) -> dict:
        """Analyze the original user query to determine intent classification.

        This helper provides structured intent analysis for LLM-based filtering.
        The actual semantic analysis should be performed by the LLM using this
        framework as guidance.

        Args:
            original_query: The original user query (not optimized queries)

        Returns:
            Intent analysis framework with keys:
            - primary_intent: LEARN, CONFIGURE, TROUBLESHOOT, REFERENCE, COMPARE
            - scope: SPECIFIC, GENERAL, CONTEXTUAL
            - depth: OVERVIEW, DETAILED, PRACTICAL
            - specificity_keywords: Key terms indicating specific focus

        Examples:
            >>> SearchHelpers.analyze_query_intent("如何配置Claude Code的hooks用于自动化测试")
            {
                "primary_intent": "CONFIGURE",
                "scope": "SPECIFIC", 
                "depth": "PRACTICAL",
                "specificity_keywords": ["hooks", "自动化测试", "配置"]
            }

        Note:
            This helper provides the framework structure. The LLM should perform
            the actual semantic analysis to populate these fields.
        """
        # Extract potential specificity keywords using existing helper
        keywords = SearchHelpers.extract_keywords(original_query)
        
        # Return framework structure - LLM should populate with semantic analysis
        return {
            "primary_intent": "UNKNOWN",  # LLM should determine: LEARN, CONFIGURE, etc.
            "scope": "UNKNOWN",           # LLM should determine: SPECIFIC, GENERAL, etc.
            "depth": "UNKNOWN",           # LLM should determine: OVERVIEW, DETAILED, etc.
            "specificity_keywords": keywords,
            "framework_note": "LLM should perform semantic analysis to populate intent fields"
        }

    @staticmethod
    def calculate_relevance_score(
        doc_title: str, 
        doc_context: Optional[str], 
        query_intent: dict
    ) -> dict:
        """Calculate relevance score framework for a document based on query intent.

        This helper provides the scoring framework structure. The LLM should
        perform the actual semantic evaluation to calculate scores.

        Args:
            doc_title: Document title
            doc_context: Additional context from TOC or content (optional)
            query_intent: Intent analysis result from analyze_query_intent()

        Returns:
            Relevance analysis framework with keys:
            - score: Overall relevance score (0.0-1.0) - LLM calculated
            - intent_match: How well document serves the intent (0.0-1.0)
            - scope_alignment: Scope alignment score (0.0-1.0)
            - depth_appropriateness: Depth appropriateness score (0.0-1.0)
            - specificity_match: Specificity alignment score (0.0-1.0)
            - rationale: Brief explanation of the scoring

        Examples:
            >>> SearchHelpers.calculate_relevance_score(
            ...     "Hooks reference",
            ...     "Configuration options and setup guide",
            ...     {"primary_intent": "CONFIGURE", "scope": "SPECIFIC"}
            ... )
            {
                "score": 0.0,  # LLM should calculate
                "intent_match": 0.0,
                "scope_alignment": 0.0,
                "depth_appropriateness": 0.0,
                "specificity_match": 0.0,
                "rationale": "LLM should provide semantic evaluation"
            }

        Note:
            This helper provides the scoring framework. The LLM should perform
            semantic evaluation to calculate actual scores.
        """
        return {
            "score": 0.0,  # LLM should calculate overall score
            "intent_match": 0.0,  # LLM should evaluate intent alignment
            "scope_alignment": 0.0,  # LLM should evaluate scope match
            "depth_appropriateness": 0.0,  # LLM should evaluate depth match
            "specificity_match": 0.0,  # LLM should evaluate specificity
            "rationale": "LLM should provide semantic evaluation and rationale",
            "doc_title": doc_title,
            "doc_context": doc_context or "",
            "query_intent": query_intent
        }

    @staticmethod
    def format_filtered_results(
        high_relevance: List[dict], 
        medium_relevance: List[dict], 
        filtered_out: List[dict]
    ) -> str:
        """Format the filtered results with relevance categories.

        Args:
            high_relevance: High relevance documents (≥0.8) with metadata
            medium_relevance: Medium relevance documents (0.5-0.79) with metadata  
            filtered_out: Filtered out documents (<0.5) with reasons

        Returns:
            Formatted filtered results section in markdown

        Examples:
            >>> SearchHelpers.format_filtered_results(
            ...     [{"title": "Hooks reference", "score": 0.9, "rationale": "Direct guide"}],
            ...     [{"title": "Testing guide", "score": 0.6, "rationale": "Related"}],
            ...     [{"title": "API ref", "score": 0.2, "reason": "Different topic"}]
            ... )
            '## 精准检索结果 (Intent-Filtered Results)\\n\\n### 高相关性文档...'
        """
        lines = ["## 精准检索结果 (Intent-Filtered Results)\n"]

        # High relevance section
        if high_relevance:
            lines.append("### 高相关性文档 (High Relevance ≥0.8)")
            for i, doc in enumerate(high_relevance, 1):
                lines.append(f"{i}. **{doc['title']}** - Relevance: {doc.get('score', 'N/A')}")
                if 'rationale' in doc:
                    lines.append(f"   - Intent Match: {doc['rationale']}")
                if 'path' in doc:
                    lines.append(f"   - TOC Path: `{doc['path']}`")
                # Add TOC content if available
                if 'toc_content' in doc and doc['toc_content']:
                    lines.append(f"   - 正文内容:")
                    lines.append(f"     {doc['toc_content']}")
                lines.append("")

        # Medium relevance section
        if medium_relevance:
            lines.append("### 相关文档 (Medium Relevance 0.5-0.79)")
            start_num = len(high_relevance) + 1
            for i, doc in enumerate(medium_relevance, start_num):
                lines.append(f"{i}. **{doc['title']}** - Relevance: {doc.get('score', 'N/A')}")
                if 'rationale' in doc:
                    lines.append(f"   - Intent Match: {doc['rationale']}")
                if 'note' in doc:
                    lines.append(f"   - Note: {doc['note']}")
                if 'path' in doc:
                    lines.append(f"   - TOC Path: `{doc['path']}`")
                # Add TOC content if available
                if 'toc_content' in doc and doc['toc_content']:
                    lines.append(f"   - 正文内容:")
                    lines.append(f"     {doc['toc_content']}")
                lines.append("")

        # Filtered out section
        if filtered_out:
            lines.append("### 已过滤文档 (Filtered Out <0.5)")
            for doc in filtered_out:
                reason = doc.get('reason', 'Low relevance score')
                lines.append(f"- \"{doc['title']}\" - Reason: {reason}")

        return "\n".join(lines)

    @staticmethod
    def format_filtering_summary(
        original_count: int, 
        final_count: int, 
        precision_improvement: str
    ) -> str:
        """Format a summary of the filtering process.

        Args:
            original_count: Number of documents before filtering
            final_count: Number of documents after filtering (high + medium)
            precision_improvement: Description of precision improvement

        Returns:
            Formatted filtering summary in markdown

        Examples:
            >>> SearchHelpers.format_filtering_summary(5, 3, "60% → 100%")
            '**Filtering Summary:**\\n- Original results: 5 documents...'
        """
        high_count = final_count  # Assuming final_count represents kept documents
        filtered_count = original_count - final_count

        lines = [
            "\n**Filtering Summary:**",
            f"- Original results: {original_count} documents",
            f"- Final results: {final_count} documents",
            f"- Filtered out: {filtered_count} documents",
            f"- Precision improvement: {precision_improvement}"
        ]

        return "\n".join(lines)

    @staticmethod
    def get_intent_classification_guide() -> dict:
        """Get the intent classification guide for LLM reference.

        Returns:
            Dictionary containing intent classification guidelines

        Note:
            This helper provides reference information for LLM-based intent analysis.
        """
        return {
            "primary_intent_types": {
                "LEARN": "User wants to understand concepts, principles, or how things work",
                "CONFIGURE": "User wants to set up, customize, or modify settings", 
                "TROUBLESHOOT": "User wants to solve problems or fix issues",
                "REFERENCE": "User wants quick lookup of syntax, parameters, or specifications",
                "COMPARE": "User wants to understand differences or choose between options"
            },
            "scope_types": {
                "SPECIFIC": "Targets a particular feature, component, or use case",
                "GENERAL": "Covers broad topics or multiple related areas", 
                "CONTEXTUAL": "Depends on user's current situation or environment"
            },
            "depth_types": {
                "OVERVIEW": "High-level understanding or introduction",
                "DETAILED": "In-depth technical information or comprehensive guides",
                "PRACTICAL": "Step-by-step instructions or hands-on examples"
            },
            "relevance_thresholds": {
                "high": 0.8,
                "medium": 0.5,
                "low": 0.0
            },
            "scoring_factors": [
                "intent_match: How well the document serves the identified intent",
                "scope_alignment: How well the document's scope matches query scope", 
                "depth_appropriateness: How well the document's depth matches information need",
                "specificity_match: How well the document's specificity matches query specificity"
            ]
        }
