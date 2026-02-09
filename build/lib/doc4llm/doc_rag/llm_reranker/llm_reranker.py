"""
LLM Reranker - 基于 LLM 的文档检索结果重排序

Features:
    - 基于 LLM 的语义相似度评分
    - 自动填充 rerank_sim 字段
    - 过滤低评分结果 (rerank_sim < 0.5)
    - 支持同步/异步调用
    - 保留 thinking 推理过程
    - 参照 query_router.py 的面向对象设计模式

Example:
    >>> reranker = LLMReranker()
    >>> result = reranker.rerank(input_data)
    >>> print(result.success)
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Optional, Union

from doc4llm.doc_rag.params_parser.output_parser import extract_json_from_codeblock
from doc4llm.llm.anthropic import invoke


# 获取当前文件所在目录
_LLM_RERANKER_DIR = Path(__file__).parent


@dataclass
class LLMRerankerConfig:
    """
    LLM Reranker 配置类

    Attributes:
        model: LLM 模型名称 (default: "MiniMax-M2.1")
        max_tokens: 最大输出 token 数 (default: 20000)
        temperature: 生成温度 0.0-1.0 (default: 0.1)
        prompt_template_path: prompt 模板文件路径
        filter_threshold: 重排序阈值 (default: 0.5)
        silent: 静默模式，不打印流式输出 (default: False)
    """
    model: str = "MiniMax-M2.1"
    # coding plan 暂时不支持
    # model: str = "MiniMax-M2.1-lightning"
    max_tokens: int = 20000
    temperature: float = 0.1
    prompt_template_path: str = str(_LLM_RERANKER_DIR / "prompt_template" / "llm_reranker_template.md")
    filter_threshold: float = 0.5
    silent: bool = False


@dataclass
class RerankerResult:
    """
    重排序结果

    Attributes:
        data: 完整的输出 JSON 数据
        success: 是否有匹配结果
        reason: 失败原因 (如有)
        total_headings_before: 过滤前 heading 数量
        total_headings_after: 过滤后 heading 数量
        thinking: LLM 推理过程 (如有)
        raw_response: 原始响应文本 (如有)
    """
    data: dict
    success: bool
    reason: Optional[str] = field(default=None, repr=False)
    total_headings_before: int = 0
    total_headings_after: int = 0
    thinking: Optional[str] = field(default=None, repr=False)
    raw_response: Optional[str] = field(default=None, repr=False)


class LLMReranker:
    """
    LLM Reranker - 基于 LLM 的文档检索结果重排序器

    对文档检索结果进行语义重排序，填充 rerank_sim 字段并过滤低评分结果。

    Attributes:
        config: 当前使用的配置
        last_result: 最近一次重排序结果

    Example:
        >>> reranker = LLMReranker()
        >>> result = reranker.rerank(input_data)
        >>> print(result.success)

        >>> # 自定义配置
        >>> config = LLMRerankerConfig(model="MiniMax-M2.1", filter_threshold=0.6)
        >>> reranker = LLMReranker(config)
    """

    config: LLMRerankerConfig
    last_result: Optional[RerankerResult]

    def __init__(self, config: Optional[LLMRerankerConfig] = None) -> None:
        """
        初始化 LLMReranker

        Args:
            config: LLMRerankerConfig 实例，为 None 时使用默认配置

        Raises:
            FileNotFoundError: prompt 模板文件不存在
        """
        self.config = config or LLMRerankerConfig()
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

    def _validate_input(self, data: dict) -> None:
        """
        验证输入数据格式

        Args:
            data: 输入数据字典

        Raises:
            ValueError: 缺少必需的键
        """
        required_keys = {"query", "results"}
        missing = required_keys - set(data.keys())
        if missing:
            raise ValueError(f"Invalid input: missing required keys {missing}")

    def _build_prompt(self, data: dict) -> str:
        """
        构建完整的 prompt

        Args:
            data: 输入数据字典

        Returns:
            格式化后的 prompt 字符串
        """
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        retrieval_scene = data.get("retrieval_scene", "how_to")
        reranker_threshold = data.get("reranker_threshold", self.config.filter_threshold)
        return self._prompt_template.format(
            SEARCHER_RETRIVAL_RESULTS=json_str,
            RETRIEVAL_SCENE=retrieval_scene,
            LLM_RERANKER_THRESHOLD=reranker_threshold
        )

    def _parse_response(self, message, data: dict = None) -> RerankerResult:
        """
        解析 LLM 响应

        Args:
            message: LLM 返回的消息对象
            data: 原始输入数据字典

        Returns:
            RerankerResult: 解析后的重排序结果
        """
        thinking: Optional[str] = None
        raw_response: Optional[str] = None

        for block in message.content:
            if block.type == "thinking":
                thinking = block.thinking
            elif block.type == "text":
                raw_response = block.text

        if raw_response:
            parsed_data = extract_json_from_codeblock(raw_response)
            if parsed_data:
                total_before = self._count_headings(parsed_data)
                total_after = total_before

                success = parsed_data.get("success", True)
                reason = None if success else parsed_data.get("reason", "Unknown error")

                return RerankerResult(
                    data=parsed_data,
                    success=success,
                    reason=reason,
                    total_headings_before=total_before,
                    total_headings_after=total_after,
                    thinking=thinking,
                    raw_response=raw_response,
                )

        # 解析失败，返回失败结果
        data = data or {}
        return RerankerResult(
            data={
                "success": False,
                "reason": "Failed to parse LLM response",
                "query": data.get("query", []),
                "doc_sets_found": data.get("doc_sets_found", []),
                "results": []
            },
            success=False,
            reason="Failed to parse LLM response",
            total_headings_before=0,
            total_headings_after=0,
            thinking=thinking,
            raw_response=raw_response,
        )

    def _count_headings(self, data: dict) -> int:
        """
        统计结果中的 heading 数量

        Args:
            data: 数据字典

        Returns:
            heading 总数
        """
        count = 0
        for result in data.get("results", []):
            count += len(result.get("headings", []))
        return count

    def rerank(self, data: dict) -> RerankerResult:
        """
        执行重排序（同步）

        将检索结果发送到 LLM 进行语义重排序，填充 rerank_sim 字段并过滤低评分结果。

        Args:
            data: 输入数据字典，包含 query, results 等字段

        Returns:
            RerankerResult: 包含重排序结果和统计信息的 RerankerResult

        Example:
            >>> input_data = {
            ...     "success": True,
            ...     "query": ["how to create skills"],
            ...     "doc_sets_found": ["OpenCode@latest"],
            ...     "results": [...]
            ... }
            >>> result = reranker.rerank(input_data)
            >>> print(result.success)
        """
        self._validate_input(data)

        if not self._prompt_template:
            self._load_prompt_template()

        prompt = self._build_prompt(data)
        message = invoke(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=self._prompt_template,
            messages=[{"role": "user", "content": prompt}],
            silent=self.config.silent,
        )
        # NOTE: 调试分析原始输出
        # print(message)

        self.last_result = self._parse_response(message, data)
        return self.last_result

    async def rerank_async(self, data: dict) -> RerankerResult:
        """
        执行重排序（异步）

        Args:
            data: 输入数据字典

        Returns:
            RerankerResult: 包含重排序结果和统计信息的 RerankerResult
        """
        return self.rerank(data)

    def __call__(self, data: dict) -> RerankerResult:
        """
        使实例可调用，等同于 rerank() 方法

        Args:
            data: 输入数据字典

        Returns:
            RerankerResult: 重排序结果
        """
        return self.rerank(data)

    def __repr__(self) -> str:
        return f"LLMReranker(model={self.config.model!r}, filter_threshold={self.config.filter_threshold})"


__all__ = ["LLMReranker", "LLMRerankerConfig", "RerankerResult"]


if __name__ == '__main__':
    from pprint import pprint
    import json

    # 测试用例
    reranker = LLMReranker()

    with open('phase1_5_input.json', 'r') as f:
        input_data = json.load(f)

    result = reranker.rerank(input_data)
    print(f"Success: {result.success}")
    print(f"Headings before: {result.total_headings_before}")
    print(f"Headings after: {result.total_headings_after}")
    if result.thinking:
        print(f"Thinking: {result.thinking}")
    pprint(result.data)
