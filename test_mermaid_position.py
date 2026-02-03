#!/usr/bin/env python3
"""
测试 Mermaid 图表位置保持功能
"""

from doc4llm.convertor.MermaidParser import MermaidParser
from doc4llm.convertor.MarkdownConverter import MarkdownConverter

def test_mermaid_position():
    """测试 Mermaid 图表在原始位置插入"""
    
    # 模拟包含 Mermaid 图表的 HTML
    test_html = """
    <div class="content">
        <h1>文档标题</h1>
        <p>这是第一段内容。</p>
        
        <div class="mermaid">
            <code type="mermaid">
                flowchart TD
                    A[开始] --> B{判断}
                    B -->|是| C[执行]
                    B -->|否| D[结束]
            </code>
        </div>
        
        <p>这是第二段内容，在图表之后。</p>
        
        <h2>另一个章节</h2>
        <p>更多内容。</p>
        
        <svg class="flowchart" id="graph2">
            <g class="nodes">
                <g class="node" id="flowchart-A-123">
                    <rect></rect>
                    <g class="nodeLabel">
                        <span>步骤A</span>
                    </g>
                </g>
                <g class="node" id="flowchart-B-456">
                    <rect></rect>
                    <g class="nodeLabel">
                        <span>步骤B</span>
                    </g>
                </g>
            </g>
            <g class="edgePaths">
                <path id="L_A_B"></path>
            </g>
            <g class="edgeLabels">
                <g class="edgeLabel">
                    <span class="edgeLabel">连接</span>
                </g>
            </g>
        </svg>
        
        <p>最后一段内容。</p>
    </div>
    """
    
    print("=== 测试 Mermaid 位置保持功能 ===\n")
    
    # 初始化解析器
    mermaid_parser = MermaidParser()
    markdown_converter = MarkdownConverter()
    
    print("1. 原始 HTML:")
    print(test_html[:200] + "...\n")
    
    # 测试新的位置保持方法
    print("2. 使用新方法（位置保持）:")
    html_with_placeholders, mermaid_map = mermaid_parser.replace_mermaid_with_placeholders(test_html)
    
    print(f"   发现 {len(mermaid_map)} 个 Mermaid 图表")
    print("   占位符映射:")
    for placeholder_id, code in mermaid_map.items():
        print(f"     {placeholder_id}: {code[:50]}...")
    
    # 转换为 Markdown
    markdown_content = markdown_converter.convert_to_markdown(html_with_placeholders)
    
    # 恢复 Mermaid 图表
    final_markdown = mermaid_parser.restore_mermaid_in_markdown(markdown_content, mermaid_map)
    
    print("\n3. 最终 Markdown 结果:")
    print(final_markdown)
    
    print("\n=== 测试完成 ===")
    
    # 验证图表是否在正确位置
    lines = final_markdown.split('\n')
    mermaid_positions = []
    for i, line in enumerate(lines):
        if '```mermaid' in line:
            mermaid_positions.append(i)
    
    print(f"\nMermaid 图表出现在行: {mermaid_positions}")
    
    # 检查是否有图表在内容中间而不是末尾
    content_lines = len(lines)
    if mermaid_positions:
        first_mermaid = mermaid_positions[0]
        if first_mermaid < content_lines - 10:  # 不在末尾
            print("✅ 成功：Mermaid 图表保持在原始位置")
        else:
            print("❌ 失败：Mermaid 图表仍在末尾")
    else:
        print("❌ 失败：未找到 Mermaid 图表")

if __name__ == "__main__":
    test_mermaid_position()