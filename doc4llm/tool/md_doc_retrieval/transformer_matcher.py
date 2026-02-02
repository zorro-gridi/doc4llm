"""
Transformer-based semantic matcher using HuggingFace embeddings.

Provides language detection and model selection for Chinese/English text.
Uses BAAI/bge-large-zh-v1.5 for Chinese and BAAI/bge-large-en-v1.5 for English.

Supports two modes:
- Remote API mode (default): Uses HuggingFace InferenceClient API
- Local mode: Uses sentence-transformers with models downloaded from HuggingFace Hub

Example:
    >>> from doc4llm.tool.md_doc_retrieval import TransformerMatcher, TransformerConfig

    Remote API mode:
    >>> matcher = TransformerMatcher()
    >>> results = matcher.rerank("查询文本", ["候选1", "候选2", "候选3"])
    >>> for text, score in results:
    ...     print(f"{score:.4f} | {text}")

    Local mode (no API key required):
    >>> config = TransformerConfig(use_local=True, device="cpu")
    >>> matcher = TransformerMatcher(config)
    >>> embeddings = matcher.encode(["文本1", "文本2"])
"""

import os
import re

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional

import dotenv
import httpx
import numpy as np
from huggingface_hub import InferenceClient, set_client_factory
from sentence_transformers import SentenceTransformer

from transformers import logging

# 禁用加载模型时的进度条（如下载权重时的进度条）
logging.disable_progress_bar()
# 只显示 error，不显示 info / warning
logging.set_verbosity_error()


@dataclass
class TransformerConfig:
    """Configuration for transformer-based semantic matching.

    Attributes:
        use_local: Whether to use local model inference (default: False)
        device: Device to use for local inference ("cpu" or "cuda")
        local_model_zh: Chinese model ID for local inference (default: BAAI/bge-base-zh-v1.5)
        local_model_en: English model ID for local inference (default: BAAI/bge-base-en-v1.5)
        model_zh: Chinese model ID for remote API inference (default: BAAI/bge-large-zh-v1.5)
        model_en: English model ID for remote API inference (default: BAAI/bge-large-en-v1.5)
        api_key_env: Environment variable name for HuggingFace API key
        env_path: Path to .env file containing HF_KEY
        batch_size: Batch size for embedding computation
        lang_threshold: Ratio of Chinese characters to trigger Chinese model (0-1)
        hf_inference_provider: HuggingFace inference provider (default: "auto")
    """
    use_local: bool = False
    device: str = "cpu"
    local_model_zh: str = "BAAI/bge-base-zh-v1.5"
    local_model_en: str = "BAAI/bge-base-en-v1.5"
    model_zh: str = "BAAI/bge-large-zh-v1.5"
    model_en: str = "BAAI/bge-large-en-v1.5"
    api_key_env: str = "HF_KEY"
    env_path: str = "doc4llm/.env"
    batch_size: int = 32
    lang_threshold: float = 0.9
    hf_inference_provider: str = "auto"


class TransformerMatcher:
    """Transformer-based semantic matcher with language auto-detection.

    Supports two modes:
    - Remote API mode (use_local=False, default): Uses HuggingFace InferenceClient
    - Local mode (use_local=True): Uses sentence-transformers with local model inference

    Features:
    - Automatic language detection (Chinese/English)
    - Model selection based on text language
    - Batch embedding computation
    - Cosine similarity via normalized dot product
    - Lazy loading of local models (downloaded from HuggingFace Hub on first use)

    Args:
        config: Optional configuration. Uses default if not provided.
    """

    def __init__(self, config: Optional[TransformerConfig] = None):
        """Initialize the transformer matcher.

        Args:
            config: Optional configuration. Uses default if not provided.
        """
        self.config = config or TransformerConfig()
        self._client: Optional[InferenceClient] = None
        self._local_models: dict = {}
        self._load_env()

    def _load_env(self):
        """Load environment variables from .env file."""
        # Local mode does not require API key
        if self.config.use_local:
            return

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

        # Configure HTTP proxy from environment variable (before creating client)
        proxy = os.environ.get("HF_PROXY")
        if proxy:
            def create_proxy_client() -> httpx.Client:
                return httpx.Client(proxy=proxy)
            set_client_factory(create_proxy_client)

        self._client = InferenceClient(
            provider=self.config.hf_inference_provider,
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

        Uses local_model_zh/local_model_en when use_local=True,
        otherwise uses model_zh/model_en for remote API inference.

        Args:
            texts: List of texts to analyze

        Returns:
            Model ID based on language and mode
        """
        if not texts:
            # Default to English model when no texts provided
            return self.config.local_model_en if self.config.use_local else self.config.model_en

        # Combine all texts for language detection
        combined = " ".join(texts)
        lang = self._detect_language(combined)

        if self.config.use_local:
            # Local mode uses local_model_zh/local_model_en
            return self.config.local_model_zh if lang == "zh" else self.config.local_model_en
        else:
            # Remote API mode uses model_zh/model_en
            return self.config.model_zh if lang == "zh" else self.config.model_en

    def _load_local_model(self, model_id: str) -> SentenceTransformer:
        """Load local SentenceTransformer model (lazy loading).

        Models are automatically downloaded from HuggingFace Hub if not cached.

        Args:
            model_id: Model ID from HuggingFace Hub (e.g., "BAAI/bge-large-zh-v1.5")

        Returns:
            SentenceTransformer model instance
        """
        if model_id not in self._local_models:
            self._local_models[model_id] = SentenceTransformer(
                model_id,
                device=self.config.device
            )
        return self._local_models[model_id]

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

        model_id = self._get_model_id(texts)

        if self.config.use_local:
            # Local mode using SentenceTransformer
            model = self._load_local_model(model_id)
            embeddings = model.encode(texts, normalize_embeddings=True)
            return np.array(embeddings, dtype=np.float32)
        else:
            # Remote API mode using InferenceClient
            if self._client is None:
                raise RuntimeError("InferenceClient not initialized. Call _load_env() first.")

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


__all__ = [
    "TransformerMatcher",
    "TransformerConfig",
]
