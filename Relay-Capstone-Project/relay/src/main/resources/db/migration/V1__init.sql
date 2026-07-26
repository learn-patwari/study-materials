-- Relay v1 schema (see Relay-Capstone-Project/02-Data-Model.md)
-- Postgres 13+ (gen_random_uuid built-in). JSON payloads stored as jsonb.

-- Definitions ---------------------------------------------------------------
CREATE TABLE workflows (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 TEXT NOT NULL,
    secret               TEXT NOT NULL,                 -- HMAC secret for webhook triggers
    published_version_id UUID,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workflow_versions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id  UUID NOT NULL REFERENCES workflows(id),
    version      INT  NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('DRAFT','PUBLISHED','ARCHIVED')),
    definition   JSONB NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workflow_id, version)
);

-- Execution -----------------------------------------------------------------
CREATE TABLE runs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id   UUID NOT NULL REFERENCES workflow_versions(id),
    status       TEXT NOT NULL CHECK (status IN
                   ('PENDING','RUNNING','WAITING_APPROVAL','SUCCEEDED','FAILED','CANCELLED')),
    input        JSONB NOT NULL,
    current_node TEXT,                                  -- id of next node to execute (null = start/terminal)
    step_count   INT  NOT NULL DEFAULT 0,
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

-- Idempotency ledger: exactly-once side effects -----------------------------
CREATE TABLE side_effects (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id       UUID NOT NULL REFERENCES runs(id),
    node_id      TEXT NOT NULL,
    attempt_key  TEXT NOT NULL,
    result       JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, node_id, attempt_key)
);

-- Observability -------------------------------------------------------------
CREATE TABLE traces (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id       UUID NOT NULL REFERENCES runs(id),
    node_id      TEXT,
    kind         TEXT NOT NULL,
    detail       JSONB NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_traces_run ON traces (run_id, created_at);

-- Durable queue (v1 outbox) -------------------------------------------------
CREATE TABLE outbox (
    id           BIGSERIAL PRIMARY KEY,
    run_id       UUID NOT NULL REFERENCES runs(id),
    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_by    TEXT,
    locked_at    TIMESTAMPTZ,
    status       TEXT NOT NULL DEFAULT 'READY' CHECK (status IN ('READY','DONE'))
);
CREATE INDEX idx_outbox_ready ON outbox (status, available_at);
