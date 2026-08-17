"""Unit tests for the model gateway: the deterministic FakeModelProvider and the
provider registry. No network, no keys — the offline guarantee (DoD) lives here.
"""
from __future__ import annotations

import json

import pytest

from core.model_gateway import fake_content
from core.model_gateway.base import ModelRequest, ProviderError
from core.model_gateway.registry import available_providers, get_provider


def _req(stage, iteration=0, scenario="fail_once"):
    return ModelRequest(
        model="fake-1",
        messages=[{"role": "user", "content": "go"}],
        metadata={"stage": stage, "iteration": iteration, "scenario": scenario},
    )


def test_fake_provider_is_registered():
    assert "fake" in available_providers()


def test_unknown_provider_fails_loudly():
    with pytest.raises(ProviderError, match="Unknown model provider"):
        get_provider("does-not-exist")


def test_runtime_provider_families_are_registered():
    assert {
        "openai_responses", "openai_compatible", "anthropic", "gemini",
        "azure_openai", "bedrock", "vertex", "cohere", "replicate",
        "cloudflare", "generic_rest",
    } <= set(available_providers())


def test_fake_response_is_deterministic_json():
    provider = get_provider("fake")
    r1 = provider.call(_req("architecture"))
    r2 = provider.call(_req("architecture"))
    assert r1.text == r2.text  # deterministic
    payload = json.loads(r1.text)
    assert "summary" in payload
    assert r1.input_tokens > 0 and r1.output_tokens > 0
    assert r1.cost > 0


def test_qa_fails_first_iteration_then_passes_fail_once():
    fail = fake_content.build("qa", iteration=0, scenario="fail_once")
    passed = fake_content.build("qa", iteration=1, scenario="fail_once")
    assert fail["evaluation"]["tests_passed"] is False
    assert passed["evaluation"]["tests_passed"] is True


def test_qa_always_fails_in_always_fail_scenario():
    for it in range(5):
        result = fake_content.build("qa", iteration=it, scenario="always_fail")
        assert result["evaluation"]["tests_passed"] is False


def test_backend_ships_fix_after_first_iteration():
    buggy = fake_content.build("backend_implementation", iteration=0, scenario="fail_once")
    fixed = fake_content.build("backend_implementation", iteration=1, scenario="fail_once")
    assert "BUG" in buggy["artifacts"][0]["content"]
    assert "BUG" not in fixed["artifacts"][0]["content"]
    assert "status" in fixed["artifacts"][0]["content"]


def test_openai_compatible_normalizes_response(monkeypatch):
    from core.model_gateway import providers

    monkeypatch.setattr(providers, "_http_json", lambda *args, **kwargs: {
        "model": "vendor/model",
        "choices": [{"message": {"content": "hello"}}],
        "usage": {"prompt_tokens": 4, "completion_tokens": 2},
    })
    response = get_provider("openai_compatible", api_key="secret", base_url="https://example.test/v1").call(
        ModelRequest(model="vendor/model", messages=[{"role": "user", "content": "hi"}])
    )
    assert response.text == "hello"
    assert response.total_tokens == 6


def test_openai_responses_extracts_output_items(monkeypatch):
    from core.model_gateway import providers

    monkeypatch.setattr(providers, "_http_json", lambda *args, **kwargs: {
        "model": "gpt-test",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": "done"}]}],
        "usage": {"input_tokens": 5, "output_tokens": 1},
    })
    response = get_provider("openai_responses", api_key="secret").call(
        ModelRequest(model="gpt-test", messages=[{"role": "user", "content": "go"}])
    )
    assert response.text == "done"
    assert response.total_tokens == 6


def test_gemini_normalizes_generate_content(monkeypatch):
    from core.model_gateway import providers

    monkeypatch.setattr(providers, "_http_json", lambda *args, **kwargs: {
        "candidates": [{"content": {"parts": [{"text": "gemini answer"}]}}],
        "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 4},
    })
    response = get_provider("gemini", api_key="secret").call(
        ModelRequest(model="gemini-test", messages=[{"role": "user", "content": "go"}])
    )
    assert response.text == "gemini answer"
    assert response.total_tokens == 7


def test_generic_rest_supports_structured_templates(monkeypatch):
    from core.model_gateway import providers

    captured = {}

    def fake_http(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return {"result": {"answer": "custom answer"}}

    monkeypatch.setattr(providers, "_http_json", fake_http)
    response = get_provider(
        "generic_rest",
        api_key="secret",
        base_url="https://self-hosted.test",
        path="/generate/{{model}}",
        request_template={"history": "{{messages}}", "limit": "{{max_tokens}}"},
        response_path="result.answer",
    ).call(ModelRequest(model="local-model", messages=[{"role": "user", "content": "hi"}], max_tokens=33))
    assert response.text == "custom answer"
    assert captured["url"].endswith("/generate/local-model")
    assert captured["body"]["history"][0]["content"] == "hi"
