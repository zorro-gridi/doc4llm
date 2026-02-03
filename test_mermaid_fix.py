#!/usr/bin/env python3
"""测试 MermaidParser 对 LangChain 格式的支持"""

from doc4llm.convertor.MermaidParser import MermaidParser


def test_langchain_mermaid_format():
    """测试 LangChain 的 mermaid 格式: <div class="mermaid"><code type="mermaid">"""
    parser = MermaidParser()

    # LangChain 实际 HTML 结构
    html = """
    <div class="content">
        <div class="mermaid">
            <code type="mermaid">flowchart LR
    S([Sources<br/>(Google Drive, Slack, Notion, etc.)]) --&gt; L[Document Loaders]
    L --&gt; A([Documents])
    A --&gt; B[Split into chunks]
    B --&gt; C[Turn into embeddings]
    C --&gt; D[(Vector Store)]
    Q([User Query]) --&gt; E[Query embedding]
    E --&gt; D
    D --&gt; F[Retriever]
    F --&gt; G[LLM uses retrieved info]
    G --&gt; H([Answer])</code>
        </div>
        <div class="mermaid">
            <code type="mermaid">graph TD
    A[Start] --&gt; B{Decision}
    B -- Yes --&gt; C[Action 1]
    B -- No --&gt; D[Action 2]</code>
        </div>
    </div>
    """

    print("🔍 测试 LangChain 格式 mermaid 解析...")

    # 测试源码提取
    sources = parser.extract_mermaid_from_pre_code_blocks(html)
    print(f"✅ 找到 {len(sources)} 个 mermaid 源码块")

    for i, source in enumerate(sources, 1):
        print(f"\n--- 源码 {i} ---")
        print(source[:200] + "..." if len(source) > 200 else source)

    # 测试完整转换
    result = parser.extract_and_convert_mermaid_blocks(html)
    print(f"\n✅ 转换结果长度: {len(result)} 字符")

    if "```mermaid" in result:
        count = result.count("```mermaid")
        print(f"✅ 成功生成 {count} 个 mermaid 代码块")
        print("\n--- 转换结果预览 ---")
        print(result[:500])
    else:
        print("❌ 未找到 mermaid 代码块")

    return result


def test_pre_mermaid_format():
    """测试标准 <pre class="mermaid"> 格式"""
    parser = MermaidParser()

    html = """
    <div>
        <pre class="mermaid">
            <code>
flowchart TB
    A[Start] --&gt; B[Process]
</code>
        </pre>
    </div>
    """

    print("\n\n🔍 测试 pre.mermaid 格式解析...")
    sources = parser.extract_mermaid_from_pre_code_blocks(html)
    print(f"✅ 找到 {len(sources)} 个 mermaid 源码块")

    if sources:
        print(f"源码: {sources[0][:100]}...")


def test_svg_format():
    """测试 SVG 格式 (保持向后兼容)"""
    parser = MermaidParser()

    html = """
    <svg class="flowchart" id="mermaid-graph-1">
        <g class="nodes">
            <g class="node" id="flowchart-A-1">
                <rect class="shape" rx="0" ry="0"></rect>
                <foreignObject class="nodeLabel">
                    <div>Start</div>
                </foreignObject>
            </g>
        </g>
        <g class="edgePaths">
            <path id="L_A_B_1" d="M..."></path>
        </g>
        <g class="edgeLabels">
            <g class="edgeLabel">
                <span class="edgeLabel"></span>
            </g>
        </g>
    </svg>
    """

    print("\n\n🔍 测试 SVG 格式解析 (向后兼容)...")
    graphs = parser.parse_graphs_from_html(html)
    print(f"✅ 找到 {len(graphs)} 个 SVG 图表")

    if graphs:
        code = parser.graph_to_mermaid_code(graphs[0])
        print(f"生成的代码:\n{code}")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 MermaidParser 修复测试")
    print("=" * 60)

    test_langchain_mermaid_format()
    test_pre_mermaid_format()
    test_svg_format()

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
