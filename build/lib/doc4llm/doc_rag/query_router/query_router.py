"""
Query Router - LLM-Based Query Classification and Routing

将用户查询分类为七种场景之一，并生成检索参数。

Features:
    - 七种场景分类: fact_lookup, faithful_reference, faithful_how_to,
      concept_learning, how_to, comparison, exploration
    - 智能参数生成: confidence, ambiguity, coverage_need
    - 自动计算 reranker_threshold
    - 支持 thinking 推理过程保留
    - 同步/异步接口

Example:
    >>> router = QueryRouter()
    >>> result = router.route("如何创建 ray cluster?")
    >>> print(result.scene, result.confidence)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from doc4llm.doc_rag.params_parser.output_parser import extract_json_from_codeblock
from doc4llm.llm.anthropic import invoke


@dataclass
class QueryRouterConfig:
    """
    QueryRouter 配置类

    Attributes:
        model: LLM 模型名称 (default: "MiniMax-M2.1")
        max_tokens: 最大输出 token 数 (default: 20000)
        temperature: 生成温度 0.0-1.0 (default: 0.1)
        prompt_template_path: prompt 模板文件路径
    """
    model: str = "MiniMax-M2.1"
    max_tokens: int = 20000
    temperature: float = 0.1
    prompt_template_path: str = "doc4llm/doc_rag/query_router/prompt_template/query_router_template.md"


@dataclass
class RoutingResult:
    """
    查询路由结果

    Attributes:
        scene: 分类场景类型
        confidence: 分类置信度 0.0-1.0
        ambiguity: 查询模糊度 0.0-1.0
        coverage_need: 内容覆盖需求 0.0-1.0
        reranker_threshold: 重排序阈值 [0.30, 0.80]
        thinking: LLM 推理过程 (如有)
        raw_response: 原始响应文本
    """
    scene: str
    confidence: float
    ambiguity: float
    coverage_need: float
    reranker_threshold: float
    thinking: Optional[str] = field(default=None, repr=False)
    raw_response: Optional[str] = field(default=None, repr=False)


class QueryRouter:
    """
    查询路由器 - 基于 LLM 的语义分类与路由

    将用户查询智能分类到预定义场景，并生成下游检索所需的参数。
    支持同步/异步调用，可自定义配置。

    Attributes:
        config: 当前使用的配置
        last_result: 最近一次路由结果

    Example:
        >>> router = QueryRouter()
        >>> result = router("如何安装 doc4llm?")
        >>> print(result.scene)
        how_to

        >>> # 自定义配置
        >>> config = QueryRouterConfig(model="MiniMax-M2.1", max_tokens=10000)
        >>> router = QueryRouter(config)
    """

    config: QueryRouterConfig
    last_result: Optional[RoutingResult]

    def __init__(self, config: Optional[QueryRouterConfig] = None) -> None:
        """
        初始化 QueryRouter

        Args:
            config: QueryRouterConfig 实例，为 None 时使用默认配置

        Raises:
            FileNotFoundError: prompt 模板文件不存在
        """
        self.config = config or QueryRouterConfig()
        self._prompt_template: Optional[str] = None
        self.last_result = None
        self._load_prompt_template()

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

    def route(self, query: str) -> RoutingResult:
        """
        执行查询路由（同步）

        将用户查询发送到 LLM 进行场景分类和参数生成。

        Args:
            query: 用户查询文本

        Returns:
            RoutingResult: 包含分类结果和参数的路由结果

        Example:
            >>> router = QueryRouter()
            >>> result = router.route("doc4llm 支持哪些平台?")
            >>> print(result.scene)
            exploration
        """
        if not self._prompt_template:
            self._load_prompt_template()

        message = invoke(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=self._prompt_template,
            messages=[{"role": "user", "content": query}],
        )

        self.last_result = self._parse_response(message)
        return self.last_result

    async def route_async(self, query: str) -> RoutingResult:
        """
        执行查询路由（异步）

        Args:
            query: 用户查询文本

        Returns:
            RoutingResult: 包含分类结果和参数的路由结果
        """
        return self.route(query)

    def _parse_response(self, message) -> RoutingResult:
        """
        解析 LLM 响应

        Args:
            message: LLM 返回的消息对象

        Returns:
            RoutingResult: 解析后的路由结果
        """
        thinking: Optional[str] = None
        raw_response: Optional[str] = None

        for block in message.content:
            if block.type == "thinking":
                thinking = block.thinking
            elif block.type == "text":
                raw_response = block.text

        if raw_response:
            data = extract_json_from_codeblock(raw_response)
            if data:
                return RoutingResult(
                    scene=data.get("scene", "fact_lookup"),
                    confidence=data.get("confidence", 0.5),
                    ambiguity=data.get("ambiguity", 0.5),
                    coverage_need=data.get("coverage_need", 0.5),
                    reranker_threshold=data.get("reranker_threshold", 0.5),
                    thinking=thinking,
                    raw_response=raw_response,
                )

        return RoutingResult(
            scene="fact_lookup",
            confidence=0.5,
            ambiguity=0.5,
            coverage_need=0.5,
            reranker_threshold=0.5,
            thinking=thinking,
            raw_response=raw_response,
        )

    def __call__(self, query: str) -> RoutingResult:
        """
        使实例可调用，等同于 route() 方法

        Args:
            query: 用户查询文本

        Returns:
            RoutingResult: 路由结果
        """
        return self.route(query)

    def __repr__(self) -> str:
        return f"QueryRouter(model={self.config.model!r}, max_tokens={self.config.max_tokens})"


__all__ = ["QueryRouter", "QueryRouterConfig", "RoutingResult"]


if __name__ == '__main__':
    router = QueryRouter()
    result = router.route('如何创建 ray cluster?')
    print(f'Scene: {result.scene}')
    print(f'Confidence: {result.confidence}')
    print(f'Reranker Threshold: {result.reranker_threshold}')
    if result.thinking:
        print(f'Thinking: {result.thinking[:1000]}...')
