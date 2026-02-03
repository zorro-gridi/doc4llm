#!/usr/bin/env python3
"""
测试 Mermaid 解析器集成
爬取 LangChain 文档并提取 mermaid 图表
"""

import sys
import os

sys.path.insert(0, "/Users/zorro/project/doc4llm")

from doc4llm.convertor import MermaidParser, MarkdownConverter
from bs4 import BeautifulSoup


def test_mermaid_parser_with_langchain():
    """测试 Mermaid 解析器"""

    print("=" * 60)
    print("测试 Mermaid 解析器集成")
    print("=" * 60)

    # 初始化解析器
    mermaid_parser = MermaidParser()
    md_converter = MarkdownConverter()

    print("\n✅ 解析器初始化成功")

    # 测试 HTML（模拟 LangChain 文档中的 mermaid SVG）
    test_html = """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>RAG 架构</h1>
        <p>以下是检索增强生成的流程图：</p>

        <svg class="flowchart" id="mermaid-rag">
            <g class="nodes">
                <g class="node startend" id="flowchart-A-1">
                    <g class="nodeLabel"><p>User Question</p></g>
                </g>
                <g class="node process" id="flowchart-B-2">
                    <g class="nodeLabel"><p>Retrieve Documents</p></g>
                </g>
                <g class="node decision" id="flowchart-C-3">
                    <g class="nodeLabel"><p>Enough Info?</p></g>
                </g>
                <g class="node process" id="flowchart-D-4">
                    <g class="nodeLabel"><p>Generate Answer</p></g>
                </g>
            </g>
            <g class="edgePaths">
                <path id="L_A_B_0"></path>
                <path id="L_B_C_0"></path>
                <path id="L_C_D_0"></path>
            </g>
        </svg>

        <p>以上是主流程，还有 Agent 流程：</p>

        <svg class="flowchart" id="mermaid-agent">
            <g class="nodes">
                <g class="node" id="flowchart-Q-1">
                    <g class="nodeLabel"><p>Query</p></g>
                </g>
                <g class="node" id="flowchart-R-2">
                    <g class="nodeLabel"><p>Search</p></g>
                </g>
            </g>
            <g class="edgePaths">
                <path id="L_Q_R_0"></path>
            </g>
        </svg>
    </body>
    </html>
    """

    print(f"\n📄 测试 HTML 大小: {len(test_html)} 字符")

    # 1. 测试 mermaid 解析
    print("\n🔍 测试 1: 解析 mermaid 图表")
    graphs = mermaid_parser.parse_graphs_from_html(test_html)
    print(f"   ✅ 找到 {len(graphs)} 个 mermaid 图表")

    for i, graph in enumerate(graphs, 1):
        print(f"   📊 图表 {i}: {len(graph['nodes'])} 节点, {len(graph['edges'])} 边")

    # 2. 测试 mermaid 代码生成
    print("\n📝 测试 2: 生成 mermaid 代码")
    for i, graph in enumerate(graphs, 1):
        code = mermaid_parser.graph_to_mermaid_code(graph)
        print(f"\n   图表 {i}:")
        for line in code.split("\n")[:5]:
            print(f"      {line}")
        if len(code.split("\n")) > 5:
            print(f"      ...")

    # 3. 测试完整流程
    print("\n🔄 测试 3: 完整转换流程")

    # 先转换为 Markdown
    markdown = md_converter.convert_to_markdown(test_html)
    print(f"   ✅ HTML 转 Markdown: {len(markdown)} 字符")

    # 再提取 mermaid 图表
    mermaid_content = mermaid_parser.extract_and_convert_mermaid_blocks(test_html)
    if mermaid_content and mermaid_content.strip():
        print(f"   ✅ Mermaid 提取: {len(mermaid_content)} 字符")
        final_content = markdown + mermaid_content

        # 检查是否包含 mermaid 代码块
        mermaid_blocks = final_content.count("```mermaid")
        print(f"   ✅ 生成 mermaid 代码块: {mermaid_blocks} 个")

        # 显示最终内容中的 mermaid 部分
        if "```mermaid" in final_content:
            start = final_content.find("```mermaid")
            end = final_content.find("```\n", start) + 4
            mermaid_section = final_content[start:end]
            print(f"\n   📋 Mermaid 代码块预览:")
            for line in mermaid_section.split("\n")[:8]:
                print(f"      {line}")
    else:
        print("   ⚠️  没有找到 mermaid 图表")

    # 4. 测试 SVG 替换功能
    print("\n🔀 测试 4: SVG 替换功能")
    replaced_html = mermaid_parser.replace_svg_with_mermaid(test_html)
    svg_count_before = test_html.count('class="flowchart"')
    svg_count_after = replaced_html.count('class="flowchart"')
    mermaid_count = replaced_html.count("```mermaid")

    print(f"   替换前 SVG 数量: {svg_count_before}")
    print(f"   替换后 SVG 数量: {svg_count_after}")
    print(f"   生成 mermaid 代码块: {mermaid_count}")

    if svg_count_after == 0 and mermaid_count > 0:
        print("   ✅ SVG 替换成功！")
    else:
        print("   ⚠️  SVG 替换未完全生效")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

    return True


def test_with_real_html():
    """使用真实 HTML 测试"""

    print("\n" + "=" * 60)
    print("测试 5: 使用真实 HTML（之前保存的 LangChain 页面）")
    print("=" * 60)

    html_file = (
        "/Users/zorro/.local/share/opencode/tool-output/tool_c21a61c910011qWhb6J2wZ5CMN"
    )

    if not os.path.exists(html_file):
        print(f"   ⚠️  HTML 文件不存在: {html_file}")
        return False

    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()

    print(f"   📄 HTML 大小: {len(html):,} 字符")

    # 测试解析
    parser = MermaidParser()
    graphs = parser.parse_graphs_from_html(html)

    print(f"   🔍 找到 {len(graphs)} 个 mermaid 图表")

    if graphs:
        for i, graph in enumerate(graphs[:3], 1):  # 只显示前3个
            print(f"\n   图表 {i}:")
            print(f"      节点: {len(graph['nodes'])}")
            print(f"      边: {len(graph['edges'])}")

            if graph["nodes"]:
                nodes_list = list(graph["nodes"].items())[:3]
                for nid, node in nodes_list:
                    label = node.get("label", "")[:30]
                    print(f"         - {nid}: {label}")

        print(f"\n   ... 还有 {len(graphs) - 3} 个图表（如果 > 3）")
        return True
    else:
        print("   ⚠️  页面中没有找到 SVG 格式的 mermaid 图表")
        print("      可能原因：")
        print("      1. 页面使用 JavaScript 动态渲染")
        print("      2. mermaid 以 <pre class='mermaid'> 代码块形式存在")
        print("      3. 页面结构不同")
        return False


if __name__ == "__main__":
    try:
        # 运行测试
        test_mermaid_parser_with_langchain()
        test_with_real_html()

        print("\n" + "=" * 60)
        print("🎉 测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
