# System Design

Consolidated system design documents from across learn-patwari repositories.

## Contents

### HLD + DB Design
| Project | Source Repo | Documents |
|---|---|---|
| BookMyShow | `learn-patwari/system-design-book-my-show` | [HLD](./BookMyShow/BookMyShow-System-Design.md) · [DB Schema](./BookMyShow/BookMyShow-DB-Design.md) |
| BookMyDoc | `learn-patwari/book-my-doc` | [PRD](./BookMyDoc/BookMyDoc-PRD.md) · [Architecture](./BookMyDoc/BookMyDoc-System-Architecture.md) · [DB Schema](./BookMyDoc/BookMyDoc-DB-Schema.md) · [API Guide](./BookMyDoc/BookMyDoc-API-Guide.md) |
| Cab Invoice AI Platform | `learn-patwari/ai-assisted-invoice-processor` | [Architecture](./CabInvoiceAI/CabInvoiceAI-Architecture.md) |
| AKP S3 Hierarchy Service | `learn-patwari/akp-industry` | [Design](./AKP-S3-Service/AKP-S3-HierarchyService.md) |

### Architecture Patterns (General Reference)
| Topic | Document |
|---|---|
| Multi-Tenant + Multi-Region SaaS | [Design](./MultiTenant-MultiRegion/MultiTenant-MultiRegion-Architecture.md) |

### Low-Level Design (LLD)
| Project | Source Repo | Documents |
|---|---|---|
| Smart Parking Lot | `learn-patwari/parking-lot-lld` | [LLD](./ParkingLot-LLD/Smart-Parking-Lot-LLD.md) |

---

## Index by Topic

### Concurrency & Locking
- [Parking Lot: SKIP LOCKED spot allocation](./ParkingLot-LLD/Smart-Parking-Lot-LLD.md#64-why-skip-locked)
- [BookMyShow: Redis NX seat reservation](./BookMyShow/BookMyShow-System-Design.md#51-seat-reservation--preventing-double-booking)

### Database Schema Design
- [BookMyShow: Full relational schema + 20 SQL queries](./BookMyShow/BookMyShow-DB-Design.md)
- [BookMyDoc: Multi-tenant PostgreSQL (schema-per-tenant) + full ERD](./BookMyDoc/BookMyDoc-DB-Schema.md)
- [Parking Lot: PostgreSQL schema with indexes](./ParkingLot-LLD/Smart-Parking-Lot-LLD.md#4-data-model-relational-schema)

### Multi-Tenancy & Multi-Region
- [Multi-Tenant Multi-Region: Full reference (Pool / Schema / Silo + Active-Active / Regional Isolation)](./MultiTenant-MultiRegion/MultiTenant-MultiRegion-Architecture.md)
- [Multi-Tenant: Noisy neighbor isolation, rate limiting, K8s ResourceQuota per tenant](./MultiTenant-MultiRegion/MultiTenant-MultiRegion-Architecture.md#9-noisy-neighbor--tenant-isolation-at-scale)
- [Multi-Region: Control plane vs data plane separation](./MultiTenant-MultiRegion/MultiTenant-MultiRegion-Architecture.md#5-control-plane-vs-data-plane)
- [Data Residency: GDPR erasure, portability, cross-region routing](./MultiTenant-MultiRegion/MultiTenant-MultiRegion-Architecture.md#6-data-residency-and-compliance)
- [JWT in multi-region: asymmetric RS256, JWKS caching, cross-tenant SSO](./MultiTenant-MultiRegion/MultiTenant-MultiRegion-Architecture.md#7-authentication-in-multi-tenant-multi-region)
- [BookMyDoc: Schema-per-tenant isolation + tenant middleware](./BookMyDoc/BookMyDoc-System-Architecture.md#multi-tenancy-strategy)

### API Design
- [Parking Lot: Gate-facing REST APIs](./ParkingLot-LLD/Smart-Parking-Lot-LLD.md#5-public-apis-gate-facing)
- [BookMyDoc: Full REST API reference](./BookMyDoc/BookMyDoc-API-Guide.md)
- [Cab Invoice AI: Async upload API (202 + Celery queue)](./CabInvoiceAI/CabInvoiceAI-Architecture.md#api-surface-apiv1)

### Idempotency
- [Parking Lot: Idempotency key on entry](./ParkingLot-LLD/Smart-Parking-Lot-LLD.md#82-idempotency)
- [BookMyShow: Payment idempotent_key](./BookMyShow/BookMyShow-System-Design.md#53-payment-idempotency)

### Async Processing & Message Queues
- [Cab Invoice AI: Celery pipeline with DLQ + exponential backoff](./CabInvoiceAI/CabInvoiceAI-Architecture.md#celery-pipeline-per-batch)

### Caching
- [AKP S3 Service: Redis cache with nightly rebuild (3 AM clear / 5 AM warm-up)](./AKP-S3-Service/AKP-S3-HierarchyService.md#caching-strategy)
- [BookMyDoc: Redis for OTP + refresh tokens](./BookMyDoc/BookMyDoc-System-Architecture.md)
- [BookMyShow: Redis bitmap for seat availability](./BookMyShow/BookMyShow-System-Design.md#54-caching-strategy)

### Observability
- [Cab Invoice AI: Prometheus + Grafana + OTel tracing + 6 alert rules](./CabInvoiceAI/CabInvoiceAI-Architecture.md#observability-stack)

### Kubernetes & Cloud-Native
- [Cab Invoice AI: K8s with HPA, NetworkPolicies, PDB, daily backup CronJob](./CabInvoiceAI/CabInvoiceAI-Architecture.md#kubernetes-deployment)
- [AKP S3 Service: K8s with Helm-managed Redis](./AKP-S3-Service/AKP-S3-HierarchyService.md#kubernetes-deployment)

### RBAC & Authentication
- [BookMyDoc: JWT + refresh token rotation + 4-role RBAC](./BookMyDoc/BookMyDoc-System-Architecture.md#authentication-flow)

### File Storage
- [BookMyDoc: MinIO with pre-signed URLs, bucket-per-tenant](./BookMyDoc/BookMyDoc-System-Architecture.md#storage-architecture)
- [Cab Invoice AI: Pluggable storage backend (MinIO / S3 / Azure / Local)](./CabInvoiceAI/CabInvoiceAI-Architecture.md#key-environment-variables)

### SaaS & Subscription
- [Multi-Tenant: Per-tier cost model (Pool $0.30 → Enterprise $550/tenant/month)](./MultiTenant-MultiRegion/MultiTenant-MultiRegion-Architecture.md#13-cost-model-and-optimization)
- [Multi-Tenant: Tenant provisioning pipeline + region migration runbook](./MultiTenant-MultiRegion/MultiTenant-MultiRegion-Architecture.md#10-tenant-onboarding-workflow)
- [Multi-Region: DR runbook for region failure with GDPR compliance](./MultiTenant-MultiRegion/MultiTenant-MultiRegion-Architecture.md#12-disaster-recovery)
- [BookMyDoc: 3-tier subscription (Starter / Growth / Enterprise)](./BookMyDoc/BookMyDoc-PRD.md#7-subscription-tiers)
