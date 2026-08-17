"""Resolve one stored model + encrypted credential into a gateway call."""
from __future__ import annotations

from core.model_gateway.base import ModelRequest
from core.model_gateway.registry import get_provider


def call_registered_model(model, credential, *, messages, temperature=0.2, max_tokens=256, metadata=None):
    provider = model.provider
    if credential is not None and credential.provider_id != provider.id:
        raise ValueError("Credential must belong to the selected model provider.")
    if credential is None:
        credential = provider.credentials.filter(label="default").first() or provider.credentials.first()

    credentials = credential.get_secret_data() if credential else {}
    options = {**(provider.config or {})}
    options["extra_body"] = {
        **(options.get("extra_body") or {}),
        **(model.default_params or {}),
    }
    adapter = get_provider(
        provider.adapter,
        api_key=credentials.get("api_key", ""),
        credentials=credentials,
        base_url=provider.base_url or "",
        **options,
    )
    response = adapter.call(ModelRequest(
        model=model.remote_id or model.key,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        metadata=metadata or {},
    ))
    response.cost = round(
        response.input_tokens / 1000 * float(model.input_cost_per_1k)
        + response.output_tokens / 1000 * float(model.output_cost_per_1k),
        6,
    )
    return response, credential
