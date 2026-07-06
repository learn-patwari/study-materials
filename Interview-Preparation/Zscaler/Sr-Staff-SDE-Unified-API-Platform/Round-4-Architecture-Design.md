[← Round 3](Round-3-Coding-and-Machine-Coding.md) · [Role index](README.md) · [Next: Round 5 →](Round-5-HR-and-Company-Research.md)

# Round 4 — Architecture-Level System Design

> **Format:** The senior design round. Expect an open-ended, large-scale prompt — very likely
> **"Design a Unified API Platform / API Gateway"** since that's the team's charter, or a related
> distributed-systems problem (rate limiter at scale, developer portal, API analytics, a
> pub/sub/eventing backbone). At Staff/Sr-Staff they want **breadth + depth + judgment**: drive
> the conversation, state assumptions, quantify, and defend trade-offs.

---

## The design framework (drive it in this order)

1. **Requirements** — functional + non-functional. Clarify scope out loud.
2. **Scale numbers** — users, RPS, data size, read/write ratio, latency SLOs. Do the math.
3. **API** — the key endpoints/contracts.
4. **High-level diagram** — boxes and data flow.
5. **Data model & storage** — pick stores and justify (SQL vs NoSQL vs cache vs stream).
6. **Deep dives** — 2–3 components they poke at (e.g., rate limiting, auth, routing).
7. **Scaling & reliability** — partitioning, replication, caching, HA, multi-region.
8. **Observability & operability** — metrics, logs, tracing, rollout/rollback (JD stresses this).
9. **Trade-offs & failure modes** — what breaks, blast radius, mitigations.

> 💡 Anchor to **Zscaler scale** from the JD: **15M+ users, 185 countries, 150+ data centers**.
> That justifies multi-region, heavy caching, and horizontal scale.

---

## Flagship: Design Zscaler's Unified API Platform / Gateway

**Requirements — functional:**
- A **single, consistent API front door** for all Zscaler products (ZIA/ZPA/ZDX/admin/config).
- **AuthN/AuthZ** (OAuth2/OIDC, API keys, mTLS), **rate limiting & quotas** per tenant/app,
  **routing** to backend product services, **request/response transformation & versioning**.
- **Developer experience:** self-service developer portal, API catalog, **auto-generated SDKs**,
  OpenAPI specs, sandbox/keys, docs.
- **Governance:** consistent standards, versioning policy, deprecation, usage analytics.

**Non-functional:** highly available (multi-region), low added latency, observable, operable,
secure, multi-tenant isolation, horizontally scalable.

**High-level architecture:**
```
Developers/Apps
   │  (HTTPS, OAuth2/OIDC or API key or mTLS)
   ▼
Global LB / Anycast ──► API Gateway (stateless, multi-region, autoscaled)
   │   pipeline: authN → authZ → rate-limit → transform → route → observe
   ├──► AuthN/AuthZ service (OIDC/JWT validation, token introspection)  ← Keycloak-style IdP
   ├──► Rate-limit service (Redis-backed counters, token bucket)
   ├──► Config/Control plane (routes, policies, API specs)   ← separate from data plane
   ├──► Product backends (ZIA / ZPA / ZDX / admin APIs)
   └──► Async: emit usage events → Kafka → analytics + billing + audit
Developer Portal ──► API catalog, SDK downloads, key management, docs (fed by OpenAPI registry)
```

**Key design decisions to raise:**

- **Control plane vs data plane separation** — the gateway data plane (per-request, must be fast
  and HA) is separate from the control plane (policy/route/config management). *You can compare
  this to Zscaler's own CA-vs-Service-Edge split — shows you did your homework* (see
  [`../Technical-Deep-Dive.md`](../Technical-Deep-Dive.md)).
- **Stateless gateway nodes** — all shared state (rate counters, tokens, routes) in Redis/config
  store, so nodes scale horizontally and any node can serve any request.
- **The request pipeline as middleware** (Chain of Responsibility) — authN → authZ →
  rate-limit → transform → route → log. New cross-cutting concerns are new middleware.
- **Auth** — validate JWTs at the edge (cache JWKS public keys), support API keys and mTLS for
  service clients; per-tenant scopes. *This is your Keycloak/OAuth2 wheelhouse — lean in.*
- **Rate limiting at scale** — token bucket with counters in **Redis** (atomic INCR/Lua),
  per-tenant + per-endpoint; degrade gracefully if Redis is slow (fail-open vs fail-closed
  decision — discuss it).
- **Routing** — trie/prefix match on path; versioned routes (`/v1`, `/v2`); canary by header/%
  weighting.
- **SDK generation & governance** — **API-first / contract-first**: OpenAPI specs are the source
  of truth in a registry; SDKs (Java/Go/Python/JS) and docs are **auto-generated** from them in
  CI; a linter enforces API standards (naming, pagination, errors) at PR time. *This is the core
  "standardization & governance + developer experience" ask.*
- **Async usage pipeline** — every call emits an event to **Kafka**; consumers do analytics,
  quota accounting, billing, and audit without slowing the request path.
- **Observability** — RED metrics (Rate/Errors/Duration) per route+tenant, structured logs,
  **distributed tracing** (OpenTelemetry) with a trace ID injected at the edge and propagated;
  dashboards + SLO alerts.
- **Multi-region & HA** — gateways in every region behind anycast/global LB; config replicated;
  Redis per-region with the right consistency choice; graceful failover.
- **Multi-tenancy** — isolation of limits, keys, and data per tenant; noisy-neighbor protection
  via quotas.

**Failure modes to volunteer:** IdP/JWKS outage (cache keys, short-circuit), Redis outage
(local fallback + fail-open/closed policy), a backend product service down (circuit breaker +
typed error), config push gone bad (versioned config + fast rollback), a tenant hammering the
platform (per-tenant quotas + shedding).

---

## Other prompts to be ready for

- **Design a distributed rate limiter** — algorithms (token bucket, sliding window log/counter),
  Redis vs local+sync, accuracy vs cost, fail-open/closed.
- **Design an API analytics / usage-metering pipeline** — Kafka ingestion, stream processing,
  approximate top-K (count-min sketch), rollups, exactly-once-ish billing.
- **Design a pub/sub / eventing backbone** — topics, partitions, consumer groups, ordering,
  delivery guarantees, retention, backpressure.
- **Design a developer portal / API catalog** — OpenAPI registry, versioning, key management,
  search, docs.
- **Design a distributed cache** — sharding (consistent hashing), replication, eviction, TTL,
  hot-key handling, cache stampede prevention.
- **Design an LLM-orchestration/gateway layer** (their "stand out" bullet) — routing prompts to
  models, caching responses, token/cost limits, guardrails, streaming — connect to your
  LangChain/LangGraph experience.

---

## Concepts to have crisp

- **CAP / PACELC**, consistency models (strong vs eventual), idempotency, exactly-once vs
  at-least-once.
- **Partitioning** (consistent hashing) & **replication** (leader/follower, quorum).
- **Caching** strategies + invalidation + stampede (request coalescing, TTL jitter).
- **Load balancing** (L4 vs L7), **backpressure**, **circuit breakers**, **bulkheads**,
  **retries with jitter**, **timeouts**.
- **Messaging:** Kafka (log, partitions, consumer groups, ordering) vs RabbitMQ (queues) —
  *your strength; use it.*
- **OAuth2/OIDC** flows, JWT validation, mTLS — *your strength; use it.*
- **Observability:** metrics vs logs vs traces; SLI/SLO/error budgets.

---

## Round-4 checklist

- [ ] Can drive the **Unified API Gateway** design end-to-end in ~40 min, out loud.
- [ ] Lead with **requirements + scale math**; separate **control vs data plane**.
- [ ] Deep-dive **auth (OAuth2/JWT)** and **rate limiting (Redis)** confidently.
- [ ] Explain **API-first + auto-generated SDKs + linting** (governance & DX).
- [ ] Always cover **observability, multi-region HA, failure modes, trade-offs**.
- [ ] Have the **LLM-gateway** angle ready as a differentiator.

---

**Next → [Round 5: HR + Company Research](Round-5-HR-and-Company-Research.md)**
