# Model Gateway

The Model Gateway (`core/model_gateway`) is the single boundary between
the platform and any language-model provider. Nothing in the domain or
the workflow engine imports a provider SDK directly; everything goes
through the gateway. This keeps the platform vendor-neutral and lets the
demo run fully offline and deterministically.

See also: [AGENT_SYSTEM.md](AGENT_SYSTEM.md),
[adr/0003-provider-abstraction.md](adr/0003-provider-abstraction.md),
[SECURITY.md](SECURITY.md).

## 1. The ModelProvider interface

Every provider implements one small interface. The gateway resolves an
`Agent`'s `(provider, model, credential)` into a concrete adapter and
calls it.

```python
# core/model_gateway/base.py  (illustrative)
class ModelRequest:
    model: str
    messages: list[Message]        # structured, role-tagged
    temperature: float
    max_tokens: int
    context_limit: int
    metadata: dict                 # agent id, prompt_version, project, task

class ModelResponse:
    text: str
    input_tokens: int
    output_tokens: int
    cost: Decimal
    latency_ms: int
    finish_reason: str

class ModelProvider(Protocol):
    def call(self, req: ModelRequest, *, credential: Secret) -> ModelResponse: ...
    def stream(self, req: ModelRequest, *, credential: Secret) -> Iterator[str]: ...
    def estimate_cost(self, req: ModelRequest) -> Decimal: ...
    def health_check(self) -> HealthStatus: ...
```

| Method | Responsibility |
| ------ | -------------- |
| `call` | Synchronous completion; returns text + token/cost/latency accounting |
| `stream` | Token/chunk iterator for streaming UIs |
| `estimate_cost` | Pre-flight budget check before the call is made |
| `health_check` | Liveness/readiness of the provider (used by ops + UI) |

The gateway wraps every `call` to: check the Agent's budget via
`estimate_cost`, emit `MODEL_CALL_STARTED`, persist a `ModelCall`, and emit
`MODEL_CALL_COMPLETED` with tokens and cost — regardless of which adapter
runs. Providers never touch the database or emit events themselves.

## 2. Resolution flow

```text
AgentTask handler
   │  Agent(provider, model, credential, temperature, max_tokens, budget)
   ▼
ModelGateway.call(agent, messages, prompt_version)
   │
   ├─ resolve adapter  ── ProviderRegistry[provider.kind] ─▶ FakeModelProvider
   │                                                       └▶ OpenAICompatibleProvider
   ├─ decrypt credential (in memory only; never logged)
   ├─ estimate_cost → check agent.cost_budget / token_budget
   ├─ emit MODEL_CALL_STARTED
   ├─ adapter.call(req, credential)
   ├─ persist ModelCall (tokens, cost, latency, prompt_version)
   └─ emit MODEL_CALL_COMPLETED  ──▶ accrues to WorkflowRun.cost_accum
```

## 3. Adapters

| Adapter | Status | Purpose |
| ------- | ------ | ------- |
| **FakeModelProvider** | Default, complete | Deterministic, offline; powers the demo and tests |
| **OpenAICompatibleProvider** | Stub | Shows how a real HTTP provider (OpenAI-style `/chat/completions`) plugs in |
| Anthropic / Gemini / local | Not implemented | Documented seams for later; added by implementing the interface only |

Adapters are registered by provider `kind`, so adding a real provider is
purely additive: implement `ModelProvider`, register it, create a
`Provider` + `Model` + `Credential` row, and point an Agent at it. No
engine or domain code changes. The roadmap replaces bespoke adapters with
a LiteLLM/Portkey-style unified backend (see [ROADMAP.md](ROADMAP.md)).

## 4. FakeModelProvider — deterministic behavior

The FakeModelProvider is the heart of the offline demo. It returns
scripted outputs keyed on `(agent, node/prompt, iteration)`, so the whole
software-company run is reproducible byte-for-byte.

### Determinism model

```text
key = (agent.name, node.name, run.iteration_for(node))
response = SCRIPT[key]        # canned text + token counts + cost
```

Because the key includes the **iteration**, the provider can encode the
"fail first, pass second" narrative directly:

```text
SCRIPT[("Engineer", "Development", 1)]  → code with a deliberate null-check bug
SCRIPT[("QA",        "Testing",     1)]  → "2 tests failing; critical_errors=1"
SCRIPT[("Engineer", "Development", 2)]  → corrected code (uses iteration-1 feedback)
SCRIPT[("QA",        "Testing",     2)]  → "all tests pass; critical_errors=0"
```

### Scenarios it can produce

| Scenario | How it is scripted |
| -------- | ------------------ |
| **Success** | Return valid output; QA metrics above the gate threshold |
| **Failure** | Return output that the TestRunner tool marks as failing; QA metrics below threshold |
| **Retry / loop** | Iteration 1 fails, iteration 2 (with feedback in context) passes → exercises the fix→retest loop |
| **Budget exhaustion** | Report token/cost figures that trip an Agent's `cost_budget`, letting `MAX_COST` fire |
| **Provider error** | Raise a simulated transient error to exercise `FATAL_ERROR` / retry paths |

Token counts and costs are deterministic constants per scripted response,
so cost accumulation, budget checks, and the `MAX_COST` stop condition are
all testable without a network. `estimate_cost` returns the same figure
the response will report.

### Configuring the script

The script is data (a Python dict or a seeded fixture), not code branches,
so new demo narratives are added by editing the script — the provider
logic stays a simple lookup. `stream()` yields the canned text in chunks;
`health_check()` always returns healthy.

## 5. Credential security

- Credentials are stored **encrypted at rest** in the `Credential` table
  (see [DATABASE.md](DATABASE.md)); the plaintext secret is decrypted only
  in memory, only at call time, and only for the resolved adapter.
- Secrets are **never logged, never emitted in events, and never
  serialized in API responses** — the credential serializer is
  write-only for the secret field and returns a masked label.
- The FakeModelProvider needs no credential, so the default offline demo
  stores no secrets at all.
- `health_check` and error messages are scrubbed of any secret material
  before they reach logs or the event stream.

See [SECURITY.md](SECURITY.md) for the full secret-handling policy.

## 6. Why a gateway (not direct calls)

- **Vendor neutrality** — the domain never depends on a provider SDK; the
  platform can run on fake, self-hosted, or commercial models
  interchangeably.
- **Uniform accounting** — tokens, cost, latency, and prompt version are
  recorded the same way for every provider, which is what makes budgets,
  cost analytics, and the future Experience/Learning loop possible.
- **Testability** — the deterministic Fake adapter makes the entire
  execution path unit- and integration-testable offline.
- **Governance** — budget checks and credential isolation happen in one
  place, not scattered across handlers.
