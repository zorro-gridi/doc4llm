"""
Pytest configuration and fixtures for doc_rag tests.

Provides shared fixtures for testing the complete RAG retrieval pipeline.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

import pytest
import dotenv

# Add parent directories to path for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "doc4llm"))


@pytest.fixture(scope="session")
def env_setup():
    """Load environment variables from .env file for LLM API access."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        dotenv.load_dotenv(str(env_path))

    missing_keys = []
    if not os.environ.get("ANTHROPIC_API_KEY"):
        missing_keys.append("ANTHROPIC_API_KEY")

    if missing_keys:
        pytest.skip(
            f"Missing required environment variables: {', '.join(missing_keys)}. "
            "Please set them in doc4llm/.env file."
        )

    yield


@pytest.fixture
def sample_queries() -> List[str]:
    """Provide a list of sample queries for testing different scenarios."""
    return [
        "如何创建 OpenCode skills?",
        "doc4llm 支持哪些功能?",
        "how to create skills in opencode",
        "what is agentic matcher",
    ]


@pytest.fixture
def simple_query() -> str:
    """A simple query for quick tests."""
    return "如何创建 skills?"


@pytest.fixture
def mock_search_results() -> Dict[str, Any]:
    """Mock search results for unit testing reranker and extractor."""
    return {
        "success": True,
        "query": ["how to create skills", "opencode skills setup"],
        "doc_sets_found": ["OpenCode_Docs@latest"],
        "results": [
            {
                "doc_set": "OpenCode_Docs@latest",
                "page_title": "Agent Skills",
                "toc_path": "doc4llm/md_docs/OpenCode_Docs@latest/Agent Skills/docTOC.md",
                "headings": [
                    {
                        "text": "Create a Skill",
                        "level": 2,
                        "score": 0.65,
                        "bm25_sim": 0.65,
                        "is_basic": True,
                        "is_precision": False,
                        "rerank_sim": None,
                    },
                    {
                        "text": "Configure Skills",
                        "level": 2,
                        "score": 0.58,
                        "bm25_sim": 0.58,
                        "is_basic": True,
                        "is_precision": False,
                        "rerank_sim": None,
                    },
                    {
                        "text": "Skill Configuration Reference",
                        "level": 3,
                        "score": 0.52,
                        "bm25_sim": 0.52,
                        "is_basic": True,
                        "is_precision": False,
                        "rerank_sim": None,
                    },
                ],
                "heading_count": 3,
                "precision_count": 0,
                "score": 0.65,
                "is_basic": True,
                "is_precision": False,
            },
            {
                "doc_set": "OpenCode_Docs@latest",
                "page_title": "Skill Configuration",
                "toc_path": "doc4llm/md_docs/OpenCode_Docs@latest/Skill Configuration/docTOC.md",
                "headings": [
                    {
                        "text": "Skill Hooks",
                        "level": 2,
                        "score": 0.45,
                        "bm25_sim": 0.45,
                        "is_basic": False,
                        "is_precision": False,
                        "rerank_sim": None,
                    },
                ],
                "heading_count": 1,
                "precision_count": 0,
                "score": 0.45,
                "is_basic": False,
                "is_precision": False,
            },
        ],
    }


@pytest.fixture
def mock_reranked_results() -> Dict[str, Any]:
    """Mock reranked results for testing downstream phases."""
    return {
        "success": True,
        "query": ["how to create skills"],
        "doc_sets_found": ["OpenCode_Docs@latest"],
        "results": [
            {
                "doc_set": "OpenCode_Docs@latest",
                "page_title": "Agent Skills",
                "toc_path": "doc4llm/md_docs/OpenCode_Docs@latest/Agent Skills/docTOC.md",
                "headings": [
                    {
                        "text": "Create a Skill",
                        "level": 2,
                        "rerank_sim": 0.82,
                        "bm25_sim": 0.65,
                        "is_basic": True,
                        "is_precision": True,
                    },
                    {
                        "text": "Configure Skills",
                        "level": 2,
                        "rerank_sim": 0.75,
                        "bm25_sim": 0.58,
                        "is_basic": True,
                        "is_precision": False,
                    },
                ],
            },
        ],
    }


@pytest.fixture
def mock_extraction_sections() -> Dict[str, str]:
    """Mock extracted content sections for testing SceneOutput."""
    return {
        "Create a Skill": """## Create a Skill

### Overview
Skills are the core building blocks of OpenCode's agentic capabilities.

### Creating Your First Skill

1. Define the skill in a YAML file
2. Configure the skill metadata
3. Register the skill with the system

```yaml
name: my_skill
description: A custom skill for specific tasks
version: 1.0.0
```
""",
        "Configure Skills": """## Configure Skills

### Configuration Options

Skills can be configured through:
- YAML configuration files
- Environment variables
- Runtime API calls

### Best Practices

1. Use descriptive names
2. Set appropriate permissions
3. Monitor skill performance
""",
    }


@pytest.fixture
def mock_doc_metas() -> List[Dict[str, Any]]:
    """Mock document metadata for SceneOutput."""
    return [
        {
            "title": "Agent Skills",
            "doc_set": "OpenCode_Docs@latest",
            "source_url": "https://docs.opencode.ai/agent-skills",
            "local_path": "doc4llm/md_docs/OpenCode_Docs@latest/Agent Skills/docTOC.md",
            "headings": ["Create a Skill", "Configure Skills"],
        },
    ]


@pytest.fixture
def kb_base_dir() -> Path:
    """Knowledge base base directory."""
    kb_path = Path(__file__).resolve().parent.parent.parent.parent / "doc4llm" / "md_docs"
    if not kb_path.exists():
        pytest.skip(f"Knowledge base directory not found: {kb_path}")
    return kb_path


@pytest.fixture
def knowledge_base_path() -> str:
    """Path to knowledge_base.json file."""
    kb_json = Path(__file__).resolve().parent.parent.parent.parent / "knowledge_base.json"
    if not kb_json.exists():
        pytest.skip(f"knowledge_base.json not found: {kb_json}")
    return str(kb_json)


@pytest.fixture
def valid_scenes() -> List[str]:
    """List of valid query scenes."""
    return [
        "fact_lookup",
        "faithful_reference",
        "faithful_how_to",
        "concept_learning",
        "how_to",
        "comparison",
        "exploration",
    ]


def count_headings_in_results(results: Dict[str, Any]) -> int:
    """Helper function to count total headings in search results."""
    count = 0
    for page in results.get("results", []):
        count += len(page.get("headings", []))
    return count


def extract_heading_texts(results: Dict[str, Any]) -> List[str]:
    """Helper function to extract all heading texts from results."""
    texts = []
    for page in results.get("results", []):
        for h in page.get("headings", []):
            if isinstance(h, dict) and "text" in h:
                texts.append(h["text"])
    return texts
