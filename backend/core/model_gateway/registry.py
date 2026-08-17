"""Provider registry — resolve a :class:`ModelProvider` by its key."""
from __future__ import annotations

from typing import Type

from core.model_gateway.base import ModelProvider, ProviderError

_REGISTRY: dict[str, Type[ModelProvider]] = {}


def register_provider(cls: Type[ModelProvider]) -> Type[ModelProvider]:
    """Class decorator / function to register a provider adapter."""
    _REGISTRY[cls.key] = cls
    return cls


def get_provider(key: str, **kwargs) -> ModelProvider:
    """Instantiate a provider adapter by key.

    Unknown adapters fail loudly. Silently replacing a paid/remote model with
    deterministic demo output makes executions look successful when the
    provider is actually misconfigured.
    """
    cls = _REGISTRY.get(key)
    if cls is None:
        raise ProviderError(f"Unknown model provider adapter: {key}")
    return cls(**kwargs)


def available_providers() -> list[str]:
    return sorted(_REGISTRY.keys())


# Import adapters so their @register_provider side effects run.
from core.model_gateway import providers  # noqa: E402,F401
