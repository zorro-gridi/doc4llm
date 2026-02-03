#!/usr/bin/env python3
"""
测试 LangChain 页面的 Mermaid 图表位置保持功能
"""

import requests
from bs4 import BeautifulSoup
from doc4llm.convertor.MermaidParser import MermaidParser
from doc4llm.convertor.MarkdownConverter import MarkdownConverter

def test_langchain_mermaid():
    """测试 LangChain 页面的 Mermaid 处理"""
    
    url = "https://docs.langchain.com/oss/python/langchain/retrieval"
    
    print(f"=== 测试 LangChain Mermaid 处理 ===")
    print(f"URL: {url}\n")
    
    try:
        # 获取页面内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        html_content = response.text
        print(f"1. 获取HTML成功，长度: {len(html_content)} 字符")
        
        # 检查是否包含 Mermaid 相关元素
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 查找各种 Mermaid 标记
        mermaid_elements = []
        mermaid_elements.extend(soup.find_all("div", class_="mermaid"))
        mermaid_elements.extend(soup.find_all("svg", class_="flowchart"))
        mermaid_elements.extend(soup.find_all(attrs={"data-component-name": "mermaid-container"}))
        mermaid_elements.extend(soup.find_all("pre", class_="mermaid"))
        
        print(f"2. 发现 {len(mermaid_elements)} 个 Mermaid 相关元素")
        
        if mermaid_elements:
            for i, elem in enumerate(mermaid_elements):
                print(f"   元素 {i+1}: {elem.name} - {elem.get('class', [])} - 内容长度: {len(elem.get_text(strip=True))}")
        
        # 使用新的位置保持方法
        mermaid_parser = MermaidParser()
        markdown_converter = MarkdownConverter()
        
        # 替换为占位符
        html_with_placeholders, mermaid_map = mermaid_parser.replace_mermaid_with_placeholders(html_content)
        
        print(f"3. 创建了 {len(mermaid_map)} 个 Mermaid 占位符")
        
        if mermaid_map:
            for placeholder_id, code in mermaid_map.items():
                print(f"   {placeholder_id}: {code[:100]}...")
            
            # 转换为 Markdown
            markdown_content = markdown_converter.convert_to_markdown(html_with_placeholders)
            
            # 恢复 Mermaid 图表
            final_markdown = mermaid_parser.restore_mermaid_in_markdown(markdown_content, mermaid_map)
            
            # 检查结果
            mermaid_count = final_markdown.count('```mermaid')
            print(f"4. 最终 Markdown 包含 {mermaid_count} 个 Mermaid 图表")
            
            # 显示部分结果
            lines = final_markdown.split('\n')
            mermaid_lines = []
            for i, line in enumerate(lines):
                if '```mermaid' in line:
                    mermaid_lines.append(i)
            
            if mermaid_lines:
                print(f"5. Mermaid 图表出现在行: {mermaid_lines}")
                print("   ✅ 成功：Mermaid 图表已插入到原始位置")
            else:
                print("   ❌ 失败：未找到 Mermaid 图表")
        else:
            print("   ℹ️  该页面没有 Mermaid 图表")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_langchain_mermaid()