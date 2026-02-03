#!/usr/bin/env python3
"""
分析 LangChain 页面的 Mermaid 选择器特征
"""

import requests
from bs4 import BeautifulSoup

# Playwright 导入（可选依赖）
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def analyze_langchain_mermaid():
    """分析 LangChain 页面的 Mermaid 选择器"""
    
    url = "https://docs.langchain.com/oss/python/langchain/retrieval"
    
    print(f"=== 分析 LangChain Mermaid 选择器 ===")
    print(f"URL: {url}\n")
    
    # 1. 先用 requests 获取静态内容
    print("1. 获取静态HTML内容...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        static_html = response.text
        print(f"   静态HTML长度: {len(static_html)} 字符")
        
        # 分析静态HTML中的Mermaid相关元素
        soup = BeautifulSoup(static_html, "html.parser")
        analyze_mermaid_elements(soup, "静态HTML")
        
    except Exception as e:
        print(f"   获取静态HTML失败: {e}")
        return
    
    # 2. 用 Playwright 获取动态渲染内容
    if PLAYWRIGHT_AVAILABLE:
        print("\n2. 获取Playwright渲染后内容...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=headers['User-Agent'],
                    ignore_https_errors=True
                )
                page = context.new_page()
                page.set_default_timeout(30000)
                
                # 访问页面
                page.goto(url, wait_until="domcontentloaded")
                
                # 等待可能的动态内容加载
                page.wait_for_timeout(5000)
                
                # 获取渲染后的HTML
                dynamic_html = page.content()
                print(f"   动态HTML长度: {len(dynamic_html)} 字符")
                
                context.close()
                browser.close()
                
                # 分析动态HTML中的Mermaid相关元素
                soup = BeautifulSoup(dynamic_html, "html.parser")
                analyze_mermaid_elements(soup, "动态HTML")
                
                # 比较静态和动态内容的差异
                if len(dynamic_html) != len(static_html):
                    print(f"\n3. 内容差异分析:")
                    print(f"   静态HTML: {len(static_html)} 字符")
                    print(f"   动态HTML: {len(dynamic_html)} 字符")
                    print(f"   差异: {len(dynamic_html) - len(static_html)} 字符")
                
        except Exception as e:
            print(f"   Playwright获取失败: {e}")
    else:
        print("\n2. Playwright不可用，跳过动态内容分析")

def analyze_mermaid_elements(soup, source_type):
    """分析HTML中的Mermaid相关元素"""
    
    print(f"\n   === {source_type} Mermaid元素分析 ===")
    
    # 检查各种可能的Mermaid选择器
    selectors = {
        "svg.flowchart": "SVG flowchart元素",
        ".mermaid": "标准.mermaid类",
        "pre.mermaid": "预格式化mermaid",
        "[data-component-name='mermaid-container']": "LangChain mermaid容器",
        "[data-component-name*='mermaid']": "包含mermaid的data-component-name",
        "code[type='mermaid']": "mermaid类型的code元素",
        "div[class*='mermaid']": "包含mermaid的div类",
        "script[src*='mermaid']": "mermaid脚本",
        "[id*='mermaid']": "包含mermaid的id",
        ".diagram": "通用图表类",
        ".chart": "图表类",
        "[data-diagram]": "图表数据属性",
        "[data-chart]": "图表数据属性"
    }
    
    found_elements = []
    
    for selector, description in selectors.items():
        elements = soup.select(selector)
        if elements:
            found_elements.append((selector, description, len(elements)))
            print(f"   ✓ {description}: {len(elements)} 个元素")
            
            # 显示前几个元素的详细信息
            for i, elem in enumerate(elements[:3]):
                print(f"     元素 {i+1}:")
                print(f"       标签: {elem.name}")
                print(f"       类: {elem.get('class', [])}")
                print(f"       ID: {elem.get('id', 'None')}")
                print(f"       属性: {dict(elem.attrs)}")
                content = elem.get_text(strip=True)
                if content:
                    print(f"       内容: {content[:100]}{'...' if len(content) > 100 else ''}")
                print()
    
    if not found_elements:
        print("   ❌ 未找到任何Mermaid相关元素")
    
    # 检查是否有可能的图表占位符或容器
    print(f"\n   === 可能的图表容器分析 ===")
    
    # 查找可能包含图表的空容器
    empty_divs = soup.find_all("div", class_=True)
    chart_candidates = []
    
    for div in empty_divs:
        classes = " ".join(div.get("class", []))
        if any(keyword in classes.lower() for keyword in ["chart", "diagram", "graph", "visual", "flow"]):
            chart_candidates.append(div)
    
    if chart_candidates:
        print(f"   发现 {len(chart_candidates)} 个可能的图表容器:")
        for i, div in enumerate(chart_candidates[:5]):
            print(f"     容器 {i+1}: {div.get('class', [])} - 内容长度: {len(div.get_text(strip=True))}")
    else:
        print("   未找到可能的图表容器")

if __name__ == "__main__":
    analyze_langchain_mermaid()