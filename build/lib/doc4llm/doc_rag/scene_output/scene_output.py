"""
Scene Output Composer - LLM-Based Output Formatting

基于场景格式化最终输出，将查询场景、文档内容和元数据组合成最终的 Markdown 输出。

Features:
    - 七种场景格式化: fact_lookup, faithful_reference, faithful_how_to,
      concept_learning, how_to, comparison, exploration
    - 同步/异步接口支持
    - 可自定义配置
    - 保留 thinking 推理过程

Example:
    >>> outputter = SceneOutput()
    >>> result = outputter({
    ...     "query": "如何安装 doc4llm?",
    ...     "scene": "how_to",
    ...     "contents": {"安装指南": "## 安装\n\npip install doc4llm"},
    ...     "doc_metas": [{"title": "安装指南", "source_url": "https://example.com", "local_path": "md_docs/install.md"}],
    ...     "compression_meta": {"compression_applied": False, "original_line_count": 0, "output_line_count": 0}
    ... })
    >>> print(result.output)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

from doc4llm.llm.anthropic import invoke


# 获取当前文件所在目录
_SCENE_OUTPUT_DIR = Path(__file__).parent


@dataclass
class SceneOutputConfig:
    """
    SceneOutput 配置类

    Attributes:
        model: LLM 模型名称 (default: "MiniMax-M2.1")
        max_tokens: 最大输出 token 数 (default: 20000)
        temperature: 生成温度 0.0-1.0 (default: 0.3)
        prompt_template_path: prompt 模板文件路径
    """
    model: str = "MiniMax-M2.1"
    max_tokens: int = 20000
    temperature: float = 0.3
    prompt_template_path: str = str(_SCENE_OUTPUT_DIR / "prompt_template" / "scene_output_template.md")


@dataclass
class SceneOutputResult:
    """
    场景输出结果

    Attributes:
        output: 格式化后的输出文本
        raw_response: 原始 LLM 响应文本
        thinking: LLM 推理过程 (如有)
    """
    output: str
    raw_response: Optional[str] = field(default=None, repr=False)
    thinking: Optional[str] = field(default=None, repr=False)


class SceneOutput:
    """
    场景化输出合成器 - 基于场景格式化最终输出

    将查询场景、文档内容和元数据组合成最终的 Markdown 输出。
    支持同步/异步调用，可自定义配置。

    Attributes:
        config: 当前使用的配置
        last_result: 最近一次输出结果

    Example:
        >>> outputter = SceneOutput()
        >>> result = outputter({
        ...     "query": "如何安装 doc4llm?",
        ...     "scene": "how_to",
        ...     "contents": {"安装指南": "## 安装\\n\\npip install doc4llm"},
        ...     "doc_metas": [{"title": "安装指南", "source_url": "https://example.com", "local_path": "md_docs/install.md"}],
        ...     "compression_meta": {"compression_applied": False, "original_line_count": 0, "output_line_count": 0}
        ... })
        >>> print(result.output)
    """

    config: SceneOutputConfig
    last_result: Optional[SceneOutputResult]

    def __init__(self, config: Optional[SceneOutputConfig] = None) -> None:
        """
        初始化 SceneOutput

        Args:
            config: SceneOutputConfig 实例，为 None 时使用默认配置

        Raises:
            FileNotFoundError: prompt 模板文件不存在
        """
        self.config = config or SceneOutputConfig()
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

    def _render_template(self, input_data: Dict) -> str:
        """
        Render prompt template by replacing placeholders with actual values.

        Args:
            input_data: Input data dictionary containing contents, compression_meta, doc_metas

        Returns:
            Rendered template string with all placeholders replaced
        """
        import json

        template = self._prompt_template

        contents = input_data.get("contents", {})
        compression_meta = input_data.get("compression_meta", {})
        doc_metas = input_data.get("doc_metas", [])
        scene = input_data.get("scene", "fact_lookup")

        reader_content = json.dumps(contents, ensure_ascii=False, indent=2)
        template = template.replace("{READER_OUTPUT_CONTENT}", reader_content)

        template = template.replace("{scene}", scene)

        template = template.replace(
            "{{original_line_count}}",
            str(compression_meta.get("original_line_count", 0))
        )
        template = template.replace(
            "{{output_line_count}}",
            str(compression_meta.get("output_line_count", 0))
        )

        sources_section = ""
        for doc_meta in doc_metas:
            sources_section += f"""1. **{doc_meta.get('title', '')}**
   - 原文链接: {doc_meta.get('source_url', '')}
   - 路径: `{doc_meta.get('local_path', '')}`

"""

        if "{{doc_meta.title}}" in template:
            template = template.replace("{{doc_meta.title}}", sources_section)

        return template

    def _serialize_input_data(self, input_data: Dict) -> str:
        """
        序列化输入数据为 JSON 字符串供 LLM 使用

        Args:
            input_data: 输入数据字典

        Returns:
            格式化的 JSON 字符串
        """
        import json

        # 提取关键字段
        query = input_data.get("query", "")
        scene = input_data.get("scene", "fact_lookup")
        contents = input_data.get("contents", {})
        doc_metas = input_data.get("doc_metas", [])
        compression_meta = input_data.get("compression_meta", {})

        # 构建结构化的输入
        structured_input = {
            "query": query,
            "scene": scene,
            "contents": contents,
            "doc_metas": doc_metas,
            "compression_meta": compression_meta
        }

        return json.dumps(structured_input, ensure_ascii=False, indent=2)

    def compose(self, input_data: Dict) -> SceneOutputResult:
        """
        执行场景化输出合成（同步）

        将输入数据发送到 LLM 进行场景化格式化。

        Args:
            input_data: 输入数据字典，包含:
                - query: 用户查询文本
                - scene: 场景类型
                - contents: 文档内容字典
                - doc_metas: 文档元数据列表
                - compression_meta: 压缩元数据

        Returns:
            SceneOutputResult: 包含格式化输出的结果

        Example:
            >>> outputter = SceneOutput()
            >>> result = outputter.compose({
            ...     "query": "doc4llm 支持哪些功能?",
            ...     "scene": "exploration",
            ...     "contents": {...},
            ...     "doc_metas": [...],
            ...     "compression_meta": {...}
            ... })
        """
        if not self._prompt_template:
            self._load_prompt_template()

        rendered_system = self._render_template(input_data)

        # 序列化输入数据
        user_message = self._serialize_input_data(input_data)

        message = invoke(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=rendered_system,
            messages=[{"role": "user", "content": user_message}],
        )

        self.last_result = self._parse_response(message)
        return self.last_result

    async def compose_async(self, input_data: Dict) -> SceneOutputResult:
        """
        执行场景化输出合成（异步）

        Args:
            input_data: 输入数据字典

        Returns:
            SceneOutputResult: 包含格式化输出的结果
        """
        return self.compose(input_data)

    def _parse_response(self, message) -> SceneOutputResult:
        """
        解析 LLM 响应

        Args:
            message: LLM 返回的消息对象

        Returns:
            SceneOutputResult: 解析后的输出结果
        """
        thinking: Optional[str] = None
        raw_response: Optional[str] = None

        for block in message.content:
            if block.type == "thinking":
                thinking = block.thinking
            elif block.type == "text":
                raw_response = block.text

        # 提取主要输出内容
        output = raw_response if raw_response else ""

        return SceneOutputResult(
            output=output,
            raw_response=raw_response,
            thinking=thinking,
        )

    def __call__(self, input_data: Dict) -> SceneOutputResult:
        """
        使实例可调用，等同于 compose() 方法

        Args:
            input_data: 输入数据字典

        Returns:
            SceneOutputResult: 输出结果
        """
        return self.compose(input_data)

    def __repr__(self) -> str:
        return f"SceneOutput(model={self.config.model!r}, max_tokens={self.config.max_tokens})"


__all__ = ["SceneOutput", "SceneOutputConfig", "SceneOutputResult"]


if __name__ == '__main__':
    # 测试代码
    outputter = SceneOutput()

    # 模拟输入数据
    test_input = {
        "query": "如何安装 doc4llm?",
        "scene": "how_to",
        "contents": {
            "安装指南": """## 安装 doc4llm

### 环境要求
- Python 3.10+
- pip 或 conda

### 安装步骤

1. 克隆仓库:
```bash
git clone https://github.com/example/doc4llm.git
```

2. 进入目录:
```bash
cd doc4llm
```

3. 安装依赖:
```bash
pip install -r requirements.txt
```
"""
        },
        "doc_metas": [
            {
                "title": "安装指南",
                "source_url": "https://example.com/docs/install",
                "local_path": "md_docs/docs@latest/安装指南/docContent.md"
            }
        ],
        "compression_meta": {
            "compression_applied": False,
            "original_line_count": 0,
            "output_line_count": 0
        }
    }

    try:
        result = outputter.compose(test_input)
        print("=== Output ===")
        print(result.output)
        if result.thinking:
            print(f"\n=== Thinking ===\n{result.thinking[:200]}...")
    except FileNotFoundError as e:
        print(f"Template not found: {e}")
    except Exception as e:
        print(f"Error: {e}")
