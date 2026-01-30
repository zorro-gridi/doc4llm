"""
Anthropic API 兼容接口

提供兼容 Anthropic API 规范的 MiniMax 模型调用接口。
"""

import os
import dotenv
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import anthropic
from anthropic import Anthropic


@dataclass
class LLM_Config:
    """LLM 调用配置类"""
    show_thinking: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60


class AnthropicClient:
    """Anthropic API 兼容的 MiniMax 模型调用客户端"""

    def __init__(self, config: Optional[LLM_Config] = None):
        """
        初始化客户端

        Args:
            config: LLM_Config 配置对象
        """
        self.config = config or LLM_Config()
        self._client = self._init_client()

    def _init_client(self) -> Anthropic:
        """初始化 Anthropic 客户端"""
        dotenv.load_dotenv('doc4llm/.env')
        api_key = self.config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        base_url = self.config.base_url or os.environ.get("ANTHROPIC_BASE_URL")

        client_kwargs = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        if base_url:
            client_kwargs["base_url"] = base_url
        if self.config.timeout:
            client_kwargs["timeout"] = self.config.timeout

        return Anthropic(**client_kwargs)

    def invoke(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 20000,
        temperature: float = 0.1,
        stream: bool = False,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Dict] = None,
        **kwargs
    ) -> Any:
        """
        调用 MiniMax 模型（兼容 Anthropic API 格式）

        Args:
            model: 模型名称，支持 MiniMax-M2.1、MiniMax-M2.1-lightning、MiniMax-M2
            messages: 消息列表，每条消息包含 role 和 content
            system: 系统提示词
            max_tokens: 最大生成 token 数
            temperature: 温度参数，取值范围 (0.0, 1.0]，推荐 1.0
            stream: 是否使用流式输出
            tools: 工具定义列表
            tool_choice: 工具选择策略
            **kwargs: 其他透传参数

        Returns:
            非 stream 模式: anthropic.types.Message 对象
            stream 模式: anthropic.types.Stream[Message] 生成器
            错误时: 透传模型的错误响应
        """
        request_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
            "stream": stream,
        }

        if system:
            request_kwargs["system"] = system
        if tools:
            request_kwargs["tools"] = tools
        if tool_choice:
            request_kwargs["tool_choice"] = tool_choice

        # 根据 show_thinking 配置启用 thinking 模式
        if self.config.show_thinking:
            request_kwargs["thinking"] = {"type": "enabled"}

        request_kwargs.update(kwargs)

        response = self._client.messages.create(**request_kwargs)

        if stream and self.config.show_thinking:
            for chunk in response:
                if hasattr(chunk, "type") and chunk.type == "content_block_delta":
                    delta = getattr(chunk, "delta", None)
                    if delta and hasattr(delta, "type") and delta.type == "thinking_delta":
                        thinking = getattr(delta, "thinking", None)
                        if thinking:
                            print(thinking, end="", flush=True)

        return response


def invoke(
    model: str,
    messages: List[Dict[str, Any]],
    system: Optional[str] = None,
    max_tokens: int = 20000,
    temperature: float = 0.1,
    stream: bool = False,
    tools: Optional[List[Dict]] = None,
    tool_choice: Optional[Dict] = None,
    config: Optional[LLM_Config] = None,
    **kwargs
) -> Any:
    """
    调用 MiniMax 模型（兼容 Anthropic API 格式）

    Args:
        model: 模型名称，支持 MiniMax-M2.1、MiniMax-M2.1-lightning、MiniMax-M2
        messages: 消息列表，每条消息包含 role 和 content
        system: 系统提示词
        max_tokens: 最大生成 token 数
        temperature: 温度参数，取值范围 (0.0, 1.0]，推荐 1.0
        stream: 是否使用流式输出
        tools: 工具定义列表
        tool_choice: 工具选择策略
        config: LLM_Config 配置对象（show_thinking 控制是否启用 thinking）
        **kwargs: 其他透传参数

    Returns:
        非 stream 模式: anthropic.types.Message 对象
        stream 模式: anthropic.types.Stream[Message] 生成器
        错误时: 透传模型的错误响应
    """
    client = AnthropicClient(config)
    return client.invoke(
        model=model,
        messages=messages,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=stream,
        tools=tools,
        tool_choice=tool_choice,
        **kwargs
    )
