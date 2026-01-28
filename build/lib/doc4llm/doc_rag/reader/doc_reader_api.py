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
from typing import Any, Dict, List, Optional, Union

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
        base_dir: 知识库根目录路径 (必须显式传入)
        config: 统一配置参数，支持 JSON 文件路径、JSON 字符串或字典。
                可同时包含 DocReaderAPI 和 MarkdownDocExtractor 的配置。
                MarkdownDocExtractor 配置可通过顶层字段或嵌套的 "matcher" 键指定。
        search_mode: Search mode for extraction (default: "exact")
        fuzzy_threshold: Fuzzy matching threshold 0.0-1.0 (default: 0.6)
        max_results: Maximum results for fuzzy/partial search (default: None)
        debug_mode: Enable debug output (default: False)
        enable_fallback: Enable fallback strategies (default: False)
        fallback_modes: Fallback mode list (default: None)
        compress_threshold: Compression threshold (default: 2000)
        enable_compression: Enable compression (default: False)

    配置优先级（从高到低）:
        1. 显式传入的参数值
        2. config 顶层字段的值
        3. config 中 "matcher" 嵌套字段的值（MarkdownDocExtractor 专用，不包含 base_dir）
        4. 字段默认值

    base_dir 优先级:
        1. 显式传入的 base_dir
        2. config 顶层字段的 base_dir
        3. 抛出 ValueError（不允许从 matcher 读取 base_dir）

    Example:
        >>> # 方式 1: 使用 config 文件
        >>> reader = DocReaderAPI(base_dir="/docs", config="reader_config.json")
        >>> # reader_config.json 内容:
        >>> # {
        >>> #   "search_mode": "fuzzy",
        >>> #   "base_dir": "/path/to/kb",
        >>> #   "matcher": {
        >>> #     "case_sensitive": true
        >>> #   }
        >>> # }
        >>>
        >>> # 方式 2: 使用字典
        >>> reader = DocReaderAPI(base_dir="/docs", config={
        ...     "search_mode": "fuzzy",
        ...     "base_dir": "/path/to/kb"
        ... })
        >>>
        >>> # 方式 3: JSON 字符串
        >>> reader = DocReaderAPI(base_dir="/docs", config='{"search_mode": "fuzzy"}')
        >>>
        >>> result = reader.extract_multi_by_headings(sections=[
        ...     {"title": "Getting Started", "headings": ["Installation"], "doc_set": "example@latest"}
        ... ])
    """
    base_dir: str
    config: Optional[Union[str, Path, Dict[str, Any]]] = None
    search_mode: Optional[str] = None
    fuzzy_threshold: Optional[float] = None
    max_results: Optional[int] = None
    debug_mode: Optional[bool] = None
    enable_fallback: Optional[bool] = None
    fallback_modes: Optional[List[str]] = None
    compress_threshold: Optional[int] = None
    enable_compression: Optional[bool] = None
    _extractor: MarkdownDocExtractor = field(init=False, default=None)

    def _load_config(self, config: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """加载配置，支持文件路径、JSON字符串、字典。

        Args:
            config: 配置来源，支持以下格式：
                - 文件路径: str 或 Path 对象，指向 JSON 文件
                - JSON 字符串: 如 '{"search_mode": "fuzzy"}'
                - 字典: Python 字典对象

        Returns:
            Dict: 解析后的配置字典

        Raises:
            json.JSONDecodeError: 当 JSON 字符串解析失败时
            FileNotFoundError: 当文件路径不存在时
        """
        if config is None:
            return {}
        if isinstance(config, dict):
            return config
        path = Path(config)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return json.loads(str(config))

    def __post_init__(self):
        """初始化 MarkdownDocExtractor。

        从 reader_config.json 读取配置，初始化 extractor。
        base_dir 优先级：显式参数 > config 顶层 > 报错（不支持从 matcher 读取）

        config JSON 结构示例:
            {
                "search_mode": "fuzzy",
                "base_dir": "/path/to/kb",
                "debug_mode": true,
                "matcher": {
                    "case_sensitive": true,
                    "fuzzy_threshold": 0.8
                }
            }
        """
        # Define default values
        DEFAULTS = {
            "search_mode": "exact",
            "fuzzy_threshold": 0.6,
            "max_results": None,
            "debug_mode": False,
            "enable_fallback": False,
            "fallback_modes": None,
            "compress_threshold": 2000,
            "enable_compression": False,
            "case_sensitive": False,
        }

        # Determine final base_dir (显式参数 > config 顶层 > 报错)
        if self.base_dir:
            base_path = Path(self.base_dir).expanduser().resolve()
            if not base_path.exists():
                raise ValueError(f"base_dir does not exist: '{self.base_dir}'")
            if not base_path.is_dir():
                raise ValueError(f"base_dir is not a directory: '{self.base_dir}'")
            final_base_dir = str(base_path)
        else:
            raise ValueError(f"base_dir must be set!")

        # Load unified config
        config = self._load_config(self.config) if self.config else {}

        # Extract matcher config from nested "matcher" key
        matcher_cfg = {}
        if "matcher" in config and isinstance(config["matcher"], dict):
            matcher_cfg = config.pop("matcher")

        # 合并 config 顶层和 matcher 嵌套的配置（排除 base_dir）
        # 顶层配置优先级高于 matcher 嵌套配置
        for key, value in matcher_cfg.items():
            if key == "base_dir":
                continue  # 跳过 matcher 中的 base_dir
            if key not in config:
                config[key] = value

        # config 中 base_dir 的覆盖逻辑（仅支持顶层）
        if "base_dir" in config:
            config_base = Path(config["base_dir"]).expanduser().resolve()
            if config_base.exists() and config_base.is_dir():
                final_base_dir = str(config_base)

        # Determine final parameter values (priority: explicit > config > default)
        final_search_mode = self.search_mode or config.get("search_mode") or DEFAULTS["search_mode"]
        final_fuzzy_threshold = self.fuzzy_threshold if self.fuzzy_threshold is not None else config.get("fuzzy_threshold") or DEFAULTS["fuzzy_threshold"]
        final_max_results = self.max_results if self.max_results is not None else config.get("max_results") or DEFAULTS["max_results"]
        final_debug_mode = self.debug_mode if self.debug_mode is not None else config.get("debug_mode") or DEFAULTS["debug_mode"]
        final_enable_fallback = self.enable_fallback if self.enable_fallback is not None else config.get("enable_fallback") or DEFAULTS["enable_fallback"]
        final_fallback_modes = self.fallback_modes if self.fallback_modes is not None else config.get("fallback_modes") or DEFAULTS["fallback_modes"]
        final_compress_threshold = self.compress_threshold if self.compress_threshold is not None else config.get("compress_threshold") or DEFAULTS["compress_threshold"]
        final_enable_compression = self.enable_compression if self.enable_compression is not None else config.get("enable_compression") or DEFAULTS["enable_compression"]
        final_case_sensitive = config.get("case_sensitive", DEFAULTS["case_sensitive"])

        # Initialize MarkdownDocExtractor
        self._extractor = MarkdownDocExtractor(
            base_dir=final_base_dir,
            search_mode=final_search_mode,
            case_sensitive=final_case_sensitive,
            max_results=final_max_results,
            fuzzy_threshold=final_fuzzy_threshold,
            debug_mode=final_debug_mode,
            enable_fallback=final_enable_fallback,
            fallback_modes=final_fallback_modes,
            compress_threshold=final_compress_threshold,
            enable_compression=final_enable_compression,
        )

        # Update instance attributes to reflect final configuration
        self.search_mode = final_search_mode
        self.fuzzy_threshold = final_fuzzy_threshold
        self.max_results = final_max_results
        self.debug_mode = final_debug_mode
        self.enable_fallback = final_enable_fallback
        self.fallback_modes = final_fallback_modes
        self.compress_threshold = final_compress_threshold
        self.enable_compression = final_enable_compression

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
            >>> reader = DocReaderAPI(base_dir="/path/to/docs")
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
