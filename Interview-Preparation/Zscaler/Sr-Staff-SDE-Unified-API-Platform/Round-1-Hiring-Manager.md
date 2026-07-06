[← Role index](README.md) · [Next: Round 2 →](Round-2-DSA-and-Design.md)

# Round 1 — Hiring Manager (30 min): Current Project & Technology

> **Format:** 30 minutes, conversational, with the Senior Manager you'd report to. Goal: assess
> seniority, communication, ownership, and whether your background fits the Unified API Platform
> mission. This is **not** a coding round — it's about *how you think and what you've built*.
> With only 30 minutes, be **crisp**: tight intro, one or two deep project stories, strong
> "why Zscaler / why this role."

---

## 1. Your 90-second intro (memorize the shape, not the words)

> "I'm Akshay, a Staff Engineer with 8+ years in Java and distributed systems. For the last ~3
> years at Samsung Electro-Mechanics I've been building **PADO**, an internal MLOps + AI
> platform — designing scalable microservices on Kubernetes, an identity/SSO layer with
> Keycloak across many developer tools, and event-driven pipelines with Kafka and Redis. I lead
> a team of six, owning architecture, code reviews, and delivery. Before that I worked in
> banking at Oracle (Flexcube) and insurance at Chubb, so I've shipped in regulated, high-stakes
> domains. What draws me to this role is that it's squarely a **platform + developer-experience**
> problem at massive scale — building the unified API layer that every Zscaler product and
> developer builds on — and I've spent my recent years doing exactly that kind of platform and
> AI-orchestration work."

Why this works: leads with scope (Staff, platform), names the exact JD keywords (microservices,
K8s, Kafka, Redis, identity, MLOps/AI, leadership), and closes on *fit*.

---

## 2. Your headline project: PADO — how to tell it (STAR)

Have **one flagship story** you can go deep on. Structure it STAR and be ready to zoom between
strategy and hands-on detail (they explicitly value "dynamic range").

- **S/T (Situation/Task):** AI teams at Samsung needed a self-service platform to manage the full
  model lifecycle — training, deployment, monitoring, and **automated redeployment on drift** —
  without each team hand-rolling infra. I owned the platform architecture and led six engineers.
- **A (Action):**
  - Designed **microservices (Spring Boot 3)** on **Kubernetes**, with a "build once, deploy to
    many clusters" model and external persistent-volume mounting for portability.
  - Built the **identity/SSO layer with Keycloak**, integrating auth (tokens, sessions) for
    Kubeflow, Grafana, Jupyter, Docker — one secure front door for every tool.
  - Made pipelines **event-driven** with Kafka/RabbitMQ and used **Redis** for caching/state;
    drift detection emits an event that triggers automated redeployment.
  - Hosted an **in-house LLM** in the platform and used LangChain/LangGraph to add AI assistance
    to developer workflows.
- **R (Result):** Reduced downtime and manual toil, standardized how AI teams ship models, and
  gave a consistent, governed, self-service developer experience.

> 💡 **The bridge to say out loud:** "That identity + event-driven + multi-tenant, self-service
> platform work is *the same shape* as a Unified API Platform — standardized contracts, a common
> auth/governance layer, observability, and great developer experience. I'd be applying the same
> muscles to APIs and SDKs at Zscaler's scale."

---

## 3. Technology talking points (be ready to go one level deeper on each)

The HM may probe any tech on your resume. One-liners you can expand:

| Tech | Be ready to explain |
|------|---------------------|
| **Microservices / Spring Boot 3** | Service boundaries, REST contracts, versioning, resilience (timeouts, retries, circuit breakers) |
| **Kubernetes** | Deployments, services, HPA, PV/PVC, multi-cluster deploy, rolling updates, health probes |
| **Kafka / RabbitMQ** | When to use a log (Kafka) vs a queue (RabbitMQ); partitions, consumer groups, ordering, idempotency, DLQ |
| **Redis** | Caching patterns (cache-aside), TTL, rate limiting, distributed locks, pub/sub |
| **Keycloak / OAuth2 / OIDC** | Tokens (access/refresh/ID), SSO, scopes, client credentials — **directly relevant to API governance** |
| **MLOps + LLM** | Model lifecycle, drift-triggered redeploy; LangChain/LangGraph orchestration; **connect to "AI-driven API gateways / LLM orchestration"** |
| **Java 8→21** | Streams, CompletableFuture, records, virtual threads (Project Loom) — good to mention for a modern platform |

---

## 4. Likely questions & how to answer

- **"Tell me about your current project."** → The PADO STAR story above; end with the bridge to APIs.
- **"What's the hardest technical problem you've solved?"** → Pick one: e.g., automated
  drift-based redeployment without downtime, or unifying auth across many tools with Keycloak.
  Explain the constraint, options considered, trade-off, outcome.
- **"How do you handle ambiguity?"** → Give a concrete example of starting with an unclear
  requirement, breaking it down, shipping an MVP, iterating. (Their success profile literally
  says "thrive in ambiguity, build the path as you walk it.")
- **"How do you lead / handle disagreement on the team?"** → Reference leading 6 devs;
  design reviews, giving/receiving candid feedback (their "challenge culture").
- **"Why do you want to leave Samsung / why Zscaler?"** → Growth into larger-scale external
  platform + security domain + AI-forward mission; avoid negativity about the current employer.
- **"You've mostly done Java — we sometimes use Go."** → "I'm language-agnostic; I go deep in
  Java but have ramped on new stacks quickly. I'd pick up Go fast — the platform thinking
  transfers." 
- **"What do you know about our team's mission?"** → Unified API platform: standardization,
  governance, developer experience, scalable/observable distributed platform (see Round 4).

---

## 5. Questions to ask the HM (pick 3)

- "What does success look like for this role in the first 6–12 months?"
- "What's the current state of the Unified API Platform — greenfield, or consolidating existing
  per-product APIs? What's the biggest pain you're solving first?"
- "How does the team balance shipping developer-facing features vs platform reliability/tech-debt?"
- "Where does AI/LLM orchestration fit into the platform roadmap today — real or aspirational?"
- "How is the team structured, and how does it work with the individual product teams whose APIs
  you're unifying?"

(More in [`../Reverse-Interview.md`](../Reverse-Interview.md).)

---

## 6. Round-1 checklist

- [ ] 90-second intro rehearsed (out loud, timed).
- [ ] PADO STAR story tight, with the "bridge to API platform" line.
- [ ] One "hardest problem" story ready.
- [ ] Ownership + ambiguity + leadership stories ready (ties to their values).
- [ ] Crisp "Why Zscaler / why this role."
- [ ] 3 questions to ask.
- [ ] Read the [company research](Round-5-HR-and-Company-Research.md) *before* this round too —
      HMs notice when you understand the mission.

---

**Next → [Round 2: DSA + Design](Round-2-DSA-and-Design.md)**
