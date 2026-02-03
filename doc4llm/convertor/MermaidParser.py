"""
Mermaid 图表解析器
从 HTML 中解析 mermaid 图表并转换为 Markdown 格式
"""

import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional


class MermaidParser:
    """
    Mermaid 图表解析器类

    功能：
    1. 从 HTML 中解析 mermaid SVG 图表
    2. 从 <pre class="mermaid"> 或 <div class="mermaid"><code type="mermaid"> 提取源码
    3. 将 SVG 转换为 mermaid 代码块格式
    4. 支持嵌入到 Markdown 文档中
    """

    # 节点类型到 Mermaid 形状的映射
    NODE_TYPE_MAP = {
        "startend": ("(", ")"),  # 圆角矩形（开始/结束）
        "process": ("[", "]"),  # 矩形
        "decision": ("{", "}"),  # 菱形
        "subroutine": ("[[", "]]"),  # 子程序（圆柱形）
        "inputoutput": ("[/", "/]"),  # I/O
        "unknown": ("[", "]"),  # 默认矩形
    }

    def __init__(self):
        """初始化 Mermaid 解析器"""
        pass

    def escape_mermaid_text(self, text: str) -> str:
        """
        转义 Mermaid 特殊字符

        Args:
            text: 原始文本

        Returns:
            str: 转义后的文本
        """
        if not text:
            return ""
        # 转义引号
        text = text.replace('"', '\\"')
        # 转义方括号（Mermaid 语法中的特殊字符）
        text = text.replace("[", "&#91;")
        text = text.replace("]", "&#93;")
        return text

    def format_node(self, node_id: str, node_data: Dict) -> str:
        """
        格式化单个节点为 Mermaid 语法

        Args:
            node_id: 节点 ID
            node_data: 节点数据字典

        Returns:
            str: Mermaid 节点语法
        """
        label = self.escape_mermaid_text(node_data.get("label", node_id))
        node_type = node_data.get("type", "unknown")

        prefix, suffix = self.NODE_TYPE_MAP.get(node_type, ("[", "]"))

        return f'{node_id}{prefix}"{label}"{suffix}'

    def format_edge(self, edge: Dict) -> str:
        """
        格式化边为 Mermaid 语法

        Args:
            edge: 边数据字典

        Returns:
            str: Mermaid 边语法
        """
        src = edge.get("from", "")
        dst = edge.get("to", "")
        label = edge.get("label")

        if label:
            label_str = f' -- "{self.escape_mermaid_text(label)}" --> '
        else:
            label_str = " --> "

        return f"{src}{label_str}{dst}"

    def parse_single_graph(self, svg) -> Optional[Dict]:
        """
        解析单个 SVG 图表

        Args:
            svg: BeautifulSoup SVG 元素

        Returns:
            Dict: 解析后的图表数据，或 None（如果无效）
        """
        graph = {"id": svg.get("id", "graph"), "nodes": {}, "edges": [], "clusters": {}}

        # 解析节点 - 支持多种SVG结构
        node_elements = []
        
        # 方式1: 标准Mermaid结构 g.nodes g.node
        node_elements.extend(svg.select("g.nodes g.node"))
        
        # 方式2: 直接查找所有g元素中包含文本的（LangChain可能的结构）
        if not node_elements:
            all_g_elements = svg.select("g")
            for g in all_g_elements:
                # 如果g元素包含文本内容，可能是节点
                text_content = g.get_text(strip=True)
                if text_content and len(text_content) > 0 and len(text_content) < 200:
                    # 排除太长的文本（可能是整个图表的文本）
                    node_elements.append(g)

        for i, g in enumerate(node_elements):
            raw_id = g.get("id", "")
            
            # 尝试多种ID模式
            node_id = None
            
            # 模式1: 标准flowchart模式
            m = re.search(r"flowchart-([A-Za-z0-9_]+)-", raw_id)
            if m:
                node_id = m.group(1)
            
            # 模式2: 其他可能的模式
            elif raw_id:
                # 使用完整ID或生成简化ID
                node_id = raw_id.replace("-", "_")[:20]  # 限制长度
            else:
                # 生成默认ID
                node_id = f"node_{i}"

            # 获取标签 - 支持多种标签结构
            label = ""
            
            # 方式1: 标准nodeLabel
            label_el = g.select_one(".nodeLabel p, .nodeLabel span, .nodeLabel")
            if label_el:
                label = label_el.get_text(strip=True)
            
            # 方式2: 直接查找text元素
            if not label:
                text_elements = g.select("text")
                if text_elements:
                    # 取最长的文本作为标签
                    texts = [t.get_text(strip=True) for t in text_elements]
                    texts = [t for t in texts if t]  # 过滤空文本
                    if texts:
                        label = max(texts, key=len)
            
            # 方式3: 使用g元素的直接文本内容
            if not label:
                label = g.get_text(strip=True)
            
            # 清理标签
            if label:
                # 移除换行符和多余空格
                label = re.sub(r'\s+', ' ', label).strip()
                # 限制长度
                if len(label) > 100:
                    label = label[:97] + "..."

            # 获取类型
            cls = g.get("class", [])
            node_type = next(
                (c for c in cls if c in self.NODE_TYPE_MAP.keys()), "unknown"
            )

            if node_id and label:  # 只有当有ID和标签时才添加节点
                graph["nodes"][node_id] = {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "cluster": None,
                }

        # -------- Edges --------
        # 支持多种边结构
        edge_labels = []
        
        # 方式1: 标准edgeLabels结构
        label_elements = svg.select("g.edgeLabels g.edgeLabel")
        for lbl in label_elements:
            text_el = lbl.select_one("span.edgeLabel")
            text = text_el.get_text(strip=True) if text_el else ""
            edge_labels.append(text)

        # 方式2: 查找所有可能的边路径
        edge_paths = svg.select("g.edgePaths path, path")
        
        # 如果没有找到标准结构，尝试从节点推断连接
        if not edge_paths and len(graph["nodes"]) > 1:
            # 简单的线性连接（适用于流程图）
            node_ids = list(graph["nodes"].keys())
            for i in range(len(node_ids) - 1):
                graph["edges"].append({
                    "from": node_ids[i], 
                    "to": node_ids[i + 1], 
                    "label": None
                })
        else:
            # 解析实际的路径
            for i, path in enumerate(edge_paths):
                edge_id = path.get("id", "")
                
                # 尝试多种边ID模式
                src, dst = None, None
                
                # 模式1: L_src_dst
                if edge_id.startswith("L_"):
                    parts = edge_id.split("_")
                    if len(parts) >= 3:
                        src, dst = parts[1], parts[2]
                
                # 模式2: 其他可能的模式
                elif "-" in edge_id:
                    # 尝试从ID中提取源和目标
                    parts = edge_id.split("-")
                    if len(parts) >= 2:
                        src, dst = parts[0], parts[1]
                
                # 如果找到了源和目标
                if src and dst:
                    # 确保源和目标节点存在
                    if src in graph["nodes"] and dst in graph["nodes"]:
                        label = edge_labels[i] if i < len(edge_labels) else None
                        graph["edges"].append(
                            {"from": src, "to": dst, "label": label if label else None}
                        )

        return graph if graph["nodes"] or graph["edges"] else None

    def parse_mermaid_source(self, source_code: str) -> str:
        """
        解析 mermaid 源码，处理转义字符

        Args:
            source_code: 原始 mermaid 源码

        Returns:
            str: 清理后的 mermaid 源码
        """
        if not source_code:
            return ""
        # 清理源码
        code = source_code.strip()
        # 处理常见的 HTML 转义
        code = code.replace("\\n", "\n")
        code = code.replace("&lt;", "<")
        code = code.replace("&gt;", ">")
        code = code.replace("&amp;", "&")
        code = code.replace("\\/", "/")
        # 处理换行符（HTML 中可能是 \n 或 <br>）
        code = code.replace("<br>", "\n")
        code = code.replace("<br/>", "\n")
        code = code.replace('\\"', '"')
        return code

    def extract_mermaid_from_pre_code_blocks(self, html: str) -> List[str]:
        """
        从 <pre class="mermaid"> 或 <code type="mermaid"> 提取 mermaid 源码

        Args:
            html: HTML 内容字符串

        Returns:
            List[str]: mermaid 源码列表
        """
        soup = BeautifulSoup(html, "html.parser")
        sources = []

        # 方式1: <pre class="mermaid">
        for pre in soup.find_all("pre", class_="mermaid"):
            code = pre.find("code")
            if code:
                text = code.get_text(strip=True)
            else:
                text = pre.get_text(strip=True)
            source = self.parse_mermaid_source(text)
            if source and "flowchart" in source.lower() or "graph" in source.lower():
                sources.append(source)

        # 方式2: <div class="mermaid"><code type="mermaid"> (LangChain 格式)
        for div in soup.find_all("div", class_="mermaid"):
            code = div.find("code", type="mermaid")
            if code:
                text = code.get_text(strip=True)
                source = self.parse_mermaid_source(text)
                if source:
                    sources.append(source)
            else:
                # 尝试直接获取 div 内容
                text = div.get_text(strip=True)
                source = self.parse_mermaid_source(text)
                if source and (
                    "flowchart" in source.lower() or "graph" in source.lower()
                ):
                    sources.append(source)

        return sources

    def parse_graphs_from_html(self, html: str) -> List[Dict]:
        """
        从 HTML 中解析所有 mermaid 图表

        Args:
            html: HTML 内容字符串

        Returns:
            List[Dict]: 解析出的图表列表
        """
        soup = BeautifulSoup(html, "html.parser")
        graphs = []

        # 查找所有 flowchart SVG
        for svg in soup.find_all("svg", class_="flowchart"):
            graph = self.parse_single_graph(svg)
            if graph:
                graphs.append(graph)

        return graphs

    def graph_to_mermaid_code(self, graph: Dict) -> str:
        """
        将图表数据转换为 Mermaid 代码

        Args:
            graph: 图表数据字典

        Returns:
            str: Mermaid 代码块
        """
        nodes = graph.get("nodes", {})
        edges = graph.get("edges", [])
        clusters = graph.get("clusters", {})

        lines = ["flowchart TB"]

        # 添加不在集群中的节点
        unclustered_nodes = []
        for node_id, node_data in nodes.items():
            cluster = node_data.get("cluster")
            if cluster is None:
                unclustered_nodes.append((node_id, node_data))

        for node_id, node_data in unclustered_nodes:
            lines.append(f"    {self.format_node(node_id, node_data)}")

        # 添加边
        for edge in edges:
            lines.append(f"    {self.format_edge(edge)}")

        # 添加集群/子图
        if clusters:
            for cluster_id, cluster_data in clusters.items():
                label = self.escape_mermaid_text(cluster_data.get("label", cluster_id))
                cluster_nodes = cluster_data.get("nodes", [])

                lines.append(f"subgraph {cluster_id}['{label}']")
                for node_id in cluster_nodes:
                    if node_id in nodes:
                        lines.append(f"    {self.format_node(node_id, nodes[node_id])}")
                lines.append("end")

        return "\n".join(lines)

    def extract_and_convert_mermaid_blocks(self, html_content: str) -> str:
        """
        从 HTML 中提取 mermaid 图表并转换为 Markdown 格式

        支持三种格式：
        1. SVG 格式: <svg class="flowchart">...
        2. 预渲染源码: <pre class="mermaid">...
        3. LangChain 格式: <div class="mermaid"><code type="mermaid">...

        Args:
            html_content: HTML 内容字符串

        Returns:
            str: 包含 mermaid 代码块的 Markdown 内容
        """
        mermaid_blocks = []
        total_count = 0

        # 方式1: 从 SVG 格式解析
        graphs = self.parse_graphs_from_html(html_content)
        for graph in graphs:
            code = self.graph_to_mermaid_code(graph)
            mermaid_blocks.append(f"\n```mermaid\n{code}\n```\n")
            total_count += 1

        # 方式2: 从源码格式解析 (pre.mermaid, div.mermaid code[type=mermaid])
        source_codes = self.extract_mermaid_from_pre_code_blocks(html_content)
        for source in source_codes:
            mermaid_blocks.append(f"\n```mermaid\n{source}\n```\n")
            total_count += 1

        if not mermaid_blocks:
            return ""

        result = f"\n\n## Mermaid 图表（共 {total_count} 个）\n\n"
        result += "\n".join(mermaid_blocks)

        return result

    def replace_mermaid_with_placeholders(self, html_content: str) -> tuple[str, dict]:
        """
        将 HTML 中的 mermaid 元素替换为占位符，并返回映射关系

        Args:
            html_content: HTML 内容字符串

        Returns:
            tuple: (替换后的HTML, {placeholder_id: mermaid_code})
        """
        soup = BeautifulSoup(html_content, "html.parser")
        mermaid_map = {}
        placeholder_counter = 0
        processed_elements = set()  # 跟踪已处理的元素，避免重复处理

        print(f"[DEBUG] 开始处理Mermaid元素替换...")

        # 处理 SVG flowchart 元素（优先级最高，这些是真正渲染的图表）
        svg_elements = soup.find_all("svg", class_="flowchart")
        print(f"[DEBUG] 找到 {len(svg_elements)} 个SVG flowchart元素")
        
        for svg in svg_elements:
            graph = self.parse_single_graph(svg)
            if graph and (graph.get("nodes") or graph.get("edges")):  # 确保图表有内容
                code = self.graph_to_mermaid_code(graph)
                if code and len(code.strip()) > 20:  # 确保生成的代码有意义
                    placeholder_id = f"MERMAID_PLACEHOLDER_{placeholder_counter}"
                    mermaid_code = f"\n```mermaid\n{code}\n```\n"
                    mermaid_map[placeholder_id] = mermaid_code
                    
                    # 创建占位符元素
                    placeholder = soup.new_tag("div", attrs={"data-mermaid-placeholder": placeholder_id})
                    placeholder.string = f"[{placeholder_id}]"
                    
                    # 记录父元素，避免重复处理
                    parent = svg.parent
                    if parent:
                        processed_elements.add(id(parent))
                    
                    svg.replace_with(placeholder)
                    placeholder_counter += 1
                    print(f"[DEBUG] 创建SVG占位符: {placeholder_id}")
                else:
                    print(f"[DEBUG] 跳过空的SVG图表")
            else:
                print(f"[DEBUG] 跳过无效的SVG图表")

        # 处理 LangChain 格式的 mermaid 容器（优先级第二）
        langchain_containers = soup.find_all(attrs={"data-component-name": "mermaid-container"})
        print(f"[DEBUG] 找到 {len(langchain_containers)} 个LangChain mermaid容器")
        
        for container in langchain_containers:
            # 跳过已处理的元素
            if id(container) in processed_elements:
                print(f"[DEBUG] 跳过已处理的LangChain容器")
                continue
                
            # 检查容器是否包含SVG（如果包含，说明已经被上面处理过了）
            if container.find("svg", class_="flowchart"):
                print(f"[DEBUG] LangChain容器包含SVG，跳过")
                processed_elements.add(id(container))
                continue
            
            # 尝试从容器中提取 mermaid 源码
            text_content = container.get_text(strip=True)
            if text_content and len(text_content) > 10:  # 确保有足够的内容
                source = self.parse_mermaid_source(text_content)
                if source and ("flowchart" in source.lower() or "graph" in source.lower()):
                    placeholder_id = f"MERMAID_PLACEHOLDER_{placeholder_counter}"
                    mermaid_code = f"\n```mermaid\n{source}\n```\n"
                    mermaid_map[placeholder_id] = mermaid_code
                    
                    # 创建占位符元素
                    placeholder = soup.new_tag("div", attrs={"data-mermaid-placeholder": placeholder_id})
                    placeholder.string = f"[{placeholder_id}]"
                    container.replace_with(placeholder)
                    placeholder_counter += 1
                    processed_elements.add(id(container))
                    print(f"[DEBUG] 创建LangChain容器占位符: {placeholder_id}")
                else:
                    print(f"[DEBUG] LangChain容器无有效mermaid源码: {text_content[:50]}...")
            else:
                print(f"[DEBUG] LangChain容器内容为空或太短")

        # 处理 .mermaid 类元素（优先级最低，避免重复处理）
        mermaid_elements = soup.find_all(class_="mermaid")
        print(f"[DEBUG] 找到 {len(mermaid_elements)} 个.mermaid类元素")
        
        for mermaid_elem in mermaid_elements:
            # 跳过已处理的元素
            if id(mermaid_elem) in processed_elements:
                print(f"[DEBUG] 跳过已处理的.mermaid元素")
                continue
                
            # 检查是否包含SVG（如果包含，说明已经被上面处理过了）
            if mermaid_elem.find("svg", class_="flowchart"):
                print(f"[DEBUG] .mermaid元素包含SVG，跳过")
                continue
            
            # 检查是否包含源码
            code_elem = mermaid_elem.find("code", type="mermaid")
            if code_elem:
                source = self.parse_mermaid_source(code_elem.get_text(strip=True))
            else:
                text_content = mermaid_elem.get_text(strip=True)
                if len(text_content) < 10:  # 内容太短，可能是空容器
                    print(f"[DEBUG] .mermaid元素内容太短，跳过: {text_content}")
                    continue
                source = self.parse_mermaid_source(text_content)
            
            if source and ("flowchart" in source.lower() or "graph" in source.lower()):
                placeholder_id = f"MERMAID_PLACEHOLDER_{placeholder_counter}"
                mermaid_code = f"\n```mermaid\n{source}\n```\n"
                mermaid_map[placeholder_id] = mermaid_code
                
                # 创建占位符元素
                placeholder = soup.new_tag("div", attrs={"data-mermaid-placeholder": placeholder_id})
                placeholder.string = f"[{placeholder_id}]"
                mermaid_elem.replace_with(placeholder)
                placeholder_counter += 1
                print(f"[DEBUG] 创建.mermaid元素占位符: {placeholder_id}")
            else:
                print(f"[DEBUG] .mermaid元素无有效源码，跳过")

        print(f"[DEBUG] 总共创建了 {len(mermaid_map)} 个有效的Mermaid占位符")
        for pid, code in mermaid_map.items():
            print(f"[DEBUG] {pid}: {len(code)} 字符")

        return str(soup), mermaid_map

    def restore_mermaid_in_markdown(self, markdown_content: str, mermaid_map: dict) -> str:
        """
        在 Markdown 内容中恢复 mermaid 图表到原始位置

        Args:
            markdown_content: Markdown 内容
            mermaid_map: 占位符到 mermaid 代码的映射

        Returns:
            str: 恢复后的 Markdown 内容
        """
        if not mermaid_map:
            print("[DEBUG] 没有Mermaid映射，跳过替换")
            return markdown_content
            
        print(f"[DEBUG] 开始替换 {len(mermaid_map)} 个Mermaid占位符")
        original_content = markdown_content
        
        for placeholder_id, mermaid_code in mermaid_map.items():
            print(f"[DEBUG] 处理占位符: {placeholder_id}")
            print(f"[DEBUG] Mermaid代码长度: {len(mermaid_code)} 字符")
            
            # 尝试多种占位符格式
            patterns_to_try = [
                f"[{placeholder_id}]",           # 标准格式
                f"`[{placeholder_id}]`",         # 可能被转义为代码
                f"\\[{placeholder_id}\\]",       # 可能被转义
                placeholder_id,                   # 纯ID
                f"```mermaid\n[{placeholder_id}]\n```",  # 可能已经在代码块中
            ]
            
            replaced = False
            for pattern in patterns_to_try:
                if pattern in markdown_content:
                    print(f"[DEBUG] 找到匹配模式: {pattern}")
                    markdown_content = markdown_content.replace(pattern, mermaid_code)
                    replaced = True
                    break
            
            # 如果都没找到，尝试正则表达式匹配
            if not replaced:
                import re
                # 查找任何包含placeholder_id的行
                pattern = re.compile(f".*{re.escape(placeholder_id)}.*", re.MULTILINE)
                matches = pattern.findall(markdown_content)
                if matches:
                    print(f"[DEBUG] 正则匹配找到: {matches}")
                    # 替换找到的第一个匹配
                    markdown_content = pattern.sub(mermaid_code, markdown_content, count=1)
                    replaced = True
                else:
                    print(f"[DEBUG] 未找到占位符 {placeholder_id} 的任何匹配")
                    # 显示markdown内容的前几行用于调试
                    lines = markdown_content.split('\n')[:10]
                    print(f"[DEBUG] Markdown前10行:")
                    for i, line in enumerate(lines):
                        print(f"[DEBUG]   {i+1}: {line}")
            
            if replaced:
                print(f"[DEBUG] 成功替换占位符: {placeholder_id}")
            else:
                print(f"[DEBUG] 失败：未能替换占位符: {placeholder_id}")
        
        final_placeholder_count = sum(1 for pid in mermaid_map.keys() if f"[{pid}]" in markdown_content)
        print(f"[DEBUG] 替换完成，剩余占位符: {final_placeholder_count} 个")
        
        return markdown_content

    def replace_svg_with_mermaid(self, html_content: str) -> str:
        """
        将 HTML 中的 mermaid SVG 替换为 mermaid 代码块

        Args:
            html_content: HTML 内容字符串

        Returns:
            str: 替换后的 HTML 内容
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # 查找并替换所有 flowchart SVG
        replacement_count = 0
        for svg in soup.find_all("svg", class_="flowchart"):
            graph = self.parse_single_graph(svg)
            if graph:
                code = self.graph_to_mermaid_code(graph)
                mermaid_code = f"\n```mermaid\n{code}\n```\n"

                # 创建新的代码块元素
                code_block = soup.new_tag("div", attrs={"class": "mermaid-code-block"})
                code_block.string = mermaid_code

                # 替换 SVG
                svg.replace_with(code_block)
                replacement_count += 1

        if replacement_count > 0:
            return str(soup)

        return html_content
