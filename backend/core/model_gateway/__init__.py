"""Model Gateway: a provider-agnostic interface to language models.

The rest of the platform never talks to a vendor SDK directly. It asks the
gateway to resolve a provider by key and calls a small, stable interface
(:class:`~core.model_gateway.base.ModelProvider`). This keeps the agent domain
decoupled from any specific vendor and lets us swap in LiteLLM/Portkey later.
"""
from core.model_gateway.base import (
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ProviderError,
)
from core.model_gateway.registry import get_provider, register_provider

__all__ = [
    "ModelProvider",
    "ModelRequest",
    "ModelResponse",
    "ProviderError",
    "get_provider",
    "register_provider",
]
