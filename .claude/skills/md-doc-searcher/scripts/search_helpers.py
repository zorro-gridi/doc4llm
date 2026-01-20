"""
Search helper functions for md-doc-searcher skill.

Core semantic retrieval functions that cannot be replaced by prompt-based operations.
"""

import re
from typing import List, Optional, Tuple, Dict, Any


class SearchHelpers:
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
        'to', 'for', 'with', 'by', 'from', 'at', 'on', 'in', 'about',
        'how', 'what', 'where', 'when', 'why', 'which', 'that', 'this',
        'these', 'those', 'use', 'using', 'can', 'will', 'would'
    }

    TECHNICAL_TERMS = {
        'api', 'cli', 'sdk', 'http', 'https', 'jwt', 'oauth', 'ssh',
        'webhook', 'middleware', 'endpoint', 'token', 'auth', 'config',
        'deploy', 'hooks', 'async', 'sync', 'json', 'xml', 'yaml', 'yml'
    }

    @staticmethod
    def extract_keywords(query: str) -> List[str]:
        words = re.findall(r'[\w\u4e00-\u9fff]+', query.lower())
        keywords = []
        for word in words:
            if re.search(r'[\u4e00-\u9fff]', word):
                keywords.append(word)
            elif word in SearchHelpers.TECHNICAL_TERMS:
                keywords.append(word)
            elif word not in SearchHelpers.STOP_WORDS:
                keywords.append(word)
        seen = set()
        result = []
        for word in keywords:
            if word not in seen:
                seen.add(word)
                result.append(word)
        return result

    @staticmethod
    def analyze_query_intent(original_query: str) -> dict:
        keywords = SearchHelpers.extract_keywords(original_query)
        return {
            "primary_intent": "UNKNOWN",
            "scope": "UNKNOWN",
            "depth": "UNKNOWN",
            "specificity_keywords": keywords,
            "framework_note": "LLM should perform semantic analysis to populate intent fields"
        }

    @staticmethod
    def calculate_relevance_score(
        doc_title: str,
        doc_context: Optional[str],
        query_intent: dict
    ) -> dict:
        return {
            "score": 0.0,
            "intent_match": 0.0,
            "scope_alignment": 0.0,
            "depth_appropriateness": 0.0,
            "specificity_match": 0.0,
            "rationale": "LLM should provide semantic evaluation and rationale",
            "doc_title": doc_title,
            "doc_context": doc_context or "",
            "query_intent": query_intent
        }

    @staticmethod
    def extract_headings_with_levels(toc_content: str) -> List[dict]:
        if not toc_content:
            return []
        lines = toc_content.split('\n')
        headings = []
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        link_pattern = re.compile(r'\[([^\]]+)\]\([^\)]+\)')
        anchor_pattern = re.compile(r'：https://[^\s]+|: https://[^\s]+')
        for line in lines:
            match = heading_pattern.match(line.strip())
            if match:
                level = len(match.group(1))
                full_text = match.group(2).strip()
                anchor = None
                anchor_match = anchor_pattern.search(full_text)
                if anchor_match:
                    anchor = anchor_match.group(0).replace('：', '').replace(': ', '').strip()
                text = anchor_pattern.sub('', full_text).strip()
                link_match = link_pattern.search(text)
                if link_match:
                    text = link_match.group(1)
                headings.append({
                    "level": level,
                    "text": text,
                    "full_text": f"{'#' * level} {text}",
                    "anchor": anchor
                })
        return headings

    @staticmethod
    def calculate_heading_relevance_score(
        heading_text: str,
        query: str,
        query_intent: Optional[dict] = None
    ) -> dict:
        return {
            "score": 0.0,
            "intent_match": 0.0,
            "scope_alignment": 0.0,
            "depth_appropriateness": 0.0,
            "rationale": "LLM should provide semantic evaluation and rationale",
            "heading_text": heading_text,
            "query": query,
            "query_intent": query_intent or {}
        }

    @staticmethod
    def calculate_page_title_relevance_score(query: str, toc_content: str = None) -> dict:
        return {
            "score": 0.0,
            "is_basic": False,
            "is_precision": False,
            "rationale": "LLM should provide semantic evaluation"
        }

    @staticmethod
    def check_heading_requirement(results: list, min_count: int = 2) -> Tuple[bool, int]:
        count = len(results)
        return count >= min_count, count

    @staticmethod
    def check_precision_requirement(results: list, precision_threshold: float = 0.7) -> Tuple[bool, int]:
        precision_count = sum(1 for r in results if r.get('score', 0) >= precision_threshold)
        return precision_count >= 1, precision_count

    @staticmethod
    def annotate_headings_with_page_title(grep_results: list[dict], doc_set: str) -> list[dict]:
        annotated = []
        for result in grep_results:
            file_path = result.get('file', '')
            match = result.get('match', '')
            match_page_title = None
            if f"/{doc_set}/" in file_path:
                parts = file_path.split(f"/{doc_set}/")
                if len(parts) > 1:
                    path_parts = parts[1].split('/')
                    if len(path_parts) >= 2:
                        match_page_title = path_parts[0]
            annotated.append({
                "heading_text": match,
                "page_title": match_page_title or "Unknown",
                "toc_path": file_path,
                "score": 0.0,
                "is_basic": False
            })
        return annotated

    @staticmethod
    def validate_cross_docset_coverage(target_doc_sets: list[str], matched_doc_sets: list[str]) -> dict:
        target_set = set(target_doc_sets)
        matched_set = set(matched_doc_sets)
        missing = target_set - matched_set
        extra = matched_set - target_set
        matched = matched_set & target_set
        coverage_percentage = (len(matched) / len(target_set) * 100) if target_set else 100.0
        return {
            "complete": len(missing) == 0,
            "matched": list(matched),
            "missing": list(missing),
            "extra": list(extra),
            "coverage_percentage": coverage_percentage
        }

    @staticmethod
    def get_docset_match_status(
        doc_set_name: str,
        page_title_count: int,
        heading_count: int,
        precision_count: int,
        min_page_title: int = 2,
        min_heading: int = 2
    ) -> dict:
        page_title_valid = page_title_count >= min_page_title
        heading_valid = heading_count >= min_heading
        has_precision_match = precision_count >= 1
        return {
            "doc_set": doc_set_name,
            "page_title_valid": page_title_valid,
            "heading_valid": heading_valid,
            "has_precision_match": has_precision_match,
            "overall_valid": page_title_valid and heading_valid and has_precision_match
        }

    @staticmethod
    def traceback_to_heading(
        content_path: str,
        match_line: int,
        context_lines: int = 10
    ) -> dict:
        page_title = "Unknown"
        if f"/docContent.md" in content_path:
            path_parts = content_path.split("/docContent.md")[0].split("/")
            if len(path_parts) >= 2:
                page_title = path_parts[-1]
        return {
            "heading_text": "",
            "heading_level": 1,
            "page_title": page_title,
            "heading_line": 0,
            "context_excerpt": ""
        }
