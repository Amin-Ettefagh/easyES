# Provider Gateway

The gateway catalogue is generated from `Provider.txt` and currently exposes
148 requested vendors plus seven local/custom runtimes. Providers are grouped
by capability instead of being incorrectly treated as interchangeable chat
APIs.

Catalogue presence and transport readiness are intentionally separate:

- Native adapters implement the vendor's current authentication, request and
  response contract directly.
- OpenAI-compatible entries are ready after endpoint/key/model configuration.
- Specialized image, video, audio, search, OCR, translation and infrastructure
  entries use the configurable REST contract. Their card remains explicit about
  that requirement rather than pretending the service is a chat model.
- `Custom REST` is the escape hatch for a private or future provider: users can
  replace the complete URL, headers, request template, response paths and async
  polling contract without a backend code change.

## Runtime adapter families

| Adapter | Request contract | Authentication |
| --- | --- | --- |
| `openai_responses` | `POST /responses` | Bearer API key |
| `openai_compatible` | `POST /chat/completions`, `GET /models` | Bearer key or optional local token |
| `anthropic` | `POST /messages` | `x-api-key` + `anthropic-version` |
| `gemini` | `models/{model}:generateContent` | `x-goog-api-key` |
| `azure_openai` | `{endpoint}/openai/v1/responses` | `api-key` |
| `bedrock` | AWS SDK `Converse` | access key/secret/session token + region |
| `vertex` | Vertex `generateContent` | encrypted service-account JSON + OAuth token |
| `cohere` | `POST /v2/chat` | Bearer API key |
| `replicate` | prediction create + bounded polling | Bearer token |
| `cloudflare` | account-scoped Workers AI `ai/run` | Bearer token + account ID |
| `generic_rest` | configurable JSON request/response/polling | configurable header/prefix |

The OpenAI-compatible family covers hosted gateways and local servers such as
Ollama, vLLM, LM Studio, LocalAI, Hugging Face TGI and user-hosted endpoints.
The UI uses `host.docker.internal` in local presets because `localhost` inside
the backend container refers to the container itself.

## Custom REST contract

Provider `config` may define:

```json
{
  "method": "POST",
  "path": "/v1/generate/{{model}}",
  "headers": {"X-Account": "{{account_id}}"},
  "auth_header": "Authorization",
  "auth_prefix": "Bearer ",
  "request_template": {
    "messages": "{{messages}}",
    "prompt": "{{prompt}}",
    "temperature": "{{temperature}}",
    "max_tokens": "{{max_tokens}}"
  },
  "response_path": "result.output.text",
  "models_path": "/v1/models",
  "models_response_path": "data",
  "poll_url_path": "urls.get",
  "status_path": "status",
  "success_values": ["succeeded", "completed"],
  "failure_values": ["failed", "canceled"],
  "error_path": "error"
}
```

Exact placeholders return structured values, so `"{{messages}}"` becomes an
array rather than a JSON-encoded string. Poll duration and request timeouts are
bounded by the adapter.

## Secret handling

Credential documents are serialized once, encrypted with Fernet and stored in
the `secret_encrypted` column. The API returns only field names and masked
hints. Updating some credential fields merges them with the existing encrypted
document; an empty UI field preserves its previous value.

## Official protocol references

- OpenAI Responses: https://developers.openai.com/api/docs/guides/latest-model
- Anthropic Messages: https://platform.claude.com/docs/en/api/messages
- Gemini API: https://ai.google.dev/api
- Azure OpenAI Responses: https://learn.microsoft.com/en-us/rest/api/microsoft-foundry/azureopenai/responses
- Amazon Bedrock APIs: https://docs.aws.amazon.com/bedrock/latest/userguide/apis.html
- Vertex generateContent: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference
- Cohere Chat v2: https://docs.cohere.com/v2/reference/chat
- Replicate HTTP API: https://replicate.com/docs/reference/http/
- Cloudflare Workers AI REST: https://developers.cloudflare.com/workers-ai/get-started/rest-api/
- Hugging Face Inference Providers: https://huggingface.co/docs/inference-providers/en/index
- Ollama compatibility: https://docs.ollama.com/api/openai-compatibility
- vLLM server: https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/
- LM Studio APIs: https://lmstudio.ai/docs/developer

## Taxonomy import

`python manage.py import_role_catalog --organization amin` parses `roll.md` and
`SoftwareEngineerCompanySamples.html`, normalizes acronym aliases, creates the
category units, and provisions exactly one editable Agent + Actor per unique
Role. Imported agents intentionally have no prompt assignment. The command is
idempotent and is run during Docker startup when
`EASYES_IMPORT_ROLE_CATALOG=1`.
