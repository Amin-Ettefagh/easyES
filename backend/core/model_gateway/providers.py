"""Provider adapters.

Only the :class:`FakeModelProvider` is fully implemented — it produces
deterministic, scenario-aware output so the entire software-company demo runs
end-to-end with no external API keys. ``OpenAICompatibleProvider`` is a working
skeleton that talks to any OpenAI-style ``/chat/completions`` endpoint; other
vendor adapters are thin stubs that show where real integrations plug in.

Fake responses are always JSON so the agent runner can extract structured
artifacts, messages and (for QA) a pass/fail result. Real providers return free
text; the runner degrades gracefully to a single summary + artifact.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Iterator
from urllib.parse import quote, urlparse

from core.model_gateway.base import (
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ProviderError,
)
from core.model_gateway.registry import register_provider
from core.model_gateway import fake_content


def _estimate_tokens(text: str) -> int:
    # Rough heuristic: ~4 chars per token. Good enough for demo accounting.
    return max(1, len(text) // 4)


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ProviderError("Provider endpoint must be an absolute HTTP(S) URL.")


def _http_json(method: str, url: str, *, body=None, headers=None, timeout=90):
    _validate_url(url)
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method=method.upper(),
    )
    try:
        with urllib.request.urlopen(request, timeout=min(max(int(timeout), 1), 300)) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")[:600]
        except Exception:  # pragma: no cover - defensive around broken sockets
            detail = ""
        raise ProviderError(f"Provider returned HTTP {exc.code}: {detail or exc.reason}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise ProviderError(f"Provider request failed: {exc}") from exc


def _path_value(data, path: str, default=None):
    if not path:
        return data
    current = data
    for part in path.replace("[", ".").replace("]", "").split("."):
        if part == "":
            continue
        try:
            current = current[int(part)] if isinstance(current, list) else current[part]
        except (KeyError, IndexError, TypeError, ValueError):
            return default
    return current


def _as_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or item.get("url") or json.dumps(item, ensure_ascii=False)))
        return "\n".join(part for part in parts if part)
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)


def _prompt_text(messages: list[dict]) -> str:
    return "\n".join(str(message.get("content", "")) for message in messages if message.get("role") != "system")


def _usage_response(data: dict, request: ModelRequest, text: str, provider: str, *, input_path="usage.prompt_tokens", output_path="usage.completion_tokens") -> ModelResponse:
    input_tokens = int(_path_value(data, input_path, 0) or _estimate_tokens(str(request.messages)))
    output_tokens = int(_path_value(data, output_path, 0) or _estimate_tokens(text))
    return ModelResponse(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=str(data.get("model") or request.model),
        provider=provider,
        raw=data,
    )


@register_provider
class FakeModelProvider(ModelProvider):
    """Deterministic offline provider.

    Selects a canned response from :mod:`core.model_gateway.fake_content` based
    on ``request.metadata['stage']``. QA/evaluation stages are additionally
    sensitive to ``iteration`` and ``scenario`` so the demo can show a failing
    first run that is fixed on a later loop iteration.
    """

    key = "fake"

    # Fake pricing so cost/budget features have something to show.
    _RATE_PER_1K_INPUT = 0.0005
    _RATE_PER_1K_OUTPUT = 0.0015

    def call(self, request: ModelRequest) -> ModelResponse:
        stage = request.metadata.get("stage", "generic")
        iteration = int(request.metadata.get("iteration", 0))
        scenario = request.metadata.get("scenario", "fail_once")

        payload = fake_content.build(stage=stage, iteration=iteration, scenario=scenario)
        text = json.dumps(payload, ensure_ascii=False)

        prompt_text = "\n".join(m.get("content", "") for m in request.messages)
        input_tokens = _estimate_tokens(prompt_text)
        output_tokens = _estimate_tokens(text)
        cost = self.estimate_cost(input_tokens, output_tokens, request.model)

        return ModelResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            model=request.model or "fake-1",
            provider=self.key,
            raw={"structured": True},
        )

    def stream(self, request: ModelRequest) -> Iterator[str]:
        yield self.call(request).text

    def estimate_cost(self, input_tokens: int, output_tokens: int, model=None) -> float:
        return round(
            input_tokens / 1000 * self._RATE_PER_1K_INPUT
            + output_tokens / 1000 * self._RATE_PER_1K_OUTPUT,
            6,
        )

    def health_check(self) -> bool:
        return True


@register_provider
class OpenAICompatibleProvider(ModelProvider):
    """Talks to any OpenAI-compatible ``/chat/completions`` endpoint.

    Works with OpenAI, together.ai, Groq, Ollama, LiteLLM, vLLM, etc. Network
    calls are performed lazily so importing this module never requires network
    access. If the SDK/endpoint is unavailable it raises :class:`ProviderError`.
    """

    key = "openai_compatible"

    _DEFAULT_BASE_URL = "https://api.openai.com/v1"

    def call(self, request: ModelRequest) -> ModelResponse:
        base = (self.base_url or self._DEFAULT_BASE_URL).rstrip("/")
        url = f"{base}/chat/completions"
        body = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            str(self.options.get("max_tokens_field", "max_tokens")): request.max_tokens,
        }
        body.update(self.options.get("extra_body") or {})
        headers = dict(self.options.get("headers") or {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = _http_json("POST", url, body=body, headers=headers, timeout=self.options.get("timeout", 90))

        choice = (data.get("choices") or [{}])[0]
        text = _as_text((choice.get("message") or {}).get("content", choice.get("text", "")))
        response = _usage_response(data, request, text, self.key)
        response.cost = self.estimate_cost(response.input_tokens, response.output_tokens, request.model)
        return response

    def estimate_cost(self, input_tokens: int, output_tokens: int, model=None) -> float:
        # Placeholder pricing; real routing/pricing belongs in a gateway
        # like LiteLLM/Portkey (see docs/MODEL_GATEWAY.md).
        return round(input_tokens / 1000 * 0.001 + output_tokens / 1000 * 0.002, 6)

    def health_check(self) -> bool:
        try:
            self.list_models()
            return True
        except ProviderError:
            return False

    def list_models(self) -> list[dict]:
        base = (self.base_url or self._DEFAULT_BASE_URL).rstrip("/")
        headers = dict(self.options.get("headers") or {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = _http_json("GET", f"{base}/models", headers=headers, timeout=30)
        rows = data.get("data", data.get("models", [])) if isinstance(data, dict) else data
        return [{"id": str(item.get("id") or item.get("name")), "name": str(item.get("name") or item.get("id"))} for item in rows if isinstance(item, dict)]


@register_provider
class OpenAIResponsesProvider(OpenAICompatibleProvider):
    """OpenAI's current Responses API, separate from compatibility gateways."""

    key = "openai_responses"

    def call(self, request: ModelRequest) -> ModelResponse:
        base = (self.base_url or self._DEFAULT_BASE_URL).rstrip("/")
        body = {
            "model": request.model,
            "input": request.messages,
            "max_output_tokens": request.max_tokens,
        }
        if not self.options.get("omit_temperature"):
            body["temperature"] = request.temperature
        body.update(self.options.get("extra_body") or {})
        headers = dict(self.options.get("headers") or {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = _http_json("POST", f"{base}/responses", body=body, headers=headers, timeout=self.options.get("timeout", 120))
        text = _as_text(data.get("output_text"))
        if not text:
            chunks = []
            for item in data.get("output", []):
                if item.get("type") == "message":
                    chunks.extend(part.get("text", "") for part in item.get("content", []) if part.get("type") in {"output_text", "text"})
            text = "\n".join(filter(None, chunks))
        response = _usage_response(data, request, text, self.key, input_path="usage.input_tokens", output_path="usage.output_tokens")
        response.cost = self.estimate_cost(response.input_tokens, response.output_tokens, request.model)
        return response


@register_provider
class AnthropicProvider(ModelProvider):
    key = "anthropic"

    def call(self, request: ModelRequest) -> ModelResponse:
        base = (self.base_url or "https://api.anthropic.com/v1").rstrip("/")
        system = "\n".join(str(item.get("content", "")) for item in request.messages if item.get("role") == "system")
        messages = [item for item in request.messages if item.get("role") != "system"]
        body = {"model": request.model, "messages": messages, "max_tokens": request.max_tokens, "temperature": request.temperature}
        if system:
            body["system"] = system
        body.update(self.options.get("extra_body") or {})
        data = _http_json("POST", f"{base}/messages", body=body, headers={
            "x-api-key": self.api_key,
            "anthropic-version": str(self.options.get("anthropic_version", "2023-06-01")),
            **(self.options.get("headers") or {}),
        }, timeout=self.options.get("timeout", 120))
        text = _as_text(data.get("content", []))
        return _usage_response(data, request, text, self.key, input_path="usage.input_tokens", output_path="usage.output_tokens")

    def list_models(self) -> list[dict]:
        base = (self.base_url or "https://api.anthropic.com/v1").rstrip("/")
        data = _http_json("GET", f"{base}/models", headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}, timeout=30)
        return [{"id": item.get("id"), "name": item.get("display_name") or item.get("id")} for item in data.get("data", [])]


def _gemini_body(request: ModelRequest) -> dict:
    systems = [str(item.get("content", "")) for item in request.messages if item.get("role") == "system"]
    contents = []
    for item in request.messages:
        if item.get("role") == "system":
            continue
        role = "model" if item.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": str(item.get("content", ""))}]})
    body = {
        "contents": contents,
        "generationConfig": {"temperature": request.temperature, "maxOutputTokens": request.max_tokens},
    }
    if systems:
        body["systemInstruction"] = {"parts": [{"text": "\n".join(systems)}]}
    return body


def _gemini_response(data: dict, request: ModelRequest, provider: str) -> ModelResponse:
    parts = _path_value(data, "candidates.0.content.parts", []) or []
    text = _as_text(parts)
    return _usage_response(data, request, text, provider, input_path="usageMetadata.promptTokenCount", output_path="usageMetadata.candidatesTokenCount")


@register_provider
class GeminiProvider(ModelProvider):
    key = "gemini"

    def call(self, request: ModelRequest) -> ModelResponse:
        base = (self.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        body = _gemini_body(request)
        body.update(self.options.get("extra_body") or {})
        data = _http_json("POST", f"{base}/models/{quote(request.model, safe='')}:generateContent", body=body, headers={"x-goog-api-key": self.api_key}, timeout=self.options.get("timeout", 120))
        return _gemini_response(data, request, self.key)

    def list_models(self) -> list[dict]:
        base = (self.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        data = _http_json("GET", f"{base}/models", headers={"x-goog-api-key": self.api_key}, timeout=30)
        return [{"id": str(item.get("name", "")).removeprefix("models/"), "name": item.get("displayName") or item.get("name")} for item in data.get("models", [])]


@register_provider
class AzureOpenAIProvider(OpenAIResponsesProvider):
    key = "azure_openai"

    def _base(self) -> str:
        if not self.base_url:
            raise ProviderError("Azure endpoint is required.")
        base = self.base_url.rstrip("/")
        return base if base.endswith("/openai/v1") else f"{base}/openai/v1"

    def call(self, request: ModelRequest) -> ModelResponse:
        original_base, original_headers = self.base_url, self.options.get("headers")
        self.base_url = self._base()
        self.options["headers"] = {"api-key": self.api_key, **(original_headers or {})}
        try:
            return super().call(request)
        finally:
            self.base_url = original_base
            self.options["headers"] = original_headers or {}

    def list_models(self) -> list[dict]:
        original_base, original_headers = self.base_url, self.options.get("headers")
        self.base_url = self._base()
        self.options["headers"] = {"api-key": self.api_key, **(original_headers or {})}
        try:
            return super().list_models()
        finally:
            self.base_url = original_base
            self.options["headers"] = original_headers or {}


@register_provider
class BedrockProvider(ModelProvider):
    key = "bedrock"

    def _client(self, service="bedrock-runtime"):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - image includes boto3
            raise ProviderError("boto3 is required for Amazon Bedrock") from exc
        kwargs = {"region_name": self.credentials.get("region") or self.options.get("region") or "us-east-1"}
        for field in ("aws_access_key_id", "aws_secret_access_key", "aws_session_token"):
            if self.credentials.get(field):
                kwargs[field] = self.credentials[field]
        if self.base_url:
            kwargs["endpoint_url"] = self.base_url
        return boto3.client(service, **kwargs)

    def call(self, request: ModelRequest) -> ModelResponse:
        systems = [{"text": str(item.get("content", ""))} for item in request.messages if item.get("role") == "system"]
        messages = [{"role": "assistant" if item.get("role") == "assistant" else "user", "content": [{"text": str(item.get("content", ""))}]} for item in request.messages if item.get("role") != "system"]
        kwargs = {"modelId": request.model, "messages": messages, "inferenceConfig": {"maxTokens": request.max_tokens, "temperature": request.temperature}}
        if systems:
            kwargs["system"] = systems
        try:
            data = self._client().converse(**kwargs)
        except Exception as exc:  # boto exceptions vary by installed version
            raise ProviderError(f"Amazon Bedrock call failed: {exc}") from exc
        text = _as_text(_path_value(data, "output.message.content", []))
        return _usage_response(data, request, text, self.key, input_path="usage.inputTokens", output_path="usage.outputTokens")

    def list_models(self) -> list[dict]:
        try:
            data = self._client("bedrock").list_foundation_models()
        except Exception as exc:
            raise ProviderError(f"Amazon Bedrock model discovery failed: {exc}") from exc
        return [{"id": item.get("modelId"), "name": item.get("modelName") or item.get("modelId")} for item in data.get("modelSummaries", [])]


@register_provider
class VertexProvider(ModelProvider):
    key = "vertex"

    def _token(self) -> tuple[str, str, str]:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
        except ImportError as exc:  # pragma: no cover - image includes dependency
            raise ProviderError("google-auth is required for Vertex AI") from exc
        value = self.credentials.get("service_account_json")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ProviderError("Service account JSON is invalid") from exc
        if not isinstance(value, dict):
            raise ProviderError("Service account JSON is required for Vertex AI")
        credentials = service_account.Credentials.from_service_account_info(value, scopes=["https://www.googleapis.com/auth/cloud-platform"])
        credentials.refresh(Request())
        project = self.credentials.get("project_id") or value.get("project_id")
        location = self.credentials.get("location") or self.options.get("location") or "us-central1"
        return credentials.token, project, location

    def call(self, request: ModelRequest) -> ModelResponse:
        token, project, location = self._token()
        base = (self.base_url or f"https://{location}-aiplatform.googleapis.com/v1").rstrip("/")
        path = f"projects/{quote(project, safe='')}/locations/{quote(location, safe='')}/publishers/google/models/{quote(request.model, safe='')}:generateContent"
        data = _http_json("POST", f"{base}/{path}", body=_gemini_body(request), headers={"Authorization": f"Bearer {token}"}, timeout=self.options.get("timeout", 120))
        return _gemini_response(data, request, self.key)

    def list_models(self) -> list[dict]:
        token, _project, location = self._token()
        base = (self.base_url or f"https://{location}-aiplatform.googleapis.com/v1").rstrip("/")
        data = _http_json("GET", f"{base}/publishers/google/models", headers={"Authorization": f"Bearer {token}"}, timeout=30)
        rows = data.get("publisherModels", data.get("models", []))
        return [{"id": str(item.get("name", "")).split("/")[-1], "name": item.get("displayName") or item.get("name")} for item in rows]


@register_provider
class CohereProvider(ModelProvider):
    key = "cohere"

    def call(self, request: ModelRequest) -> ModelResponse:
        base = (self.base_url or "https://api.cohere.com").rstrip("/")
        body = {"model": request.model, "messages": request.messages, "temperature": request.temperature, "max_tokens": request.max_tokens, "stream": False}
        data = _http_json("POST", f"{base}/v2/chat", body=body, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=self.options.get("timeout", 120))
        text = _as_text(_path_value(data, "message.content", []))
        return _usage_response(data, request, text, self.key, input_path="usage.tokens.input_tokens", output_path="usage.tokens.output_tokens")

    def list_models(self) -> list[dict]:
        base = (self.base_url or "https://api.cohere.com").rstrip("/")
        data = _http_json("GET", f"{base}/v1/models", headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30)
        return [{"id": item.get("name"), "name": item.get("name")} for item in data.get("models", [])]


@register_provider
class ReplicateProvider(ModelProvider):
    key = "replicate"

    def call(self, request: ModelRequest) -> ModelResponse:
        base = (self.base_url or "https://api.replicate.com/v1").rstrip("/")
        body = {"input": {"prompt": _prompt_text(request.messages), "max_tokens": request.max_tokens, "temperature": request.temperature, **(self.options.get("model_input") or {})}}
        model_path = quote(request.model, safe="/")
        data = _http_json("POST", f"{base}/models/{model_path}/predictions", body=body, headers={"Authorization": f"Bearer {self.api_key}", "Prefer": "wait=60"}, timeout=self.options.get("timeout", 90))
        deadline = time.monotonic() + min(int(self.options.get("poll_timeout", 120)), 300)
        while data.get("status") in {"starting", "processing"} and time.monotonic() < deadline:
            time.sleep(1)
            poll_url = _path_value(data, "urls.get")
            if not poll_url:
                break
            data = _http_json("GET", poll_url, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30)
        if data.get("status") in {"failed", "canceled"}:
            raise ProviderError(f"Replicate prediction {data.get('status')}: {data.get('error', '')}")
        text = _as_text(data.get("output"))
        return _usage_response(data, request, text, self.key, input_path="metrics.input_token_count", output_path="metrics.output_token_count")

    def list_models(self) -> list[dict]:
        base = (self.base_url or "https://api.replicate.com/v1").rstrip("/")
        data = _http_json("GET", f"{base}/models", headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30)
        return [{"id": f"{item.get('owner')}/{item.get('name')}", "name": f"{item.get('owner')}/{item.get('name')}"} for item in data.get("results", [])]


@register_provider
class CloudflareProvider(ModelProvider):
    key = "cloudflare"

    def call(self, request: ModelRequest) -> ModelResponse:
        account_id = self.credentials.get("account_id") or self.options.get("account_id")
        if not account_id:
            raise ProviderError("Cloudflare Account ID is required")
        base = (self.base_url or "https://api.cloudflare.com/client/v4").rstrip("/")
        url = f"{base}/accounts/{quote(str(account_id), safe='')}/ai/run/{quote(request.model, safe='@/')}"
        data = _http_json("POST", url, body={"messages": request.messages, "max_tokens": request.max_tokens, "temperature": request.temperature}, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=self.options.get("timeout", 120))
        if data.get("success") is False:
            raise ProviderError(f"Cloudflare Workers AI failed: {data.get('errors')}")
        text = _as_text(_path_value(data, "result.response", data.get("result")))
        return _usage_response(data, request, text, self.key, input_path="result.usage.prompt_tokens", output_path="result.usage.completion_tokens")

    def list_models(self) -> list[dict]:
        account_id = self.credentials.get("account_id") or self.options.get("account_id")
        if not account_id:
            raise ProviderError("Cloudflare Account ID is required")
        base = (self.base_url or "https://api.cloudflare.com/client/v4").rstrip("/")
        data = _http_json("GET", f"{base}/accounts/{quote(str(account_id), safe='')}/ai/models/search", headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30)
        return [{"id": item.get("name"), "name": item.get("name")} for item in data.get("result", [])]


def _template_value(value, variables):
    if isinstance(value, dict):
        return {key: _template_value(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [_template_value(item, variables) for item in value]
    if isinstance(value, str):
        exact = re_full_placeholder(value)
        if exact in variables:
            return variables[exact]
        rendered = value
        for key, item in variables.items():
            rendered = rendered.replace("{{" + key + "}}", json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item))
        return rendered
    return value


def re_full_placeholder(value: str) -> str:
    return value[2:-2].strip() if value.startswith("{{") and value.endswith("}}") and value.count("{{") == 1 else ""


@register_provider
class GenericRESTProvider(ModelProvider):
    """Configurable JSON REST transport for specialised and self-hosted APIs.

    Config supports method/path/headers/request_template/response_path plus an
    optional asynchronous poll_url_path/status_path/result_path contract.
    Placeholders: model, messages, prompt, temperature and max_tokens.
    """

    key = "generic_rest"

    def call(self, request: ModelRequest) -> ModelResponse:
        if not self.base_url:
            raise ProviderError("A base URL is required for Generic REST")
        variables = {
            "model": request.model,
            "messages": request.messages,
            "prompt": _prompt_text(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            **self.credentials,
        }
        path = _template_value(str(self.options.get("path") or "/v1/chat/completions"), variables)
        url = path if str(path).startswith("http") else f"{self.base_url.rstrip('/')}/{str(path).lstrip('/')}"
        template = self.options.get("request_template") or {"model": "{{model}}", "messages": "{{messages}}", "temperature": "{{temperature}}", "max_tokens": "{{max_tokens}}"}
        headers = _template_value(self.options.get("headers") or {}, variables)
        auth_header = self.options.get("auth_header", "Authorization")
        auth_prefix = self.options.get("auth_prefix", "Bearer ")
        if self.api_key and auth_header:
            headers[auth_header] = f"{auth_prefix}{self.api_key}"
        data = _http_json(str(self.options.get("method", "POST")), url, body=_template_value(template, variables), headers=headers, timeout=self.options.get("timeout", 120))
        poll_path = self.options.get("poll_url_path")
        if poll_path:
            deadline = time.monotonic() + min(int(self.options.get("poll_timeout", 120)), 300)
            status_path = self.options.get("status_path", "status")
            success = set(self.options.get("success_values") or ["succeeded", "completed", "success"])
            failure = set(self.options.get("failure_values") or ["failed", "canceled", "error"])
            while str(_path_value(data, status_path, "")).lower() not in success and time.monotonic() < deadline:
                status = str(_path_value(data, status_path, "")).lower()
                if status in failure:
                    raise ProviderError(f"Provider job failed: {_path_value(data, self.options.get('error_path', 'error'), status)}")
                poll_url = _path_value(data, poll_path)
                if not poll_url:
                    break
                time.sleep(float(self.options.get("poll_interval", 1)))
                data = _http_json("GET", poll_url, headers=headers, timeout=30)
        text = _as_text(_path_value(data, self.options.get("response_path", "choices.0.message.content"), data))
        return _usage_response(data, request, text, self.key, input_path=self.options.get("input_tokens_path", "usage.prompt_tokens"), output_path=self.options.get("output_tokens_path", "usage.completion_tokens"))

    def list_models(self) -> list[dict]:
        path = self.options.get("models_path")
        if not path:
            return []
        url = path if str(path).startswith("http") else f"{self.base_url.rstrip('/')}/{str(path).lstrip('/')}"
        headers = dict(self.options.get("headers") or {})
        if self.api_key:
            headers[self.options.get("auth_header", "Authorization")] = f"{self.options.get('auth_prefix', 'Bearer ')}{self.api_key}"
        data = _http_json("GET", url, headers=headers, timeout=30)
        rows = _path_value(data, self.options.get("models_response_path", "data"), [])
        return [{"id": str(item.get("id") or item.get("name")), "name": str(item.get("name") or item.get("id"))} for item in rows if isinstance(item, dict)]
