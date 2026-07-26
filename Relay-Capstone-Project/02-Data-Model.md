[← Architecture](01-Architecture.md) · [Relay README](README.md) · [Next: API Design →](03-API-Design.md)

# 2. Data Model

**Data model first** — before any logic, we need somewhere to put state. All persistence is
PostgreSQL. Flexible, node-shaped data (definitions, inputs, outputs) is stored as **JSONB**;
everything that needs constraints, ordering, or joins is relational.

## 2.1 Entity overview

```mermaid
erDiagram
  workflows ||--o{ workflow_versions : has
  workflow_versions ||--o{ runs : "executed as"
  runs ||--o{ steps : contains
  runs ||--o{ approvals : "may require"
  runs ||--o{ traces : emits
  steps ||--o{ side_effects : "records (idempotency)"

  workflows { uuid id; text name; uuid published_version_id; }
  workflow_versions { uuid id; int version; text status; jsonb definition; }
  runs { uuid id; uuid version_id; text status; jsonb input; int step_cursor; }
  steps { uuid id; uuid run_id; text node_id; text status; jsonb output; int attempt; }
  approvals { uuid id; uuid run_id; text node_id; text status; }
  traces { uuid id; uuid run_id; text node_id; jsonb detail; }
  side_effects { uuid id; uuid run_id; text node_id; text attempt_key; }
```

## 2.2 Core tables

- **`workflows`** — the logical workflow and a pointer to its currently published version.
- **`workflow_versions`** — **immutable** draft/published snapshots. `definition` (JSONB) holds
  the node graph. `status ∈ {DRAFT, PUBLISHED, ARCHIVED}`. Publishing freezes a version.
- **`runs`** — one execution of a published version. Carries `input`, a `status`, and a
  `step_cursor` (which node is next). This row is the resumable checkpoint.
- **`steps`** — one row per node execution attempt: resolved inputs, output, status, timing,
  attempt number.
- **`approvals`** — a pending/decided gate for a sensitive node; a run cannot pass the node
  without a matching `GRANTED` record.
- **`traces`** — append-only observability rows (resolved I/O, attempts, timing, token usage).
- **`side_effects`** — the idempotency ledger: a **unique** `(run_id, node_id, attempt_key)`
  guarantees a side effect executes at most once.
- **`outbox`** — the DB-backed queue (see [Execution Engine](04-Execution-Engine.md)).

## 2.3 DDL (v1)

```sql
-- Definitions -------------------------------------------------------------
CREATE TABLE workflows (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                 TEXT NOT NULL,
  published_version_id UUID,                       -- FK set on publish
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workflow_versions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id  UUID NOT NULL REFERENCES workflows(id),
  version      INT  NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('DRAFT','PUBLISHED','ARCHIVED')),
  definition   JSONB NOT NULL,                     -- node graph + config
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workflow_id, version)
);

-- Execution ---------------------------------------------------------------
CREATE TABLE runs (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  version_id   UUID NOT NULL REFERENCES workflow_versions(id),
  status       TEXT NOT NULL CHECK (status IN
                 ('PENDING','RUNNING','WAITING_APPROVAL','SUCCEEDED','FAILED','CANCELLED')),
  input        JSONB NOT NULL,
  step_cursor  INT  NOT NULL DEFAULT 0,            -- index of next node
  step_count   INT  NOT NULL DEFAULT 0,            -- for max-step guardrail
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE steps (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id       UUID NOT NULL REFERENCES runs(id),
  node_id      TEXT NOT NULL,
  attempt      INT  NOT NULL DEFAULT 1,
  status       TEXT NOT NULL CHECK (status IN ('RUNNING','SUCCEEDED','FAILED','SKIPPED')),
  input        JSONB,
  output       JSONB,
  error        TEXT,
  started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at  TIMESTAMPTZ,
  UNIQUE (run_id, node_id, attempt)
);

CREATE TABLE approvals (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id       UUID NOT NULL REFERENCES runs(id),
  node_id      TEXT NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('PENDING','GRANTED','REJECTED')),
  decided_by   TEXT,
  decided_at   TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (run_id, node_id)
);

-- Idempotency ledger: the exactly-once guarantee for side effects ----------
CREATE TABLE side_effects (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id       UUID NOT NULL REFERENCES runs(id),
  node_id      TEXT NOT NULL,
  attempt_key  TEXT NOT NULL,                      -- idempotency key for the call
  result       JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (run_id, node_id, attempt_key)            -- <== the hard guarantee
);

-- Observability -----------------------------------------------------------
CREATE TABLE traces (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id       UUID NOT NULL REFERENCES runs(id),
  node_id      TEXT,
  kind         TEXT NOT NULL,                      -- e.g. INPUT_RESOLVED, LLM_CALL, GATE
  detail       JSONB NOT NULL,                     -- inputs/outputs/timing/tokens
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Durable queue (v1) ------------------------------------------------------
CREATE TABLE outbox (
  id           BIGSERIAL PRIMARY KEY,
  run_id       UUID NOT NULL REFERENCES runs(id),
  available_at TIMESTAMPTZ NOT NULL DEFAULT now(), -- supports delay nodes / backoff
  locked_by    TEXT,
  locked_at    TIMESTAMPTZ,
  status       TEXT NOT NULL DEFAULT 'READY' CHECK (status IN ('READY','DONE'))
);
CREATE INDEX ON outbox (status, available_at);
```

## 2.4 The `definition` JSONB shape

A published version's `definition` describes nodes and their wiring. Example:

```json
{
  "start": "fetch_order",
  "nodes": {
    "fetch_order":  { "type": "http_request", "next": "check_amount",
                      "config": { "url": "https://api.mock/orders/{{input.orderId}}" } },
    "check_amount": { "type": "condition", "config": { "expr": "{{fetch_order.amount}} > 1000" },
                      "onTrue": "approve_gate", "onFalse": "place_order" },
    "approve_gate": { "type": "approval", "next": "place_order" },
    "place_order":  { "type": "http_request", "sensitive": true, "next": "notify",
                      "config": { "url": "https://api.mock/orders", "method": "POST" } },
    "notify":       { "type": "notify", "next": null,
                      "config": { "to": "ops", "template": "Order {{fetch_order.id}} placed" } }
  }
}
```

Templates like `{{fetch_order.amount}}` are resolved from prior step outputs at execution time
(see [Node Executors](05-Node-Executors.md)); template resolution is a tested unit.

## 2.5 Versioning & immutability rules

- A **draft** version is mutable; **publishing** transitions it to `PUBLISHED` and it becomes
  immutable. Edits after publish create a **new** draft version.
- A **run always references a specific `version_id`**, never "the workflow" — so a publish during
  an in-flight run can never change that run's shape.
- `workflows.published_version_id` points at the latest published version used by *new* triggers.

---

**Next → [3. API Design](03-API-Design.md)**
