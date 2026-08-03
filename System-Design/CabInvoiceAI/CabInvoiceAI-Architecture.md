# Cab Invoice AI Platform — Architecture

> Source: learn-patwari/ai-assisted-invoice-processor

## Overview

Enterprise cab invoice reimbursement platform. Users upload a ZIP of PDF invoices (Rapido, Ola, Uber, Namma Yatri). The system extracts, parses, classifies AM/PM, generates an Excel reimbursement report, merges PDFs in date order, and makes both downloadable. Also includes a **Carpooling Calculator** for shared cab reimbursement across multiple commuters.

---

## System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Next.js 15 │────▶│  FastAPI     │────▶│  PostgreSQL  │
│  Frontend   │     │  Backend     │     └─────────────┘
└─────────────┘     └──────┬───────┘
                           │ enqueue
                    ┌──────▼───────┐     ┌─────────────┐
                    │  Celery      │────▶│    Redis     │
                    │  Worker      │     └─────────────┘
                    └──────┬───────┘
                           │ store
                    ┌──────▼───────┐
                    │ MinIO / S3   │
                    │ / Azure Blob │
                    └─────────────┘
```

**Processing pipeline (per batch)**
```
Upload ZIP → Extract PDFs → Parse Invoices → Generate Excel → Sort & Merge PDF → Done
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, React Query, Axios |
| Backend | FastAPI, SQLAlchemy (async), Alembic, Pydantic v2 |
| Workers | Celery, Redis |
| Database | PostgreSQL 16 |
| Storage | MinIO (default) · AWS S3 · Azure Blob · Local filesystem |
| PDF | pypdf, Tesseract OCR (fallback) |
| Excel | openpyxl |
| Observability | Prometheus, Grafana, OpenTelemetry, structlog |
| Infra | Docker Compose, Kubernetes + Kustomize, GitHub Actions CI |

---

## Monorepo Layout

```
cab_invoice_ai_platform/
├── frontend/          Next.js 15 + TypeScript + Tailwind
├── backend/           FastAPI + SQLAlchemy async + Celery
├── k8s/               Kubernetes manifests + Helm-ready kustomization
├── observability/     Prometheus config, alert rules, Grafana dashboard, OTel config
├── scripts/           backup.sh
├── docker-compose.yml
├── docker-compose.dev.yml
└── docker-compose.observability.yml
```

---

## Data Models

```
User
  id, email, full_name, hashed_password, is_active, is_superuser

InvoiceBatch
  id, user_id, original_filename, status (pending/processing/completed/failed)
  total_invoices, processed_invoices, total_amount
  zip_storage_key, excel_storage_key, merged_pdf_storage_key
  task_id, started_at, completed_at, error_message

InvoiceRecord
  id, batch_id, filename, provider (rapido/ola/uber/namma_yatri/unknown)
  ride_date (YYYY-MM-DD), amount, time_of_day (am/pm/unknown)
  is_reimbursable, pdf_storage_key, parse_error
```

---

## Celery Pipeline (per batch)

```
process_invoice_batch (task)
  1. _stage_extract   — unzip PDFs → MinIO, create InvoiceRecord rows
  2. _stage_parse     — pypdf text extraction → provider parser → reimbursement rules
  3. _stage_excel     — generate 3-sheet XLSX → MinIO
  4. _stage_merge_pdf — sort by date+AM/PM, rename, merge with bookmarks → MinIO
```

**Retry:** 3 attempts, exponential back-off (30s→60s→120s), jitter.  
**DLQ:** Failed tasks route to `cab_invoice_dlx`. DLQ depth monitored by beat task every 5 min.

---

## Business Rules

- AM ride (hour < 12) → `to_office`
- PM ride (hour ≥ 12) → `to_home`
- Both directions reimbursable if `amount ≤ MAX_REIMBURSEMENT_AMOUNT` (default ₹500, env-configurable)
- Differential column = actual − capped amount (for audit)
- Over-cap invoices included at capped amount (not excluded)

---

## API Surface (`/api/v1/`)

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | 5/min rate limit |
| POST | `/auth/login` | 10/min rate limit |
| POST | `/auth/refresh` | |
| GET  | `/auth/me` | JWT required |
| POST | `/auth/logout` | |
| GET  | `/auth/sso/google` | 501 placeholder |
| POST | `/upload/` | 10/min; returns 202 + queues Celery task |
| GET  | `/upload/batches` | paginated |
| GET  | `/upload/batches/{id}` | |
| DELETE | `/upload/batches/{id}` | blocks if processing |
| GET  | `/invoices/batch/{id}` | parsed invoice records |
| GET  | `/invoices/batch/{id}/reimbursement-json` | per-date AM/PM eligible amounts as JSON |
| POST | `/carpooling/calculate` | multi-commuter Excel — base sheet + attendance xlsx files |
| POST | `/carpooling/calculate-from-json` | invoice JSON + pasted attendance text |
| GET  | `/carpooling/history` | paginated history |
| GET  | `/history/batches` | filters: status, year, month |
| GET  | `/history/monthly` | aggregated monthly summaries |
| GET  | `/health` | root liveness |
| GET  | `/ready` | readiness — checks DB |
| GET  | `/health/storage` | storage backend liveness |
| GET  | `/metrics` | Prometheus scrape endpoint |

---

## Supported Invoice Providers

| Provider | Detection | Extracted fields |
|---|---|---|
| **Rapido** | `rapido` keyword | Invoice ID, date, amount |
| **Ola** | `\bola\b` keyword | Trip ID, date, amount |
| **Uber** | `\buber\b` keyword | Trip ID, date, amount |
| **Namma Yatri** | `namma yatri` / `yatri` | Ride ID, date, amount |

When no provider matches → saved as `unknown` with `is_reimbursable = false`.

---

## Observability Stack

```
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

| Service | URL |
|---|---|
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin / admin) |
| OTel Collector | grpc://localhost:4317 |

Grafana dashboard panels: batch throughput, processing latency P50/P95/P99, invoices by provider, reimbursement amount, Celery task states.  
Enable OTel tracing: `OTLP_ENDPOINT=http://otel-collector:4317`

---

## Kubernetes Deployment

Manifests in `k8s/`. Kustomize for resource ordering.

- StatefulSets with PVCs for PostgreSQL, Redis, MinIO
- Deployments for backend, Celery worker, frontend
- HorizontalPodAutoscalers (backend: 2–8 pods, worker: 2–10, frontend: 2–6)
- NGINX Ingress with TLS + cert-manager
- Alembic migration Job (runs before backend starts)
- NetworkPolicies (least-privilege pod-to-pod traffic)
- PodDisruptionBudgets (zero-downtime rolling updates)
- Daily backup CronJob (pg_dump + MinIO mirror to S3)

---

## Security

- Rate limiting: 5/min register, 10/min login, 10/min upload
- Security headers via middleware
- Zip-bomb guard on upload
- Zip-slip prevention on extract
- Malware scan hook (ClamAV placeholder — not implemented)
- JWT with refresh token rotation
- Magic-byte validation on PDF upload

---

## Key Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL async URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `JWT_SECRET` | — | **Required.** Token signing secret |
| `STORAGE_PROVIDER` | `minio` | `minio` · `s3` · `azure` · `local` |
| `MAX_REIMBURSEMENT_AMOUNT` | `500` | Per-ride reimbursement cap in ₹ |
| `CARPOOLING_GAP_MINUTES` | `10` | Max entry/exit time gap for carpooling |
| `OCR_PROVIDER` | `tesseract` | OCR backend |
| `OTLP_ENDPOINT` | *(empty)* | OTel collector endpoint; empty = disabled |
| `RATELIMIT_STORAGE_URI` | `memory://` | Use `redis://redis:6379/2` in production |
