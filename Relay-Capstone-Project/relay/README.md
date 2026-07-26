# Relay — Spring Boot Implementation

Runnable implementation of the [Relay design](../README.md). Covers **Phases 0–9** of the
[roadmap](../09-Implementation-Roadmap.md): schema → definition APIs → triggers → durable
execution core → deterministic nodes with exactly-once idempotency → **AI node** → **approval
gates** → **retry/backoff** → **console**.

> **Status:** Implemented — workflow CRUD + publish validation, manual & webhook (HMAC) triggers,
> transactional outbox queue + worker, `http_request` / `condition` / `delay` / `notify` nodes,
> the idempotency ledger, **`ai` node with JSON-Schema-validated output**, **approval gates**
> (pause/resume, hard-block on `sensitive` nodes), **exponential-backoff retries** (with
> non-retryable deterministic failures), tracing, a **web console** (runs, traces, approvals), and
> run/trace/approval REST APIs.
> **Not yet:** distributed queue (Kafka/RabbitMQ) and real LLM providers — both are interfaces
> with a v1 implementation (DB outbox; deterministic mock LLM).

Open **http://localhost:8080/** after starting the app to use the console.

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
# Pure unit tests (no Docker): validator, template resolver, condition, HMAC, JSON-Schema, mock LLM
mvn test -Dtest='DefinitionValidatorTest,TemplateResolverTest,ConditionEvaluatorTest,HmacVerifierTest,SchemaValidatorTest,MockLlmProviderTest'

# Full engine integration test — happy path, AI-node schema pass/fail, approval park/grant/reject
# (requires Docker for Testcontainers Postgres)
mvn test -Dtest=RelayEngineIT
```

## Approval-gate demo (curl)

A `sensitive: true` node parks the run until a human approves:

```bash
# after triggering a run that hits a sensitive node:
curl -s localhost:8080/api/approvals?status=PENDING            # find the pending approval id
curl -s -XPOST localhost:8080/api/approvals/<APPROVAL_ID>/grant \
  -H 'Content-Type: application/json' -d '{"decidedBy":"alice"}'   # resumes; side effect fires once
# or /reject to fail the run without performing the side effect
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
