"""
Configuration Manager - Load, validate, and merge search configurations.

This module provides the ConfigManager class for handling configuration
loading from various sources and managing configuration merging.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .config import SearchConfig


class ConfigManager:
    """Configuration manager for searcher module.

    Handles configuration loading from dictionaries or JSON files,
    validation, and merging with default values.

    Example:
        >>> manager = ConfigManager(base_dir="/path/to/docs")
        >>> config = manager.get_search_config()

        # Load from dict
        >>> config = manager.load_config({"bm25": {"k1": 1.5}})

        # Load from JSON file
        >>> config = manager.load_config("/path/to/config.json")
    """

    def __init__(
        self,
        config: Optional[Union[Dict[str, Any], str]] = None,
        base_dir: str = "",
    ):
        """Initialize configuration manager.

        Args:
            config: Initial configuration (dict or JSON file path)
            base_dir: Base directory for resolving relative paths
        """
        self._base_dir = base_dir
        self._config: Optional[SearchConfig] = None

        if config is not None:
            self._config = self._parse_config(config)

    def _parse_config(
        self, config: Union[Dict[str, Any], str]
    ) -> SearchConfig:
        """Parse configuration from dict or file path.

        Args:
            config: Configuration dictionary or JSON file path

        Returns:
            SearchConfig instance
        """
        if isinstance(config, dict):
            return SearchConfig.from_dict(config)

        if isinstance(config, str):
            # Check if it's a JSON string
            if config.strip().startswith("{"):
                data = json.loads(config)
                return SearchConfig.from_dict(data)

            # Treat as file path
            config_path = Path(config).expanduser()
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return SearchConfig.from_dict(data)
            else:
                raise FileNotFoundError(f"Config file not found: {config}")

        raise TypeError(f"Unsupported config type: {type(config)}")

    def get_search_config(self) -> SearchConfig:
        """Get the current search configuration.

        Returns:
            SearchConfig instance with default values if not set
        """
        if self._config is None:
            self._config = SearchConfig()
        return self._config

    def set_search_config(self, config: SearchConfig) -> None:
        """Set the search configuration.

        Args:
            config: SearchConfig instance to set
        """
        self._config = config

    def load_config(
        self, config: Union[Dict[str, Any], str]
    ) -> SearchConfig:
        """Load configuration from dict or file.

        Args:
            config: Configuration dictionary or JSON file path

        Returns:
            Loaded SearchConfig instance
        """
        self._config = self._parse_config(config)
        return self._config

    def load_skiped_keywords(self) -> List[str]:
        """Load skipped keywords from file.

        Looks for skiped_keywords.txt in:
        1. Custom path if configured
        2. Same directory as this module
        3. Base directory if configured

        Returns:
            List of skipped keywords
        """
        config = self.get_search_config()

        # Check for custom path
        if config.skiped_keywords_path:
            skiped_file = Path(config.skiped_keywords_path).expanduser()
            if skiped_file.exists():
                return self._read_keywords_file(skiped_file)
            return []

        # Look in module directory
        module_dir = Path(__file__).parent
        skiped_file = module_dir / "skiped_keywords.txt"
        if skiped_file.exists():
            return self._read_keywords_file(skiped_file)

        # Look in base directory
        if self._base_dir:
            skiped_file = Path(self._base_dir) / "skiped_keywords.txt"
            if skiped_file.exists():
                return self._read_keywords_file(skiped_file)

        return []

    def _read_keywords_file(self, path: Path) -> List[str]:
        """Read keywords from file.

        Args:
            path: Path to keywords file

        Returns:
            List of keywords (non-empty, stripped lines)
        """
        try:
            return [
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except Exception:
            return []

    def validate(self) -> Dict[str, Any]:
        """Validate current configuration.

        Returns:
            Dictionary with 'valid' (bool) and 'errors' (list) fields
        """
        config = self.get_search_config()
        errors: List[str] = []

        # Validate fallback mode
        if config.fallback.mode not in ("serial", "parallel"):
            errors.append(
                f"Invalid fallback mode: '{config.fallback.mode}'. "
                "Must be 'serial' or 'parallel'"
            )

        # Validate reranker embedding provider
        if config.reranker.embedding_provider not in ("hf", "ms"):
            errors.append(
                f"Invalid embedding provider: '{config.reranker.embedding_provider}'. "
                "Must be 'hf' or 'ms'"
            )

        # Validate rerank_scopes
        valid_scopes = {"page_title", "headings"}
        invalid_scopes = set(config.rerank_scopes) - valid_scopes
        if invalid_scopes:
            errors.append(
                f"Invalid rerank_scopes: {invalid_scopes}. "
                f"Must be subset of {valid_scopes}"
            )

        # Validate BM25 parameters
        if not 0.0 <= config.bm25.k1 <= 5.0:
            errors.append(f"BM25 k1 must be between 0.0 and 5.0, got {config.bm25.k1}")

        if not 0.0 <= config.bm25.b <= 1.0:
            errors.append(f"BM25 b must be between 0.0 and 1.0, got {config.bm25.b}")

        # Validate thresholds
        if not 0.0 <= config.thresholds.page_title <= 1.0:
            errors.append(
                f"threshold_page_title must be between 0.0 and 1.0, "
                f"got {config.thresholds.page_title}"
            )

        if not 0.0 <= config.thresholds.headings <= 1.0:
            errors.append(
                f"threshold_headings must be between 0.0 and 1.0, "
                f"got {config.thresholds.headings}"
            )

        if not 0.0 <= config.thresholds.precision <= 1.0:
            errors.append(
                f"threshold_precision must be between 0.0 and 1.0, "
                f"got {config.thresholds.precision}"
            )

        # Validate fallback_2_local_rerank_ratio
        if not 0.0 <= config.fallback.fallback_2_local_rerank_ratio <= 1.0:
            errors.append(
                f"fallback_2_local_rerank_ratio must be between 0.0 and 1.0, "
                f"got {config.fallback.fallback_2_local_rerank_ratio}"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def merge_with_defaults(self, user_config: Dict[str, Any]) -> SearchConfig:
        """Merge user configuration with defaults.

        Args:
            user_config: User-provided configuration dictionary

        Returns:
            Merged SearchConfig instance
        """
        current = self.get_search_config()
        merged_data = current.to_dict()

        # Deep merge user config
        self._deep_merge(merged_data, user_config)

        return SearchConfig.from_dict(merged_data)

    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """Deep merge override into base dictionary.

        Args:
            base: Base dictionary to merge into
            override: Override dictionary
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def save_config(self, path: Union[str, Path]) -> None:
        """Save current configuration to JSON file.

        Args:
            path: Output file path
        """
        config = self.get_search_config()
        data = config.to_dict()

        # Convert to JSON-compatible format
        output_path = Path(path).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_bm25_params(self) -> Dict[str, Any]:
        """Get BM25 parameters as a simple dictionary.

        Returns:
            Dictionary with k1, b, and threshold values
        """
        config = self.get_search_config()
        return {
            "k1": config.bm25.k1,
            "b": config.bm25.b,
            "threshold_page_title": config.thresholds.page_title,
            "threshold_headings": config.thresholds.headings,
            "threshold_precision": config.thresholds.precision,
        }

    def get_reranker_params(self) -> Dict[str, Any]:
        """Get reranker parameters as a simple dictionary.

        Returns:
            Dictionary with reranker configuration
        """
        config = self.get_search_config()
        return {
            "enabled": config.reranker.enabled,
            "model_zh": config.reranker.model_zh,
            "model_en": config.reranker.model_en,
            "threshold": config.reranker.threshold,
            "top_k": config.reranker.top_k,
            "lang_threshold": config.reranker.lang_threshold,
            "embedding_provider": config.reranker.embedding_provider,
            "embedding_model_id": config.reranker.embedding_model_id,
        }

    def get_fallback_params(self) -> Dict[str, Any]:
        """Get fallback parameters as a simple dictionary.

        Returns:
            Dictionary with fallback configuration
        """
        config = self.get_search_config()
        return {
            "mode": config.fallback.mode,
            "fallback_2_local_rerank": config.fallback.fallback_2_local_rerank,
            "fallback_2_local_rerank_ratio": config.fallback.fallback_2_local_rerank_ratio,
            "local_device": config.fallback.local_device,
            "local_model_zh": config.fallback.local_model_zh,
            "local_model_en": config.fallback.local_model_en,
        }


__all__ = [
    "ConfigManager",
]
