"""
Text Preprocessor Module - Language detection, keyword filtering, and text cleaning.

This module provides:
    TextPreprocessor: Text preprocessing for rerank calculations
    LanguageDetector: Doc-set level language detection
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class TextPreprocessor:
    """文本预处理器 - 语言检测、关键词过滤、文本清洗"""

    def __init__(
        self,
        domain_nouns: Optional[List[str]] = None,
        predicate_verbs: Optional[List[str]] = None,
        skiped_keywords: Optional[List[str]] = None,
        reranker_lang_threshold: float = 0.9,
    ):
        """
        Initialize TextPreprocessor.

        Args:
            domain_nouns: List of domain-specific nouns for text preprocessing
            predicate_verbs: List of predicate verbs for text preprocessing
            skiped_keywords: List of keywords to skip during search
            reranker_lang_threshold: Language detection threshold for Chinese char ratio
        """
        self.domain_nouns = domain_nouns or []
        self.predicate_verbs = predicate_verbs or []
        self.skiped_keywords = skiped_keywords or []
        self.reranker_lang_threshold = reranker_lang_threshold

    def detect_language(self, text: str) -> str:
        """
        Detect text language based on Chinese character ratio.

        Args:
            text: Input text to analyze

        Returns:
            "zh" if Chinese character ratio >= threshold, "en" otherwise
        """
        # Count Chinese characters (Unicode range for CJK Unified Ideographs)
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(text.strip())

        if total_chars == 0:
            return "en"

        ratio = chinese_chars / total_chars
        return "zh" if ratio >= self.reranker_lang_threshold else "en"

    def contains_domain_noun(self, text: str) -> bool:
        """
        检查 text 是否包含 domain_nouns 中至少一个名词（支持中英文和词干匹配）。

        规则：
        - 英文：使用词干匹配（"hook" 匹配 "hooks"）
        - 中文：直接子串匹配

        Args:
            text: 待检查的文本

        Returns:
            True 如果包含至少一个 domain_nouns，否则 False
        """
        if not text or not self.domain_nouns:
            return False

        text_lower = text.lower()

        for noun in self.domain_nouns:
            noun_lower = noun.lower()

            # 检测是否为中文（包含中文字符）
            if re.search(r"[\u4e00-\u9fff]", noun_lower):
                # 中文：直接子串匹配
                if noun_lower in text_lower:
                    return True
            else:
                # 英文：词干匹配
                stem = self._get_english_stem(noun_lower)
                if stem in text_lower or noun_lower in text_lower:
                    return True

        return False

    def _get_english_stem(self, word: str) -> str:
        """获取英文单词的词干（简单实现，处理常见复数形式）。"""
        # 常见的英文复数后缀
        suffixes = ["s", "es", "ied", "ies", "ves"]
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                # 处理特殊情况：ies -> y, ves -> f
                if (
                    suffix == "ies"
                    and not word.endswith("aies")
                    and not word.endswith("eies")
                ):
                    return word[:-3] + "y"
                elif suffix == "ves":
                    return word[:-3] + "f"
                elif (
                    suffix == "ied"
                    and not word.endswith("aied")
                    and not word.endswith("eied")
                ):
                    return word[:-3] + "y"
                else:
                    return word[: -len(suffix)]
        return word

    def preprocess_for_rerank(self, text: str) -> str:
        """
        预处理文本用于 rerank 计算。

        规则：
        1. 检查 text 是否包含 domain_nouns 中至少一个名词
        2. 如果不包含任何 domain_nouns，则剔除 text 中的 predicate_verbs
        3. 返回处理后的文本

        Args:
            text: 原始 heading 或 page_title 文本

        Returns:
            处理后的文本（如果包含 domain_nouns 则返回原文本，否则剔除 predicate_verbs）
        """
        if not text:
            return text

        # 如果 domain_nouns 为空或 None，直接返回原文本
        if not self.domain_nouns:
            return text

        # 检查是否包含至少一个 domain_nouns
        if self.contains_domain_noun(text):
            return text

        # 如果不包含任何 domain_nouns，剔除 predicate_verbs
        if not self.predicate_verbs:
            return text

        # 获取受保护的关键词（skiped_keywords 与 domain_nouns 的交集）
        protected_keywords = self.get_protected_keywords()

        # 使用正则替换，移除所有 predicate_verbs（不区分大小写）
        # 但跳过受保护的关键词
        processed_text = text
        for verb in self.predicate_verbs:
            # 跳过受保护的关键词
            if protected_keywords and verb.lower() in {
                kw.lower() for kw in protected_keywords
            }:
                continue
            # 检测是否为中文（包含中文字符）
            if re.search(r"[\u4e00-\u9fff]", verb):
                # 中文：直接子串匹配（不使用 word boundary）
                pattern = re.compile(re.escape(verb), re.IGNORECASE)
                processed_text = pattern.sub("", processed_text)
            else:
                # 英文：使用 word boundary 确保完整匹配
                pattern = re.compile(r"\b" + re.escape(verb) + r"\b", re.IGNORECASE)
                processed_text = pattern.sub("", processed_text)

        # 清理多余空格并 strip
        processed_text = re.sub(r"\s+", " ", processed_text).strip()

        return processed_text

    def preprocess_headings_for_rerank(
        self, headings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        预处理 headings 列表用于 rerank 计算。

        Args:
            headings: heading 字典列表

        Returns:
            处理后的 heading 字典列表
        """
        if not self.domain_nouns:
            return headings

        processed_headings = []
        for h in headings:
            text = h.get("text", "")
            processed_text = self.preprocess_for_rerank(text)
            processed_headings.append({**h, "text": processed_text})

        return processed_headings

    def get_protected_keywords(self) -> set:
        """
        获取受保护的关键词集合（skiped_keywords 与 domain_nouns 的交集）。

        这些关键词在预处理时不会被剔除。

        Returns:
            受保护的关键词集合
        """
        if not self.domain_nouns or not self.skiped_keywords:
            return set()
        return set(self.domain_nouns) & set(self.skiped_keywords)

    def filter_query_keywords(self, query: str) -> str:
        """Filter out skiped keywords from query string (case-insensitive).

        Args:
            query: Original query string

        Returns:
            Filtered query string
        """
        query_lower = query.strip()
        result = query_lower

        for keyword in self.skiped_keywords:
            keyword_lower = keyword.strip().lower()
            if not keyword_lower:
                continue
            pattern = keyword_lower
            result = re.sub(re.escape(pattern), "", result, flags=re.IGNORECASE)

        result = re.sub(r"\s+", " ", result).strip()
        return result


class LanguageDetector:
    """语言检测器 - doc-set 级别的语言检测"""

    def __init__(self, base_dir: str, lang_threshold: float = 0.9, debug: bool = False):
        """
        Initialize LanguageDetector.

        Args:
            base_dir: Knowledge base root directory
            lang_threshold: Language detection threshold for Chinese char ratio
            debug: Enable debug mode
        """
        self.base_dir = base_dir
        self.lang_threshold = lang_threshold
        self.debug = debug

    def detect_docset_language(self, doc_set: str, sample_size: int = 5) -> str:
        """
        Detect the primary language of a doc-set by sampling docTOC.md files.

        Args:
            doc_set: Name of the doc-set to analyze
            sample_size: Maximum number of TOC files to sample

        Returns:
            "zh" if Chinese is dominant, "en" otherwise
        """
        docset_path = Path(self.base_dir) / doc_set
        if not docset_path.exists():
            self._debug_print(f"Doc-set path not found: {docset_path}")
            return "en"  # Default to English

        # Find all docTOC.md files
        toc_files = list(docset_path.rglob("docTOC.md"))
        if not toc_files:
            self._debug_print(f"No docTOC.md files found in {doc_set}")
            return "en"  # Default to English

        # Sample files
        sample_files = toc_files[:sample_size]
        self._debug_print(
            f"Sampling {len(sample_files)} TOC files for language detection"
        )

        # Collect all text from sampled files
        all_text = []
        for toc_file in sample_files:
            try:
                with open(toc_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Extract headings (lines starting with #)
                    headings = [
                        line
                        for line in content.split("\n")
                        if line.strip().startswith("#")
                    ]
                    all_text.extend(headings)
            except Exception as e:
                self._debug_print(f"Error reading {toc_file}: {e}")

        if not all_text:
            return "en"

        # Combine all headings for language detection
        combined_text = " ".join(all_text)
        detector = TextPreprocessor(reranker_lang_threshold=self.lang_threshold)
        detected_lang = detector.detect_language(combined_text)
        self._debug_print(f"Detected doc-set language: {detected_lang}")

        return detected_lang

    def _debug_print(self, message: str):
        """Print debug message."""
        if self.debug:
            print(f"[DEBUG] {message}")
