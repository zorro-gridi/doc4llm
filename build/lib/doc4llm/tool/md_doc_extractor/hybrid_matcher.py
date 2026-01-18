"""
Hybrid Agentic Document Matcher

Fast rule-based matching with LLM fallback for semantic understanding.
"""
import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .agentic_matcher import (
    AgenticDocMatcher,
    ProgressiveRetriever,
    ReflectiveReRanker,
    MatchResult,
)
from .doc_extractor import MarkdownDocExtractor


@dataclass
class LLMEnhancement:
    """LLM 增强结果"""
    triggered: bool              # 是否触发了 LLM
    reason: str                  # 触发原因
    original_count: int          # 原始结果数量
    enhanced_count: int          # 增强后数量
    query_refinement: str = ""   # LLM 优化后的查询
    intent: str = ""             # LLM 识别的意图


class HybridMatcher:
    """
    混合文档匹配器

    策略：
    1. 优先使用快速规则匹配
    2. 评估结果质量
    3. 质量不足时触发 LLM 增强语义理解
    """

    def __init__(
        self,
        extractor: MarkdownDocExtractor,
        config: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        debug_mode: bool = False
    ):
        """
        初始化混合匹配器

        Args:
            extractor: 文档提取器
            config: 配置字典
            api_key: Anthropic API key (可选，默认从环境变量读取)
            debug_mode: 调试模式
        """
        self.extractor = extractor
        self.config = config or self._default_config()
        self.debug_mode = debug_mode

        # 快速匹配器（基于规则）
        self.rule_matcher = AgenticDocMatcher(
            extractor, config, debug_mode=debug_mode
        )

        # LLM API key
        self.api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
        self.llm_available = bool(self.api_key)

        if not self.llm_available:
            self._debug_print("Warning: No ANTHROPIC_AUTH_TOKEN found, LLM fallback disabled")

    def _default_config(self) -> Dict[str, Any]:
        return {
            # LLM 触发阈值
            "llm_trigger_min_results": 2,        # 最少结果数
            "llm_trigger_max_similarity": 0.7,   # 最高相似度阈值
            "llm_trigger_open_questions": [      # 开放性问题触发词
                "how", "how to", "why", "what is",
                "explain", "best way", "difference"
            ],

            # LLM 配置
            "llm_model": "claude-3-5-haiku-20241022",  # 使用 Haiku 降低成本
            "llm_max_tokens": 1024,
            "llm_temperature": 0.3,

            # 混合策略
            "llm_max_refinements": 2,          # 最多优化次数
            "llm_merge_results": True,         # 是否合并原始结果
        }

    def match(
        self,
        query: str,
        doc_set: Optional[str] = None,
        max_results: int = 10,
        force_llm: bool = False
    ) -> Dict[str, Any]:
        """
        执行混合匹配

        Args:
            query: 搜索查询
            doc_set: 文档集过滤
            max_results: 最大结果数
            force_llm: 强制使用 LLM（用于测试）

        Returns:
            {
                "results": List[Dict],      # 匹配结果
                "enhancement": LLMEnhancement,  # 增强信息
                "query": str,               # 最终使用的查询
            }
        """
        self._debug_print(f"\n{'='*60}")
        self._debug_print(f"Hybrid Matching: '{query}'")
        self._debug_print(f"{'='*60}")

        enhancement = LLMEnhancement(
            triggered=False,
            reason="",
            original_count=0,
            enhanced_count=0
        )

        # Phase 1: 快速规则匹配
        self._debug_print("\n[Phase 1] Fast Rule-Based Matching")
        rule_results = self.rule_matcher.match(
            query, doc_set, max_results=max_results
        )
        enhancement.original_count = len(rule_results)

        self._debug_print(f"  → Found {len(rule_results)} results")

        # Phase 2: 评估是否需要 LLM
        needs_llm = force_llm or self._should_trigger_llm(query, rule_results)

        if not needs_llm or not self.llm_available:
            self._debug_print("\n[Result] Rule-based results sufficient")
            return {
                "results": rule_results[:max_results],
                "enhancement": enhancement,
                "query": query
            }

        # Phase 3: LLM 增强匹配
        self._debug_print("\n[Phase 2] LLM Semantic Enhancement")
        enhancement.triggered = True
        enhancement.reason = self._get_trigger_reason(query, rule_results)

        # LLM 分析查询并生成优化策略
        llm_analysis = self._llm_analyze_query(query, rule_results)

        if self.debug_mode:
            self._debug_print(f"  LLM Intent: {llm_analysis.get('intent', 'unknown')}")
            self._debug_print(f"  Refined Query: {llm_analysis.get('refined_query', query)}")

        enhancement.intent = llm_analysis.get("intent", "")
        enhancement.query_refinement = llm_analysis.get("refined_query", query)

        # 使用优化后的查询执行额外搜索
        refined_query = llm_analysis.get("refined_query", query)
        search_terms = llm_analysis.get("search_terms", [refined_query])

        llm_results = []
        for term in search_terms[:self.config["llm_max_refinements"]]:
            self._debug_print(f"  → Searching with: '{term}'")
            term_results = self.rule_matcher.match(
                term, doc_set, max_results=max_results
            )
            llm_results.extend(term_results)

        # 合并和去重
        if self.config["llm_merge_results"]:
            enhanced_results = self._merge_results(rule_results, llm_results)
        else:
            enhanced_results = llm_results

        enhancement.enhanced_count = len(enhanced_results)

        self._debug_print(f"\n[Result] Enhanced to {len(enhanced_results)} results")

        return {
            "results": enhanced_results[:max_results],
            "enhancement": enhancement,
            "query": refined_query if enhancement.triggered else query
        }

    def _should_trigger_llm(self, query: str, results: List[Dict]) -> bool:
        """判断是否需要触发 LLM 增强"""

        # 条件 1: 结果数量不足
        if len(results) < self.config["llm_trigger_min_results"]:
            return True

        # 条件 2: 结果质量不足（最高相似度低）
        max_sim = max((r.get("similarity", 0) for r in results), default=0)
        if max_sim < self.config["llm_trigger_max_similarity"]:
            return True

        # 条件 3: 查询包含开放性问题关键词
        query_lower = query.lower()
        open_question_triggers = self.config["llm_trigger_open_questions"]
        if any(trigger in query_lower for trigger in open_question_triggers):
            return True

        return False

    def _get_trigger_reason(self, query: str, results: List[Dict]) -> str:
        """获取触发 LLM 的原因（用于日志）"""
        reasons = []

        if len(results) < self.config["llm_trigger_min_results"]:
            reasons.append(f"insufficient_results ({len(results)} < {self.config['llm_trigger_min_results']})")

        max_sim = max((r.get("similarity", 0) for r in results), default=0)
        if max_sim < self.config["llm_trigger_max_similarity"]:
            reasons.append(f"low_similarity ({max_sim:.2f} < {self.config['llm_trigger_max_similarity']})")

        query_lower = query.lower()
        for trigger in self.config["llm_trigger_open_questions"]:
            if trigger in query_lower:
                reasons.append(f"open_question ('{trigger}')")
                break

        return "; ".join(reasons) if reasons else "forced"

    def _llm_analyze_query(
        self,
        query: str,
        current_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        LLM 分析查询并生成优化策略

        返回:
        {
            "intent": "tutorial|api_reference|troubleshooting|...",
            "refined_query": "优化后的查询",
            "search_terms": ["term1", "term2"],
            "expected_sections": ["section1", "section2"],
            "reasoning": "分析过程"
        }
        """
        results_summary = self._format_results_summary(current_results)

        prompt = f"""Analyze this search query and suggest improvements.

Query: "{query}"

Current Results (unsatisfactory):
{results_summary}

Your task:
1. Identify the USER'S INTENT:
   - "tutorial" - User wants to learn how to do something
   - "api_reference" - User wants API details or syntax
   - "troubleshooting" - User has a problem to solve
   - "concept" - User wants to understand something
   - "comparison" - User wants to compare things
   - "configuration" - User wants setup/config help

2. Generate a REFINED QUERY that would work better for document search

3. Suggest 2-3 alternative SEARCH TERMS that might find relevant documents

4. Identify which DOCUMENT SECTIONS would most likely contain the answer

Respond ONLY in JSON format:
{{
    "intent": "tutorial|api_reference|troubleshooting|concept|comparison|configuration",
    "refined_query": "better search query",
    "search_terms": ["term1", "term2", "term3"],
    "expected_sections": ["section1", "section2"],
    "reasoning": "brief explanation"
}}"""

        try:
            response = self._call_claude(prompt)
            analysis = json.loads(response)

            # 验证并补全缺失字段
            if "refined_query" not in analysis or not analysis["refined_query"]:
                analysis["refined_query"] = query
            if "search_terms" not in analysis or not analysis["search_terms"]:
                analysis["search_terms"] = [query]
            if "intent" not in analysis:
                analysis["intent"] = "unknown"

            return analysis

        except Exception as e:
            self._debug_print(f"  LLM analysis failed: {e}")
            # 返回默认值
            return {
                "intent": "unknown",
                "refined_query": query,
                "search_terms": [query],
                "expected_sections": [],
                "reasoning": f"LLM error: {str(e)}"
            }

    def _format_results_summary(self, results: List[Dict]) -> str:
        """格式化结果摘要供 LLM 分析"""
        if not results:
            return "No results found."

        summary = f"Found {len(results)} result(s):\n"
        for r in results[:5]:
            sim = r.get("similarity", 0)
            source = r.get("source", "unknown")
            title = r.get("title", "")
            summary += f"  - {title} (similarity: {sim:.2f}, source: {source})\n"

        return summary

    def _merge_results(
        self,
        original: List[Dict],
        enhanced: List[Dict]
    ) -> List[Dict]:
        """
        合并原始结果和增强结果，去重并保持最优

        策略：同一文档取相似度最高的版本
        """
        seen_titles = {}
        merged = []

        for result in original + enhanced:
            title = result.get("title", "")
            if not title:
                continue

            if title not in seen_titles:
                seen_titles[title] = result
                merged.append(result)
            else:
                # 保留相似度更高的
                existing = seen_titles[title]
                if result.get("similarity", 0) > existing.get("similarity", 0):
                    # 替换
                    idx = merged.index(existing)
                    merged[idx] = result
                    seen_titles[title] = result

        # 按相似度排序
        merged.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        return merged

    def _call_claude(self, prompt: str) -> str:
        """调用 Claude API"""
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=self.api_key)

            message = client.messages.create(
                model=self.config["llm_model"],
                max_tokens=self.config["llm_max_tokens"],
                temperature=self.config["llm_temperature"],
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # 提取文本内容
            # message.content 是一个 ContentBlock 列表，我们需要找到 TextBlock
            content = message.content

            # 方法 1: 遍历所有 blocks，找到 text 类型的
            for block in content:
                block_type = getattr(block, 'type', None)
                if block_type == 'text':
                    # TextBlock 有 text 属性
                    return getattr(block, 'text', '')

            # 方法 2: 如果只有一个 block 且是 text 类型
            if len(content) == 1 and getattr(content[0], 'type', None) == 'text':
                return getattr(content[0], 'text', '')

            # 方法 3: 兜底 - 转换为字符串
            return str(content[0]) if content else ''

        except ImportError:
            self._debug_print("  Error: anthropic package not installed")
            raise
        except Exception as e:
            self._debug_print(f"  API Error: {e}")
            raise

    def _debug_print(self, msg: str):
        if self.debug_mode:
            print(f"[HybridMatcher] {msg}")


# 便捷函数
def hybrid_search(
    query: str,
    base_dir: str = "md_docs",
    api_key: Optional[str] = None,
    max_results: int = 10,
    debug_mode: bool = False
) -> Dict[str, Any]:
    """
    便捷的混合搜索函数

    Args:
        query: 搜索查询
        base_dir: 文档目录
        api_key: Anthropic API key（可选）
        max_results: 最大结果数
        debug_mode: 调试模式

    Returns:
        {
            "results": List[Dict],
            "enhancement": LLMEnhancement,
            "query": str
        }

    Example:
        >>> result = hybrid_search("how to use skills")
        >>> print(f"Found {len(result['results'])} results")
        >>> if result['enhancement'].triggered:
        ...     print(f"LLM enhanced: {result['enhancement'].intent}")
    """
    extractor = MarkdownDocExtractor(base_dir=base_dir)
    matcher = HybridMatcher(
        extractor,
        api_key=api_key,
        debug_mode=debug_mode
    )
    return matcher.match(query, max_results=max_results)
