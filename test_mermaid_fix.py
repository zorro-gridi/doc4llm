#!/usr/bin/env python3
"""
测试修复后的 Mermaid 占位符替换功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'doc4llm'))

from doc4llm.convertor.MermaidParser import MermaidParser

def test_langchain_mermaid_fix():
    """测试 LangChain 页面的 Mermaid 处理"""
    
    # 模拟 LangChain 页面的 HTML 结构
    html_content = '''
    <html>
    <body>
        <div data-component-name="mermaid-container">
            <div class="mermaid">
                <svg class="flowchart" id="flowchart-1">
                    <g class="nodes">
                        <g class="node" id="flowchart-A-1">
                            <text>Load Documents</text>
                        </g>
                        <g class="node" id="flowchart-B-2">
                            <text>Split Text</text>
                        </g>
                    </g>
                    <g class="edgePaths">
                        <path id="L_A_B"></path>
                    </g>
                </svg>
            </div>
        </div>
        
        <div data-component-name="mermaid-container">
            <div class="mermaid">
                <!-- 空容器，应该被跳过 -->
            </div>
        </div>
        
        <div data-component-name="mermaid-container">
            <div class="mermaid">
                <svg class="flowchart" id="flowchart-2">
                    <g class="nodes">
                        <g class="node" id="flowchart-C-3">
                            <text>Embed</text>
                        </g>
                        <g class="node" id="flowchart-D-4">
                            <text>Store</text>
                        </g>
                    </g>
                </svg>
            </div>
        </div>
        
        <div data-component-name="mermaid-container">
            <!-- 另一个空容器 -->
        </div>
        
        <div class="mermaid">
            <!-- 独立的空 mermaid 容器 -->
        </div>
        
        <div class="mermaid">
            <code type="mermaid">
                flowchart TD
                    E[Query] --> F[Retrieve]
                    F --> G[Generate]
            </code>
        </div>
    </body>
    </html>
    '''
    
    parser = MermaidParser()
    
    print("=== 测试占位符替换 ===")
    modified_html, mermaid_map = parser.replace_mermaid_with_placeholders(html_content)
    
    print(f"\n生成的占位符数量: {len(mermaid_map)}")
    for placeholder_id, code in mermaid_map.items():
        print(f"- {placeholder_id}: {len(code)} 字符")
    
    print(f"\n修改后的HTML中的占位符:")
    import re
    placeholders = re.findall(r'\[MERMAID_PLACEHOLDER_\d+\]', modified_html)
    for p in placeholders:
        print(f"- {p}")
    
    # 模拟 Markdown 转换后的内容
    markdown_content = '''
# Retrieval

Some content here...

[MERMAID_PLACEHOLDER_0]

More content...

[MERMAID_PLACEHOLDER_1]

Final content...

[MERMAID_PLACEHOLDER_2]
'''
    
    print("\n=== 测试占位符恢复 ===")
    restored_markdown = parser.restore_mermaid_in_markdown(markdown_content, mermaid_map)
    
    print("\n恢复后的 Markdown:")
    print(restored_markdown[:500] + "..." if len(restored_markdown) > 500 else restored_markdown)
    
    # 检查是否还有未替换的占位符
    remaining_placeholders = re.findall(r'\[MERMAID_PLACEHOLDER_\d+\]', restored_markdown)
    if remaining_placeholders:
        print(f"\n⚠️  仍有未替换的占位符: {remaining_placeholders}")
    else:
        print("\n✅ 所有占位符都已成功替换")

if __name__ == "__main__":
    test_langchain_mermaid_fix()