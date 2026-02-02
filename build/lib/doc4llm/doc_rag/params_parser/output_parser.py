"""
JSON data extractor for parsing JSON from markdown code blocks.
"""

import re
import json
from typing import Optional

from json_repair import repair_json


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
            # 使用 json_repair 修复后重新解析
            repaired = repair_json(json_str)
            # repair_json 可能直接返回 dict
            if isinstance(repaired, dict):
                return repaired
            # 只有当修复结果是字符串时才尝试 json.loads
            if isinstance(repaired, str):
                try:
                    return json.loads(repaired)
                except (json.JSONDecodeError, TypeError):
                    pass

    raw_match = text.strip()
    if raw_match.startswith('{') and raw_match.endswith('}'):
        try:
            return json.loads(raw_match)
        except (json.JSONDecodeError, TypeError):
            # 使用 json_repair 修复后重新解析
            repaired = repair_json(raw_match)
            # repair_json 可能直接返回 dict
            if isinstance(repaired, dict):
                return repaired
            # 只有当修复结果是字符串时才尝试 json.loads
            if isinstance(repaired, str):
                try:
                    return json.loads(repaired)
                except (json.JSONDecodeError, TypeError):
                    pass

    return None
