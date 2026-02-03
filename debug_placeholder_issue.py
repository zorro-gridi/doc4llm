#!/usr/bin/env python3
"""
调试占位符替换问题
"""

from doc4llm.convertor.MermaidParser import MermaidParser
from doc4llm.convertor.MarkdownConverter import MarkdownConverter

def debug_placeholder_issue():
    """调试占位符替换问题"""
    
    print("=== 调试占位符替换问题 ===\n")
    
    # 模拟包含Mermaid的HTML
    test_html = """
    <div class="content">
        <h1>测试文档</h1>
        <p>第一段内容</p>
        
        <div class="mermaid">
            <code type="mermaid">
                flowchart TD
                    A[开始] --> B[处理]
                    B --> C[结束]
            </code>
        </div>
        
        <p>第二段内容</p>
        
        <svg class="flowchart" id="test-svg">
            <g class="nodes">
                <g class="node" id="flowchart-X-123">
                    <g class="nodeLabel">
                        <span>节点X</span>
                    </g>
                </g>
                <g class="node" id="flowchart-Y-456">
                    <g class="nodeLabel">
                        <span>节点Y</span>
                    </g>
                </g>
            </g>
            <g class="edgePaths">
                <path id="L_X_Y"></path>
            </g>
            <g class="edgeLabels">
                <g class="edgeLabel">
                    <span class="edgeLabel">连接</span>
                </g>
            </g>
        </svg>
        
        <p>第三段内容</p>
    </div>
    """
    
    mermaid_parser = MermaidParser()
    markdown_converter = MarkdownConverter()
    
    print("1. 原始HTML:")
    print(test_html[:200] + "...\n")
    
    # 步骤1: 替换为占位符
    print("2. 替换为占位符...")
    html_with_placeholders, mermaid_map = mermaid_parser.replace_mermaid_with_placeholders(test_html)
    
    print(f"   创建了 {len(mermaid_map)} 个占位符")
    for placeholder_id, mermaid_code in mermaid_map.items():
        print(f"   {placeholder_id}: {len(mermaid_code)} 字符")
        print(f"     代码预览: {mermaid_code[:100]}...")
    
    print(f"\n   HTML中的占位符:")
    for placeholder_id in mermaid_map.keys():
        placeholder_text = f"[{placeholder_id}]"
        if placeholder_text in html_with_placeholders:
            print(f"     ✅ 找到: {placeholder_text}")
        else:
            print(f"     ❌ 未找到: {placeholder_text}")
            # 查找可能的变体
            import re
            pattern = re.escape(placeholder_id)
            matches = re.findall(f".*{pattern}.*", html_with_placeholders)
            if matches:
                print(f"       可能的匹配: {matches[:3]}")
    
    # 步骤2: 转换为Markdown
    print(f"\n3. 转换为Markdown...")
    markdown_content = markdown_converter.convert_to_markdown(html_with_placeholders)
    
    print(f"   Markdown长度: {len(markdown_content)} 字符")
    print(f"   Markdown预览:")
    print("   " + "\n   ".join(markdown_content.split('\n')[:10]))
    
    # 检查占位符在Markdown中的状态
    print(f"\n   Markdown中的占位符:")
    for placeholder_id in mermaid_map.keys():
        placeholder_text = f"[{placeholder_id}]"
        if placeholder_text in markdown_content:
            print(f"     ✅ 找到: {placeholder_text}")
        else:
            print(f"     ❌ 未找到: {placeholder_text}")
            # 查找可能的变体
            import re
            # 查找包含placeholder_id的任何文本
            lines = markdown_content.split('\n')
            for i, line in enumerate(lines):
                if placeholder_id in line:
                    print(f"       行 {i+1}: {line.strip()}")
    
    # 步骤3: 恢复占位符
    print(f"\n4. 恢复占位符...")
    final_markdown = mermaid_parser.restore_mermaid_in_markdown(markdown_content, mermaid_map)
    
    print(f"   最终Markdown长度: {len(final_markdown)} 字符")
    
    # 检查是否成功替换
    mermaid_count = final_markdown.count('```mermaid')
    placeholder_count = sum(1 for pid in mermaid_map.keys() if f"[{pid}]" in final_markdown)
    
    print(f"   Mermaid代码块: {mermaid_count} 个")
    print(f"   剩余占位符: {placeholder_count} 个")
    
    if placeholder_count > 0:
        print(f"   ❌ 仍有占位符未替换")
        for placeholder_id in mermaid_map.keys():
            if f"[{placeholder_id}]" in final_markdown:
                print(f"     未替换: [{placeholder_id}]")
    else:
        print(f"   ✅ 所有占位符已成功替换")
    
    print(f"\n5. 最终结果:")
    print("=" * 50)
    print(final_markdown)
    print("=" * 50)

if __name__ == "__main__":
    debug_placeholder_issue()