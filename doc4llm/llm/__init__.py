"""
LLM 接口模块

提供兼容 Anthropic API 的 MiniMax 模型调用接口。
"""

from .anthropic import invoke, LLM_Config, AnthropicClient

__all__ = ["invoke", "LLM_Config", "AnthropicClient"]
