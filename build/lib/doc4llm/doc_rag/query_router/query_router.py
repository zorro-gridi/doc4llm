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


class QueryRouterValidationError(Exception):
    """查询路由验证失败异常"""
    pass


@dataclass
class QueryRouterConfig:
    """
    QueryRouter 配置类

    Attributes:
        model: LLM 模型名称 (default: "MiniMax-M2.1")
        max_tokens: 最大输出 token 数 (default: 20000)
        temperature: 生成温度 0.0-1.0 (default: 0.1)
        prompt_template_path: prompt 模板文件路径
        max_retries: 最大重试次数（不包含首次调用）(default: 2)
        retry_on_empty_fields: 是否启用重试机制 (default: True)
        silent: 静默模式，不打印流式输出 (default: False)
    """
    model: str = "MiniMax-M2.1"
    max_tokens: int = 20000
    temperature: float = 0.1
    prompt_template_path: str = "doc4llm/doc_rag/query_router/prompt_template/query_router_template.md"
    max_retries: int = 2
    retry_on_empty_fields: bool = True
    silent: bool = False


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

    # 有效场景类型集合
    VALID_SCENES = {"fact_lookup", "faithful_reference", "faithful_how_to",
                    "concept_learning", "how_to", "comparison", "exploration"}

    def _validate_response_data(self, data: dict) -> tuple[bool, list[str]]:
        """
        验证响应数据的关键字段是否有效

        Args:
            data: 包含 scene, confidence, ambiguity, coverage_need, reranker_threshold 的字典

        Returns:
            tuple: (是否有效, 无效字段列表)
        """
        invalid_fields = []

        # scene 必填且必须是有效场景
        scene = data.get("scene")
        if not scene or scene not in self.VALID_SCENES:
            invalid_fields.append(f"scene (must be one of {self.VALID_SCENES})")

        # 验证数值字段范围
        for field in ["confidence", "ambiguity", "coverage_need", "reranker_threshold"]:
            value = data.get(field)
            if value is None:
                invalid_fields.append(field)
            elif field == "reranker_threshold":
                if not (0.30 <= value <= 0.80):
                    invalid_fields.append(f"{field} (must be in [0.30, 0.80])")
            else:
                if not (0.0 <= value <= 1.0):
                    invalid_fields.append(f"{field} (must be in [0.0, 1.0])")

        return len(invalid_fields) == 0, invalid_fields

    def _create_retry_prompt(
        self,
        original_query: str,
        raw_response: str,
        invalid_fields: list[str]
    ) -> str:
        """
        构建重试 prompt

        Args:
            original_query: 原始用户查询
            raw_response: 上一次 LLM 返回的原始响应
            invalid_fields: 无效字段列表

        Returns:
            str: 重试用的 prompt 内容
        """
        invalid_fields_str = ", ".join(invalid_fields)
        valid_scenes_str = ", ".join(self.VALID_SCENES)
        return f"""
## 重试指令

你上一次返回的结果中存在以下问题: [{invalid_fields_str}]

请重新分析用户查询并确保输出完整且有效的数据结构:
- `scene` 必须是以下之一: {valid_scenes_str}
- `confidence`, `ambiguity`, `coverage_need` 必须在 [0.0, 1.0] 范围内
- `reranker_threshold` 必须在 [0.30, 0.80] 范围内

用户查询: {original_query}

上一次返回的数据:
```json
{raw_response}
```

请严格按照原 system prompt 的要求，重新生成完整的 JSON 数据。
"""

    def _extract_data_from_result(self, result: "RoutingResult") -> dict:
        """
        从 RoutingResult 提取用于验证的数据字典

        Args:
            result: RoutingResult 实例

        Returns:
            dict: 包含关键字段的字典
        """
        return {
            "scene": result.scene,
            "confidence": result.confidence,
            "ambiguity": result.ambiguity,
            "coverage_need": result.coverage_need,
            "reranker_threshold": result.reranker_threshold,
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

    def route(self, query: str) -> RoutingResult:
        """
        执行查询路由（同步）

        将用户查询发送到 LLM 进行场景分类和参数生成。

        Args:
            query: 用户查询文本

        Returns:
            RoutingResult: 包含分类结果和参数的路由结果

        Raises:
            QueryRouterValidationError: 重试用尽后仍无法获取有效响应

        Example:
            >>> router = QueryRouter()
            >>> result = router.route("doc4llm 支持哪些平台?")
            >>> print(result.scene)
            exploration
        """
        if not self._prompt_template:
            self._load_prompt_template()

        # 首次调用
        message = invoke(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=self._prompt_template,
            messages=[{"role": "user", "content": query}],
            silent=self.config.silent,
        )

        # 首次尝试解析
        try:
            result = self._parse_response(message)
            raw_response = result.raw_response or ""
        except Exception:
            # 解析失败时创建无效结果供验证使用
            result = RoutingResult(
                scene=None, confidence=None, ambiguity=None,
                coverage_need=None, reranker_threshold=None,
                thinking=None, raw_response=""
            )
            raw_response = ""

        # 重试循环
        retry_count = 0
        max_retries = self.config.max_retries if self.config.retry_on_empty_fields else 0
        combined_thinking = result.thinking or ""
        is_valid = False

        while retry_count < max_retries:
            data = self._extract_data_from_result(result)
            is_valid, invalid_fields = self._validate_response_data(data)

            if is_valid:
                break

            retry_count += 1

            # 构建重试 prompt
            retry_content = self._create_retry_prompt(query, raw_response, invalid_fields)

            # 重新调用 LLM（略微提高 temperature）
            retry_temp = min(self.config.temperature + 0.1, 0.2)
            retry_message = invoke(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=retry_temp,
                system=self._prompt_template,
                messages=[{"role": "user", "content": retry_content}],
                silent=self.config.silent,
            )

            # 尝试解析，失败则继续重试
            try:
                result = self._parse_response(retry_message)
                raw_response = result.raw_response or ""
            except Exception:
                result = RoutingResult(
                    scene=None, confidence=None, ambiguity=None,
                    coverage_need=None, reranker_threshold=None,
                    thinking=None, raw_response=""
                )
                raw_response = ""

            # 合并 thinking
            if result.thinking:
                combined_thinking += f"\n\n=== Retry {retry_count} ===\n{result.thinking}"

        # 重试用尽后仍无效，抛出异常
        if not is_valid:
            raise QueryRouterValidationError("本地文档检索错误，请退出重试")

        # 更新 thinking（合并后的）
        result.thinking = combined_thinking if combined_thinking else None

        self.last_result = result
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

        Raises:
            QueryRouterValidationError: 解析失败或必填字段缺失
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
                scene = data.get("scene")
                confidence = data.get("confidence")
                ambiguity = data.get("ambiguity")
                coverage_need = data.get("coverage_need")
                reranker_threshold = data.get("reranker_threshold")

                # 检查必填字段，任一字段为空则抛出异常触发重试
                if scene is not None and confidence is not None and ambiguity is not None \
                   and coverage_need is not None and reranker_threshold is not None:
                    return RoutingResult(
                        scene=scene,
                        confidence=confidence,
                        ambiguity=ambiguity,
                        coverage_need=coverage_need,
                        reranker_threshold=reranker_threshold,
                        thinking=thinking,
                        raw_response=raw_response,
                    )

        # 解析失败或必填字段缺失时抛出异常
        raise QueryRouterValidationError("本地文档检索错误，请退出重试")

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


__all__ = ["QueryRouter", "QueryRouterConfig", "RoutingResult", "QueryRouterValidationError"]


if __name__ == '__main__':
    router = QueryRouter()
    result = router.route('如何创建 ray cluster?')
    print(f'Scene: {result.scene}')
    print(f'Confidence: {result.confidence}')
    print(f'Reranker Threshold: {result.reranker_threshold}')
    if result.thinking:
        print(f'Thinking: {result.thinking[:1000]}...')
