#!/usr/bin/env python3
"""
使用 Playwright 测试 Mermaid 图表解析器
动态渲染页面，解析 mermaid 图表
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
import json


async def parse_mermaid_from_page(page):
    """从渲染后的页面解析 mermaid 图表"""

    # 等待 mermaid 渲染完成
    await page.wait_for_selector("svg.flowchart", timeout=30000)
    await asyncio.sleep(2)  # 额外等待确保完全渲染

    # 获取页面 HTML
    html = await page.content()

    # 解析 SVG 图表
    soup = BeautifulSoup(html, "lxml")
    graphs = []

    for svg in soup.find_all("svg", class_="flowchart"):
        graph = {
            "id": svg.get("id", "unknown"),
            "nodes": {},
            "edges": [],
            "clusters": {},
        }

        # 解析节点
        for g in svg.select("g.nodes g.node"):
            raw_id = g.get("id", "")
            m = re.search(r"flowchart-([A-Za-z0-9_]+)-", raw_id)
            if not m:
                continue
            node_id = m.group(1)

            # 获取标签
            label_el = g.select_one(".nodeLabel p, .nodeLabel span")
            label = label_el.get_text(strip=True) if label_el else ""

            # 获取类型
            cls = g.get("class", [])
            node_type = next(
                (
                    c
                    for c in cls
                    if c
                    in ("startend", "process", "decision", "subroutine", "inputoutput")
                ),
                "unknown",
            )

            graph["nodes"][node_id] = {
                "id": node_id,
                "label": label,
                "type": node_type,
                "cluster": None,
            }

        # 解析边
        for path in svg.select("g.edgePaths path"):
            edge_id = path.get("id", "")
            if edge_id.startswith("L_"):
                parts = edge_id.split("_")
                if len(parts) >= 3:
                    _, src, dst = parts[0], parts[1], parts[2]
                    graph["edges"].append({"from": src, "to": dst, "label": None})

        if graph["nodes"] or graph["edges"]:
            graphs.append(graph)

    return graphs


async def test_mermaid_url(url: str, timeout: int = 60000):
    """测试 URL 的 mermaid 图表"""

    print(f"\n{'=' * 60}")
    print(f"测试 URL: {url}")
    print(f"{'=' * 60}")

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        # 监听控制台消息
        console_messages = []
        page.on(
            "console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}")
        )

        try:
            # 导航到页面 - 使用 domcontentloaded 而不是 networkidle
            print(f"\n📡 正在导航到页面...")
            try:
                response = await page.goto(
                    url, wait_until="domcontentloaded", timeout=timeout
                )
                print(
                    f"📊 页面响应状态: {response.status if response else 'No response'}"
                )
            except Exception as e:
                print(f"⚠️  导航异常: {e}")
                # 尝试继续执行
                pass

            # 等待页面稳定
            await asyncio.sleep(5)

            # 检查当前 URL
            current_url = page.url
            print(f"🔗 当前 URL: {current_url}")

            # 检查是否有 mermaid 图表
            mermaid_count = await page.locator("pre.mermaid, svg.flowchart").count()
            print(f"📊 找到 {mermaid_count} 个 mermaid 元素")

            # 打印控制台消息
            if console_messages:
                print(f"\n💬 控制台消息 ({len(console_messages)} 条):")
                for msg in console_messages[:5]:
                    print(f"   {msg}")
                if len(console_messages) > 5:
                    print(f"   ... 还有 {len(console_messages) - 5} 条")

            # 如果没找到，尝试查找其他格式
            if mermaid_count == 0:
                print(f"\n🔍 查找其他 mermaid 格式...")
                # 查找 mermaid 代码块
                mermaid_divs = await page.locator("[class*='mermaid']").count()
                print(f"   包含 mermaid 类的元素: {mermaid_divs}")

                # 查找 SVG
                svg_count = await page.locator("svg").count()
                print(f"   SVG 元素总数: {svg_count}")

                # 查找特定模式
                flowchart = await page.locator(".flowchart").count()
                print(f"   flowchart 类: {flowchart}")

            # 尝试解析
            print(f"\n🔍 正在解析 mermaid 图表...")
            graphs = await parse_mermaid_from_page(page)

            # 打印结果
            if graphs:
                print(f"\n✅ 成功解析 {len(graphs)} 个图表!")

                for i, graph in enumerate(graphs, 1):
                    print(f"\n图表 {i}:")
                    print(f"  ID: {graph['id']}")
                    print(f"  节点数: {len(graph['nodes'])}")
                    print(f"  边数: {len(graph['edges'])}")

                    if graph["nodes"]:
                        print(f"\n  节点详情:")
                        for nid, node in list(graph["nodes"].items())[:10]:
                            label = node.get("label", "")[:30]
                            print(f"    - {nid}: {label} ({node['type']})")
                        if len(graph["nodes"]) > 10:
                            print(f"    ... 还有 {len(graph['nodes']) - 10} 个节点")

                    if graph["edges"]:
                        print(f"\n  边详情:")
                        for edge in graph["edges"][:10]:
                            print(f"    - {edge['from']} → {edge['to']}")
                        if len(graph["edges"]) > 10:
                            print(f"    ... 还有 {len(graph['edges']) - 10} 条边")

                    # 保存为 JSON
                    filename = f"mermaid_graph_{i}.json"
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(graph, f, ensure_ascii=False, indent=2)
                    print(f"\n  💾 已保存到: {filename}")
            else:
                print("\n❌ 未找到 SVG 格式的 mermaid 图表")

                # 检查是否以 <pre class="mermaid"> 形式存在
                pre_mermaid = await page.locator("pre.mermaid").count()
                if pre_mermaid > 0:
                    print(f"\n📝 找到 {pre_mermaid} 个 <pre class='mermaid'> 代码块")
                    print("这些需要使用 mermaid-js 渲染器来解析")

                    # 尝试获取代码块内容
                    for i in range(min(pre_mermaid, 3)):
                        code = await page.locator("pre.mermaid").nth(i).inner_text()
                        print(f"\n代码块 {i + 1}:")
                        print("-" * 40)
                        print(code[:500])
                        if len(code) > 500:
                            print("... (截断)")

            return graphs

        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback

            traceback.print_exc()
            return []

        finally:
            await browser.close()


async def main():
    """主函数"""
    print("🔍 使用 Playwright 测试 Mermaid 图表解析器")
    print("\n该测试将:")
    print("1. 使用 Playwright 渲染页面（支持 JavaScript）")
    print("2. 等待 Mermaid 图表渲染完成")
    print("3. 解析 SVG 格式的图表")
    print("4. 提取节点、边、标签信息")

    # 测试 URL
    url = "https://docs.langchain.com/oss/python/langchain/retrieval"

    graphs = await test_mermaid_url(url)

    # 总结
    print(f"\n{'=' * 60}")
    print("测试总结")
    print(f"{'=' * 60}")

    if graphs:
        print(f"✅ 成功解析 {len(graphs)} 个 mermaid 图表")
        print("\n📊 图表已保存为 JSON 文件:")
        for i in range(1, len(graphs) + 1):
            print(f"   - mermaid_graph_{i}.json")
    else:
        print("❌ 未找到可解析的 mermaid 图表")
        print("\n💡 可能的原因:")
        print("   1. 页面使用 <pre class='mermaid'> 代码块，需要 mermaid-js 渲染")
        print("   2. 页面没有 mermaid 图表")
        print("   3. 需要登录或特殊权限才能访问")


if __name__ == "__main__":
    asyncio.run(main())
