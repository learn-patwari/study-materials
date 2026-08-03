# System Architecture — BookMyDoc Healthcare SaaS

> Source: learn-patwari/book-my-doc

## Architecture Pattern
**Modular Monolith** (FastAPI) with clean domain boundaries.  
Microservices extraction path is documented but not premature.

## Multi-Tenancy Strategy
**Schema-per-tenant** in PostgreSQL.

- `public` schema: platform-level (tenants, plans, super admins)
- `tenant_{slug}` schema: per-clinic isolated data

Tenant is resolved per-request via middleware → sets `SET search_path = tenant_{slug}, public` on the connection.

This gives:
- Strong data isolation (accidental cross-tenant query is structurally impossible)
- Easier per-tenant backup/restore
- Manageable up to ~1,000 tenants; shared-table approach needed beyond that

## Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼─────────────────────────────────┐
│                    Nginx (Reverse Proxy)                      │
│            SSL termination, rate limiting, CORS              │
└───────┬───────────────────────────────────────┬─────────────┘
        │ /                                      │ /api/
┌───────▼────────┐                    ┌──────────▼───────────┐
│  Next.js 15    │                    │   FastAPI (Python)    │
│  (Port 3000)   │                    │   (Port 8000)         │
│  App Router    │                    │   /api/v1/*           │
│  SSR + Static  │                    │                       │
└────────────────┘                    └──┬──────┬──────┬──────┘
                                         │      │      │
                          ┌──────────────▼─┐ ┌──▼──┐ ┌▼──────┐
                          │  PostgreSQL 16  │ │Redis│ │ MinIO │
                          │  Multi-schema   │ │Cache│ │Storage│
                          │  (tenant data)  │ │+OTP │ │+Files │
                          └────────────────┘ └─────┘ └───────┘
```

## Request Flow

```
Client Request
  → Nginx (SSL, rate limit)
    → FastAPI
      → TenantMiddleware (resolve slug → set search_path)
        → AuthMiddleware (validate JWT → set current_user)
          → RBAC Dependency (check role permission)
            → Router → Service → Repository → DB
              → Response (Pydantic schema)
```

## Backend Module Structure

```
app/
  core/
    config.py       # pydantic-settings from .env
    database.py     # async SQLAlchemy engine + session factory
    security.py     # JWT encode/decode, password hashing
    dependencies.py # FastAPI dependency injection (auth, tenant, pagination)

  middleware/
    tenant.py       # Extract X-Tenant-Slug → set DB search_path
    audit.py        # Log all mutating requests to audit_logs
    rate_limit.py   # Redis-backed sliding window

  models/           # SQLAlchemy ORM (declarative, async)
  schemas/          # Pydantic v2 (request/response, strict typing)
  repositories/     # Repository pattern (BaseRepository[T] + domain repos)
  services/         # Business logic (thin controllers, fat services)
  api/v1/routers/   # FastAPI APIRouter per domain
  tasks/            # Background tasks (notifications, cleanup)
  utils/
    storage.py      # MinIO/S3 client abstraction
    pdf.py          # Prescription PDF generation (WeasyPrint)
    otp.py          # OTP generation and Redis TTL storage
    sms.py          # SMS gateway abstraction (Fast2SMS adapter)
    email.py        # Email sending abstraction (SMTP/SendGrid)
```

## Authentication Flow

```
Register/Login
  → Validate credentials
  → Generate JWT (access: 15min, HS256)
  → Generate refresh token (UUID, store in Redis with TTL 7d)
  → Return {access_token, refresh_token}

Authenticated Request
  → Extract Bearer token from Authorization header
  → Decode JWT → validate expiry + signature
  → Load user from DB → check is_active + role
  → Inject into endpoint via Depends(get_current_user)

Token Refresh
  → Validate refresh token exists in Redis
  → Delete old refresh token (rotation)
  → Issue new access + refresh token pair
```

## RBAC Model

```
Role hierarchy (non-inheriting, explicit permissions):
  SUPER_ADMIN  → all platform operations + cross-tenant reads
  CLINIC_ADMIN → all operations within own tenant
  DOCTOR       → read patients, manage own appointments + Rx
  PATIENT      → read/book own appointments, view own records
```

Permission check is a FastAPI dependency:
```python
require_roles([Role.DOCTOR, Role.CLINIC_ADMIN])
```

## Storage Architecture

All files stored in MinIO with organized bucket structure:
```
bucket: bookmydoc-{tenant_slug}
  /profiles/          doctor and patient profile photos
  /prescriptions/     scanned prescription images/PDFs
  /records/           EMR file uploads (lab, radiology, etc.)
  /logos/             clinic logos
```

Access via pre-signed URLs (15-minute expiry) — files never proxied through API server.

Migration to AWS S3: change `STORAGE_ENDPOINT` env var. Zero code change (boto3-compatible).

## Notification Architecture

```
Appointment booked
  → AppointmentService.create()
    → NotificationTask.schedule(appointment)
      → Redis queue (lightweight task)
        → Background worker
          → SMS via Fast2SMS API
          → Email via SMTP/SendGrid
          → In-app notification record in DB
```

Celery + Redis upgrade path: swap background tasks for Celery tasks with same interface.

## Scalability Path

| Load | Action |
|---|---|
| < 100 tenants | Single Docker Compose stack |
| 100–1000 tenants | Add read replica, Redis cluster |
| 1000+ tenants | Split to row-based multi-tenancy, add connection pooling (PgBouncer) |
| High throughput | Extract notification service as microservice |
