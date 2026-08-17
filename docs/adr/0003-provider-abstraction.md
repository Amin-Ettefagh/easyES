# ADR 0003 — Model Provider Abstraction

- **Status:** Accepted
- **Date:** 2026-08-08
- **Deciders:** Platform architecture

## Context

The platform must support many model providers (OpenAI, Anthropic,
Gemini, local/self-hosted) and let **each Agent** pick a different
provider, model, credential, and budget. It must also run as a
**deterministic, offline demo with no API keys**, and it must record
tokens, cost, latency, and prompt version uniformly for governance and
the future learning loop.

If domain code or the workflow engine called provider SDKs directly, we
would couple the platform to vendors, make offline/testing impossible,
and scatter budget and credential handling across the codebase. The R&D
references (LiteLLM, Portkey) show the value of a single unified interface
in front of all providers.

## Decision

Introduce a **`ModelProvider` abstraction** in `core/model_gateway` as the
sole boundary to any model.

- Interface: `call`, `stream`, `estimate_cost`, `health_check`.
- Adapters are registered by provider `kind`; adding a provider is purely
  additive (implement the interface, register it, add
  Provider/Model/Credential rows, point an Agent at it).
- The gateway — not the adapters — performs budget checks
  (`estimate_cost` vs the Agent's `cost_budget`/`token_budget`),
  persists `ModelCall`, and emits `MODEL_CALL_*` events.
- The default adapter is the **FakeModelProvider**: deterministic,
  offline, keyed on `(agent, node, iteration)` so it can script the
  demo's success/failure/retry narrative. An `OpenAICompatibleProvider`
  stub shows the real-HTTP shape.
- Credentials are encrypted at rest and decrypted only in memory at call
  time; never logged or serialized.

See [MODEL_GATEWAY.md](../MODEL_GATEWAY.md).

## Consequences

**Positive**

- Vendor-neutral domain; providers are swappable per Agent.
- Fully offline, reproducible demo and tests via the Fake provider.
- Uniform cost/token/latency/prompt-version accounting in one place —
  the basis for budgets, analytics, and learning.
- Credential isolation and budget enforcement are centralized, not
  duplicated.

**Negative / trade-offs**

- An abstraction layer to maintain as provider APIs evolve.
- The interface may need extension for advanced features (tool-calling,
  multimodal, structured output) as real providers are added.
- Cost estimation accuracy depends on per-provider pricing metadata.

## Alternatives considered

- **Direct SDK calls in handlers** — rejected: vendor lock-in, no offline
  mode, scattered budget/credential logic, untestable.
- **Adopt LiteLLM/Portkey now as the only gateway** — deferred: excellent
  fit for Phase 1, but the demo needs a deterministic Fake provider and a
  minimal interface first; the abstraction lets LiteLLM slot in later
  behind the same seam.
- **One global model/provider for all agents** — rejected: violates the
  Agent ≠ Model decoupling and the per-agent-configuration requirement.
