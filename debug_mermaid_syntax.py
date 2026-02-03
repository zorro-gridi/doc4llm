#!/usr/bin/env python3
"""
调试 Mermaid 语法错误
"""

from doc4llm.convertor.MermaidParser import MermaidParser
from bs4 import BeautifulSoup

# Playwright 导入（可选依赖）
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def debug_mermaid_syntax():
    """调试Mermaid语法问题"""
    
    print("=== 调试 Mermaid 语法错误 ===\n")
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright不可用")
        return
    
    url = "https://docs.langchain.com/oss/python/langchain/retrieval"
    
    # 获取动态渲染的HTML
    print("1. 获取LangChain页面内容...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                ignore_https_errors=True
            )
            page = context.new_page()
            page.set_default_timeout(30000)
            
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)  # 等待Mermaid渲染
            
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
    
    # 查找SVG元素
    svg_elements = soup.find_all("svg", class_="flowchart")
    print(f"\n2. 发现 {len(svg_elements)} 个SVG flowchart元素")
    
    if not svg_elements:
        print("   没有找到SVG元素，检查其他可能的结构...")
        
        # 检查.mermaid容器
        mermaid_divs = soup.find_all("div", class_="mermaid")
        print(f"   .mermaid容器: {len(mermaid_divs)} 个")
        
        # 检查LangChain容器
        langchain_containers = soup.find_all(attrs={"data-component-name": "mermaid-container"})
        print(f"   LangChain容器: {len(langchain_containers)} 个")
        
        if langchain_containers:
            print("   分析第一个LangChain容器:")
            container = langchain_containers[0]
            print(f"     容器类: {container.get('class', [])}")
            print(f"     容器内容长度: {len(container.get_text(strip=True))}")
            
            # 查找内部SVG
            inner_svgs = container.find_all("svg")
            print(f"     内部SVG: {len(inner_svgs)} 个")
            
            if inner_svgs:
                svg = inner_svgs[0]
                print(f"     SVG类: {svg.get('class', [])}")
                print(f"     SVG ID: {svg.get('id', 'None')}")
                
                # 分析SVG结构
                analyze_svg_structure(svg)
                
                # 尝试解析
                print("\n3. 尝试解析SVG...")
                graph = mermaid_parser.parse_single_graph(svg)
                
                if graph:
                    print(f"   ✅ 解析成功: {len(graph['nodes'])} 个节点, {len(graph['edges'])} 条边")
                    
                    # 显示节点详情
                    print("\n   节点详情:")
                    for node_id, node_data in graph['nodes'].items():
                        print(f"     {node_id}: '{node_data['label']}'")
                    
                    # 显示边详情
                    print("\n   边详情:")
                    for edge in graph['edges']:
                        label_str = f" ('{edge['label']}')" if edge['label'] else ""
                        print(f"     {edge['from']} -> {edge['to']}{label_str}")
                    
                    # 生成Mermaid代码
                    print("\n4. 生成的Mermaid代码:")
                    mermaid_code = mermaid_parser.graph_to_mermaid_code(graph)
                    print("=" * 50)
                    print(mermaid_code)
                    print("=" * 50)
                    
                    # 检查语法问题
                    print("\n5. 语法检查:")
                    check_mermaid_syntax(mermaid_code)
                    
                else:
                    print("   ❌ 解析失败")
        
        return
    
    # 如果找到了SVG元素
    for i, svg in enumerate(svg_elements[:2]):  # 只分析前2个
        print(f"\n=== 分析SVG {i+1} ===")
        print(f"SVG ID: {svg.get('id', 'None')}")
        
        # 分析SVG结构
        analyze_svg_structure(svg)
        
        # 尝试解析
        print(f"\n解析SVG {i+1}...")
        graph = mermaid_parser.parse_single_graph(svg)
        
        if graph:
            print(f"✅ 解析成功: {len(graph['nodes'])} 个节点, {len(graph['edges'])} 条边")
            
            # 显示节点详情
            print("\n节点详情:")
            for node_id, node_data in graph['nodes'].items():
                print(f"  {node_id}: '{node_data['label']}'")
            
            # 显示边详情
            print("\n边详情:")
            for edge in graph['edges']:
                label_str = f" ('{edge['label']}')" if edge['label'] else ""
                print(f"  {edge['from']} -> {edge['to']}{label_str}")
            
            # 生成Mermaid代码
            print(f"\n生成的Mermaid代码 {i+1}:")
            mermaid_code = mermaid_parser.graph_to_mermaid_code(graph)
            print("=" * 50)
            print(mermaid_code)
            print("=" * 50)
            
            # 检查语法问题
            print(f"\n语法检查 {i+1}:")
            check_mermaid_syntax(mermaid_code)
            
        else:
            print("❌ 解析失败")

def analyze_svg_structure(svg):
    """分析SVG结构"""
    print("   SVG结构分析:")
    
    # 查找所有g元素
    g_elements = svg.find_all("g")
    print(f"     总g元素: {len(g_elements)} 个")
    
    # 查找包含文本的g元素
    text_g_elements = []
    for g in g_elements:
        text_content = g.get_text(strip=True)
        if text_content and len(text_content) < 200:  # 过滤太长的文本
            text_g_elements.append((g, text_content))
    
    print(f"     包含文本的g元素: {len(text_g_elements)} 个")
    
    # 显示前几个文本元素
    for i, (g, text) in enumerate(text_g_elements[:5]):
        print(f"       g{i+1}: ID='{g.get('id', 'None')}' 文本='{text[:50]}...'")
    
    # 查找path元素
    paths = svg.find_all("path")
    print(f"     path元素: {len(paths)} 个")
    
    if paths:
        for i, path in enumerate(paths[:3]):
            print(f"       path{i+1}: ID='{path.get('id', 'None')}'")

def check_mermaid_syntax(mermaid_code):
    """检查Mermaid语法问题"""
    lines = mermaid_code.split('\n')
    
    issues = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # 检查常见语法问题
        
        # 1. 检查节点定义中的特殊字符
        if '[' in line and ']' in line:
            # 节点定义
            if '["' in line and '"]' in line:
                # 检查引号内的内容
                import re
                matches = re.findall(r'\["([^"]+)"\]', line)
                for match in matches:
                    if any(char in match for char in ['(', ')', '[', ']', '{', '}', '-->', '<--']):
                        issues.append(f"行 {i+1}: 节点标签包含特殊字符: '{match}'")
        
        # 2. 检查箭头语法
        if '-->' in line:
            # 检查箭头前后的节点ID
            parts = line.split('-->')
            if len(parts) == 2:
                left = parts[0].strip()
                right = parts[1].strip()
                
                # 检查节点ID是否包含空格或特殊字符
                if ' ' in left.split()[-1]:
                    issues.append(f"行 {i+1}: 左节点ID包含空格: '{left}'")
                if ' ' in right.split()[0]:
                    issues.append(f"行 {i+1}: 右节点ID包含空格: '{right}'")
        
        # 3. 检查缩进
        if line.startswith('    ') and not line.startswith('        '):
            # 正确的缩进
            pass
        elif line.startswith('flowchart'):
            # 图表声明
            pass
        elif line.strip() and not line.startswith(' '):
            issues.append(f"行 {i+1}: 缺少缩进: '{line}'")
    
    if issues:
        print("   发现语法问题:")
        for issue in issues:
            print(f"     ❌ {issue}")
    else:
        print("   ✅ 未发现明显语法问题")
    
    # 检查整体结构
    if not mermaid_code.strip().startswith('flowchart'):
        print("   ❌ 缺少flowchart声明")
    
    node_count = mermaid_code.count('[')
    arrow_count = mermaid_code.count('-->')
    print(f"   统计: {node_count} 个节点定义, {arrow_count} 个箭头连接")

if __name__ == "__main__":
    debug_mermaid_syntax()