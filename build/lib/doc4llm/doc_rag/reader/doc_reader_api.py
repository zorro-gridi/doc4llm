#!/usr/bin/env python3
"""
Markdown Document Reader API - 封装 MarkdownDocExtractor 的初始化和调用。

遵循 doc_reader_cli.py 的参数规范，提供多文档/多章节提取功能。

Example:
    >>> from doc4llm.doc_rag.reader.doc_reader_api import DocReaderAPI
    >>> reader = DocReaderAPI()
    >>> result = reader.extract_multi_by_headings(sections=[...])
    >>> print(result.contents)
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from doc4llm.tool.md_doc_retrieval.doc_extractor import (
    ExtractionResult,
    MarkdownDocExtractor,
)


@dataclass
class DocReaderAPI:
    """Markdown Document Reader API.

    封装 MarkdownDocExtractor 的初始化和多文档提取功能，
    遵循 doc_reader_cli.py 的参数规范。

    Attributes:
        knowledge_base_path: Path to knowledge_base.json (default: knowledge_base.json)
        base_dir: Override base_dir from config (parameter > config)
        search_mode: Search mode for extraction (default: "exact")
        fuzzy_threshold: Fuzzy matching threshold 0.0-1.0 (default: 0.6)
        max_results: Maximum results for fuzzy/partial search (default: None)
        debug_mode: Enable debug output (default: False)
        enable_fallback: Enable fallback strategies (default: False)
        fallback_modes: Fallback mode list (default: None)
        compress_threshold: Compression threshold (default: 2000)
        enable_compression: Enable compression (default: False)

    Example:
        >>> reader = DocReaderAPI()
        >>> result = reader.extract_multi_by_headings(sections=[
        ...     {"title": "Getting Started", "headings": ["Installation"], "doc_set": "example@latest"}
        ... ])
    """
    knowledge_base_path: str = "knowledge_base.json"
    base_dir: Optional[str] = None
    search_mode: str = "exact"
    fuzzy_threshold: float = 0.6
    max_results: Optional[int] = None
    debug_mode: bool = False
    enable_fallback: bool = False
    fallback_modes: Optional[List[str]] = None
    compress_threshold: int = 2000
    enable_compression: bool = False
    _extractor: MarkdownDocExtractor = field(init=False, default=None)

    def __post_init__(self):
        """初始化 MarkdownDocExtractor，遵循 doc_reader_cli.py 规范。

        从 knowledge_base.json 读取配置，初始化 extractor。
        base_dir 优先级：参数 > 配置 > 默认值
        """
        # Determine knowledge_base.json path
        kb_config_path = None

        # Use user-provided knowledge_base_path if specified
        if self.knowledge_base_path:
            kb_path = Path(self.knowledge_base_path).expanduser().resolve()
            if kb_path.exists():
                if kb_path.is_file() and kb_path.name == "knowledge_base.json":
                    kb_config_path = kb_path
                elif kb_path.is_dir():
                    # Treat as directory, look for knowledge_base.json inside
                    kb_config_path = kb_path / "knowledge_base.json"
                    if not kb_config_path.exists():
                        kb_config_path = None

        # Fallback: search parent directories from current script
        if not kb_config_path:
            current = Path(__file__).resolve()
            for _ in range(6):  # Search up to 6 levels up
                if (current / "knowledge_base.json").exists():
                    kb_config_path = current / "knowledge_base.json"
                    break
                current = current.parent

        if not kb_config_path:
            raise ValueError(
                f"knowledge_base.json not found. Please provide knowledge_base_path parameter "
                f"or ensure knowledge_base.json exists in parent directories of {__file__}"
            )

        try:
            with open(kb_config_path, "r", encoding="utf-8") as f:
                kb_config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in knowledge_base.json: {e}")

        kb_base_dir = kb_config.get("knowledge_base", {}).get("base_dir")
        if not kb_base_dir:
            raise ValueError(
                "base_dir not found in knowledge_base.json['knowledge_base']"
            )

        # Expand ~ to user's home directory
        kb_base_dir = str(Path(kb_base_dir).expanduser().resolve())

        # Determine final base_dir (parameter > config)
        if self.base_dir:
            base_path = Path(self.base_dir).expanduser().resolve()
            if not base_path.exists():
                raise ValueError(f"base_dir does not exist: '{self.base_dir}'")
            if not base_path.is_dir():
                raise ValueError(f"base_dir is not a directory: '{self.base_dir}'")
            final_base_dir = str(base_path)
        else:
            final_base_dir = kb_base_dir

        # Initialize MarkdownDocExtractor (fully following doc_reader_cli.py)
        self._extractor = MarkdownDocExtractor(
            base_dir=final_base_dir,
            search_mode=self.search_mode or kb_config.get("default_search_mode", "exact"),
            fuzzy_threshold=self.fuzzy_threshold or kb_config.get("fuzzy_threshold", 0.6),
            max_results=self.max_results or kb_config.get("max_results", 10),
            debug_mode=self.debug_mode,
            enable_fallback=self.enable_fallback or kb_config.get("enable_fallback", False),
            fallback_modes=self.fallback_modes or kb_config.get("fallback_modes", None),
            compress_threshold=self.compress_threshold or kb_config.get("compress_threshold", 2000),
            enable_compression=self.enable_compression or kb_config.get("enable_compression", False),
        )

    def extract_multi_by_headings(
        self,
        sections: List[Dict[str, Any]],
        threshold: int = 2100,
    ) -> ExtractionResult:
        """多文档多章节提取。

        从多个文档中提取指定章节的内容，支持按标题列表精确提取文档片段。

        Args:
            sections: 章节配置列表，每个元素包含：
                - title (str): 页面标题，用于定位文档
                - headings (List[str]): 要提取的标题列表。
                  空列表表示提取整个文档内容。
                - doc_set (str): 文档集标识符 (例如 "example@latest")
            threshold: 行数阈值，超过此值时 requires_processing 为 True (默认: 2100)

        Returns:
            ExtractionResult: 提取结果，包含：
                - contents: dict，键为 "title::heading" 复合键
                  (headings 为空时仅使用 "title")
                - total_line_count: 总行数
                - individual_counts: 每个 section 的行数
                - requires_processing: 是否超过阈值
                - threshold: 使用的阈值
                - document_count: 成功提取的 section 数量

        提取规则:
            - headings 列表为空时：提取整个文档内容
            - headings 列表不为空时：提取每个 heading 对应的章节内容
            - 章节结束条件：遇到同级或更高级别 (current_level <= heading_level) 标题时停止
            - 如果找不到相同层级的下一个标题行：提取到文档末尾

        Raises:
            ValueError: sections 参数格式无效

        Example:
            >>> reader = DocReaderAPI()
            >>> result = reader.extract_multi_by_headings(sections=[
            ...     {
            ...         "title": "Agent Skills",
            ...         "headings": ["Create Skills", "Configure Hooks"],
            ...         "doc_set": "OpenCode_Docs@latest"
            ...     },
            ...     {
            ...         "title": "Agents",
            ...         "headings": [],  # 提取整个文档
            ...         "doc_set": "OpenCode_Docs@latest"
            ...     }
            ... ])
            >>> # 按复合键访问内容
            >>> content = result.contents["Agent Skills::Create Skills"]
            >>> # 检查是否需要后处理
            >>> if result.requires_processing:
            ...     print(f"内容超出阈值 {result.threshold} 行")
            >>> print(result.to_summary())
        """
        # 输入验证
        if not isinstance(sections, list):
            raise ValueError(f"sections must be a list, got {type(sections).__name__}")

        for i, section in enumerate(sections):
            if not isinstance(section, dict):
                raise ValueError(
                    f"sections[{i}] must be a dict, got {type(section).__name__}"
                )
            if "title" not in section:
                raise ValueError(f"sections[{i}] must contain 'title' key")
            if "headings" not in section:
                raise ValueError(f"sections[{i}] must contain 'headings' key")
            if "doc_set" not in section:
                raise ValueError(f"sections[{i}] must contain 'doc_set' key")
            if not isinstance(section["headings"], list):
                raise ValueError(
                    f"sections[{i}]['headings'] must be a list, got "
                    f"{type(section['headings']).__name__}"
                )

        return self._extractor.extract_multi_by_headings(
            sections=sections,
            threshold=threshold,
        )

    def extract_by_titles(
        self,
        titles: List[str],
        threshold: int = 2100,
        doc_set: Optional[str] = None,
    ) -> Dict[str, str]:
        """按标题提取多个文档内容。

        Args:
            titles: 文档标题列表
            threshold: 行数阈值
            doc_set: 文档集标识符

        Returns:
            dict: 标题到内容的映射
        """
        return self._extractor.extract_by_titles(
            titles=titles,
            threshold=threshold,
            doc_set=doc_set,
        )

    def extract_by_title(
        self,
        title: str,
        doc_set: Optional[str] = None,
    ) -> Optional[str]:
        """按标题提取单个文档内容。

        Args:
            title: 文档标题
            doc_set: 文档集标识符

        Returns:
            str 或 None: 文档内容，未找到时返回 None
        """
        return self._extractor.extract_by_title(title, doc_set=doc_set)

    def list_available_documents(self) -> List[str]:
        """列出可用的文档。

        Returns:
            list: 可用文档标题列表
        """
        return self._extractor.list_available_documents()

    def search_documents(
        self,
        query: str,
        search_mode: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """搜索文档。

        Args:
            query: 搜索查询
            search_mode: 搜索模式 (覆盖实例配置)

        Returns:
            list: 搜索结果列表
        """
        return self._extractor.search_documents(
            query,
            search_mode=search_mode or self.search_mode,
        )


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "DocReaderAPI",
]
