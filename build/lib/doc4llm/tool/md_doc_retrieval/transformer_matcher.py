"""
Transformer-based semantic matcher using HuggingFace embeddings.

Provides language detection and model selection for Chinese/English text.
Uses BAAI/bge-large-zh-v1.5 for Chinese and BAAI/bge-large-en-v1.5 for English.

Example:
    >>> from doc4llm.tool.md_doc_retrieval import TransformerMatcher, TransformerConfig
    >>> matcher = TransformerMatcher()
    >>> results = matcher.rerank("查询文本", ["候选1", "候选2", "候选3"])
    >>> for text, score in results:
    ...     print(f"{score:.4f} | {text}")
"""

import os
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

import dotenv
import numpy as np
from huggingface_hub import InferenceClient


@dataclass
class TransformerConfig:
    """Configuration for transformer-based semantic matching.

    Attributes:
        model_zh: Chinese model ID (default: BAAI/bge-large-zh-v1.5)
        model_en: English model ID (default: BAAI/bge-large-en-v1.5)
        api_key_env: Environment variable name for HuggingFace API key
        env_path: Path to .env file containing HF_KEY
        device: Device to use ("cpu" or "cuda")
        batch_size: Batch size for embedding computation
        lang_threshold: Ratio of Chinese characters to trigger Chinese model (0-1)
    """
    model_zh: str = "BAAI/bge-large-zh-v1.5"
    model_en: str = "BAAI/bge-large-en-v1.5"
    api_key_env: str = "HF_KEY"
    env_path: str = "doc4llm/.env"
    device: str = "cpu"
    batch_size: int = 32
    lang_threshold: float = 0.9  # >=90% Chinese chars -> use zh model


class TransformerMatcher:
    """Transformer-based semantic matcher with language auto-detection.

    Uses HuggingFace InferenceClient for embeddings and supports:
    - Automatic language detection (Chinese/English)
    - Model selection based on text language
    - Batch embedding computation
    - Cosine similarity via normalized dot product
    """

    def __init__(self, config: Optional[TransformerConfig] = None):
        """Initialize the transformer matcher.

        Args:
            config: Optional configuration. Uses default if not provided.
        """
        self.config = config or TransformerConfig()
        self._client: Optional[InferenceClient] = None
        self._load_env()

    def _load_env(self):
        """Load environment variables from .env file."""
        env_path = self.config.env_path
        if not os.path.isabs(env_path):
            # Try to find the .env file relative to the project root
            script_dir = Path(__file__).resolve().parent
            for _ in range(6):  # Search up to 6 levels up
                if (script_dir / env_path).exists():
                    env_path = str(script_dir / env_path)
                    break
                script_dir = script_dir.parent

        dotenv.load_dotenv(env_path)

        api_key = os.environ.get(self.config.api_key_env)
        if not api_key:
            raise ValueError(
                f"{self.config.api_key_env} not found in environment. "
                f"Please set {self.config.api_key_env} in {self.config.env_path}"
            )

        self._client = InferenceClient(
            provider="hf-inference",
            api_key=api_key,
        )

    def _detect_language(self, text: str) -> str:
        """Detect text language based on Chinese character ratio.

        Args:
            text: Input text to analyze

        Returns:
            "zh" if Chinese character ratio >= threshold, "en" otherwise
        """
        # Count Chinese characters (Unicode range for CJK Unified Ideographs)
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text.strip())

        if total_chars == 0:
            return "en"

        ratio = chinese_chars / total_chars
        return "zh" if ratio >= self.config.lang_threshold else "en"

    def _get_model_id(self, texts: List[str]) -> str:
        """Select model based on aggregated language detection of all texts.

        Args:
            texts: List of texts to analyze

        Returns:
            Model ID (either model_zh or model_en)
        """
        if not texts:
            return self.config.model_en

        # Combine all texts for language detection
        combined = " ".join(texts)
        lang = self._detect_language(combined)
        return self.config.model_zh if lang == "zh" else self.config.model_en

    def _normalize(self, v: np.ndarray) -> np.ndarray:
        """Normalize vectors for cosine similarity via dot product.

        Args:
            v: Input vectors of shape (N, D)

        Returns:
            Normalized vectors of shape (N, D)
        """
        norm = np.linalg.norm(v, axis=1, keepdims=True)
        # Avoid division by zero
        norm = np.where(norm == 0, 1, norm)
        return v / norm

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to embeddings.

        Args:
            texts: List of text strings to encode

        Returns:
            Embeddings array of shape (N, D) where D is embedding dimension
        """
        if not texts:
            return np.array([], dtype=np.float32)

        if self._client is None:
            raise RuntimeError("InferenceClient not initialized. Call _load_env() first.")

        model_id = self._get_model_id(texts)

        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            # The InferenceClient.feature_extraction accepts a list of strings
            outputs = self._client.feature_extraction(batch, model=model_id)
            all_embeddings.append(outputs)

        # Concatenate all batches
        embeddings = np.concatenate(all_embeddings, axis=0)
        return np.array(embeddings, dtype=np.float32)

    def rerank(
        self,
        query: str,
        candidates: List[str]
    ) -> List[Tuple[str, float]]:
        """Re-rank candidates by semantic similarity to query.

        Args:
            query: Query string
            candidates: List of candidate texts to rank

        Returns:
            List of (candidate, score) tuples sorted by similarity descending
        """
        if not candidates:
            return []

        # Encode query and candidates
        query_emb = self.encode([query])  # [1, D]
        candidate_embs = self.encode(candidates)  # [N, D]

        # Normalize for cosine similarity
        query_emb = self._normalize(query_emb)
        candidate_embs = self._normalize(candidate_embs)

        # Cosine similarity via dot product
        scores = query_emb @ candidate_embs.T  # [1, N]

        # Sort by score descending
        reranked = sorted(
            zip(candidates, scores[0]),
            key=lambda x: x[1],
            reverse=True
        )

        return reranked

    def rerank_batch(
        self,
        queries: List[str],
        candidates: List[str]
    ) -> Tuple[np.ndarray, List[str]]:
        """Batch calculate similarity matrix for multiple queries and candidates.

        Args:
            queries: List of query strings
            candidates: List of candidate texts

        Returns:
            sim_matrix: [Q, C] similarity matrix where sim_matrix[q_idx][c_idx] = similarity(queries[q_idx], candidates[c_idx])
            returned_candidates: The candidate list (corresponds to sim_matrix columns)
        """
        if not queries or not candidates:
            return np.array([]), []

        # Batch encode all queries and candidates
        query_embs = self.encode(queries)  # [Q, D]
        candidate_embs = self.encode(candidates)  # [C, D]

        # Normalize for cosine similarity
        query_embs = self._normalize(query_embs)
        candidate_embs = self._normalize(candidate_embs)

        # Similarity matrix via dot product
        sim_matrix = query_embs @ candidate_embs.T  # [Q, C]

        return sim_matrix, candidates


# Import Path for relative path resolution
from pathlib import Path


__all__ = [
    "TransformerMatcher",
    "TransformerConfig",
]
