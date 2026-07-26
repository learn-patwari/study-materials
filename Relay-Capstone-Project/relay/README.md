# Relay — Spring Boot Implementation (v1 vertical slice)

Runnable implementation of the [Relay design](../README.md). This milestone covers
**Phases 0–5** of the [roadmap](../09-Implementation-Roadmap.md): schema → definition APIs →
triggers → durable execution core → deterministic nodes with exactly-once idempotency.

> **Status:** vertical slice. Implemented: workflow CRUD + publish validation, manual & webhook
> (HMAC) triggers, transactional outbox queue + worker, `http_request` / `condition` / `delay` /
> `notify` nodes, the idempotency ledger, tracing, and run/trace read APIs.
> **Not yet:** AI node (P6), approval gates (P7), retry/backoff + full guardrail surface (P8),
> console UI (P9). The `ai`/`approval` node types validate at publish but have no executor yet.

## Stack

Java 21 · Spring Boot 3 · PostgreSQL (Flyway) · JUnit 5 + Testcontainers.

## Run it

```bash
# 1. Start Postgres (example)
docker run -d --name relay-pg -e POSTGRES_DB=relay -e POSTGRES_USER=relay \
  -e POSTGRES_PASSWORD=relay -p 5432:5432 postgres:16-alpine

# 2. Run the app (Flyway migrates on boot)
mvn spring-boot:run
```

## Try the happy path

```bash
# Create a workflow (note the returned "secret" for webhook signing)
curl -s localhost:8080/api/workflows -H 'Content-Type: application/json' \
  -d '{"name":"orders"}'

# Save a draft definition (raw JSON body)
curl -s localhost:8080/api/workflows/<ID>/versions -H 'Content-Type: application/json' -d '{
  "start":"check",
  "nodes":{
    "check":{"type":"condition","config":{"expr":"{{input.amount}} > 1000"},"onTrue":"charge","onFalse":"small"},
    "charge":{"type":"http_request","sensitive":true,"next":"big","config":{"method":"POST","url":"https://api.mock/orders"}},
    "big":{"type":"notify","next":null,"config":{"to":"ops","template":"charged {{input.amount}}"}},
    "small":{"type":"notify","next":null,"config":{"to":"ops","template":"too small"}}
  }}'

# Publish v1 (validates the definition)
curl -s -XPOST localhost:8080/api/workflows/<ID>/versions/1/publish

# Trigger a run
curl -s -XPOST localhost:8080/api/triggers/<ID>/manual \
  -H 'Content-Type: application/json' -d '{"amount":2499}'

# Watch it
curl -s localhost:8080/api/runs/<RUN_ID>
curl -s localhost:8080/api/runs/<RUN_ID>/trace
```

## Tests

```bash
# Pure unit tests (no Docker needed): validator, template resolver, condition, HMAC
mvn test -Dtest='DefinitionValidatorTest,TemplateResolverTest,ConditionEvaluatorTest,HmacVerifierTest'

# Full engine integration test (requires Docker for Testcontainers Postgres)
mvn test -Dtest=RelayEngineIT
```

## Key design points realized here

- **Transactional outbox** — a run and its queue message are inserted in one transaction
  (`TriggerService`); workers claim with `FOR UPDATE SKIP LOCKED` (`OutboxRepository`).
- **One node per message** — `RunAdvancer` executes exactly one node per message and enqueues the
  next in the same transaction, so a crash resumes from that node.
- **Exactly-once side effects** — `IdempotencyService` + the `side_effects` unique key, with the
  mocked world (`MockExternalWorld`) idempotent by key.
- **Engine guarantees** — publish validation (`DefinitionValidator`), hard `max-steps` cap, and
  HMAC webhook auth are all enforced in engine/DB code, never by the model.

See the design docs in the parent folder for the full picture, including the parts not yet built.
