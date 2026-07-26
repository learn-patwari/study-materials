[← Data Model](02-Data-Model.md) · [Relay README](README.md) · [Next: Execution Engine →](04-Execution-Engine.md)

# 3. API Design

REST over JSON, API-first. Three groups: **workflow definition**, **triggers**, and
**operations** (approvals, runs, traces). All mutations are validated; publish is the pivotal
operation.

## 3.1 Workflow definition APIs

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/workflows` | Create a workflow (returns id + initial draft version) |
| `GET` | `/api/workflows` | List workflows |
| `GET` | `/api/workflows/{id}` | Get a workflow + version list |
| `POST` | `/api/workflows/{id}/versions` | Create/update a **draft** version (definition JSON) |
| `POST` | `/api/workflows/{id}/versions/{v}/publish` | **Publish** → freeze an immutable, runnable snapshot |

**Publish semantics (the key moment):**
- Validates the definition: every `next`/`onTrue`/`onFalse` points to a real node; exactly one
  `start`; no unreachable/dangling nodes; sensitive nodes are well-formed; step count bound is
  satisfiable. *Publish validation is a tested unit.*
- On success: sets version `status=PUBLISHED`, updates `workflows.published_version_id`.
- Drafts remain editable; published versions are immutable — new edits make a new draft.

```
POST /api/workflows/{id}/versions/3/publish
200 OK  { "versionId": "…", "version": 3, "status": "PUBLISHED" }
409 Conflict  { "error": "validation_failed", "issues": ["node 'notify' has unknown next 'end'"] }
```

## 3.2 Trigger APIs

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/triggers/{workflowId}/webhook` | Real traffic; body verified by **HMAC** workflow secret |
| `POST` | `/api/triggers/{workflowId}/manual` | Manual trigger for demos |

- The incoming payload becomes the run's `input`.
- Webhook requests carry `X-Relay-Signature: sha256=…`; the server recomputes HMAC over the raw
  body using the workflow's secret and rejects on mismatch (constant-time compare). See
  [Guardrails & Security](06-Guardrails-and-Security.md).
- Response is **202 Accepted** with a `runId`; execution is asynchronous.

```
POST /api/triggers/{id}/webhook
Headers: X-Relay-Signature: sha256=9f86d0…
Body:    { "orderId": "A-1001", "amount": 2499 }
202 Accepted  { "runId": "…", "status": "PENDING" }
```

## 3.3 Approval APIs

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/approvals?status=PENDING` | List pending approvals (console feeds off this) |
| `POST` | `/api/approvals/{id}/grant` | Approve — engine resumes the paused run |
| `POST` | `/api/approvals/{id}/reject` | Reject — run transitions to FAILED/CANCELLED |

Granting/rejecting records the decision (`decided_by`, `decided_at`) and enqueues the run to
resume. The **engine**, not the API caller, enforces that the sensitive node was actually blocked.

## 3.4 Run & trace (observability) APIs

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/runs` | List runs (filter by workflow, status) |
| `GET` | `/api/runs/{runId}` | Run detail: status, cursor, step summaries |
| `GET` | `/api/runs/{runId}/steps` | Per-step inputs/outputs/attempts/timing |
| `GET` | `/api/runs/{runId}/trace` | Full trace incl. AI token usage |
| `POST` | `/api/runs/{runId}/cancel` | Cancel an in-flight run |

## 3.5 Cross-cutting API concerns

- **Validation:** request bodies validated (Bean Validation); definition validated at publish.
- **Errors:** consistent problem shape `{ "error": code, "message": …, "issues": [...] }`.
- **Idempotent triggers (optional):** accept a client `Idempotency-Key` header to dedupe retried
  webhooks into the same run.
- **AuthN/AuthZ:** out of scope for v1 beyond the webhook HMAC; a bearer token on the console/API
  is a natural v2 addition.
- **Versioning:** URI-versioned (`/api/v1/...`) once external consumers exist.

---

**Next → [4. Execution Engine](04-Execution-Engine.md)**
