[← Back to Zscaler folder](../README.md)

# Zscaler — Sr Staff SDE, Unified API Platform — Interview Prep

> **Role:** Sr Staff Software Development Engineer, **Unified API Platform** team (hybrid,
> Bengaluru). Reports to Sr Manager, SDE. Builds a **unified API & developer platform** for all
> Zscaler products — standardization, governance, developer experience, and a scalable,
> highly-available, observable distributed API platform.
>
> **Candidate:** Akshay Patwari — 8+ yrs, Java/Spring Boot microservices, Kafka/RabbitMQ, Redis,
> Kubernetes, Keycloak (SSO/OAuth2/OIDC), MLOps + GenAI/LLM (LangChain/LangGraph), tech lead of 6.
>
> This folder has **one file per interview round** plus this index. Work them in order.

---

## The 5-round loop (from the JD/recruiter)

| Round | Focus | Prep file |
|-------|-------|-----------|
| 1 | **Hiring Manager (30 min)** — current project & technology | [Round-1-Hiring-Manager.md](Round-1-Hiring-Manager.md) |
| 2 | **DSA + Design** | [Round-2-DSA-and-Design.md](Round-2-DSA-and-Design.md) |
| 3 | **Technical coding + Machine coding** | [Round-3-Coding-and-Machine-Coding.md](Round-3-Coding-and-Machine-Coding.md) |
| 4 | **Architecture-level system design** | [Round-4-Architecture-Design.md](Round-4-Architecture-Design.md) |
| 5 | **HR** — company research & fit | [Round-5-HR-and-Company-Research.md](Round-5-HR-and-Company-Research.md) |

📊 **Also:** [`DSA-Interview-Experiences.md`](DSA-Interview-Experiences.md) — real,
community-reported Zscaler DSA questions/patterns + a 2-week drill plan (pairs with Round 2).

Company/product background lives in the parent folder:
[`../README.md`](../README.md), [`../Technical-Deep-Dive.md`](../Technical-Deep-Dive.md),
[`../Reverse-Interview.md`](../Reverse-Interview.md).

---

## JD → your experience: the mapping to lead with

| JD asks for | You have | How to frame it |
|-------------|----------|-----------------|
| Scalable **distributed API platform**, HA, observable, operable | Microservices on **Kubernetes**, production ops, resilience | "I built and operated a multi-tenant platform (PADO) on K8s — build once, deploy to many clusters, external PV mounting, HA." |
| **API design standards, API-first, SDKs** | Spring Boot 3 REST microservices, integrating many tools via APIs | Emphasize contract-first thinking; be ready to talk OpenAPI, versioning, SDK generation. |
| **Message brokers, caches, queues, pub/sub** | **Kafka/RabbitMQ**, **Redis** | Strong direct hit — have concrete stories (event-driven MLOps, drift-triggered redeploy). |
| **Standardization & governance**, developer experience | **Keycloak** SSO/OAuth2/OIDC across many tools; team lead | Governance = auth, rate limits, API keys, consistent contracts — you did the auth/identity layer. |
| **AI/ML foundation; AI-driven API gateways, LLM orchestration** | **MLOps** lifecycle + **GenAI/LLM** hosting, LangChain/LangGraph | This is your differentiator — connect LLM orchestration to API-platform automation. |
| Go/Java/C++/Rust/JS | **Java 8–21** (deep) | Java is accepted; mention willingness to pick up Go (common at Zscaler for platform). |
| Ambiguity, ownership, cross-functional | Led 6 devs, client-facing, across geographies | Have STAR stories ready (see Round 1 & 5). |

> ⚠️ **Gaps to pre-empt:** (1) **Go** — Zscaler platform teams often use Go; say you're
> language-agnostic and have context. (2) **External/public API scale** — your APIs were more
> internal-platform; bridge by talking about multi-tenant governance and auth you already did.
> (3) **API gateway products** (Kong/Apigee/Envoy) — skim these (Round 4).

---

## Suggested 1–2 week study plan

- **Days 1–2:** Round 1 story polish + Round 5 company research (low effort, high payoff, do early).
- **Days 3–5:** Round 2 DSA — 3–4 problems/day on the priority patterns; review Java collections/concurrency.
- **Days 6–8:** Round 3 machine coding — build 2–3 mini-systems end to end in Java (rate limiter, in-memory cache w/ TTL, pub/sub).
- **Days 9–11:** Round 4 system design — practice "Design a Unified API Gateway/Platform" out loud twice.
- **Day 12:** Mock the full loop; refine the reverse-interview questions.

---

**Start → [Round 1: Hiring Manager](Round-1-Hiring-Manager.md)**
