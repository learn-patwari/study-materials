# Relay — AI Workflow Orchestrator (Capstone Design)

> **What Relay is:** a durable engine that runs multi-step workflows — a mix of deterministic
> steps (HTTP calls, conditions, delays, notifications) and **AI steps** (LLM calls) — with
> **exactly-once side effects**, **human approval gates**, hard **guardrails**, full **tracing**,
> and a lightweight **console**. Workflows are authored, versioned, published, then triggered
> (via webhook or manual API); each run executes step-by-step against a **mocked external world**
> so every side effect is safely idempotent.
>
> This folder is the **implementation design** for that system — the plan an engineer follows to
> build it. It is design/specification, not the running code (the roadmap in
> [`09-Implementation-Roadmap.md`](09-Implementation-Roadmap.md) sequences the build).

---

## The architecture in one line

> Requests come in through a **REST API**, get recorded in **Postgres** (workflows, versions,
> runs, steps, approvals, traces), and flow into a **durable queue** backed by a **worker pool**.
> Workers hand each step to a **node executor** — deterministic or AI — which acts against a
> **mocked external world** so every side effect is idempotent. A **console** sits on top so
> anyone can watch runs, inspect traces, and clear pending approvals.

```mermaid
flowchart LR
  subgraph API[REST API - Spring Boot]
    A1[Workflow CRUD + Publish]
    A2[Triggers: webhook HMAC / manual]
    A3[Approvals + Runs/Traces]
  end
  subgraph DB[(Postgres)]
    D1[workflows / workflow_versions]
    D2[runs / steps]
    D3[approvals / traces]
    D4[outbox queue]
  end
  subgraph ENG[Execution Core]
    Q[Durable Queue - DB outbox -> Kafka/RabbitMQ]
    W[Worker Pool + Step State Machine]
    NE[Node Executors]
  end
  subgraph EXT[Mocked External World]
    H[HTTP adapter]
    L[LLM provider adapter]
  end
  A1 --> D1
  A2 --> D2 --> Q
  Q --> W --> NE --> EXT
  W --> D2
  NE --> D3
  A3 --> D3
  Console[Console UI] --> API
```

---

## Design documents (read in order)

| # | Doc | Covers |
|---|-----|--------|
| 1 | [Architecture](01-Architecture.md) | Components, data flow, control-plane vs data-plane, tech stack |
| 2 | [Data Model](02-Data-Model.md) | Postgres schema (DDL), entities, versioning, state columns |
| 3 | [API Design](03-API-Design.md) | REST endpoints: workflow CRUD/publish, triggers, approvals, runs/traces |
| 4 | [Execution Engine](04-Execution-Engine.md) | Durable queue, worker loop, step state machine, crash recovery, pause/resume |
| 5 | [Node Executors](05-Node-Executors.md) | Deterministic nodes + AI node, provider adapter, JSON-Schema validation |
| 6 | [Guardrails & Security](06-Guardrails-and-Security.md) | Idempotency, max-step cap, approval gates, HMAC, prompt-injection handling |
| 7 | [Tracing & Console](07-Tracing-and-Console.md) | Trace model, observability, console UI |
| 8 | [Testing & Verification](08-Testing-and-Verification.md) | Test plan + the live kill-and-resume demo |
| 9 | [Implementation Roadmap](09-Implementation-Roadmap.md) | Phased milestones and estimates |
| 10 | [Hard Problems](10-Hard-Problems.md) | The three genuinely hard parts and how we solve them |

---

## Design principles (the non-negotiables)

1. **The engine guarantees; the AI never polices itself.** Approval gates and step caps live in
   the engine, enforced structurally — never delegated to an LLM prompt.
2. **Exactly-once side effects.** Every side-effecting call carries an **idempotency key** backed
   by a unique DB constraint, so a mid-step crash never double-acts.
3. **State after every step.** Run state is persisted step-by-step; a crashed worker resumes from
   the last completed step, not from the start.
4. **Immutable published versions.** Publishing freezes a runnable snapshot; drafts stay editable
   so a workflow can't change shape mid-run.
5. **Guardrails you can't turn off.** The max-step cap is a hard engine constant in v1, not
   author-configurable.
6. **Pluggable, mocked externals.** HTTP and the LLM provider sit behind adapter interfaces
   (LangChain/LangGraph-compatible), mocked for the capstone — no lock-in, fully testable.

---

## Tech stack (default)

- **Backend:** Java 21 + Spring Boot 3 (author's depth; Node.js/Python are viable alternatives).
- **Persistence:** PostgreSQL (all state, plus the initial DB-backed outbox queue).
- **Queue:** DB outbox table → Kafka or RabbitMQ only if scale demands it.
- **AI:** provider adapter interface, mocked for the capstone (LangChain/LangGraph-compatible).
- **Validation:** JSON Schema for AI-node outputs.
- **Console:** lightweight web UI (server-rendered or a small SPA) over the REST API.
- **Testing:** JUnit 5 + Testcontainers (Postgres), plus a scripted kill-and-resume demo.
