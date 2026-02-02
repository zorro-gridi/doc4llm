"""
DocMeta Utils - 文档来源元数据构造工具模块

Features:
    - 从 sections 列表构建 document metadata
    - 从 docContent.md 读取原文链接
    - 支持 headings anchor 输出
"""

from typing import Any, Dict, List


def read_source_url_from_doc_content(local_path: str) -> str:
    """从 docContent.md 文件读取原文链接。

    Args:
        local_path: docContent.md 文件路径

    Returns:
        原文链接 URL，失败返回空字符串
    """
    try:
        with open(local_path, "r", encoding="utf-8") as f:
            for line in f:
                if "> **原文链接**:" in line or "原文链接:" in line:
                    return (
                        line.replace("> **原文链接**:", "")
                        .replace("原文链接:", "")
                        .strip()
                    )
    except Exception:
        pass
    return ""


def build_doc_metas_from_sections(
    sections: List[Dict[str, Any]],
    base_dir: str,
) -> List[Dict[str, Any]]:
    """从 sections 列表构建 document metadata。

    Args:
        sections: Reader API 输出的 sections 列表
        base_dir: 知识库根目录

    Returns:
        doc_metas 列表
    """
    doc_metas = []
    for section in sections:
        title = section.get("title", "")
        doc_set = section.get("doc_set", "")
        headings = section.get("headings", [])

        # 构造 local_path: <base_dir>/<doc_set>/<title>/docContent.md
        local_path = f"{base_dir}/{doc_set}/{title}/docContent.md"

        # 读取 source_url
        source_url = read_source_url_from_doc_content(local_path)

        doc_metas.append({
            "title": title,
            "doc_set": doc_set,
            "source_url": source_url,
            "local_path": local_path,
            "headings": headings,  # 保留 headings 用于 anchor 输出
        })

    return doc_metas


def build_sources_section(doc_metas: List[Dict[str, Any]]) -> str:
    """构建文档来源 (Sources) Markdown 区块。

    Args:
        doc_metas: doc_metas 列表

    Returns:
        Markdown 格式的 Sources 区块
    """
    sources_section = ""
    for doc_meta in doc_metas:
        title = doc_meta.get("title", "")
        source_url = doc_meta.get("source_url", "")
        local_path = doc_meta.get("local_path", "")
        headings = doc_meta.get("headings", [])

        sources_section += f"- **{title}**\n"
        sources_section += f"   - 原文链接: {source_url}\n"

        # heading anchors
        for heading in headings:
            anchor_url = f"{source_url}#{heading}" if source_url else ""
            sources_section += f"   - #{heading}: {anchor_url}\n"

        sources_section += f"   - 本地文档: `{local_path}`\n\n"

    return f"---\n\n### 文档来源 (Sources)\n\n{sources_section}"


def build_doc_metas_from_results(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从 search/rerank results 构建 document metadata（兼容旧接口）。

    用于 Phase 1/1.5 停止时的返回结果，此时尚无 sections 数据。

    Args:
        results: Search results from DocSearcherAPI or reranked results

    Returns:
        List of document metadata dictionaries
    """
    doc_metas = []
    for page in results.get("results", []):
        doc_set = page.get("doc_set", "")
        page_title = page.get("page_title", "")

        # Extract toc_path for source tracking
        toc_path = page.get("toc_path", "")

        # Fallback: 如果 toc_path 为空，尝试从 page_title 推断
        if not toc_path:
            toc_path = f"{doc_set}/{page_title}/docTOC.md"

        # Build local_path and source_url
        local_path = ""
        source_url = ""
        if toc_path:
            # local_path points to docContent.md
            local_path = toc_path.replace("/docTOC.md", "/docContent.md")
            # Extract original URL from docContent.md
            source_url = read_source_url_from_doc_content(local_path)

        headings = page.get("headings", [])
        heading_texts = [h.get("text", "") for h in headings if h.get("text")]

        doc_metas.append(
            {
                "title": page_title,
                "doc_set": doc_set,
                "source_url": source_url,
                "local_path": local_path,
                "headings": heading_texts,
            }
        )

    return doc_metas


__all__ = [
    "read_source_url_from_doc_content",
    "build_doc_metas_from_sections",
    "build_doc_metas_from_results",
    "build_sources_section",
]
