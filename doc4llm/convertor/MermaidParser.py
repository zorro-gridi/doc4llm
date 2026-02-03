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
                (c for c in cls if c in self.NODE_TYPE_MAP.keys()), "unknown"
            )

            graph["nodes"][node_id] = {
                "id": node_id,
                "label": label,
                "type": node_type,
                "cluster": None,
            }

        # -------- Edges --------
        # Mermaid SVG 中 edgeLabels 和 edgePaths 按相同顺序排列
        edge_labels = []
        label_elements = svg.select("g.edgeLabels g.edgeLabel")
        for lbl in label_elements:
            text_el = lbl.select_one("span.edgeLabel")
            text = text_el.get_text(strip=True) if text_el else ""
            edge_labels.append(text)

        edge_paths = svg.select("g.edgePaths path")
        for i, path in enumerate(edge_paths):
            edge_id = path.get("id", "")
            if edge_id.startswith("L_"):
                parts = edge_id.split("_")
                if len(parts) >= 3:
                    _, src, dst = parts[0], parts[1], parts[2]
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
