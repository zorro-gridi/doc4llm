#!/usr/bin/env python3
"""测试 LangChain 页面上的 mermaid 图表结构"""

import asyncio
from playwright.async_api import async_playwright


async def analyze_mermaid_page():
    url = "https://docs.langchain.com/oss/python/langchain/retrieval"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(proxy={"server": "http://127.0.0.1:7890"})
        page = await context.new_page()

print(f"🔗 正在访问: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # 等待页面加载
        await page.wait_for_timeout(5000)

        # 检查 mermaid 相关元素
        print("\n" + "=" * 60)
        print("🔍 查找 mermaid 相关元素")
        print("=" * 60)

        # 1. 查找 <pre class='mermaid'>
        pre_mermaid = await page.query_selector_all("pre.mermaid")
        print(f"\n1. <pre class='mermaid'> 数量: {len(pre_mermaid)}")
        for i, el in enumerate(pre_mermaid):
            html = await el.inner_html()
            text = await el.inner_text()
            print(f"   [{i}] HTML长度: {len(html)}, 文本长度: {len(text)}")
            print(f"       文本前100字符: {text[:100]}...")

        # 2. 查找 <svg class='flowchart'>
        svg_flowchart = await page.query_selector_all("svg.flowchart")
        print(f"\n2. <svg class='flowchart'> 数量: {len(svg_flowchart)}")
        for i, el in enumerate(svg_flowchart):
            outer_html = await el.evaluate("el => el.outerHTML")
            print(f"   [{i}] SVG HTML长度: {len(outer_html)}")
            print(f"       前200字符: {outer_html[:200]}...")

        # 3. 查找 [data-component-name='mermaid-container']
        mermaid_containers = await page.query_selector_all(
            "[data-component-name='mermaid-container']"
        )
        print(
            f"\n3. [data-component-name='mermaid-container'] 数量: {len(mermaid_containers)}"
        )
        for i, el in enumerate(mermaid_containers):
            html = await el.inner_html()
            class_attr = await el.get_attribute("class")
            print(f"   [{i}] HTML长度: {len(html)}, class: {class_attr}")
            print(f"       内容前200字符: {html[:200]}...")

        # 4. 查找 .mermaid 类元素
        mermaid_class = await page.query_selector_all(".mermaid")
        print(f"\n4. .mermaid 类元素数量: {len(mermaid_class)}")
        for i, el in enumerate(mermaid_class):
            html = await el.inner_html()
            tag = await el.evaluate("el => el.tagName")
            class_attr = await el.get_attribute("class")
            print(f"   [{i}] 标签: {tag}, class: {class_attr}, HTML长度: {len(html)}")
            print(f"       内容前200字符: {html[:200]}...")

        # 5. 查找任意包含 mermaid 的元素
        all_mermaid = await page.evaluate("""
            () => {
                const results = [];
                // 所有带 mermaid 类的元素
                document.querySelectorAll('[class*="mermaid"]').forEach(el => {
                    results.push({
                        tag: el.tagName,
                        class: el.className,
                        html: el.innerHTML.substring(0, 500),
                        id: el.id
                    });
                });
                return results;
            }
        """)
        print(f"\n5. 所有 [class*='mermaid'] 元素: {len(all_mermaid)}")
        for i, el in enumerate(all_mermaid):
            print(f"   [{i}] 标签: {el['tag']}, id: {el['id']}")
            print(f"       class: {el['class']}")
            print(f"       内容前200字符: {el['html'][:200]}...")

        # 6. 检查页面是否有 mermaid.js
        has_mermaid_js = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[src*="mermaid"]');
                const mermaidEl = document.querySelector('.mermaid');
                return {
                    mermaidScripts: scripts.length,
                    hasMermaidElement: !!mermaidEl,
                    windowMermaid: typeof window.mermaid !== 'undefined'
                };
            }
        """)
        print(f"\n6. Mermaid.js 检查:")
        print(f"   - mermaid 脚本数量: {has_mermaid_js['mermaidScripts']}")
        print(f"   - .mermaid 元素存在: {has_mermaid_js['hasMermaidElement']}")
        print(f"   - window.mermaid 存在: {has_mermaid_js['windowMermaid']}")

        await browser.close()
        print("\n" + "=" * 60)
        print("✅ 分析完成")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(analyze_mermaid_page())
