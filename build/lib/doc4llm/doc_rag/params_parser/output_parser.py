"""
JSON data extractor for parsing JSON from markdown code blocks.
"""

import re
import json
from typing import Any, Optional


# Regex pattern to match JSON code blocks in markdown
JSON_BLOCK_PATTERN = re.compile(
    r'```json\s*\n(.*?)\n```',
    re.DOTALL
)


def extract_json_from_codeblock(text: str) -> Optional[dict]:
    """
    从markdown代码块中提取JSON数据。

    支持两种格式:
    1. ```json ... ``` 代码块
    2. 原始JSON字符串 (无代码块)

    Args:
        text: 包含 JSON 的文本

    Returns:
        解析后的字典，如果提取失败返回 None
    """
    match = JSON_BLOCK_PATTERN.search(text)
    if match:
        json_str = match.group(1).strip()
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            pass

    raw_match = text.strip()
    if raw_match.startswith('{') and raw_match.endswith('}'):
        try:
            return json.loads(raw_match)
        except (json.JSONDecodeError, TypeError):
            pass

    return None
