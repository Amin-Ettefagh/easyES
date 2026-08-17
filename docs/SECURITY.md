# Security

This document describes the security posture of the easyES
Foundation/Demo: authentication, tenant isolation, authorization, secret
handling, input validation, web-security defaults, and the sandboxing of
agent tool execution. Some items are hardened for the demo and others are
explicitly deferred to the roadmap; both are called out.

See also: [API.md](API.md), [MODEL_GATEWAY.md](MODEL_GATEWAY.md),
[AGENT_SYSTEM.md](AGENT_SYSTEM.md), [DATABASE.md](DATABASE.md).

## 1. Password hashing

- Passwords are stored using Django's default password hashers
  (PBKDF2-SHA256, with Argon2 available when the extra is installed).
  Plaintext passwords are never stored or logged.
- Django's password validators are enabled (minimum length, common-
  password, numeric, and user-attribute-similarity checks).
- The demo user `amin` / `123456` is **seeded only in development**
  (`DJANGO_ENV=dev`); the seed command refuses to create it in
  production settings.

## 2. Authentication — JWT and session

Two mechanisms coexist (see [API.md](API.md) §2):

- **SimpleJWT** for programmatic and frontend clients: short-lived access
  tokens, rotating refresh tokens, and refresh-token blacklisting on
  logout.
- **Django session** for the browsable API and Swagger UI.

Safety measures:

- Access tokens are short-lived; refresh tokens rotate and are
  invalidated on logout.
- Tokens are signed with `SECRET_KEY` / a dedicated signing key sourced
  from the environment, never committed.
- Cookies (session, and refresh cookie if used) are `HttpOnly`, `Secure`
  (in production), and `SameSite=Lax`.
- No credentials or tokens are ever written to logs or emitted as events.

## 3. Organization isolation (multi-tenancy)

Isolation is a first-class concern from the first migration (see
[DATABASE.md](DATABASE.md)):

- Every business object carries `organization_id` (directly or via a
  short FK chain).
- The active organization is derived from the authenticated principal's
  `Membership`; **all** business queries are filtered by it in the
  service/queryset layer.
- Cross-tenant access returns **404, not 403**, so the API never reveals
  the existence of another tenant's objects.
- The SSE event stream is org-scoped the same way (see
  [REALTIME.md](REALTIME.md)).
- Tenant isolation is covered by dedicated permission tests (see
  [TESTING.md](TESTING.md)); a user in org A must never read, list, or
  stream anything in org B.

*Deferred:* database row-level security and fine-grained
relationship-based authorization (OpenFGA/Casbin) are roadmap items; the
demo enforces isolation in application code.

## 4. Authorization

- **Coarse (org role):** `Membership.org_role` (owner/admin/member) gates
  administrative actions within an organization.
- **Fine (policy hierarchy):** the `policies` app + `core/rules` resolve
  Platform → Organization → Project → Workflow → Agent → Task, with the
  most specific rule winning (effect = allow / deny / require_approval).
  This governs, e.g., "AI cannot deploy to production without human
  approval" as an `Approval` node backed by a policy.
- Control endpoints check both the org scope and the applicable policy
  before mutating state; a permitted-but-out-of-state action returns
  `409`, an unauthorized action returns `403`, a cross-tenant target
  returns `404`.

## 5. Secret masking and handling

- Provider **credentials are encrypted at rest** (`Credential.
  secret_encrypted`) and decrypted only in memory, only at model-call
  time, only for the resolved adapter (see [MODEL_GATEWAY.md](MODEL_GATEWAY.md)).
- The credential serializer is **write-only** for the secret; API
  responses return only a masked label, never the value.
- Secrets are **never logged, never emitted in events, never included in
  error messages** — provider errors and `health_check` output are
  scrubbed before they reach logs or the stream.
- `SECRET_KEY`, signing keys, database URLs, and the credential-
  encryption key come from environment variables and are excluded from
  version control.
- The default offline demo uses the FakeModelProvider, which needs no
  credential, so a clean demo stores no external secrets at all.

## 6. Input validation

- All write endpoints validate through DRF serializers; unknown fields
  are rejected and types are enforced.
- Workflow graphs are validated on save: node types must be known, edges
  must reference existing nodes, and cycles are permitted **only** through
  a `Loop` construct — an unbounded cycle is rejected with `422` (see
  [API.md](API.md), [WORKFLOW_ENGINE.md](WORKFLOW_ENGINE.md)).
- Condition expressions on edges are evaluated in a **restricted,
  sandboxed evaluator** over named context values only — no arbitrary
  Python, no attribute access, no imports.
- JSON fields (node config, contracts, payloads) are schema-checked at
  the boundary where a known shape exists.

## 7. CSRF and CORS

- **CSRF:** session-authenticated, state-changing requests are protected
  by Django's CSRF middleware. JWT-authenticated API calls are exempt by
  design (no ambient cookie is used for JWT auth), which avoids CSRF for
  the token path while keeping the browsable API safe.
- **CORS:** an explicit allowlist (`CORS_ALLOWED_ORIGINS`) is configured
  for the frontend origin(s); credentials are only allowed for trusted
  origins. Wildcard origins are never used in production.

## 8. Web-security defaults (production)

- HTTPS enforced (`SECURE_SSL_REDIRECT`), HSTS enabled.
- `SECURE_CONTENT_TYPE_NOSNIFF`, `X-Frame-Options: DENY`, and a
  restrictive `Referrer-Policy`.
- `DEBUG=False` in production; `ALLOWED_HOSTS` set explicitly.
- Errors return sanitized messages; stack traces are never shown to
  clients.

## 9. Restricted agent tool and shell access

Agent-invoked tools are the highest-risk surface and are constrained on
several axes (see [AGENT_SYSTEM.md](AGENT_SYSTEM.md) §5):

- **Least privilege:** an Agent may call only the Tools it holds a
  `ToolPermission` for; grants carry a `scope` and `constraints` and can
  be disabled without deletion.
- **Every call logged:** each tool invocation writes a `ToolCall` and
  `TOOL_CALL_*` events (WHO/WHAT/WHEN/result) — full auditability.
- **Shell/Code limits:** execution runs with timeouts, no ambient network
  unless the HTTP tool is explicitly granted with an allowed-host scope,
  and constrained resource use.
- **Git/HTTP scoping:** Git can be granted read-only; HTTP is limited to
  allowlisted hosts per grant.

## 10. Workspace sandboxing

File, Code, Shell, and TestRunner tools operate **only** within the
per-project workspace:

```text
D:\easyES\data\workspaces\<project-id>\
```

- Paths are resolved and checked against the workspace root **before**
  any filesystem operation; traversal outside the root (`..`, absolute
  paths, symlinks escaping the root) is rejected by the tool abstraction.
- Each project gets its own workspace, so one project's agents cannot read
  or write another project's files.
- The workspace is the unit of cleanup/reset (see
  [DEPLOYMENT.md](DEPLOYMENT.md)).

*Deferred (roadmap):* stronger isolation via containerized/E2B-style
sandboxes with per-execution filesystem, network policy, and resource
limits. The current filesystem sandbox is adequate for the offline demo,
where the FakeModelProvider produces the "code" and no untrusted external
model output is executed against real systems.

## 11. Observability without leaking

The event/audit system records the substance of every action — Decision
Summary, Action Summary, Evidence, Tool Calls, Inputs, Outputs, Result,
plus cost/tokens/prompt version for AI — but **never** private
chain-of-thought and **never** secrets. This gives strong auditability
while keeping sensitive material out of the trail (see
[DOMAIN_MODEL.md](DOMAIN_MODEL.md) §11, §15).

## 12. Summary — enforced now vs. deferred

| Area | Demo (enforced) | Deferred (roadmap) |
| ---- | --------------- | ------------------ |
| Passwords | PBKDF2/Argon2, validators | — |
| Auth | JWT (rotating) + session | SSO/OIDC via Keycloak |
| Tenant isolation | App-layer org scoping, 404 on cross-tenant | DB row-level security |
| AuthZ | Org role + policy hierarchy | OpenFGA/Casbin fine-grained |
| Secrets | Encrypted at rest, masked, never logged | External secret manager |
| Tool access | Per-agent grants, logged, workspace-bound | Container/E2B sandboxes |
| Web | CSRF, CORS allowlist, HSTS, secure cookies | — |
