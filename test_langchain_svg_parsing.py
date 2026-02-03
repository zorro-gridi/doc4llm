#!/usr/bin/env python3
"""
测试 LangChain SVG 解析问题
"""

from doc4llm.convertor.MermaidParser import MermaidParser
from bs4 import BeautifulSoup

# Playwright 导入（可选依赖）
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def test_langchain_svg_parsing():
    """测试LangChain SVG解析"""
    
    print("=== 测试 LangChain SVG 解析 ===\n")
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright不可用，无法获取动态内容")
        return
    
    url = "https://docs.langchain.com/oss/python/langchain/retrieval"
    
    # 获取动态渲染的HTML
    print("1. 获取动态渲染的HTML...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # 改为非无头模式
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                ignore_https_errors=True
            )
            page = context.new_page()
            page.set_default_timeout(30000)
            
            page.goto(url, wait_until="domcontentloaded")
            
            # 等待更长时间让Mermaid渲染
            print("   等待Mermaid渲染...")
            page.wait_for_timeout(10000)
            
            # 检查是否有Mermaid相关元素
            mermaid_count = page.evaluate("""
                () => {
                    const selectors = [
                        '.mermaid',
                        'svg.flowchart',
                        '[data-component-name="mermaid-container"]'
                    ];
                    let total = 0;
                    for (const sel of selectors) {
                        const elements = document.querySelectorAll(sel);
                        console.log(`${sel}: ${elements.length} 个元素`);
                        total += elements.length;
                    }
                    return total;
                }
            """)
            
            print(f"   页面中发现 {mermaid_count} 个Mermaid相关元素")
            
            html_content = page.content()
            context.close()
            browser.close()
            
            print(f"   获取成功，HTML长度: {len(html_content)} 字符")
            
    except Exception as e:
        print(f"   获取失败: {e}")
        return
    
    # 解析HTML
    soup = BeautifulSoup(html_content, "html.parser")
    mermaid_parser = MermaidParser()
    
    # 详细分析HTML内容
    print("\n2. 详细分析HTML内容...")
    
    # 检查各种可能的选择器
    selectors_to_check = [
        ("svg.flowchart", "SVG flowchart"),
        (".mermaid", "标准mermaid类"),
        ("[data-component-name='mermaid-container']", "LangChain容器"),
        ("[data-component-name*='mermaid']", "包含mermaid的容器"),
        ("svg", "所有SVG元素"),
        (".diagram", "diagram类"),
        ("[id*='mermaid']", "包含mermaid的ID")
    ]
    
    for selector, description in selectors_to_check:
        elements = soup.select(selector)
        print(f"   {description}: {len(elements)} 个")
        
        if elements and len(elements) <= 5:  # 只显示前5个
            for i, elem in enumerate(elements):
                print(f"     元素 {i+1}: {elem.name} - 类: {elem.get('class', [])} - ID: {elem.get('id', 'None')}")
                content = elem.get_text(strip=True)
                if content:
                    print(f"       内容: {content[:100]}...")
    
    # 测试当前的解析方法
    print("\n3. 测试当前解析方法...")
    
    # 方法1: 查找SVG flowchart
    svg_elements = soup.find_all("svg", class_="flowchart")
    print(f"   发现 {len(svg_elements)} 个SVG flowchart元素")
    
    # 方法2: 查找.mermaid类
    mermaid_divs = soup.find_all("div", class_="mermaid")
    print(f"   发现 {len(mermaid_divs)} 个.mermaid div元素")
    
    # 方法3: 查找LangChain容器
    langchain_containers = soup.find_all(attrs={"data-component-name": "mermaid-container"})
    print(f"   发现 {len(langchain_containers)} 个LangChain mermaid容器")
    
    # 测试新的占位符方法
    print("\n4. 测试新的占位符方法...")
    html_with_placeholders, mermaid_map = mermaid_parser.replace_mermaid_with_placeholders(html_content)
    
    print(f"   创建了 {len(mermaid_map)} 个占位符")
    
    if mermaid_map:
        for placeholder_id, mermaid_code in mermaid_map.items():
            print(f"   {placeholder_id}:")
            print(f"     代码长度: {len(mermaid_code)} 字符")
            print(f"     代码预览: {mermaid_code[:100]}...")
    else:
        print("   ❌ 没有创建任何占位符")
        
        # 如果没有找到，检查是否是访问限制问题
        if "access denied" in html_content.lower() or "blocked" in html_content.lower():
            print("   可能遇到访问限制")
        elif len(html_content) < 100000:  # 正常页面应该更大
            print("   页面内容可能不完整")
            print(f"   页面开头: {html_content[:500]}...")

if __name__ == "__main__":
    test_langchain_svg_parsing()