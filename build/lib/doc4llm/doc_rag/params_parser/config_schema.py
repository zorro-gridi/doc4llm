"""
Config Schema Definitions for Doc-RAG Pipeline Phases

This module defines the input/output schemas for each phase in the doc-rag workflow.
"""

from typing import Any, Dict, List, Optional


# =============================================================================
# Phase 0a: md-doc-query-optimizer Output Schema
# =============================================================================

SCHEMA_PHASE_0A_OUTPUT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "query_analysis": {
            "type": "object",
            "properties": {
                "doc_set": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Target documentation sets to search"
                },
                "domain_nouns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domain-specific nouns extracted from query"
                },
                "predicate_verbs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Action verbs extracted from query"
                }
            },
            "required": ["doc_set"]
        },
        "optimized_queries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rank": {"type": "integer", "description": "Query ranking"},
                    "query": {"type": "string", "description": "Optimized query text"},
                    "strategy": {
                        "type": "string",
                        "enum": ["translation", "expansion", "entity_extraction", "original"]
                    }
                },
                "required": ["rank", "query"]
            }
        }
    },
    "required": ["query_analysis", "optimized_queries"]
}


# =============================================================================
# Phase 0b: md-doc-query-router Output Schema
# =============================================================================

SCHEMA_PHASE_0B_OUTPUT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "scene": {
            "type": "string",
            "enum": ["fact_lookup", "tutorial", "api_reference", "troubleshooting"],
            "description": "Query scene/type classification"
        },
        "reranker_threshold": {
            "type": "number",
            "description": "Threshold for LLM reranking (default: 0.63)"
        },
        "reranker_enabled": {
            "type": "boolean",
            "description": "Whether LLM reranking is enabled"
        },
        "confidence": {
            "type": "number",
            "description": "Classification confidence score"
        }
    },
    "required": ["scene", "reranker_threshold"]
}


# =============================================================================
# Phase 1: md-doc-searcher Output Schema
# =============================================================================

SCHEMA_PHASE_1_OUTPUT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "total_hits": {"type": "integer"},
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "doc_set": {"type": "string"},
                    "file_path": {"type": "string"},
                    "page_title": {"type": "string"},
                    "headings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "level": {"type": "integer"},
                                "text": {"type": "string"},
                                "score": {"type": "number"},
                                "rerank_sim": {
                                    "type": "number",
                                    "description": "LLM reranking similarity (None if not reranked)"
                                }
                            }
                        }
                    }
                }
            }
        },
        "search_stats": {
            "type": "object",
            "properties": {
                "query_time_ms": {"type": "number"},
                "total_docs_searched": {"type": "integer"}
            }
        }
    },
    "required": ["success", "results"]
}


# =============================================================================
# Phase 1.5: md-doc-llm-reranker Output Schema
# =============================================================================

SCHEMA_PHASE_1_5_OUTPUT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "toc_fallback": {"type": "boolean"},
        "grep_fallback": {"type": "boolean"},
        "query": {
            "type": "array",
            "items": {"type": "string"}
        },
        "doc_sets_found": {
            "type": "array",
            "items": {"type": "string"}
        },
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "doc_set": {"type": "string"},
                    "toc_path": {"type": "string"},
                    "page_title": {"type": "string"},
                    "headings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "level": {"type": "integer"},
                                "text": {"type": "string"},
                                "rerank_sim": {
                                    "type": ["number", "null"],
                                    "description": "LLM reranking similarity"
                                },
                                "bm25_sim": {
                                    "type": ["number", "null"],
                                    "description": "BM25 similarity score"
                                }
                            }
                        }
                    },
                    "bm25_sim": {
                        "type": ["number", "null"],
                        "description": "BM25 similarity score"
                    },
                    "rerank_sim": {
                        "type": ["number", "null"],
                        "description": "Result-level rerank similarity"
                    }
                }
            }
        },
        "fallback_used": {"type": "string"},
        "message": {"type": "string"}
    },
    "required": ["success", "results"]
}


# =============================================================================
# Phase 2: md-doc-reader Output Schema
# =============================================================================

SCHEMA_PHASE_2_OUTPUT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "contents": {
            "type": "object",
            "description": "Map of doc_set -> list of heading contents"
        },
        "total_line_count": {"type": "integer"},
        "page_count": {"type": "integer"},
        "requires_processing": {
            "type": "boolean",
            "description": "Whether content needs further processing"
        },
        "page_titles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "headings": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "doc_set": {"type": "string"}
                }
            }
        },
        "metadata": {
            "type": "object",
            "description": "Reader metadata"
        }
    },
    "required": ["success", "contents", "total_line_count"]
}


# =============================================================================
# Phase 1: md-doc-searcher Input Schema (CLI config format)
# =============================================================================

SCHEMA_PHASE_1_INPUT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Search queries"
        },
        "base_dir": {
            "type": "string",
            "description": "Base directory for documentation"
        },
        "doc_sets": {
            "type": "string",
            "description": "Comma-separated list of doc sets"
        },
        "reranker": {
            "type": "boolean",
            "description": "Enable reranker (disable for Phase 1.5)"
        },
        "reranker_threshold": {
            "type": "number",
            "description": "Reranking threshold"
        },
        "domain_nouns": {
            "type": "array",
            "items": {"type": "string"}
        },
        "predicate_verbs": {
            "type": "array",
            "items": {"type": "string"}
        },
        "json": {
            "type": "boolean",
            "description": "Output JSON format"
        }
    },
    "required": ["query", "base_dir", "doc_sets"]
}


# =============================================================================
# Phase 2: md-doc-reader Input Schema (CLI config format)
# =============================================================================

SCHEMA_PHASE_2_INPUT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "page_titles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "headings": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "doc_set": {"type": "string"}
                }
            }
        },
        "with_metadata": {"type": "boolean"},
        "format": {
            "type": "string",
            "enum": ["json", "text"]
        }
    },
    "required": ["page_titles"]
}


# =============================================================================
# Schema Registry
# =============================================================================

PHASE_SCHEMAS = {
    "0a_output": SCHEMA_PHASE_0A_OUTPUT,
    "0b_output": SCHEMA_PHASE_0B_OUTPUT,
    "1_input": SCHEMA_PHASE_1_INPUT,
    "1_output": SCHEMA_PHASE_1_OUTPUT,
    "1.5_output": SCHEMA_PHASE_1_5_OUTPUT,
    "2_input": SCHEMA_PHASE_2_INPUT,
    "2_output": SCHEMA_PHASE_2_OUTPUT,
}


def validate_schema(data: dict, schema: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate data against a schema.

    Args:
        data: Data to validate
        schema: JSON schema dict

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Basic type validation
    if "type" in schema:
        if schema["type"] == "object" and not isinstance(data, dict):
            errors.append(f"Expected object, got {type(data).__name__}")
            return False, errors

        if schema["type"] == "array" and not isinstance(data, list):
            errors.append(f"Expected array, got {type(data).__name__}")
            return False, errors

    # Check required fields
    if "required" in schema and isinstance(data, dict):
        for field in schema["required"]:
            if field not in data:
                errors.append(f"Missing required field: {field}")

    # Validate properties
    if "properties" in schema and isinstance(data, dict):
        for prop_name, prop_schema in schema["properties"].items():
            if prop_name in data:
                prop_data = data[prop_name]
                is_valid, prop_errors = validate_schema(prop_data, prop_schema)
                errors.extend(prop_errors)

    return len(errors) == 0, errors


def get_schema(phase: str, io_type: str) -> Optional[Dict[str, Any]]:
    """
    Get schema for a specific phase and I/O type.

    Args:
        phase: Phase identifier (e.g., "0a", "1", "1.5")
        io_type: "input" or "output"

    Returns:
        Schema dict or None if not found
    """
    key = f"{phase}_{io_type}"
    return PHASE_SCHEMAS.get(key)
