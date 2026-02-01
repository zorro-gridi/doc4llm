"""
Searcher Registry - Central registry for managing searcher instances.

This module provides a registry pattern for managing searcher instances,
allowing dynamic registration and retrieval of searchers by name.
"""

from typing import Any, Dict, List, Optional, Type

from .interfaces import BaseSearcher


class SearcherRegistry:
    """Registry for managing searcher instances.

    The registry maintains a collection of searcher instances that can be
    retrieved by name. This enables dynamic searcher selection and
    dependency injection.

    Example:
        >>> registry = SearcherRegistry()
        >>> registry.register("bm25", bm25_searcher)
        >>> registry.register("anchor", anchor_searcher)
        >>> searcher = registry.get("bm25")
        >>> results = searcher.search(queries, doc_sets)
    """

    def __init__(self):
        """Initialize the registry with empty storage."""
        self._searchers: Dict[str, BaseSearcher] = {}
        self._searcher_types: Dict[str, Type[BaseSearcher]] = {}

    def register(
        self,
        name: str,
        searcher: BaseSearcher,
        overwrite: bool = False
    ) -> None:
        """Register a searcher instance.

        Args:
            name: Unique identifier for the searcher
            searcher: Searcher instance to register
            overwrite: Whether to overwrite existing registration

        Raises:
            ValueError: If a searcher with the name already exists
        """
        if name in self._searchers and not overwrite:
            raise ValueError(f"Searcher '{name}' is already registered")
        self._searchers[name] = searcher

    def register_class(
        self,
        name: str,
        searcher_class: Type[BaseSearcher],
        **constructor_kwargs
    ) -> None:
        """Register a searcher class for lazy instantiation.

        Args:
            name: Unique identifier for the searcher
            searcher_class: Searcher class to register
            **constructor_kwargs: Arguments to pass to class constructor
        """
        self._searcher_types[name] = (searcher_class, constructor_kwargs)

    def get(self, name: str) -> Optional[BaseSearcher]:
        """Retrieve a searcher by name.

        Args:
            name: Name of the searcher to retrieve

        Returns:
            Searcher instance or None if not found
        """
        if name in self._searchers:
            return self._searchers[name]

        if name in self._searcher_types:
            searcher_class, kwargs = self._searcher_types[name]
            instance = searcher_class(**kwargs)
            self._searchers[name] = instance
            return instance

        return None

    def get_or_create(
        self,
        name: str,
        factory: callable,
        **factory_kwargs
    ) -> BaseSearcher:
        """Get existing searcher or create a new one.

        Args:
            name: Name of the searcher
            factory: Function to create searcher if not exists
            **factory_kwargs: Arguments to pass to factory

        Returns:
            Searcher instance
        """
        if name in self._searchers:
            return self._searchers[name]

        instance = factory(**factory_kwargs)
        self._searchers[name] = instance
        return instance

    def list_all(self) -> List[str]:
        """List all registered searcher names.

        Returns:
            List of searcher names
        """
        return list(set(self._searchers.keys()) | set(self._searcher_types.keys()))

    def list_instances(self) -> Dict[str, BaseSearcher]:
        """Get dictionary of all instantiated searchers.

        Returns:
            Dictionary mapping names to searcher instances
        """
        return dict(self._searchers)

    def unregister(self, name: str) -> bool:
        """Unregister a searcher by name.

        Args:
            name: Name of the searcher to remove

        Returns:
            True if searcher was removed, False if not found
        """
        if name in self._searchers:
            del self._searchers[name]
            return True
        if name in self._searcher_types:
            del self._searcher_types[name]
            return True
        return False

    def clear(self) -> None:
        """Remove all registered searchers."""
        self._searchers.clear()
        self._searcher_types.clear()

    def __contains__(self, name: str) -> bool:
        """Check if a searcher is registered."""
        return name in self._searchers or name in self._searcher_types

    def __len__(self) -> int:
        """Get total number of registered searchers."""
        return len(self._searchers) + len(self._searcher_types)


# Global registry instance
_default_registry: Optional[SearcherRegistry] = None


def get_registry() -> SearcherRegistry:
    """Get the default global registry.

    Returns:
        Default SearcherRegistry instance
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = SearcherRegistry()
    return _default_registry


def reset_registry() -> SearcherRegistry:
    """Reset and return a new default registry.

    Returns:
        New SearcherRegistry instance
    """
    global _default_registry
    _default_registry = SearcherRegistry()
    return _default_registry


__all__ = [
    "SearcherRegistry",
    "get_registry",
    "reset_registry",
]
