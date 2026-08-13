# Multi-Tenant Multi-Region Architecture — System Design

> Reference architecture for SaaS platforms serving enterprise customers across
> multiple geographies, with data residency, isolation, and consistency guarantees.
>
> Companies with this problem: Salesforce, Shopify, Atlassian, Stripe, GitHub,
> Twilio, Razorpay, Freshworks, Zoho, Postman

---

## 1. Problem Statement

A SaaS company wants to:
- Serve thousands of tenants (companies) on shared infrastructure
- Allow tenants to choose which region their data lives in (GDPR, DPDP, data sovereignty)
- Provide strong isolation so one tenant's load doesn't affect others
- Keep global operations (auth, billing, routing) fast across regions
- Support active users in any region with low latency

**The core tensions:**
1. **Isolation vs Cost** — dedicated infra per tenant is safe but expensive; shared infra is cheap but noisy
2. **Consistency vs Latency** — strong consistency requires round trips; eventual consistency is fast but complex
3. **Data Residency vs Global Features** — tenant data must stay in EU, but global auth spans all regions

---

## 2. Multi-Tenancy Models

### 2.1 Silo (Dedicated per Tenant)

```
Tenant A                    Tenant B
┌─────────────────────┐    ┌─────────────────────┐
│  App Instance       │    │  App Instance       │
│  Database           │    │  Database           │
│  Cache              │    │  Cache              │
│  Network (VPC)      │    │  Network (VPC)      │
└─────────────────────┘    └─────────────────────┘
```

| Pros | Cons |
|---|---|
| Perfect isolation (blast radius = 1 tenant) | Highest cost (N tenants = N infra stacks) |
| Independent scaling | Slow onboarding (minutes to provision) |
| Dedicated backup/restore | Underutilized resources |
| Easier compliance (SOC2, HIPAA, FedRAMP) | Operational overhead (N databases to manage) |

**When to use:** Enterprise contracts ($100K+/year), FedRAMP/ITAR requirements, data residency mandates, customers with custom SLAs.

**Examples:** Salesforce's largest customers get dedicated "pods", AWS Control Tower customer accounts.

---

### 2.2 Pool (Shared Everything)

```
┌──────────────────────────────────────────────────────┐
│                  Shared App Tier                      │
│  ┌─────────────────────────────────────────────────┐  │
│  │           Single Database                        │  │
│  │  tenant_id column in every table                │  │
│  │  Row-Level Security enforces isolation           │  │
│  └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

Row-level security (PostgreSQL):
```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- App sets context at connection time
SET app.current_tenant = '550e8400-e29b-41d4-a716-446655440000';
SELECT * FROM orders;  -- only sees current tenant's rows
```

| Pros | Cons |
|---|---|
| Lowest cost | Noisy neighbor problem |
| Instant tenant onboarding | Data leaks if RLS misconfigured |
| Shared schema migrations | Complex query optimization (all queries filter by tenant_id) |
| Simple operations | Single point of failure affects all tenants |

**When to use:** SMB/startup customers, free tier, internal tools. Thousands of small tenants.

---

### 2.3 Bridge (Schema-per-Tenant) — Most Common for Mid-Market SaaS

```
┌──────────────────────────────────────────────────────┐
│                  Shared App Tier                      │
│                                                       │
│   PostgreSQL (shared cluster)                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │tenant_a  │  │tenant_b  │  │tenant_c  │           │
│   │ schema   │  │ schema   │  │ schema   │           │
│   └──────────┘  └──────────┘  └──────────┘           │
│   public schema (tenants, plans, global config)       │
└──────────────────────────────────────────────────────┘
```

```sql
-- Middleware sets search_path per request
SET search_path = tenant_acme, public;

-- All queries naturally scoped to tenant schema
SELECT * FROM orders;  -- hits tenant_acme.orders
```

| Pros | Cons |
|---|---|
| Strong logical isolation | Schema migrations run N times (once per tenant) |
| Per-tenant backup (pg_dump one schema) | Scaling limited by single PG cluster |
| Shared infra costs | Cross-tenant queries need dynamic schema name |
| Fast onboarding (CREATE SCHEMA + migrate) | Max ~1000 tenants per cluster practically |

**Used by:** Freshworks, Zoho, BookMyDoc (our own project), many mid-market SaaS

---

### 2.4 Tiered Hybrid (Production Reality)

Most mature SaaS platforms use all three tiers:

```
Customer Size          Model              Example
─────────────────────────────────────────────────────
Free / Startup         Pool (shared)     100,000 tenants, 1 cluster
SMB                    Schema-per-tenant 5,000 tenants, 10 clusters
Enterprise ($50K+)     Silo (dedicated)  50 tenants, 50 stacks
```

The app code is identical — only the connection string and provisioning layer differ. Tenants are migrated upward as they grow.

---

## 3. Multi-Region Architecture

### 3.1 Active-Passive (Hot Standby)

```
                    ┌─────────────────────────────┐
         DNS/GLB    │    Global Load Balancer      │
                    │  (Route53 / Cloudflare)      │
                    └──────────┬──────────────────┘
                               │  All traffic
                    ┌──────────▼─────────┐
                    │  Region: us-east-1 │  ← PRIMARY
                    │  App + DB (write)  │
                    └──────────┬─────────┘
                               │  Async replication
                    ┌──────────▼─────────┐
                    │  Region: eu-west-1 │  ← STANDBY
                    │  App + DB (read)   │
                    └────────────────────┘
```

**Failover:** DNS TTL flip to standby region. RTO: 1–10 minutes. RPO: seconds (async replication lag).

**Pros:** Simple, no write conflicts, strong consistency.

**Cons:** Users in EU hit US datacenter (100–200ms RTT), standby region is wasted cost, failover is manual or slow.

**Use when:** Single primary region acceptable, disaster recovery only, budget-constrained.

---

### 3.2 Active-Active (Multi-Master Write)

```
         ┌─────────────────────────────────────────────┐
         │           Global Load Balancer               │
         │    GeoDNS: routes based on client IP         │
         └──────────┬───────────────────────┬───────────┘
                    │                       │
         ┌──────────▼─────────┐  ┌──────────▼─────────┐
         │  Region: us-east-1 │  │  Region: eu-west-1 │
         │  App (write+read)  │  │  App (write+read)  │
         │  DB (write+read)   │◄─►  DB (write+read)   │
         └──────────┬─────────┘  └──────────┬─────────┘
                    │                        │
                    └───────────┬────────────┘
                                │
                    ┌───────────▼────────────┐
                    │  Region: ap-south-1    │
                    │  App (write+read)      │
                    │  DB (write+read)       │
                    └────────────────────────┘
```

**Challenge: Write conflicts.** Two users in different regions modify the same record simultaneously.

**Conflict resolution strategies:**
1. **Last-Write-Wins (LWW):** Higher timestamp wins. Simple, but loses data.
2. **CRDT (Conflict-free Replicated Data Types):** Math-proven merge. Works for counters, sets. Not for arbitrary records.
3. **Application-level merge:** Custom logic per entity type. Complex but correct.
4. **Sticky sessions:** User's writes always go to their "home" region, reads are local. Avoids conflicts entirely.

---

### 3.3 Regional Isolation (Most Common for Data Residency) ⭐

Each tenant's data lives in exactly one region. Users in that tenant are routed there.

```
                    ┌──────────────────────────────────────┐
                    │        Control Plane (Global)         │
                    │  - Tenant registry                    │
                    │  - Auth (token issuance)              │
                    │  - Billing                            │
                    │  - Global routing table               │
                    └───┬──────────────────────────┬────────┘
                        │ "tenant A → eu-west-1"    │ "tenant B → ap-south-1"
         ┌──────────────▼──────────────┐  ┌──────────▼──────────────────┐
         │     Data Plane: EU          │  │     Data Plane: India        │
         │  App + DB + Cache           │  │  App + DB + Cache            │
         │  Tenant A, C, D data        │  │  Tenant B, E data            │
         │  (never leaves EU)          │  │  (never leaves India)        │
         └─────────────────────────────┘  └──────────────────────────────┘
```

**How routing works:**

```
User from acme.yoursaas.com
  → Global DNS resolves to anycast IP or GLB
  → GLB checks tenant registry: acme → eu-west-1
  → Proxy routes request to eu-west-1 app cluster
  → eu-west-1 app handles entirely within region
  → Response: data never left EU
```

**Tenant registry (control plane):**
```json
{
  "tenant_id": "acme",
  "slug": "acme",
  "region": "eu-west-1",
  "tier": "enterprise",
  "subdomain": "acme.yoursaas.com",
  "status": "active",
  "data_residency": "GDPR-EU"
}
```

This document is **globally replicated** (read-heavy, tiny, no PII) — every region caches it for routing.

---

## 4. Full Architecture Blueprint (Regional Isolation Pattern)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            GLOBAL LAYER                                       │
│                                                                               │
│  ┌─────────────────────┐   ┌─────────────────────┐   ┌──────────────────┐   │
│  │  GeoDNS / Anycast   │   │  Global Auth Service │   │  Billing Service │   │
│  │  (Cloudflare/R53)   │   │  (Token issuance)    │   │  (Stripe)        │   │
│  └──────────┬──────────┘   └──────────┬──────────┘   └──────────────────┘   │
│             │                         │                                       │
│  ┌──────────▼──────────────────────────────────────────────────────────────┐ │
│  │              Tenant Routing Layer (Control Plane)                        │ │
│  │  - Maps subdomain/tenant_id → region                                    │ │
│  │  - Replicated to all regions (Cockroach / DynamoDB Global Tables)       │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼──────────────────────┐
              │                     │                       │
┌─────────────▼───────┐ ┌──────────▼──────────┐ ┌─────────▼───────────┐
│  REGION: us-east-1  │ │  REGION: eu-west-1  │ │  REGION: ap-south-1 │
│  ─────────────────  │ │  ─────────────────  │ │  ─────────────────  │
│  CDN (CloudFront)   │ │  CDN (CloudFront)   │ │  CDN (CloudFront)   │
│  API Gateway        │ │  API Gateway        │ │  API Gateway        │
│  WAF + Rate Limit   │ │  WAF + Rate Limit   │ │  WAF + Rate Limit   │
│                     │ │                     │ │                     │
│  App Tier (EKS)     │ │  App Tier (EKS)     │ │  App Tier (EKS)     │
│  ┌───────────────┐  │ │  ┌───────────────┐  │ │  ┌───────────────┐  │
│  │ Pod: tenant A │  │ │  │ Pod: tenant C │  │ │  │ Pod: tenant B │  │
│  │ Pod: tenant F │  │ │  │ Pod: tenant D │  │ │  │ Pod: tenant E │  │
│  └───────────────┘  │ │  └───────────────┘  │ │  └───────────────┘  │
│                     │ │                     │ │                     │
│  Cache (ElastiCache)│ │  Cache (ElastiCache)│ │  Cache (ElastiCache)│
│  DB: RDS Aurora     │ │  DB: RDS Aurora     │ │  DB: RDS Aurora     │
│  (Multi-AZ)         │ │  (Multi-AZ)         │ │  (Multi-AZ)         │
│                     │ │                     │ │                     │
│  Object Store (S3)  │ │  Object Store (S3)  │ │  Object Store (S3)  │
│  Queue (SQS)        │ │  Queue (SQS)        │ │  Queue (SQS)        │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

---

## 5. Control Plane vs Data Plane

This is the most important architectural distinction.

### 5.1 Control Plane (Global)

Handles **metadata and coordination** — not tenant data. Must be globally consistent.

| Service | Purpose | Storage |
|---|---|---|
| Tenant Registry | Maps tenant → region, tier, status | CockroachDB / DynamoDB Global |
| Auth Service | Issues + validates JWT tokens | Redis (global) + replicated key pairs |
| Billing Service | Subscription state, invoices | Stripe + DB |
| Feature Flags | Which features enabled per tenant | LaunchDarkly / Unleash (global) |
| DNS Management | Subdomain → endpoint routing | Route53 / Cloudflare |
| Audit Log Collector | Cross-region audit aggregation | S3 + Athena |

**Key constraint:** Control plane data is tiny but accessed on every request. Cache it aggressively (1-minute TTL at region edge). Stale control plane data means routing to wrong region or accepting requests for suspended tenants — acceptable for 60 seconds.

### 5.2 Data Plane (Regional)

Handles **tenant data** — never crosses regional boundary. Each region is independent.

| Service | Purpose | Storage |
|---|---|---|
| Application API | Business logic | Stateless (Kubernetes pods) |
| Primary Database | Tenant data (orders, users, etc.) | RDS Aurora PostgreSQL (Multi-AZ) |
| Cache | Session data, query cache | ElastiCache Redis (with replica) |
| Object Storage | Files, attachments | S3 (regional bucket) |
| Message Queue | Async processing | SQS / Kafka (regional) |
| Search | Full-text search | OpenSearch (regional cluster) |

---

## 6. Data Residency and Compliance

### 6.1 GDPR (EU) Requirements

- **Article 17 (Right to Erasure):** Delete all EU resident data within 30 days of request
- **Article 20 (Data Portability):** Export all data in machine-readable format
- **Article 44 (Transfer Restrictions):** EU resident data must not leave EU without adequate safeguards

**Implementation:**

```python
# Data export (Article 20)
def export_tenant_data(tenant_id: str) -> str:
    # Only export, never cross region
    assert get_tenant_region(tenant_id) == CURRENT_REGION
    
    data = {
        "users": db.query("SELECT * FROM users"),
        "orders": db.query("SELECT * FROM orders"),
        "files": [s3.generate_presigned_url(key) for key in list_tenant_files()]
    }
    
    export_key = f"exports/{tenant_id}/{uuid4()}.json.gz"
    s3.put_object(
        Bucket=TENANT_BUCKET,
        Key=export_key,
        Body=gzip.compress(json.dumps(data).encode()),
        ServerSideEncryption="aws:kms"  # encrypt at rest
    )
    return s3.generate_presigned_url(export_key, ExpiresIn=3600)

# Right to erasure (Article 17)
def erase_user_data(tenant_id: str, user_id: str):
    with db.transaction():
        # Anonymize instead of hard-delete (preserves referential integrity)
        db.execute("""
            UPDATE users
            SET email = 'deleted@gdpr.invalid',
                name = 'Deleted User',
                phone = NULL,
                gdpr_erased_at = NOW()
            WHERE id = ? AND tenant_id = ?
        """, user_id, tenant_id)
        
        # Delete from cache immediately
        redis.delete(f"user:{tenant_id}:{user_id}")
        
        # Audit log (must keep 7 years for compliance)
        audit_log.write({
            "action": "GDPR_ERASURE",
            "user_id": user_id,
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat()
        })
```

### 6.2 Data Residency Technical Controls

```python
# Middleware: ensure request stays in correct region
class DataResidencyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        tenant_id = extract_tenant_id(scope)
        expected_region = tenant_registry.get_region(tenant_id)
        current_region = os.environ["AWS_REGION"]
        
        if expected_region != current_region:
            # This request was misrouted — redirect to correct region
            endpoint = get_regional_endpoint(expected_region)
            await redirect(scope, send, f"{endpoint}{scope['path']}")
            return
        
        await self.app(scope, receive, send)
```

**Cross-region data leak prevention:**
```python
# Database connection is always regional
DATABASE_URL = os.environ["DATABASE_URL"]  # points to local region DB

# Never store cross-region references in tenant data
# WRONG:
order.user_id = "user:eu:abc123"  # embeds region in ID

# RIGHT: user IDs are opaque UUIDs; region is in the routing layer
order.user_id = "550e8400-e29b-41d4-a716-446655440000"
```

---

## 7. Authentication in Multi-Tenant Multi-Region

### 7.1 The JWT Cross-Region Challenge

Token issued in EU must be validatable in India without a network call to EU.

**Solution: Asymmetric JWT (RS256/ES256)**

```
Control Plane (Global):
  - Generates RSA or EC key pair
  - Private key: used to sign tokens (never leaves control plane)
  - Public key: published at /.well-known/jwks.json
  - All regions cache JWKS with 1-hour TTL

User Login (EU region):
  POST /auth/token
  → validate credentials against eu-west-1 DB
  → sign JWT with private key
  → embed: {sub, tenant_id, region, roles, exp, iat}
  → return JWT

API Request to any region:
  GET /api/orders (with Bearer token)
  → region fetches JWKS from cache (local)
  → verify JWT signature with public key (no network call!)
  → extract tenant_id from claims
  → verify tenant belongs to this region
  → proceed
```

**JWKS caching in each region:**
```python
class JWKSCache:
    def __init__(self):
        self._cache = {}
        self._last_refresh = 0
    
    def get_public_key(self, kid: str):
        if time.time() - self._last_refresh > 3600:
            self._refresh()
        return self._cache.get(kid)
    
    def _refresh(self):
        # Fetch from control plane's public endpoint
        response = requests.get("https://auth.yoursaas.com/.well-known/jwks.json")
        for key in response.json()["keys"]:
            self._cache[key["kid"]] = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        self._last_refresh = time.time()
```

### 7.2 Multi-Tenant JWT Claims

```json
{
  "sub": "user:550e8400",
  "tenant_id": "acme",
  "tenant_region": "eu-west-1",
  "roles": ["clinic_admin", "user"],
  "plan": "enterprise",
  "iat": 1699000000,
  "exp": 1699003600,
  "iss": "https://auth.yoursaas.com",
  "aud": "https://api.yoursaas.com"
}
```

**Role resolution:**
```python
def has_permission(token_claims: dict, required_permission: str) -> bool:
    tenant_id = token_claims["tenant_id"]
    roles = token_claims["roles"]
    
    # Permission matrix cached per tenant (from control plane)
    permissions = permission_cache.get(tenant_id, roles)
    return required_permission in permissions
```

### 7.3 Cross-Tenant SSO (Enterprise)

Enterprise customers often have their own IdP (Okta, Azure AD). SAML or OIDC.

```
User → acme.yoursaas.com/login
  → detect tenant from subdomain
  → redirect to tenant's IdP (Okta)
  → Okta authenticates → sends SAML assertion to ACS URL
  → ACS validates assertion, creates local session
  → issue platform JWT with claims from SAML attributes
  → user lands on dashboard
```

---

## 8. Database Architecture for Multi-Tenant Multi-Region

### 8.1 Schema Migration Across All Tenants

Every schema change must be applied to all tenant schemas — in all regions — safely.

**Migration strategy:**
```python
# Tenant-aware Alembic-style migration runner
def run_migration(migration_script: str):
    # Get all tenants in current region
    tenants = control_plane.list_tenants_in_region(CURRENT_REGION)
    
    failed = []
    for tenant in tenants:
        try:
            with db.connect() as conn:
                conn.execute(f"SET search_path = {tenant.schema_name}, public")
                conn.execute(migration_script)
                conn.commit()
        except Exception as e:
            failed.append((tenant.id, str(e)))
            log.error(f"Migration failed for {tenant.id}: {e}")
    
    if failed:
        raise MigrationPartialFailure(failed)

# Migration must be backward compatible (expand-contract pattern):
# Phase 1: ADD new column (nullable, no default) — deploy
# Phase 2: Backfill data — run async
# Phase 3: Add NOT NULL constraint — deploy
# Phase 4: Remove old column — deploy (next release)
```

**Zero-downtime migrations (expand-contract):**
```sql
-- Phase 1: Add nullable column (backward compatible — old code ignores it)
ALTER TABLE orders ADD COLUMN new_status VARCHAR(50);

-- Phase 2: Backfill (run while serving traffic)
UPDATE orders SET new_status = old_status WHERE new_status IS NULL;

-- Phase 3: Add constraint (once all rows filled)
ALTER TABLE orders ALTER COLUMN new_status SET NOT NULL;

-- Phase 4: Remove old column (once new code is deployed everywhere)
ALTER TABLE orders DROP COLUMN old_status;
```

### 8.2 Global Tables (Control Plane Data)

Some data must be globally consistent:
- Tenant registry
- Feature flags
- Global user identities (cross-tenant SSO)

**Options:**

| Database | Replication | Consistency | Latency | Use case |
|---|---|---|---|---|
| CockroachDB | Raft (synchronous) | Serializable | 50–150ms for global | Global control plane |
| Google Spanner | TrueTime + Paxos | External consistency | 1–10ms (regional) | Same as above |
| DynamoDB Global Tables | Async multi-master | Eventually consistent | <10ms (local) | Routing table, feature flags |
| PostgreSQL logical replication | Async | Eventual (replicas) | <1s lag | Read replicas in each region |
| CockroachDB (multi-region) | Raft | Regional serializable | <10ms (regional) | Global + regional mix |

**CockroachDB multi-region survival goals:**
```sql
-- Database survives region failure
ALTER DATABASE platform SET PRIMARY REGION "us-east1";
ALTER DATABASE platform ADD REGION "eu-west1";
ALTER DATABASE platform ADD REGION "ap-southeast1";
ALTER DATABASE platform SET SECONDARY REGION "eu-west1";

-- Global table (reads fast everywhere, writes go to primary)
ALTER TABLE tenant_registry SET LOCALITY GLOBAL;

-- Regional table (reads/writes optimized for home region)
ALTER TABLE tenant_data SET LOCALITY REGIONAL BY ROW;
-- CockroachDB automatically routes to home region based on crdb_region column
```

### 8.3 Read Replicas Per Region

For the data plane, each region has a primary + read replicas:

```
eu-west-1:
  Primary (writer) ─── reads go here for strong consistency
       │
       ├── Read Replica 1 (AZ-a) ← reads (99% of traffic)
       └── Read Replica 2 (AZ-b) ← reads + failover

Read replica lag monitoring:
  SELECT now() - pg_last_xact_replay_timestamp() AS lag;
  -- Alert if lag > 100ms

Connection routing (pgBouncer + application):
  writer: postgres://primary.eu.rds.amazonaws.com:5432/db
  reader: postgres://replica.eu.rds.amazonaws.com:5432/db
```

---

## 9. Noisy Neighbor — Tenant Isolation at Scale

### 9.1 Compute Isolation

**Kubernetes:** Namespace + ResourceQuota per tenant tier

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: starter-tier-quota
  namespace: tenant-acme
spec:
  hard:
    requests.cpu: "2"
    requests.memory: "4Gi"
    limits.cpu: "4"
    limits.memory: "8Gi"
    pods: "10"
---
apiVersion: policy/v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: tenant-acme
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    type: Container
```

**Priority classes (enterprise tenants get higher scheduling priority):**
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: enterprise-tenant
value: 1000
globalDefault: false
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: starter-tenant
value: 100
```

### 9.2 Database Isolation

**Per-tenant connection limits (PostgreSQL):**
```sql
-- Limit connections per role
ALTER ROLE tenant_acme CONNECTION LIMIT 20;

-- Per-tenant rate limiting via pg_cron or pgBouncer pool
-- pgBouncer pool per tenant schema
[tenant_acme]
host = localhost
port = 5432
dbname = saas_db
auth_user = tenant_acme
pool_size = 20
max_client_conn = 50
```

**Query timeout per tenant tier:**
```python
class TenantAwareConnection:
    TIER_TIMEOUTS = {
        "starter": 5000,      # 5 seconds
        "growth": 15000,      # 15 seconds
        "enterprise": 60000   # 60 seconds
    }
    
    def get_connection(self, tenant: Tenant):
        conn = db_pool.get_connection()
        timeout = self.TIER_TIMEOUTS[tenant.tier]
        conn.execute(f"SET statement_timeout = {timeout}")
        conn.execute(f"SET search_path = {tenant.schema_name}, public")
        return conn
```

### 9.3 Rate Limiting Per Tenant

```python
def check_rate_limit(tenant_id: str, endpoint: str) -> bool:
    # Tenant-specific limits from config
    limits = get_tenant_limits(tenant_id)
    # e.g., {"api_rpm": 1000, "upload_per_day": 100}
    
    key = f"ratelimit:{tenant_id}:{endpoint}:{int(time.time() // 60)}"
    
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, 120)
    count, _ = pipe.execute()
    
    limit = limits.get(f"{endpoint}_rpm", 100)
    if count > limit:
        metrics.increment("rate_limit.hit", tags={"tenant": tenant_id})
        return False
    return True
```

**Global rate limiting across regions (shared Redis):**
```python
# If rate limits must be enforced globally (not per-region),
# use a global Redis in the control plane:
GLOBAL_REDIS = redis.Redis(host="global-redis.yoursaas.internal")

def check_global_api_limit(tenant_id: str, limit: int) -> bool:
    key = f"global_api:{tenant_id}:{int(time.time() // 60)}"
    count = GLOBAL_REDIS.incr(key)
    if count == 1:
        GLOBAL_REDIS.expire(key, 120)
    return count <= limit
```

---

## 10. Tenant Onboarding Workflow

### 10.1 Provisioning Pipeline

```
Sales closes deal → CRM event → Provisioning Webhook
                                        │
                            ┌───────────▼───────────────┐
                            │   Provisioning Service    │
                            │                           │
                            │  1. Assign region         │
                            │  2. Create DNS record     │
                            │  3. Create DB schema      │
                            │  4. Run migrations        │
                            │  5. Seed default data     │
                            │  6. Create admin user     │
                            │  7. Send welcome email    │
                            │  8. Update tenant registry│
                            └───────────────────────────┘
```

```python
class TenantProvisioner:
    def provision(self, tenant_config: TenantConfig) -> Tenant:
        region = self._assign_region(tenant_config)
        
        with self._regional_db(region) as db:
            # 1. Create schema
            schema_name = f"tenant_{tenant_config.slug}"
            db.execute(f"CREATE SCHEMA {schema_name}")
            
            # 2. Run all migrations on new schema
            db.execute(f"SET search_path = {schema_name}, public")
            migration_runner.run_all(db)
            
            # 3. Seed default data
            db.execute("""
                INSERT INTO subscription_plans SELECT * FROM public.default_plans
            """)
        
        # 4. Register in control plane (globally)
        tenant = control_plane.register_tenant(
            id=uuid4(),
            slug=tenant_config.slug,
            region=region,
            tier=tenant_config.tier,
            schema_name=schema_name
        )
        
        # 5. Configure DNS
        dns.create_cname(
            f"{tenant_config.slug}.yoursaas.com",
            f"lb.{region}.yoursaas.com"
        )
        
        # 6. Create admin user
        self._create_admin_user(tenant, tenant_config.admin_email, region)
        
        # 7. Notify
        notifications.send_welcome(tenant_config.admin_email, tenant)
        
        return tenant
    
    def _assign_region(self, config: TenantConfig) -> str:
        if config.data_residency == "GDPR-EU":
            return "eu-west-1"
        elif config.data_residency == "India":
            return "ap-south-1"
        else:
            return "us-east-1"  # default
```

### 10.2 Tenant Migration (Region Transfer)

When a tenant moves from US to EU (GDPR request):

```
1. Set tenant status = MIGRATING (new writes blocked or dual-written)
2. Export all tenant data from us-east-1 (S3 archive)
3. Import into eu-west-1 (restore to new schema)
4. Verify checksums (row counts, sums of key metrics)
5. Update DNS: acme.yoursaas.com → eu-west-1 load balancer
6. Update tenant registry: region = eu-west-1
7. Delete data from us-east-1
8. Set tenant status = ACTIVE in eu-west-1
```

---

## 11. Observability in Multi-Tenant Multi-Region

### 11.1 Per-Tenant Metrics

```python
# Every metric tagged with tenant + region
metrics.increment(
    "api.requests",
    tags={
        "tenant": tenant_id,
        "tier": tenant.tier,
        "region": CURRENT_REGION,
        "endpoint": endpoint,
        "status": response_status
    }
)

# SLA tracking per tenant
metrics.histogram(
    "api.latency_ms",
    value=response_time_ms,
    tags={"tenant": tenant_id, "region": CURRENT_REGION}
)
```

**Datadog / Grafana query for per-tenant SLA:**
```promql
# P99 latency per tenant in EU region
histogram_quantile(0.99,
  rate(api_latency_ms_bucket{region="eu-west-1"}[5m])
) by (tenant)
```

### 11.2 Distributed Tracing Across Regions

When a request touches control plane (global) + data plane (regional):

```python
# Propagate trace context across regional boundaries
import opentelemetry.trace as trace

tracer = trace.get_tracer(__name__)

def handle_request(request):
    # Extract trace from incoming request (W3C TraceContext)
    ctx = propagate.extract(request.headers)
    
    with tracer.start_as_current_span(
        "handle_api_request",
        context=ctx,
        attributes={
            "tenant.id": tenant_id,
            "tenant.region": tenant_region,
            "service.region": CURRENT_REGION
        }
    ) as span:
        # Cross-region call to control plane
        with tracer.start_as_current_span("fetch_tenant_config"):
            config = control_plane.get_config(tenant_id)
        
        result = business_logic(request, config)
        return result
```

**Trace correlation across regions:** Use the same `trace_id` (128-bit), sampled consistently (Jaeger / Zipkin / OTEL Collector in each region, aggregated to central Jaeger).

### 11.3 Audit Logs (Compliance)

```python
# Every write operation generates an immutable audit event
class AuditLogger:
    def log(self, event: AuditEvent):
        entry = {
            "id": str(uuid4()),
            "tenant_id": event.tenant_id,
            "user_id": event.user_id,
            "action": event.action,         # CREATE / UPDATE / DELETE / VIEW
            "entity": event.entity,
            "entity_id": event.entity_id,
            "old_values": event.old_values, # redact PII from logs
            "new_values": event.new_values,
            "ip_address": event.ip,
            "region": CURRENT_REGION,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Write to regional S3 (stays in region — compliance!)
        s3.put_object(
            Bucket=f"audit-logs-{CURRENT_REGION}",
            Key=f"tenant={event.tenant_id}/{datetime.utcnow().date()}/{entry['id']}.json",
            Body=json.dumps(entry),
            ServerSideEncryption="aws:kms"
        )
```

**Audit log querying (Athena):**
```sql
-- All actions by a user in the last 30 days
SELECT action, entity, entity_id, timestamp
FROM audit_logs
WHERE tenant_id = 'acme'
  AND user_id = 'user-123'
  AND timestamp >= current_date - interval '30' day
ORDER BY timestamp DESC;
```

---

## 12. Disaster Recovery

### 12.1 RTO and RPO Targets by Tier

| Tier | RTO (Recovery Time) | RPO (Recovery Point) | Strategy |
|---|---|---|---|
| Starter | 4 hours | 1 hour | RDS automated backups to S3 |
| Growth | 30 minutes | 5 minutes | Multi-AZ + point-in-time recovery |
| Enterprise | 5 minutes | 0 (zero RPO) | Synchronous replication + hot standby |

### 12.2 Failover Runbook (Region Failure)

```
INCIDENT: eu-west-1 region degraded

1. Detect: PagerDuty alert fires (latency > 5s, error rate > 1%)

2. Assess:
   - Is entire region down or specific AZ?
   - Is DB primary affected or just replicas?

3. For AZ failure: Aurora auto-fails to standby AZ (automatic, ~30s)

4. For region failure:
   a. Notify all EU tenants (status page + email)
   b. Promote eu-central-1 (Frankfurt) as DR region
   c. Restore from latest S3 backup to eu-central-1
   d. Update tenant registry: eu-west-1 tenants → eu-central-1
   e. Update DNS: * .eu.yoursaas.com → eu-central-1 LB
   f. Verify EU tenants can access eu-central-1

5. Post-recovery:
   - Data still in EU (Frankfurt is EU — GDPR compliant)
   - When eu-west-1 recovers: sync back, migrate tenants home
```

---

## 13. Cost Model and Optimization

### 13.1 Per-Tier Cost Analysis

```
Starter (Pool model):
  Shared RDS: $0.20/tenant/month (10,000 tenants on 10 RDS clusters)
  Shared EKS: $0.05/tenant/month
  Storage: $0.05/tenant/month
  Total: ~$0.30/tenant/month → sell at $0/month (free tier, loss leader)

Growth (Schema-per-tenant):
  Dedicated schema on shared RDS: $2/tenant/month
  Dedicated namespaced pods: $5/tenant/month
  Redis namespace: $0.50/tenant/month
  Total: ~$8/tenant/month → sell at ₹2,999/month (~$36) → 4.5x margin

Enterprise (Silo):
  Dedicated RDS: $200/tenant/month
  Dedicated EKS node group: $300/tenant/month
  VPN + PrivateLink: $50/tenant/month
  Total: ~$550/tenant/month → sell at $8,333/month → 15x margin
```

### 13.2 Database Cost Optimization

```python
# Pool connections across tenants on same DB cluster
# pgBouncer transaction-mode pooling
[pgbouncer]
pool_mode = transaction        # connection returned after each transaction
default_pool_size = 20
max_client_conn = 1000
# 1000 tenant connections → 20 real DB connections!
```

**Aurora Serverless v2 for small tenants:**
- Auto-scales from 0.5 ACU to 128 ACU (1 ACU ≈ 2 GB RAM)
- Scales to near-zero when idle (cost = near $0 for inactive tenants)
- Scales up in ~5 seconds for sudden traffic

---

## 14. Anti-Patterns to Avoid

### 14.1 Hardcoded Region Assumptions

```python
# WRONG: assumes all data in one region
DATABASE_URL = "postgres://us-east-1-primary.rds.amazonaws.com/db"

# RIGHT: inject region-specific URLs from environment
DATABASE_URL = os.environ["DATABASE_URL"]  # set by deployment per region
S3_BUCKET = os.environ["TENANT_BUCKET"]   # per-region bucket
```

### 14.2 Calling Control Plane on Every Request

```python
# WRONG: every API call hits global control plane
def handle_request(request):
    tenant = control_plane.get_tenant(request.tenant_id)  # 50ms RTT cross-region!
    ...

# RIGHT: cache in regional Redis
def handle_request(request):
    tenant = tenant_cache.get(request.tenant_id)  # <1ms local
    if not tenant:
        tenant = control_plane.get_tenant(request.tenant_id)  # on miss only
        tenant_cache.set(request.tenant_id, tenant, ttl=300)
    ...
```

### 14.3 Running Schema Migrations During Traffic

```bash
# WRONG: migrate all 5000 tenant schemas during peak hours
# → Database overloaded, queries blocked, timeouts

# RIGHT: migrate in off-peak batches with rate limiting
for tenant in get_tenants_for_region():
    run_migration(tenant)
    time.sleep(0.1)   # 10 migrations/second max
    if error_rate > 0.01:
        alert_and_pause()
```

### 14.4 Synchronous Cross-Region Writes

```python
# WRONG: user action triggers write to another region
def create_order(order):
    local_db.insert(order)
    other_region_db.replicate(order)  # 150ms cross-region RTT! Fails if network blip

# RIGHT: async replication with event sourcing
def create_order(order):
    local_db.insert(order)
    event_bus.publish("order.created", order)  # async, non-blocking
    # Replication happens eventually via event consumers
```

### 14.5 Shared Cache Across Tenants Without Namespacing

```python
# WRONG: no tenant namespace → Tenant A can see Tenant B's cached data
redis.set("user:123", user_data)

# RIGHT: always prefix with tenant_id
redis.set(f"{tenant_id}:user:123", user_data)
```

---

## 15. Trade-Off Summary Table

| Dimension | Pool | Schema-per-Tenant | Silo |
|---|---|---|---|
| Isolation | Low | Medium | High |
| Cost | Lowest | Medium | Highest |
| Noisy neighbor risk | High | Medium | None |
| Data compliance | Hard | Medium | Easy |
| Migration complexity | Simple (once) | N migrations | N migrations |
| Tenant onboarding | Instant | ~30 seconds | ~5 minutes |
| Scale ceiling | 100K tenants/cluster | 1K tenants/cluster | Unlimited (per-cluster) |
| Custom schema per tenant | No | Limited | Yes |
| Suitable revenue tier | Free / $10/mo | $50–$500/mo | $1K+/mo |

| Dimension | Active-Passive | Active-Active | Regional Isolation |
|---|---|---|---|
| Write latency | Low (primary) | Low (local) | Low (regional) |
| Read latency | High for remote users | Low (local reads) | Low (local reads) |
| Consistency | Strong | Eventual / complex | Strong (regional) |
| Conflict handling | N/A | Required | N/A |
| Data residency | Hard | Very hard | Native |
| Operational complexity | Low | High | Medium |
| Failover RTO | Minutes | Seconds (automatic) | Minutes (per region) |
| Best for | Single-region SaaS | Global consumer app | Regulated B2B SaaS |
