"""
Query Optimizer - LLM-Based Query Optimization and Expansion

将用户查询优化为多个检索友好的查询变体，支持查询分解、同义词扩展、多语言处理。

Features:
    - 五阶段优化协议: 文档集检测、策略选择、查询优化、意图识别、实体提取
    - 智能查询扩展: 分解、翻译、同义词扩展
    - 动态查询数量: 根据实体数量自动调整输出数量
    - 谓词动词提取: 从优化后的查询中提取动作变体
    - 同步/异步接口

Example:
    >>> optimizer = QueryOptimizer()
    >>> result = optimizer.optimize("如何创建 ray cluster?")
    >>> print(result.optimized_queries)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from doc4llm.doc_rag.params_parser.output_parser import extract_json_from_codeblock
from doc4llm.llm.anthropic import invoke


@dataclass
class QueryOptimizerConfig:
    """
    QueryOptimizer 配置类

    Attributes:
        model: LLM 模型名称 (default: "MiniMax-M2.1")
        max_tokens: 最大输出 token 数 (default: 20000)
        temperature: 生成温度 0.0-1.0 (default: 0.1)
        prompt_template_path: prompt 模板文件路径
        doc_sets_base_path: 文档集基础路径
        max_retries: 最大重试次数（不包含首次调用）(default: 2)
        retry_on_empty_fields: 是否启用重试机制 (default: True)
    """
    model: str = "MiniMax-M2.1"
    max_tokens: int = 20000
    temperature: float = 0.1
    prompt_template_path: str = "doc4llm/doc_rag/query_optimizer/prompt_template/query_optimizer_prompt.md"
    doc_sets_base_path: str = "doc4llm/md_docs_base"
    max_retries: int = 2
    retry_on_empty_fields: bool = True


@dataclass
class OptimizationResult:
    """
    查询优化结果

    Attributes:
        query_analysis: 查询分析结果
        optimized_queries: 优化后的查询列表
        search_recommendation: 搜索建议
        thinking: LLM 推理过程 (如有)
        raw_response: 原始响应文本
    """
    query_analysis: dict
    optimized_queries: list
    search_recommendation: dict
    thinking: Optional[str] = field(default=None, repr=False)
    raw_response: Optional[str] = field(default=None, repr=False)


class QueryOptimizer:
    """
    查询优化器 - 基于 LLM 的查询优化与扩展

    将用户原始查询通过五阶段协议转换为多个检索友好的查询变体。
    支持同步/异步调用，可自定义配置。

    Attributes:
        config: 当前使用的配置
        last_result: 最近一次优化结果
        _doc_sets_list: 已加载的文档集列表

    Example:
        >>> optimizer = QueryOptimizer()
        >>> result = optimizer("opencode 如何创建 skills?")
        >>> for q in result.optimized_queries:
        ...     print(q.get("query"))

        >>> # 自定义配置
        >>> config = QueryOptimizerConfig(model="MiniMax-M2.1", max_tokens=10000)
        >>> optimizer = QueryOptimizer(config)
    """

    config: QueryOptimizerConfig
    last_result: Optional[OptimizationResult]

    def __init__(self, config: Optional[QueryOptimizerConfig] = None) -> None:
        """
        初始化 QueryOptimizer

        Args:
            config: QueryOptimizerConfig 实例，为 None 时使用默认配置

        Raises:
            FileNotFoundError: prompt 模板文件不存在
        """
        self.config = config or QueryOptimizerConfig()
        self._prompt_template: Optional[str] = None
        self._doc_sets_list: list = []
        self.last_result = None
        self._load_prompt_template()
        self._load_doc_sets()

    def _load_prompt_template(self) -> None:
        """
        加载 prompt 模板文件

        Raises:
            FileNotFoundError: 模板文件不存在
        """
        path = Path(self.config.prompt_template_path)
        if path.exists():
            self._prompt_template = path.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(f"Prompt template not found: {path}")

    def _load_doc_sets(self) -> None:
        """加载本地文档集列表"""
        base_path = Path(self.config.doc_sets_base_path)
        if base_path.exists():
            self._doc_sets_list = sorted(base_path.iterdir())
            self._doc_sets_list = [d.name for d in self._doc_sets_list if d.is_dir()]

    def _validate_response_data(self, data: dict) -> tuple[bool, list[str]]:
        """
        验证响应数据的关键字段是否非空

        Returns:
            tuple: (是否有效, 空字段列表)
        """
        empty_fields = []
        query_analysis = data.get("query_analysis", {})

        # 必填字段检查（predicate_verbs 允许为空）
        if not query_analysis.get("original"):
            empty_fields.append("query_analysis.original")
        if query_analysis.get("domain_nouns") is None or len(query_analysis.get("domain_nouns", [])) == 0:
            empty_fields.append("query_analysis.domain_nouns")
        # predicate_verbs 可为空，不检查
        if data.get("optimized_queries") is None or len(data.get("optimized_queries", [])) == 0:
            empty_fields.append("optimized_queries")

        return len(empty_fields) == 0, empty_fields

    def _create_retry_prompt(
        self,
        original_query: str,
        raw_response: str,
        empty_fields: list[str]
    ) -> str:
        """
        构建重试 prompt
        """
        empty_fields_str = ", ".join(empty_fields)
        return f"""
## 重试指令

你上一次返回的结果中以下关键字段为空: [{empty_fields_str}]

请重新分析用户查询并确保输出完整的数据结构:
- `original` 必须是原始查询文本
- `domain_nouns` （不能为空）
- `predicate_verbs` 可为空
- `optimized_queries` （不能为空）

用户查询: {original_query}

上一次返回的数据:
```json
{raw_response}
```

请严格按照原 system prompt 的要求，重新生成完整的 JSON 数据。
"""

    def _extract_data_from_result(self, result: OptimizationResult) -> dict:
        """
        从 OptimizationResult 提取用于验证的数据字典
        """
        return {
            "query_analysis": result.query_analysis or {},
            "optimized_queries": result.optimized_queries or [],
        }

    def set_prompt_template(self, path: Union[str, Path]) -> None:
        """
        设置自定义 prompt 模板

        Args:
            path: 模板文件路径

        Raises:
            FileNotFoundError: 模板文件不存在
        """
        p = Path(path)
        if p.exists():
            self._prompt_template = p.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(f"Prompt template not found: {p}")

    def set_doc_sets_path(self, path: Union[str, Path]) -> None:
        """
        设置文档集路径并重新加载

        Args:
            path: 文档集基础路径
        """
        self.config.doc_sets_base_path = str(path)
        self._load_doc_sets()

    def _extract_text_from_block(self, block) -> Optional[str]:
        """
        从不同类型的 block 中提取文本内容

        支持多种 block 类型和访问方式：
        - thinking block: block.type == "thinking", block.thinking
        - text block: block.type == "text", block.text
        - content_block: 新版 SDK 的内容块类型
        - 其他: 尝试多种属性访问方式

        Args:
            block: LLM 返回的消息 block

        Returns:
            提取的文本内容，失败返回 None
        """
        # 方式1: 直接通过 type 属性判断（旧版 SDK）
        if hasattr(block, 'type'):
            block_type = block.type
            if block_type == "thinking":
                return getattr(block, 'thinking', None)
            elif block_type == "text":
                return getattr(block, 'text', None)

        # 方式2: 检查是否是 ContentBlock 类型（新版 SDK）
        try:
            from anthropic.types import ContentBlock
            if isinstance(block, ContentBlock):
                # 尝试多种属性名
                for attr in ['text', 'content', 'model_dump']:
                    if hasattr(block, attr):
                        value = getattr(block, attr)
                        if isinstance(value, str) and value:
                            return value
                        elif attr == 'model_dump':
                            # model_dump 返回字典，尝试提取文本
                            dump = value()
                            if isinstance(dump, dict):
                                return dump.get('text') or dump.get('content')
                return None
        except ImportError:
            pass

        # 方式3: 通用属性尝试
        for attr_name in ['text', 'content', 'thinking']:
            if hasattr(block, attr_name):
                value = getattr(block, attr_name)
                if isinstance(value, str) and value:
                    return value

        return None

    def optimize(self, query: str) -> OptimizationResult:
        """
        执行查询优化（同步）

        将用户查询发送到 LLM 进行五阶段优化处理。
        支持重试机制，当关键字段为空时自动重新调用 LLM。

        Args:
            query: 用户查询文本

        Returns:
            OptimizationResult: 包含分析和优化结果的响应

        Example:
            >>> optimizer = QueryOptimizer()
            >>> result = optimizer.optimize("doc4llm 支持哪些平台?")
            >>> print(result.query_analysis.get("language"))
        """
        if not self._prompt_template:
            self._load_prompt_template()

        system_prompt = self._prompt_template.format(
            LOCAL_DOC_SETS_LIST=self._doc_sets_list
        )

        # 首次调用
        message = invoke(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": query}],
        )

        result = self._parse_response(message)
        raw_response = result.raw_response or ""

        # 重试循环
        retry_count = 0
        max_retries = self.config.max_retries if self.config.retry_on_empty_fields else 0
        combined_thinking = result.thinking or ""

        while retry_count < max_retries:
            data = self._extract_data_from_result(result)
            is_valid, empty_fields = self._validate_response_data(data)

            if is_valid:
                break

            retry_count += 1

            # 构建重试 prompt
            retry_content = self._create_retry_prompt(query, raw_response, empty_fields)

            # 重新调用 LLM（略微提高 temperature）
            retry_temp = min(self.config.temperature + 0.1, 0.2)
            retry_message = invoke(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=retry_temp,
                system=system_prompt,
                messages=[{"role": "user", "content": retry_content}],
            )

            result = self._parse_response(retry_message)
            raw_response = result.raw_response or ""

            # 合并 thinking
            if result.thinking:
                combined_thinking += f"\n\n=== Retry {retry_count} ===\n{result.thinking}"

        # 记录重试信息
        if retry_count > 0:
            result.search_recommendation["retry_count"] = retry_count
            result.search_recommendation["retry_reason"] = f"Empty fields: {empty_fields}"

        # 更新 thinking（合并后的）
        result.thinking = combined_thinking if combined_thinking else None

        self.last_result = result
        return self.last_result

    async def optimize_async(self, query: str) -> OptimizationResult:
        """
        执行查询优化（异步）

        Args:
            query: 用户查询文本

        Returns:
            OptimizationResult: 包含分析和优化结果的响应
        """
        return self.optimize(query)

    def _parse_response(self, message) -> OptimizationResult:
        """
        解析 LLM 响应

        Args:
            message: LLM 返回的消息对象

        Returns:
            OptimizationResult: 解析后的优化结果
        """
        thinking: Optional[str] = None
        raw_response: Optional[str] = None

        # 调试：打印消息结构（开发时使用）
        # print(f"[DEBUG] Message content type: {type(message.content)}")
        # print(f"[DEBUG] Content items: {len(message.content) if message.content else 0}")

        for block in message.content:
            # 尝试提取文本
            text_content = self._extract_text_from_block(block)

            if text_content:
                # 如果还没设置 raw_response，设置为第一个文本内容
                if not raw_response:
                    raw_response = text_content
                # 否则追加（可能有多个 text block）
                else:
                    raw_response += "\n" + text_content

            # 专门提取 thinking（兼容多种方式）
            if not thinking:
                # 方式1: 直接通过 type 判断
                if hasattr(block, 'type') and block.type == "thinking":
                    thinking = getattr(block, 'thinking', None)
                # 方式2: 从提取的文本中判断（如果文本内容像是 thinking）
                elif text_content and "Let me analyze" in text_content and len(text_content) > 500:
                    # 这可能是 thinking 内容
                    pass  # 已经在 text_content 中

        if raw_response:
            data = extract_json_from_codeblock(raw_response)
            if data:
                return OptimizationResult(
                    query_analysis=data.get("query_analysis", {}),
                    optimized_queries=data.get("optimized_queries", []),
                    search_recommendation=data.get("search_recommendation", {}),
                    thinking=thinking,
                    raw_response=raw_response,
                )

        return OptimizationResult(
            query_analysis={},
            optimized_queries=[],
            search_recommendation={"online_suggested": True, "reason": "Failed to parse LLM response"},
            thinking=thinking,
            raw_response=raw_response,
        )

    def __call__(self, query: str) -> OptimizationResult:
        """
        使实例可调用，等同于 optimize() 方法

        Args:
            query: 用户查询文本

        Returns:
            OptimizationResult: 优化结果
        """
        return self.optimize(query)

    def __repr__(self) -> str:
        return f"QueryOptimizer(model={self.config.model!r}, max_tokens={self.config.max_tokens})"


__all__ = ["QueryOptimizer", "QueryOptimizerConfig", "OptimizationResult"]


if __name__ == '__main__':
    optimizer = QueryOptimizer()
    result = optimizer.optimize("opencode 如何创建 skills?")
    if result.thinking:
        print(f"\nThinking: {result.thinking[:2000]}...")

    print(f"Original Query: {result.query_analysis.get('original', 'N/A')}")
    print(f"Language: {result.query_analysis.get('language', 'N/A')}")
    print(f"Doc Set: {result.query_analysis.get('doc_set', [])}")
    print(f"Domain Nouns: {result.query_analysis.get('domain_nouns', [])}")
    print(f"Predicate Verbs: {result.query_analysis.get('predicate_verbs', [])}")
    print("\n--- Optimized Queries ---")
    for q in result.optimized_queries:
        print(f"[{q.get('rank')}] {q.get('query')} ({q.get('strategy')})")
