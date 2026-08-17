"""Core contracts for the model gateway."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional


class ProviderError(Exception):
    """Raised when a provider call fails in a recoverable way."""


@dataclass
class ModelRequest:
    """A normalized request sent to any provider.

    ``messages`` is a list of ``{"role": ..., "content": ...}`` dicts, matching
    the de-facto chat format used across vendors.
    """

    model: str
    messages: list[dict]
    temperature: float = 0.7
    max_tokens: int = 1024
    # Free-form hints the FakeModelProvider uses to pick a deterministic
    # response (e.g. {"stage": "backend_implementation", "scenario": "fail"}).
    metadata: dict = field(default_factory=dict)


@dataclass
class ModelResponse:
    """A normalized response returned by any provider."""

    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    model: str = ""
    provider: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class ModelProvider:
    """Abstract provider interface.

    Concrete adapters implement :meth:`call` (and optionally :meth:`stream`).
    ``key`` is the stable identifier used by the registry and stored on
    ``ModelProvider`` rows in the database.
    """

    key: str = "base"

    def __init__(self, *, api_key: str = "", credentials: dict | None = None, base_url: str = "", **options):
        self.credentials = credentials or ({"api_key": api_key} if api_key else {})
        self.api_key = api_key or self.credentials.get("api_key", "")
        self.base_url = base_url
        self.options = options

    def call(self, request: ModelRequest) -> ModelResponse:  # pragma: no cover
        raise NotImplementedError

    def stream(self, request: ModelRequest) -> Iterator[str]:  # pragma: no cover
        # Default: yield the full response once. Adapters may override.
        yield self.call(request).text

    def estimate_cost(
        self, input_tokens: int, output_tokens: int, model: Optional[str] = None
    ) -> float:
        """Rough cost estimate in USD. Overridden per provider."""
        return 0.0

    def health_check(self) -> bool:
        """Return True if the provider is usable."""
        return True

    def list_models(self) -> list[dict]:
        """Discover remote models without invoking inference when supported."""
        return []
