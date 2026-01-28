"""
ModelScope-based semantic matcher using OpenAI-compatible API.

Provides embedding and reranking capabilities via ModelScope's inference API.
Uses Qwen/Qwen3-Embedding-8B as the default multilingual embedding model.

Example:
    >>> from doc4llm.tool.md_doc_retrieval import ModelScopeMatcher, ModelScopeConfig
    >>> matcher = ModelScopeMatcher()
    >>> results = matcher.rerank("查询文本", ["候选1", "候选2", "候选3"])
    >>> for text, score in results:
    ...     print(f"{score:.4f} | {text}")
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import dotenv
import numpy as np
from openai import OpenAI


@dataclass
class ModelScopeConfig:
    """Configuration for ModelScope-based semantic matching.

    Attributes:
        model_id: Model ID for embeddings (default: Qwen/Qwen3-Embedding-8B)
        api_key_env: Environment variable name for ModelScope API key
        env_path: Path to .env file containing API key
        batch_size: Batch size for embedding computation
    """
    model_id: str = "Qwen/Qwen3-Embedding-8B"
    api_key_env: str = "MODELSCOPE_KEY"
    env_path: str = "doc4llm/.env"
    batch_size: int = 32


class ModelScopeMatcher:
    """ModelScope-based semantic matcher with OpenAI-compatible API.

    Uses ModelScope's inference API for embeddings with support for:
    - Batch embedding computation
    - Cosine similarity via normalized vectors
    - Compatible interface with TransformerMatcher
    """

    def __init__(self, config: Optional[ModelScopeConfig] = None):
        """Initialize the ModelScope matcher.

        Args:
            config: Optional configuration. Uses default if not provided.
        """
        self.config = config or ModelScopeConfig()
        self._client: Optional[OpenAI] = None
        self._load_env()

    def _load_env(self):
        """Load environment variables from .env file."""
        env_path = self.config.env_path
        if not os.path.isabs(env_path):
            # Try to find the .env file relative to the current file
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

        self._client = OpenAI(
            base_url="https://api-inference.modelscope.cn/v1",
            api_key=api_key,
        )

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
            raise RuntimeError("OpenAI client not initialized. Call _load_env() first.")

        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            response = self._client.embeddings.create(
                model=self.config.model_id,
                input=batch,
                encoding_format="float"
            )
            # Extract embedding vectors from response
            embeddings = [data.embedding for data in response.data]
            all_embeddings.append(embeddings)

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


__all__ = [
    "ModelScopeMatcher",
    "ModelScopeConfig",
]
