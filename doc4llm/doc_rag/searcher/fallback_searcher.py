#!/usr/bin/env python
"""FallbackSearcher - Pythonic 降级搜索器。

独立于 grep 的检索实现，提供：
- 纯 Python 文件搜索
- Heading 级去重（page_title + heading）
- 全局结果数量限制（无每 doc_set 限制）
- 足够的上下文回溯 heading

与 DocSearcherAPI 的 FALLBACK_2 策略对比：
- grep 版本：基于 source_file 去重，每 doc_set 最多 10 条
- Pythonic 版本：基于 (doc_set, page_title, heading) 去重，全局最多 20 条
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class FallbackSearcher:
    """Pythonic 降级搜索器 - 独立于 grep 的检索实现。

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
        """初始化 FallbackSearcher。

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

    def search(
        self, queries: List[str], doc_sets: List[str]
    ) -> List[Dict[str, Any]]:
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
            self._debug_print("No domain_nouns, skipping FallbackSearcher")
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
                        self._debug_print(f"Reached max_results ({self.max_results}), stopping")
                        break

                # 检查是否达到全局限制
                if len(results) >= self.max_results:
                    break

            if len(results) >= self.max_results:
                break

        self._debug_print(f"FallbackSearcher: found {len(results)} results")
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
            page_title = self._extract_page_title_from_path(str(content_file))

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
                    "toc_path": "",
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
        self, lines: List[str], match_line: int, context_size: int = 5
    ) -> str:
        """提取匹配行周围的上下文。

        Args:
            lines: 文件所有行
            match_line: 匹配行号（1-based）
            context_size: 上下文行数（前后各多少行）

        Returns:
            上下文文本
        """
        context_lines = []

        # 提取上下文行
        start_idx = max(0, match_line - context_size - 1)
        end_idx = min(len(lines), match_line + context_size)

        for i in range(start_idx, end_idx):
            line = lines[i].strip()
            if line and not line.startswith("--"):
                context_lines.append(line)

        # 清理 URL 信息
        context_text = "\n".join(context_lines)
        return self._clean_context_from_urls(context_text)

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
        """从文件路径提取页面标题。

        Args:
            file_path: 文件路径

        Returns:
            页面标题
        """
        path = Path(file_path)

        # 从路径中提取，如 "docSetName/pageTitle/docContent.md"
        parts = path.parts
        if len(parts) >= 2:
            potential_title = (
                parts[-2] if parts[-1] in ("docTOC.md", "docContent.md") else parts[-1]
            )
            if potential_title and not potential_title.endswith(".md"):
                return potential_title

        # 尝试读取文件内容
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("#"):
                        title = first_line.lstrip("#").strip()
                        if title:
                            return title
        except Exception:
            pass

        return "Unknown"

    def _remove_url_from_heading(self, heading_text: str) -> str:
        """从 heading 文本中移除 URL 链接。

        Args:
            heading_text: 原始 heading 文本

        Returns:
            清理后的 heading 文本
        """
        # 移除 markdown 链接格式 [text](url) -> text
        link_pattern = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
        # 移除行尾锚点链接
        anchor_pattern = re.compile(r"：https://[^\s]+|: https://[^\s]+")

        text = link_pattern.sub(r"\1", heading_text)
        text = anchor_pattern.sub("", text).strip()

        return text

    def _clean_context_from_urls(self, context: str) -> str:
        """从上下文中清理 URL 信息。

        Args:
            context: 原始上下文

        Returns:
            清理后的上下文
        """
        # 移除行尾锚点链接
        anchor_pattern = re.compile(r"：https://[^\s]+|: https://[^\s]+")
        cleaned = anchor_pattern.sub("", context)
        return cleaned.strip()

    def _debug_print(self, message: str) -> None:
        """调试输出。

        Args:
            message: 调试消息
        """
        if self.debug:
            print(f"[FallbackSearcher] {message}")
