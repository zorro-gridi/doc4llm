#!/usr/bin/env python3
"""
将解析的 Mermaid JSON 图表渲染回 Mermaid 语法格式
"""

import json
from typing import Dict, List, Optional


# 节点类型到 Mermaid 形状的映射
NODE_TYPE_MAP = {
    "startend": ("[", "]"),  # 矩形（圆角）
    "process": ("[", "]"),  # 矩形
    "decision": ("{", "}"),  # 菱形
    "subroutine": ("[[", "]]"),  # 圆柱形（子程序）
    "inputoutput": ("[", "]"),  # I/O
    "unknown": ("[", "]"),  # 默认矩形
}


def escape_mermaid_text(text: str) -> str:
    """转义 Mermaid 特殊字符"""
    if not text:
        return ""
    # 转义引号和特殊字符
    text = text.replace('"', '\\"')
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("[", "&#91;")
    text = text.replace("]", "&#93;")
    return text


def format_node(node_id: str, node_data: Dict) -> str:
    """格式化单个节点为 Mermaid 语法"""
    label = escape_mermaid_text(node_data.get("label", node_id))
    node_type = node_data.get("type", "unknown")

    prefix, suffix = NODE_TYPE_MAP.get(node_type, ("[", "]"))

    return f'{node_id}{prefix}"{label}"{suffix}'


def format_edge(edge: Dict) -> str:
    """格式化边为 Mermaid 语法"""
    src = edge.get("from", "")
    dst = edge.get("to", "")
    label = edge.get("label")

    if label:
        label_str = f' -- "{escape_mermaid_text(label)}" --> '
    else:
        label_str = " --> "

    return f"{src}{label_str}{dst}"


def format_cluster(cluster_id: str, cluster_data: Dict, all_nodes: Dict) -> str:
    """格式化集群/子图为 Mermaid 语法"""
    label = escape_mermaid_text(cluster_data.get("label", cluster_id))
    nodes = cluster_data.get("nodes", [])

    lines = [f"subgraph {cluster_id}['{label}']"]

    # 添加节点
    for node_id in nodes:
        if node_id in all_nodes:
            lines.append(f"    {format_node(node_id, all_nodes[node_id])}")

    lines.append("end")

    return "\n".join(lines)


def json_to_mermaid(graph: Dict, graph_id: Optional[str] = None) -> str:
    """
    将 JSON 图表转换为 Mermaid 语法

    Args:
        graph: JSON 图表数据
        graph_id: 可选的图表 ID

    Returns:
        Mermaid 语法字符串
    """
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", [])
    clusters = graph.get("clusters", {})

    lines = []

    # 图表定义开头
    if graph_id:
        lines.append(f"flowchart {graph_id}")
    else:
        lines.append("flowchart TB")  # 默认从上到下

    lines.append("")

    # 先添加不在集群中的节点
    unclustered_nodes = []
    for node_id, node_data in nodes.items():
        cluster = node_data.get("cluster")
        if cluster is None:
            unclustered_nodes.append((node_id, node_data))

    for node_id, node_data in unclustered_nodes:
        lines.append(f"    {format_node(node_id, node_data)}")

    # 添加边
    lines.append("")
    for edge in edges:
        lines.append(f"    {format_edge(edge)}")

    # 添加集群/子图
    if clusters:
        lines.append("")
        for cluster_id, cluster_data in clusters.items():
            lines.append(format_cluster(cluster_id, cluster_data, nodes))

    return "\n".join(lines)


def save_mermaid(graph: Dict, output_file: str, graph_id: Optional[str] = None):
    """保存 Mermaid 图表到文件"""
    mermaid_code = json_to_mermaid(graph, graph_id)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(mermaid_code)

    return mermaid_code


def render_graphs_from_json_files(json_files: List[str], output_dir: str = "."):
    """从多个 JSON 文件渲染 Mermaid 图表"""
    import os

    os.makedirs(output_dir, exist_ok=True)

    results = []

    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            graph = json.load(f)

        # 生成 Mermaid 文件名
        base_name = json_file.replace(".json", "")
        mermaid_file = f"{output_dir}/{base_name}.mmd"

        # 保存
        mermaid_code = save_mermaid(graph, mermaid_file)

        results.append(
            {
                "json_file": json_file,
                "mermaid_file": mermaid_file,
                "graph_id": graph.get("id"),
                "node_count": len(graph.get("nodes", {})),
                "edge_count": len(graph.get("edges", [])),
                "code": mermaid_code,
            }
        )

    return results


# 示例使用
if __name__ == "__main__":
    # 示例图表
    sample_graph = {
        "id": "example-flow",
        "nodes": {
            "A": {"id": "A", "label": "User Question", "type": "startend"},
            "B": {"id": "B", "label": "Retrieve Documents", "type": "process"},
            "C": {"id": "C", "label": "Generate Answer", "type": "process"},
            "D": {"id": "D", "label": "Enough Info?", "type": "decision"},
        },
        "edges": [
            {"from": "A", "to": "B", "label": None},
            {"from": "B", "to": "D", "label": None},
            {"from": "D", "to": "C", "label": "Yes"},
            {"from": "D", "to": "B", "label": "No"},
        ],
        "clusters": {},
    }

    # 转换为 Mermaid
    mermaid_code = json_to_mermaid(sample_graph)

    print("=" * 60)
    print("JSON 转 Mermaid 示例")
    print("=" * 60)
    print("\n📄 JSON 输入:")
    print(json.dumps(sample_graph, indent=2, ensure_ascii=False))

    print("\n📊 Mermaid 输出:")
    print(mermaid_code)

    # 保存到文件
    with open("example_flowchart.mmd", "w", encoding="utf-8") as f:
        f.write(mermaid_code)

    print(f"\n💾 已保存到: example_flowchart.mmd")
