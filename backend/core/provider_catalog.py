"""Provider catalogue loaded from the project's ``Provider.txt`` source.

The source contains services with very different capabilities (LLM, media,
speech, search, document processing and infrastructure).  This module does not
pretend that they all implement chat completions.  Instead every entry exposes
its capability, authentication fields and the transport adapter that can be
used by the model gateway.  Unknown/specialised APIs remain usable through the
configurable ``generic_rest`` adapter.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.utils.text import slugify


LOCAL_PROVIDERS = [
    ("Ollama (local)", "ollama-local", "http://host.docker.internal:11434/v1", "https://docs.ollama.com/api/openai-compatibility"),
    ("vLLM (local)", "vllm-local", "http://host.docker.internal:8000/v1", "https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/"),
    ("LM Studio (local)", "lm-studio-local", "http://host.docker.internal:1234/v1", "https://lmstudio.ai/docs/developer/openai-compat"),
    ("LocalAI (local)", "localai-local", "http://host.docker.internal:8080/v1", "https://localai.io/basics/getting_started/"),
    ("Hugging Face TGI (local)", "tgi-local", "http://host.docker.internal:8080/v1", "https://huggingface.co/docs/text-generation-inference/reference/api_reference"),
    ("Custom OpenAI-compatible", "custom-openai-compatible", "", ""),
    ("Custom REST / self-hosted", "custom-rest", "", ""),
]


# Stable overrides backed by the vendors' public API documentation. Providers
# not listed here still appear in the catalogue and use Generic REST templates.
OVERRIDES = {
    "openai": ("openai_responses", "https://api.openai.com/v1"),
    "google-gemini-api": ("gemini", "https://generativelanguage.googleapis.com/v1beta"),
    "microsoft-azure-ai-foundry": ("azure_openai", ""),
    "amazon-bedrock": ("bedrock", ""),
    "anthropic": ("anthropic", "https://api.anthropic.com/v1"),
    "google-vertex-ai": ("vertex", ""),
    "nvidia-nim-api-catalog": ("openai_compatible", "https://integrate.api.nvidia.com/v1"),
    "hugging-face-inference-providers": ("openai_compatible", "https://router.huggingface.co/v1"),
    "openrouter": ("openai_compatible", "https://openrouter.ai/api/v1"),
    "xai": ("openai_compatible", "https://api.x.ai/v1"),
    "deepseek": ("openai_compatible", "https://api.deepseek.com"),
    "mistral-ai": ("openai_compatible", "https://api.mistral.ai/v1"),
    "together-ai": ("openai_compatible", "https://api.together.ai/v1"),
    "groq": ("openai_compatible", "https://api.groq.com/openai/v1"),
    "replicate": ("replicate", "https://api.replicate.com/v1"),
    "cloudflare-workers-ai": ("cloudflare", "https://api.cloudflare.com/client/v4"),
    "fireworks-ai": ("openai_compatible", "https://api.fireworks.ai/inference/v1"),
    "cohere": ("cohere", "https://api.cohere.com"),
    "alibaba-cloud-model-studio-qwen": ("openai_compatible", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"),
    "github-models": ("openai_compatible", "https://models.github.ai/inference"),
    "cerebras": ("openai_compatible", "https://api.cerebras.ai/v1"),
    "deepinfra": ("openai_compatible", "https://api.deepinfra.com/v1/openai"),
    "moonshot-ai-kimi": ("openai_compatible", "https://api.moonshot.ai/v1"),
    "zai-glm": ("openai_compatible", "https://api.z.ai/api/paas/v4"),
    "sambanova-cloud": ("openai_compatible", "https://api.sambanova.ai/v1"),
    "nebius-ai-studio": ("openai_compatible", "https://api.tokenfactory.nebius.com/v1"),
    "aiml-api": ("openai_compatible", "https://api.aimlapi.com/v1"),
    "novita-ai": ("openai_compatible", "https://api.novita.ai/openai"),
    "siliconflow": ("openai_compatible", "https://api.siliconflow.com/v1"),
    "hyperbolic": ("openai_compatible", "https://api.hyperbolic.xyz/v1"),
    "friendliai": ("openai_compatible", "https://api.friendli.ai/serverless/v1"),
    "featherless-ai": ("openai_compatible", "https://api.featherless.ai/v1"),
    "chutes": ("openai_compatible", "https://llm.chutes.ai/v1"),
    "scaleway-generative-apis": ("openai_compatible", "https://api.scaleway.ai/v1"),
    "vercel-ai-gateway": ("openai_compatible", "https://ai-gateway.vercel.sh/v1"),
    "portkey": ("openai_compatible", "https://api.portkey.ai/v1"),
    "litellm": ("openai_compatible", ""),
    "requesty": ("openai_compatible", "https://router.requesty.ai/v1"),
    "zenmux": ("openai_compatible", "https://zenmux.ai/api/v1"),
    "poe-api": ("openai_compatible", "https://api.poe.com/v1"),
    "perplexity-api": ("openai_compatible", "https://api.perplexity.ai"),
    "cloudflare-ai-gateway": ("openai_compatible", ""),
}


DOC_OVERRIDES = {
    "openai": "https://developers.openai.com/api/docs/guides/latest-model",
    "anthropic": "https://platform.claude.com/docs/en/api/messages",
    "google-gemini-api": "https://ai.google.dev/api",
    "microsoft-azure-ai-foundry": "https://learn.microsoft.com/en-us/rest/api/microsoft-foundry/azureopenai/responses",
    "amazon-bedrock": "https://docs.aws.amazon.com/bedrock/latest/userguide/apis.html",
    "google-vertex-ai": "https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference",
    "cohere": "https://docs.cohere.com/v2/reference/chat",
    "replicate": "https://replicate.com/docs/reference/http/",
    "cloudflare-workers-ai": "https://developers.cloudflare.com/workers-ai/get-started/rest-api/",
}


def _clean_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _source_path() -> Path | None:
    candidates = [
        Path(settings.BASE_DIR) / "catalog" / "Provider.txt",
        Path(settings.BASE_DIR).parent / "Provider.txt",
        Path("/app/catalog/Provider.txt"),
    ]
    return next((path for path in candidates if path.exists()), None)


def _capability_for(index: int) -> tuple[str, list[str]]:
    if index in {21, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116}:
        return "audio", ["speech", "audio"]
    if 117 <= index <= 120:
        return "music", ["music", "audio"]
    if 75 <= index <= 89 or index in {22, 26, 27}:
        return "image", ["image"]
    if 90 <= index <= 98 or index in {28, 29, 30}:
        return "video", ["video"]
    if 121 <= index <= 125:
        return "embedding", ["embedding", "rerank"]
    if 126 <= index <= 130:
        return "search", ["search", "retrieval"]
    if 131 <= index <= 140 or index in {23, 46}:
        return "infrastructure", ["hosting", "custom_endpoint"]
    if 141 <= index <= 144:
        return "document", ["document", "ocr"]
    if 145 <= index <= 148:
        return "translation", ["translation"]
    if 56 <= index <= 69:
        return "gateway", ["text", "gateway", "routing"]
    return "language", ["text", "chat"]


def _credential_fields(adapter: str, local: bool = False) -> list[dict]:
    if local:
        return [{"key": "api_key", "label": "API key (optional)", "secret": True, "required": False}]
    if adapter == "bedrock":
        return [
            {"key": "aws_access_key_id", "label": "AWS access key ID", "secret": True, "required": True},
            {"key": "aws_secret_access_key", "label": "AWS secret access key", "secret": True, "required": True},
            {"key": "aws_session_token", "label": "AWS session token", "secret": True, "required": False},
            {"key": "region", "label": "AWS region", "secret": False, "required": True},
        ]
    if adapter == "vertex":
        return [
            {"key": "service_account_json", "label": "Service account JSON", "secret": True, "required": True, "multiline": True},
            {"key": "project_id", "label": "Google Cloud project", "secret": False, "required": True},
            {"key": "location", "label": "Location", "secret": False, "required": True},
        ]
    if adapter == "cloudflare":
        return [
            {"key": "api_key", "label": "API token", "secret": True, "required": True},
            {"key": "account_id", "label": "Account ID", "secret": False, "required": True},
        ]
    return [{"key": "api_key", "label": "API key / token", "secret": True, "required": adapter != "generic_rest"}]


def provider_catalog() -> list[dict]:
    entries: list[dict] = []
    path = _source_path()
    if path:
        pattern = re.compile(r"^\s*(\d+)\.\s+\[([^]]+)]\(([^)]+)\)")
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            match = pattern.match(line)
            if not match:
                continue
            index = int(match.group(1))
            name = match.group(2).strip()
            key = slugify(name.replace("/", " "))[:80]
            category, capabilities = _capability_for(index)
            adapter, base_url = OVERRIDES.get(key, ("generic_rest", ""))
            entries.append({
                "index": index,
                "key": key,
                "name": name,
                "category": category,
                "capabilities": capabilities,
                "adapter": adapter,
                "base_url": base_url,
                "website": _clean_url(match.group(3)),
                "docs_url": DOC_OVERRIDES.get(key, _clean_url(match.group(3))),
                "credential_fields": _credential_fields(adapter),
                "configuration_required": not bool(base_url) or adapter == "generic_rest",
                "local": False,
            })

    start = len(entries) + 1
    for offset, (name, key, base_url, docs_url) in enumerate(LOCAL_PROVIDERS):
        adapter = "generic_rest" if key == "custom-rest" else "openai_compatible"
        entries.append({
            "index": start + offset,
            "key": key,
            "name": name,
            "category": "local",
            "capabilities": ["text", "chat", "local"],
            "adapter": adapter,
            "base_url": base_url,
            "website": docs_url,
            "docs_url": docs_url,
            "credential_fields": _credential_fields(adapter, local=True),
            "configuration_required": not bool(base_url) or key.startswith("custom"),
            "local": True,
        })
    return entries


def get_catalog_entry(key: str) -> dict | None:
    return next((entry for entry in provider_catalog() if entry["key"] == key), None)
