#!/usr/bin/env python
"""ContentSearcher - Pythonic 内容搜索器。

- 纯 Python 文件搜索
- Heading 级去重（page_title + heading）
- 全局结果数量限制（无每 doc_set 限制）
- 足够的上下文回溯 heading
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .common_utils import (
    remove_url_from_heading,
    extract_page_title_from_path,
    count_words,
    clean_context_from_urls,
)
from .interfaces import BaseSearcher


class ContentSearcher(BaseSearcher):
    """Pythonic 内容搜索器 - 独立于 grep 的检索实现。

    Features:
    - 纯 Python 实现，无需调用外部 grep 命令
    - Heading 级去重：基于 (doc_set, page_title, heading) 去重
    - 全局结果数量限制：默认最多 20 条（无每 doc_set 限制）
    - 关键词策略：仅使用 domain_nouns（与原 FALLBACK_2 一致）
    - 上下文搜索：从匹配行向上回溯查找 heading
    """

    def __init__(
        self,
        base_dir: str,
        domain_nouns: Optional[List[str]] = None,
        max_results: int = 20,
        context_lines: int = 100,
        debug: bool = False,
    ):
        """初始化 ContentSearcher。

        Args:
            base_dir: 知识库根目录
            domain_nouns: 领域关键词列表（用于精确匹配）
            max_results: 全局最大结果数量（默认 20）
            context_lines: 回溯 heading 的上下文行数（默认 100）
            debug: 是否启用调试输出
        """
        self.base_dir = Path(base_dir)
        self.domain_nouns = domain_nouns or []
        self.max_results = max_results
        self.context_lines = context_lines
        self.debug = debug

    @property
    def name(self) -> str:
        """Get the searcher name.

        Returns:
            Human-readable name identifying this searcher
        """
        return "FALLBACK_2"

    def search(self, queries: List[str], doc_sets: List[str]) -> List[Dict[str, Any]]:
        """主搜索方法。

        Features:
        - 仅使用 domain_nouns 进行精确匹配（与 FALLBACK_2 一致）
        - Heading 级去重，避免同一 heading 重复返回
        - 返回格式与 FALLBACK_2 兼容

        Args:
            queries: 查询列表（仅用于日志，实际搜索使用 domain_nouns）
            doc_sets: 文档集列表

        Returns:
            搜索结果列表，格式与 FALLBACK_2 兼容
        """
        self._debug_print(f"FALLBACK_2.search: queries={queries}, doc_sets={doc_sets}")

        # Step 1: 确定关键词 - 仅使用 domain_nouns
        keywords = self.domain_nouns
        if not keywords:
            self._debug_print("No domain_nouns, skipping ContentSearcher")
            return []

        # Step 2: 构建正则表达式
        pattern = self._build_pattern(keywords)
        if not pattern:
            return []

        # Step 3: 搜索并收集结果
        results = []
        seen: Set[Tuple[str, str, str]] = set()  # (doc_set, page_title, heading) 去重

        for doc_set in doc_sets:
            doc_set_path = self.base_dir / doc_set
            if not doc_set_path.exists():
                continue

            # 遍历所有 docContent.md 文件
            for content_file in doc_set_path.rglob("docContent.md"):
                file_results = self._search_single_file(
                    content_file, doc_set, pattern, seen
                )
                # 逐个添加结果并检查限制
                for result in file_results:
                    results.append(result)
                    if len(results) >= self.max_results:
                        self._debug_print(
                            f"Reached max_results ({self.max_results}), stopping"
                        )
                        break

                # 检查是否达到全局限制
                if len(results) >= self.max_results:
                    break

            if len(results) >= self.max_results:
                break

        self._debug_print(f"ContentSearcher: found {len(results)} results")
        return results

    def _build_pattern(self, keywords: List[str]) -> Optional[re.Pattern]:
        """构建关键词正则表达式。

        Args:
            keywords: 关键词列表

        Returns:
            编译后的正则表达式
        """
        if not keywords:
            return None

        # 转义关键词并构建模式
        escaped = [re.escape(kw) for kw in keywords]
        pattern_str = "|".join(escaped)

        try:
            return re.compile(pattern_str, re.IGNORECASE)
        except re.error as e:
            self._debug_print(f"Pattern error: {e}")
            return None

    def _search_single_file(
        self,
        content_file: Path,
        doc_set: str,
        pattern: re.Pattern,
        seen: Set[Tuple[str, str, str]],
    ) -> List[Dict[str, Any]]:
        """搜索单个文件。

        Args:
            content_file: docContent.md 文件路径
            doc_set: 文档集名称
            pattern: 关键词正则表达式
            seen: 已去重集合

        Returns:
            该文件的搜索结果列表
        """
        results = []

        try:
            lines = content_file.read_text(encoding="utf-8").split("\n")
        except Exception as e:
            self._debug_print(f"Error reading {content_file}: {e}")
            return results

        # 提取页面标题
        page_title = self._extract_page_title(lines)
        if page_title == "Unknown":
            page_title = extract_page_title_from_path(str(content_file))

        # 计算 toc_path（与 docContent.md 同目录的 docTOC.md）
        toc_path = str(content_file.parent / "docTOC.md")

        # 搜索所有匹配行
        for line_num, line in enumerate(lines, start=1):
            if not pattern.search(line):
                continue

            # 回溯查找 heading
            heading = self._find_heading_backward(lines, line_num)
            if not heading:
                continue

            # Heading 级去重
            key = (doc_set, page_title, heading)
            if key in seen:
                continue
            seen.add(key)

            # 提取上下文
            context = self._extract_context(lines, line_num)

            results.append(
                {
                    "doc_set": doc_set,
                    "page_title": page_title,
                    "heading": heading,
                    "toc_path": toc_path,
                    "bm25_sim": 0.0,
                    "is_basic": True,
                    "is_precision": False,
                    "related_context": context,
                    "source_file": str(content_file),
                    "match_line_num": line_num,
                    "source": "FALLBACK_2",
                }
            )

        return results

    def _find_heading_backward(
        self, lines: List[str], start_line: int
    ) -> Optional[str]:
        """从指定行向上回溯查找最近的 heading。

        Args:
            lines: 文件所有行
            start_line: 起始行号（1-based）

        Returns:
            找到的 heading 文本，未找到返回 None
        """
        # 向前回溯，最多 context_lines 行
        end_idx = max(0, start_line - self.context_lines - 1)

        for i in range(start_line - 1, end_idx, -1):
            line = lines[i].strip()
            if not line:
                continue

            # 检测 heading（# 开头）
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                heading_text = match.group(2)
                # 清理 URL 链接
                heading_text = self._remove_url_from_heading(heading_text)
                if heading_text:
                    return f"{match.group(1)} {heading_text}"

        return None

    def _extract_context(
        self, lines: List[str], match_line: int, context_size: int = 2
    ) -> str:
        """提取匹配行周围的上下文（限制在 heading 边界内）。

        特点：
        - 上下文限制在上下 heading 边界内
        - 返回内容不包含 heading 行
        - 以匹配行为中心，动态扩展，返回不超过 80 单词的文本

        Args:
            lines: 文件所有行
            match_line: 匹配行号（1-based）
            context_size: 初始上下文行数（前后各多少行）

        Returns:
            上下文文本（不超过 80 单词，不包含 heading）
        """
        # 空列表检查
        if not lines:
            return ""

        # 边界检查：match_line 超出范围
        if match_line < 1 or match_line > len(lines):
            return ""

        # 获取 heading 边界
        upper_bound, lower_bound = self._find_heading_boundaries(lines, match_line)
        match_idx = match_line - 1
        max_words = 80
        max_context_size = 50
        expand_step = 5

        # 确保 context_size 不超过最大值
        current_size = min(context_size, max_context_size)
        context_lines: List[str] = []  # 预初始化，避免 Pyright 警告

        # 使用 for-else 语法：当循环正常结束（达到最大 context_size）时执行截断
        for _ in range((max_context_size - context_size) // expand_step + 1):
            # 计算行索引范围（0-based），限制在 heading 边界内
            start_idx = max(upper_bound, match_idx - current_size)
            end_idx = min(lower_bound, match_idx + current_size + 1)

            # 提取并过滤 heading 行
            for i in range(start_idx, end_idx):
                line = lines[i].strip()
                # 跳过 heading 行
                if self._is_heading_line(line):
                    continue
                # 移除 leading "---"（表格分隔线、YAML 分隔符等），保留后续正文
                line = re.sub(r"^---+\s*", "", line)
                if line:  # 清理后非空则保留
                    context_lines.append(line)

            # 清理 URL 并统计单词
            context_text = "\n".join(context_lines)
            context_text = self._clean_context_from_urls(context_text)
            word_count = self._count_words(context_text)

            if word_count <= max_words:
                return context_text

            # 超过单词限制，扩展上下文再尝试
            if current_size < max_context_size:
                current_size += expand_step
            else:
                # 已达到最大 context_size，进行截断
                return self._truncate_symmetric(context_lines, 0, max_words)

        # 兜底：达到最大 context_size，进行截断
        return self._truncate_symmetric(context_lines, 0, max_words)

    def _extract_page_title(self, lines: List[str]) -> str:
        """从文件内容提取页面标题（第一行的 # heading）。

        Args:
            lines: 文件所有行

        Returns:
            页面标题
        """
        if not lines:
            return "Unknown"

        first_line = lines[0].strip()
        if first_line.startswith("#"):
            title = first_line.lstrip("#").strip()
            if title:
                return title

        return "Unknown"

    def _extract_page_title_from_path(self, file_path: str) -> str:
        """从文件路径提取页面标题。"""
        return extract_page_title_from_path(file_path)

    def _remove_url_from_heading(self, heading_text: str) -> str:
        """从 heading 文本中移除 URL 链接。"""
        return remove_url_from_heading(heading_text)

    def _clean_context_from_urls(self, context: str) -> str:
        """从上下文中清理 URL 信息。"""
        return clean_context_from_urls(context)

    def _count_words(self, text: str) -> int:
        """统计文本中的词/字符数量（中英文混合支持）。"""
        return count_words(text)

    def _find_heading_boundaries(
        self, lines: List[str], match_line: int
    ) -> Tuple[int, int]:
        """查找匹配行上下文的扩展边界（受 heading 限制）。

        向上：找到匹配行所属 heading，返回其下一行作为上边界
        向下：找到下一个 heading，返回其上一行作为下边界

        简言之，上下文只能在匹配行所在 heading 的内容范围内扩展。

        Args:
            lines: 文件所有行
            match_line: 匹配行号（1-based）

        Returns:
            (start_idx, end_idx) 0-based 索引范围
            - start_idx: 上边界（可扩展的最早行）
            - end_idx: 下边界（可扩展的最晚行）+ 1
        """
        match_idx = match_line - 1  # 0-based
        n = len(lines)

        # 向上查找最近的 heading
        upper_bound = 0
        for i in range(match_idx - 1, -1, -1):
            line = lines[i].strip()
            if self._is_heading_line(line):
                upper_bound = i + 1  # heading 的下一行开始
                break

        # 向下查找最近的 heading
        lower_bound = n
        for i in range(match_idx + 1, n):
            line = lines[i].strip()
            if self._is_heading_line(line):
                lower_bound = i  # heading 的上一行结束
                break

        return (upper_bound, lower_bound)

    def _is_heading_line(self, line: str) -> bool:
        """检查行是否为 markdown heading。

        Args:
            line: 行文本

        Returns:
            是否为 heading 行
        """
        stripped = line.strip()
        return bool(stripped.startswith("#")) and bool(
            re.match(r"^#{1,6}\s+", stripped)
        )

    def _truncate_symmetric(
        self, lines: List[str], match_idx: int, max_words: int
    ) -> str:
        """截断文本到目标词数，使用上下交替剔除策略。

        Args:
            lines: 原始行列表（已排除 heading 行）
            match_idx: 匹配行索引（0-based，相对于输入的 lines）
            max_words: 最大词数

        Returns:
            截断后的文本
        """
        if not lines:
            return ""

        current_text = "\n".join(lines)
        word_count = self._count_words(current_text)

        if word_count <= max_words:
            return current_text

        # 交替剔除上下文
        left_idx = 0
        right_idx = len(lines) - 1

        while word_count > max_words and left_idx < right_idx:
            # 交替从两边剔除一行
            if (left_idx + right_idx) % 2 == 0:
                left_idx += 1  # 剔除左边
            else:
                right_idx -= 1  # 剔除右边

            current_lines = lines[left_idx : right_idx + 1]
            current_text = "\n".join(current_lines)
            word_count = self._count_words(current_text)

        # 边界情况：如果最后 word_count 仍超过 max_words（只剩一行），截断该行
        if word_count > max_words and current_text:
            words = current_text.split()
            if len(words) > max_words:
                current_text = " ".join(words[:max_words])

        return current_text

    def _debug_print(self, message: str) -> None:
        """调试输出。

        Args:
            message: 调试消息
        """
        if self.debug:
            print(f"[ContentSearcher] {message}")
