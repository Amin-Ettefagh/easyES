# ADR 0001 — Modular Monolith

- **Status:** Accepted
- **Date:** 2026-08-08
- **Deciders:** Platform architecture

## Context

easyES is a large, ambitious platform (organizations,
structure, actors, agents, models, prompts, tools, projects, workflows,
executions, communications, artifacts, evaluations, policies, audit). The
long-term vision spans durable execution, sandboxing, memory, knowledge,
connectors, and fine-grained authorization.

At the Foundation/Demo stage we have a small team, need fast iteration,
and want a **clean, well-bounded domain model** more than we want
horizontal scale. A microservice topology now would impose network
boundaries, distributed transactions, service discovery, and operational
overhead before the domain boundaries are even proven — and it would slow
the very iteration the demo depends on. At the same time, we must not
paint ourselves into a corner: the decoupled domains must be able to
become independently deployable later if needed.

## Decision

Build the backend as a **modular monolith**: a single Django project with
many well-bounded apps under `backend/apps/`, plus a framework-agnostic
engine under `backend/core/`.

- Each app owns its models, serializers, services, and tests.
- Cross-app interaction goes through **explicit service functions** and
  **domain events**, not by reaching into another app's ORM internals.
- Dependencies flow one direction: Intelligence/Evolution →
  Business/Execution → Foundation → `core/`. `core/` imports nothing from
  `apps/`.
- The whole system runs in one process for the demo (including the
  default thread-based execution backend).

## Consequences

**Positive**

- Fast local development; one migrate, one runserver, one deploy.
- Strong module boundaries and a coherent domain model, enforced by the
  dependency-direction rule.
- Easy end-to-end testing and a deterministic offline demo.
- Clear extraction seams: an app or the engine can later become a service
  because coupling is already explicit.

**Negative / trade-offs**

- No independent scaling or deployment of modules yet.
- Discipline required to prevent sideways coupling between apps (guarded
  by conventions and review).
- A single process is a shared failure domain for the demo (acceptable at
  this stage; durability is a roadmap item).

## Alternatives considered

- **Microservices from day one** — rejected: premature; high operational
  cost; boundaries not yet proven; would slow iteration.
- **Single unstructured Django app** — rejected: would erode the domain
  decoupling that is the whole point of the product.
- **Serverless functions** — rejected: poor fit for a stateful workflow
  engine and long-running executions.
