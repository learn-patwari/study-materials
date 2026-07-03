# Cloud Computing — A Proper Study Guide (Concept-First, Scenario-Driven)

> **What this is:** A ground-up learning guide to *understanding cloud computing* — the
> ideas, the vocabulary, and how real systems are built — anchored with concrete **AWS**
> examples and packed with **real-time scenarios** you can reason through.
>
> **How it pairs with the other doc:** `AWS-IAM-Interview-Prep.md` in this repo is the
> deep/advanced reference (heavy on IAM and interview scenarios). *This* guide is the
> on-ramp: read it first to build intuition, then go there for depth. Identity/security is
> kept brief here and links out to that doc.

---

## Table of Contents

1. [How to Use This Guide](#1-how-to-use-this-guide)
2. [What Is Cloud Computing](#2-what-is-cloud-computing)
3. [Service Models — IaaS / PaaS / SaaS / FaaS](#3-service-models)
4. [Deployment Models — Public / Private / Hybrid / Multi-Cloud](#4-deployment-models)
5. [The Building Blocks (AWS-Anchored)](#5-the-building-blocks)
6. [Core Cloud Principles](#6-core-cloud-principles)
7. [Real-Time Scenario Case Studies](#7-real-time-scenario-case-studies)
8. [Operational / Troubleshooting Playbook](#8-operational--troubleshooting-playbook)
9. [Cloud Best-Practices Checklist](#9-cloud-best-practices-checklist)
10. [Glossary](#10-glossary)
11. [Next Steps](#11-next-steps)

---

## 1. How to Use This Guide

Read sections 2–6 in order — they build vocabulary and intuition. Section 7 is the heart:
eight end-to-end **scenarios** where the concepts turn into real architectures and real
incidents. Sections 8–10 are quick references you'll return to.

**A learning tip:** for every service you meet, ask three questions:
1. *What problem does it solve?* (why does it exist?)
2. *What's the trade-off?* (nothing is free — cost, latency, complexity, lock-in)
3. *What breaks, and how would I know?* (the day-2 reality)

If you can answer those three for a service, you *understand* it — you don't just know its name.

---

## 2. What Is Cloud Computing

**The one-sentence definition:** Cloud computing is renting computing resources (servers,
storage, networking, databases, software) over the internet, on demand, and paying only
for what you use — instead of buying and running your own hardware.

**The analogy:** Running your own data center is like owning a car — big upfront cost,
you maintain it, it sits idle most of the day, and scaling up means buying another car.
The cloud is like ride-hailing — a car appears in minutes, you pay per trip, and if you
need twenty cars for an event you just request twenty. You trade *ownership* for
*access on demand*.

### On-premises vs Cloud

| | On-Premises | Cloud |
|---|---|---|
| **Money model** | CapEx — big upfront purchase | OpEx — pay-as-you-go |
| **Provisioning time** | Weeks/months (order, rack, cable) | Seconds/minutes (an API call) |
| **Scaling** | Buy more hardware, guess capacity ahead | Elastic — grow/shrink with demand |
| **Maintenance** | You patch, cool, power, replace disks | Provider handles the undifferentiated heavy lifting |
| **Failure** | You own redundancy end-to-end | Provider gives building blocks (AZs, regions) you compose |
| **Risk** | Over-provision (waste) or under-provision (outage) | Match capacity to real demand |

### The 5 Essential Characteristics (NIST — worth knowing by name)

1. **On-demand self-service** — you provision resources yourself, no human ticket.
2. **Broad network access** — reachable over the network from anywhere.
3. **Resource pooling** — the provider's hardware is shared (multi-tenant) and abstracted.
4. **Rapid elasticity** — scale out and back in quickly, appearing "infinite."
5. **Measured service** — metered usage; you pay for exactly what you consume.

### The Shared Responsibility Model (internalize this early)

The provider secures the cloud; **you** secure what you put *in* it. The dividing line
moves depending on the service:

> **Security "OF" the cloud** (AWS's job): physical data centers, hardware, the
> hypervisor, the global network, managed-service internals.
>
> **Security "IN" the cloud** (your job): your data, who can access it (IAM),
> encryption choices, network rules (security groups), patching your own OS/app on EC2,
> and correct configuration.

The line shifts by service model: on EC2 (IaaS) you patch the OS; on Lambda (FaaS) AWS
does — but *your code and its permissions are always yours*. **Most real-world breaches
are customer-side misconfigurations** (a public S3 bucket, a leaked key), not the
provider being hacked. That's why the IAM doc in this repo matters so much.

---

## 3. Service Models

The classic mental model is **"Pizza as a Service"** — how much you make vs how much is
provided:

| You want pizza… | Analogy | Cloud model | You manage | Provider manages |
|---|---|---|---|---|
| Make from scratch at home | Own kitchen | **On-prem** | Everything | Nothing |
| Buy dough/sauce, bake at home | Take-and-bake | **IaaS** | OS, runtime, app, data | Hardware, virtualization, network |
| Delivery to your door | Delivery | **PaaS** | App, data | + OS, runtime, scaling |
| Go to a restaurant | Dine out | **SaaS** | Nothing (just use it) | Everything |

### IaaS — Infrastructure as a Service
You rent raw building blocks: virtual machines, storage, networks. Maximum control and
flexibility; you're responsible for the OS upward.
- **AWS examples:** EC2 (VMs), EBS (disks), VPC (networking).
- **Use when:** you need OS-level control, are lifting-and-shifting existing apps, or have
  specialized software.

### PaaS — Platform as a Service
You bring code; the platform runs it, handling OS, patching, scaling, load balancing.
- **AWS examples:** Elastic Beanstalk, App Runner, RDS (managed databases).
- **Use when:** you want to ship features fast without managing servers.

### SaaS — Software as a Service
Ready-to-use software over the browser; you just log in.
- **Examples:** Gmail, Salesforce, Slack, Microsoft 365.
- **Use when:** the capability isn't your differentiator — don't build what you can buy.

### FaaS / Serverless — Functions as a Service
You deploy individual functions that run on demand; no servers to manage, scales to zero,
pay per invocation and per-millisecond of compute.
- **AWS example:** Lambda (+ API Gateway, DynamoDB, S3, EventBridge as the serverless kit).
- **Use when:** event-driven, spiky, or unpredictable workloads; glue between services.

> **Scenario — picking a model.**
> *A two-person startup wants an MVP live in three weeks.* → Lean **serverless/PaaS**
> (Lambda + API Gateway + DynamoDB, or Beanstalk): no servers to babysit, scales itself,
> near-zero idle cost, fastest to ship.
> *A bank migrating a licensed Oracle-based core system with strict OS-hardening rules.*
> → **IaaS** (EC2) for OS control, or a managed DB where allowed. The startup optimizes for
> speed; the bank optimizes for control and compliance. **Match the model to the constraint
> that dominates.**

---

## 4. Deployment Models

| Model | What it is | Best for | Trade-off |
|---|---|---|---|
| **Public cloud** | Shared provider infra (AWS/Azure/GCP) | Most workloads; speed, scale, cost | Less physical control |
| **Private cloud** | Dedicated infra (on-prem or hosted) for one org | Strict compliance, legacy, data residency | Costly, you manage more |
| **Hybrid** | Public + private working together | Keep sensitive data private, burst to public | Integration complexity |
| **Multi-cloud** | More than one public provider | Avoid lock-in, best-of-breed, resilience | Operational overhead, skills spread |

> **Scenario — hybrid at a bank.**
> A bank must keep its **core ledger** on-premises for regulatory reasons, but its
> **fraud-analytics** jobs are bursty and compute-heavy. Solution: keep the ledger private,
> and connect to AWS via **Direct Connect** (a dedicated private link). Nightly, anonymized
> transaction extracts flow to an S3 data lake where elastic analytics (EMR/Athena) run and
> scale to zero afterward. Sensitive data stays home; heavy compute rents capacity only when
> needed. That's hybrid earning its keep.

---

## 5. The Building Blocks (AWS-Anchored)

Think of building a system in the cloud as assembling a virtual data center. Here are the
Lego bricks, each with *why it exists* and a *real use*.

### 5.1 Global Infrastructure — Regions & Availability Zones
- **Region** — a geographic area (e.g., `us-east-1` N. Virginia, `ap-south-1` Mumbai).
  You choose regions for **latency** (close to users), **data residency** (laws), **cost**
  (prices vary), and **service availability**.
- **Availability Zone (AZ)** — one or more isolated data centers within a region, with
  independent power/cooling/network. Regions have 3+ AZs.
- **Edge locations** — hundreds of CDN points (CloudFront) close to users.

> **Why it matters:** deploying across **multiple AZs** is how you survive a data-center
> failure; deploying across **regions** is how you survive a regional disaster or serve a
> global audience. "Multi-AZ" is your default reliability posture. **Blast radius** =
> how much breaks when one thing fails; good architecture keeps it small.

### 5.2 Compute — "where code runs"
| Option | What | Pick when |
|---|---|---|
| **EC2** | Virtual machines | Full OS control, long-running, legacy apps, predictable load |
| **Containers** (ECS/EKS/Fargate) | Packaged apps, portable | Microservices, consistent envs, Fargate = no servers |
| **Lambda** | Functions, event-driven | Spiky/unpredictable, glue, scale-to-zero, minimal ops |

Rule of thumb: **start serverless/managed; drop to EC2 only when you need the control.**

### 5.3 Storage — "where data rests"
Three shapes of storage — knowing which to use is a classic decision:

| Type | AWS | Analogy | Use for |
|---|---|---|---|
| **Object** | **S3** | A giant key→file locker | Images, videos, backups, logs, static sites, data lakes |
| **Block** | **EBS** | A raw hard disk for one VM | Boot volumes, databases on EC2 (low-latency R/W) |
| **File** | **EFS / FSx** | A shared network drive | Many servers sharing the same files |

> **Decision tree:** *Serving files to the world or storing lots of unstructured data?* →
> **S3**. *A single server needs a fast attached disk (esp. a database)?* → **EBS**.
> *Multiple servers need to read/write the same files at once?* → **EFS**.

**S3 depth worth knowing:** 11 nines of durability; **storage classes** (Standard →
Intelligent-Tiering → Glacier) with **lifecycle rules** to cut cost automatically;
**versioning** to recover deletes; **Block Public Access** on by default (the guardrail
that prevents accidental public data). See the IAM doc for the identity-vs-bucket-policy details.

### 5.4 Networking — "how it all connects"
- **VPC (Virtual Private Cloud)** — your private, isolated network in AWS. You define IP
  ranges and carve it into **subnets**.
- **Public subnet** — has a route to the **Internet Gateway** (web servers live here).
  **Private subnet** — no direct internet route (databases live here); reaches out via a
  **NAT Gateway**.
- **Security Group** — a stateful firewall on a resource ("allow 443 from anywhere, 22 from
  the office"). Allow-rules only; return traffic is automatic.
- **NACL** — a stateless firewall at the subnet edge; supports deny rules; needs explicit
  return-traffic rules. (SG = your everyday tool; NACL = coarse subnet-wide blocking.)
- **Load Balancer (ELB)** — spreads traffic across many servers. **ALB** for HTTP(S) with
  path/host routing; **NLB** for ultra-low-latency TCP/UDP and static IPs.
- **CloudFront (CDN)** — caches content at edge locations near users; speeds delivery and
  absorbs traffic spikes/DDoS.
- **Route 53** — DNS with smart routing (latency-based, failover, weighted for canaries).

> **The mental picture:** users → **Route 53** (DNS) → **CloudFront** (cache) →
> **Load Balancer** → **web servers in public subnets** → **databases in private subnets**.
> Firewalls (security groups) gate each hop. That layered layout is the backbone of almost
> every scenario in Section 7.

### 5.5 Databases — "structured data, managed"
| Need | Service | Notes |
|---|---|---|
| Relational (SQL), transactions, joins | **RDS / Aurora** | Managed MySQL/Postgres/etc.; Aurora = cloud-native, fast, HA |
| Key-value / document, massive scale, low latency | **DynamoDB** | Serverless NoSQL; design around access patterns |
| In-memory cache | **ElastiCache** (Redis) | Speed up reads, sessions, leaderboards |
| Analytics / warehouse | **Redshift / Athena** | OLAP over big data; Athena queries S3 directly |

> **SQL vs NoSQL, simply:** SQL when you need flexible queries, joins, and strong
> consistency (orders, finance). NoSQL when you know your access patterns and need
> effortless scale and predictable low latency (user profiles, carts, IoT, sessions).

### 5.6 Identity & Security (brief — deep-dive lives elsewhere)
**IAM (Identity and Access Management)** decides *who can do what*. The golden rules:
**least privilege** (grant only what's needed), **prefer roles over long-lived keys**,
**enable MFA**, and **never hardcode credentials**. Encrypt data at rest (KMS) and in
transit (TLS). Log everything with **CloudTrail**.

> 👉 For the full treatment — policy evaluation, roles vs users, permission boundaries,
> SCPs, cross-account access, federation, and interview scenarios — see
> **`AWS-IAM-Interview-Prep.md`** in this repo. This guide deliberately stays high-level here.

### 5.7 Observability & Automation — "eyes and hands"
- **CloudWatch** — metrics, logs, alarms, dashboards. Your monitoring nerve center.
- **CloudTrail** — an audit log of every API call (who did what, when).
- **Infrastructure as Code (IaC)** — define infra in files (CloudFormation / Terraform /
  CDK) so environments are repeatable, reviewable, and versioned. *Click-ops doesn't scale.*
- **Auto Scaling** — automatically add/remove capacity based on load or a schedule.

---

## 6. Core Cloud Principles

These are the ideas interviewers and architectures keep coming back to.

### Scalability vs Elasticity
- **Scalability** = the *ability* to handle more load. **Vertical (scale up)** = a bigger
  server; simple but has a ceiling and a reboot. **Horizontal (scale out)** = more servers;
  near-limitless and resilient — the cloud-native default.
- **Elasticity** = scaling **automatically and both ways** with real-time demand (out at
  peak, back in when quiet). Scalability is the capability; elasticity is doing it
  automatically to match spend to need.

### High Availability (HA) vs Disaster Recovery (DR)
- **HA** = staying up despite *component* failures (e.g., Multi-AZ — if one AZ dies, another
  serves traffic). It's about *avoiding* downtime.
- **DR** = *recovering* after a larger disaster (region loss, data corruption). Measured by:
  - **RTO (Recovery Time Objective)** — how fast you must be back up.
  - **RPO (Recovery Point Objective)** — how much data you can afford to lose (time).
- The four DR strategies, cheapest/slowest → priciest/fastest:
  **Backup & Restore → Pilot Light → Warm Standby → Multi-Site Active/Active.**

### Statelessness & Loose Coupling
- **Stateless** app servers keep no session data locally (push it to Redis/DynamoDB), so any
  server can handle any request — essential for horizontal scaling and painless failure.
- **Loose coupling** — components communicate through queues/events (SQS, SNS, EventBridge)
  rather than calling each other directly, so one slow/failed part doesn't cascade.

### Design for Failure
"Everything fails, all the time." Assume any instance, AZ, or dependency can vanish. Build
redundancy, retries (with backoff + idempotency), health checks, and graceful degradation.

### The Well-Architected Framework — 6 Pillars (name-drop with confidence)
1. **Operational Excellence** — run and monitor systems, automate, learn from failure.
2. **Security** — protect data and systems (IAM, encryption, least privilege).
3. **Reliability** — recover from failure, scale to meet demand.
4. **Performance Efficiency** — use resources efficiently; pick the right tool.
5. **Cost Optimization** — avoid waste; pay for what you need.
6. **Sustainability** — minimize environmental impact.

---

## 7. Real-Time Scenario Case Studies

Each scenario follows the same shape: **Problem → Requirements → Architecture → Why these
choices → How it scales → What breaks → Cost/security notes.** Read them as stories.

---

### Scenario A — A Scalable E-Commerce Web Application

**Problem:** An online store gets steady traffic that spikes 10× on sale days. It must stay
fast, never lose orders, and not fall over under load.

**Architecture (request path):**
```
Users → Route 53 (DNS) → CloudFront (CDN, caches images/CSS/JS)
      → Application Load Balancer (public subnets, 2+ AZs)
      → Auto Scaling Group of EC2 web servers (private subnets, 2+ AZs)
      → ElastiCache (Redis)  ← session + hot product cache
      → RDS/Aurora (Multi-AZ)  ← orders, inventory (primary + standby)
Static assets & product images → S3  (served via CloudFront)
```

**Why these choices:**
- **CloudFront + S3** offload static content from the servers and serve it fast worldwide.
- **ALB across AZs** spreads traffic and removes single points of failure at the edge.
- **Auto Scaling Group** adds EC2 instances when CPU/requests climb, removes them when quiet
  — this is *elasticity* handling the 10× sale spike automatically.
- **Stateless web tier** (sessions in Redis) lets any instance serve any user, so scaling
  out and instance failures are painless.
- **RDS Multi-AZ** gives an automatic standby: if the primary's AZ fails, it fails over with
  no data loss.
- **ElastiCache** absorbs repeated reads (product catalog) so the database isn't hammered.

**How it scales on sale day:** CloudWatch sees CPU cross a threshold → ASG launches more
instances across AZs → ALB spreads load → Redis shields the DB from read storms. Afterward,
capacity scales back in and the bill drops.

**What breaks & how we'd know:**
- *Database becomes the bottleneck* (writes can't scale horizontally like the web tier).
  → Add **read replicas** for read-heavy pages; cache aggressively; consider sharding or
  moving carts/sessions to DynamoDB. Watch RDS CPU/connections in CloudWatch.
- *An AZ fails* → ALB stops routing to it, ASG relaunches instances elsewhere, RDS fails over.
- *Cache stampede* (cache expires under load, all requests hit the DB) → use TTL jitter and
  request coalescing.

**Cost/security notes:** Reserved Instances/Savings Plans for the baseline fleet, On-Demand
for the elastic layer; S3 lifecycle for old assets; TLS everywhere; DB in private subnets;
security group chain (ALB → web SG → DB SG); WAF on CloudFront to block bad traffic.

---

### Scenario B — A Serverless REST API

**Problem:** A startup wants a REST API for a mobile app with unpredictable traffic and a
tiny ops budget. They don't want to manage servers or pay for idle capacity.

**Architecture:**
```
Mobile app → API Gateway (auth, throttling, routing)
           → Lambda functions (one per endpoint / domain)
           → DynamoDB (user data, low-latency, serverless)
Async work (e.g., send welcome email) → SQS → Lambda worker
```

**Why these choices:**
- **API Gateway + Lambda** = zero servers, **scales to zero** (pay nothing when idle) and
  scales out automatically under load. Perfect for unpredictable traffic and a small team.
- **DynamoDB** pairs naturally with Lambda: serverless, single-digit-ms, no connection-pool
  headaches, scales with the API.
- **SQS + a worker Lambda** decouples slow side-effects (emails, image processing) from the
  request path so the API stays fast (*loose coupling*).

**How it scales:** each incoming request can trigger its own Lambda; AWS runs thousands
concurrently. No capacity planning — you set a concurrency ceiling to protect downstream
systems and control cost.

**What breaks & how we'd know:**
- *Cold starts* add latency to the first call after idle. → Use **Provisioned Concurrency**
  for latency-sensitive endpoints.
- *A downstream (a database or third-party API) can't scale as fast as Lambda* → cap Lambda
  with **reserved concurrency**, buffer with SQS.
- *Retries cause duplicate side-effects* → make handlers **idempotent** (at-least-once
  delivery is the norm). Failed async messages land in a **Dead-Letter Queue** for inspection.

**Cost/security notes:** pay-per-request is dirt cheap at low/spiky volume (can be pricier
than containers at massive steady scale — know that trade-off). Each Lambda gets a
least-privilege **execution role**; secrets in Secrets Manager, not env vars in plaintext.

---

### Scenario C — Photo/Video Upload & Delivery Pipeline

**Problem:** A social app lets users upload photos, auto-generates thumbnails, and serves
images fast globally. Uploads shouldn't bog down the app servers.

**Architecture:**
```
1. App server issues a PRESIGNED S3 URL to the client.
2. Client uploads DIRECTLY to S3 (bypasses app servers entirely).
3. S3 "object created" event → triggers a Lambda.
4. Lambda generates thumbnails / transcodes → writes back to S3.
5. CloudFront serves images from S3 to users worldwide (cached at edge).
```

**Why these choices:**
- **Presigned URLs** let clients upload straight to S3 — the app servers never touch the
  bytes, so uploads scale infinitely and cheaply.
- **S3 event → Lambda** is event-driven processing: work happens automatically on upload,
  scales with volume, costs nothing when idle.
- **CloudFront** caches images near users for fast global delivery and shields S3 from load.

**How it scales:** S3 and CloudFront are effectively limitless; Lambda scales with the
number of uploads. No servers to size.

**What breaks & how we'd know:**
- *A malicious huge upload* → presigned URL with size/content-type constraints + a max age.
- *Thumbnail Lambda fails on a weird file* → retries + DLQ; alarm on DLQ depth.
- *Users see stale images after re-upload* → use versioned object keys or CloudFront
  invalidations.

**Cost/security notes:** S3 lifecycle moves originals to cheaper tiers over time; bucket
stays private (served only via CloudFront **OAC**); Block Public Access on.

---

### Scenario D — A Data / Analytics Pipeline (Data Lake)

**Problem:** A company generates millions of clickstream events per day and wants to analyze
them without running a database cluster 24/7.

**Architecture:**
```
App/IoT events → Kinesis Data Streams (real-time ingestion)
              → Kinesis Firehose (buffers, batches, converts to Parquet)
              → S3 "data lake" (raw + curated zones)
              → Glue (catalog/ETL) → Athena (serverless SQL) / Redshift (warehouse)
              → QuickSight / dashboards
```

**Why these choices:**
- **Kinesis** ingests high-volume streaming data reliably and lets multiple consumers read it.
- **S3 as the data lake** is cheap, durable, and decouples storage from compute — you store
  everything and bring compute only when querying.
- **Athena** runs SQL directly over S3 with **zero infrastructure**, priced per data scanned
  — so you store cheaply and pay only when you actually query.
- **Parquet + partitioning** dramatically cut query cost (columnar, less data scanned).

**How it scales:** add Kinesis shards for more throughput; S3 is limitless; Athena scales
transparently. Compute cost tracks query volume, not idle time.

**What breaks & how we'd know:**
- *Query costs balloon* → you forgot to partition or store as Parquet; you're scanning raw
  JSON. Fix the file format and add date partitions.
- *Hot shard / throttling in Kinesis* → uneven partition keys; choose a higher-cardinality key.

**Cost/security notes:** lifecycle raw data to Glacier; encrypt the lake with KMS; restrict
access with bucket policies + Lake Formation permissions.

---

### Scenario E — High Availability & Disaster Recovery

**Problem:** A payments platform must tolerate an entire AWS **region** going down, with an
RTO of minutes and near-zero data loss (RPO seconds).

**Architecture (Warm Standby → Active/Active):**
```
Primary region (us-east-1): full stack serving traffic.
Secondary region (us-west-2): scaled-down but live copy.
- Aurora Global Database replicates cross-region (~1s lag) → low RPO.
- Data in S3 with Cross-Region Replication.
- Route 53 health checks + failover routing flip traffic to us-west-2 on outage.
- Infrastructure defined as code so the standby is identical and can scale up fast.
```

**Choosing a DR strategy (the trade-off table):**
| Strategy | RTO | RPO | Cost | How |
|---|---|---|---|---|
| Backup & Restore | Hours | Hours | $ | Restore from backups into a new region |
| Pilot Light | 10s of min | Minutes | $$ | Core (DB) always running, rest launched on demand |
| Warm Standby | Minutes | Seconds | $$$ | Scaled-down full stack always live |
| Active/Active | ~0 | ~0 | $$$$ | Both regions serve simultaneously |

**Why:** payments can't lose data or stay down, so we pay for Warm Standby/Active-Active.
A blog would pick Backup & Restore. **Match the strategy to the cost of downtime.**

**What breaks & how we'd know:** the classic failure is an *untested* DR plan — do regular
**game days** (fail over on purpose). Route 53 health checks detect the outage and shift DNS;
Aurora Global promotes the secondary.

---

### Scenario F — Migrating a Legacy Monolith to the Cloud (The 7 R's)

**Problem:** A company runs a monolithic app on aging on-prem servers and wants to move to
AWS with minimal risk.

**The 7 migration strategies ("7 R's"):**
| Strategy | Meaning | When |
|---|---|---|
| **Rehost** ("lift & shift") | Move as-is to EC2 | Fast exit from data center, optimize later |
| **Replatform** ("lift & tinker") | Minor tweaks (e.g., DB → RDS) | Small wins without rewriting |
| **Refactor** | Re-architect (e.g., to microservices/serverless) | Long-term agility, worth the effort |
| **Repurchase** | Move to a SaaS product | Replace with off-the-shelf |
| **Retire** | Turn it off | It's no longer needed |
| **Retain** | Leave on-prem for now | Not ready / not worth moving |
| **Relocate** | Move VMware wholesale | Bulk move without conversion |

**Phased plan:**
1. **Assess** — inventory apps & dependencies (Migration Hub, Application Discovery).
2. **Pilot** — rehost one low-risk app; validate networking (VPN/Direct Connect), IAM, monitoring.
3. **Migrate in waves** — group by dependency; rehost most, replatform the database to RDS.
4. **Optimize** — after stabilizing, refactor hot spots (extract a service to Lambda,
   right-size instances, add auto scaling).

**Pitfalls & how we'd know:**
- *"Lift & shift" then forget to optimize* → you pay cloud prices for on-prem inefficiency.
  Right-size and modernize after the move.
- *Underestimating data transfer time* → use Snowball for huge datasets; sync deltas before cutover.
- *Hidden dependencies break at cutover* → discovery phase + a tested rollback plan.

---

### Scenario G — "Our AWS Bill Tripled Last Month" (Cost Investigation)

**Problem:** Finance flags that the bill jumped from \$10k to \$32k with no obvious traffic
change. Find and fix it.

**Diagnosis method (do this in order):**
1. **Cost Explorer** — group by *service*, then by *usage type*, filter to the spike's
   start date. Which service jumped?
2. **Common culprits (in the order they usually bite):**
   - **NAT Gateway data processing** — a chatty app in private subnets pulling GBs through
     NAT; or traffic that should use a (free) S3 **gateway endpoint** going through NAT instead.
   - **Cross-AZ / inter-region data transfer** — services chatting across AZs pay per GB.
   - **Idle/forgotten resources** — a dev environment left running, unattached EBS volumes,
     old snapshots, idle load balancers, unused Elastic IPs.
   - **S3 in Standard that should be tiered** — TBs of old logs never lifecycled.
   - **Over-provisioned EC2/RDS** — huge instances at 5% utilization.
   - **A runaway Lambda/recursion or a log flood into CloudWatch.**
3. **Tag and attribute** — cost-allocation **tags** tell you *which team/app* owns the spend.

**Fixes:** add S3/DynamoDB **gateway endpoints** (free, bypass NAT); co-locate chatty
services in one AZ; delete idle resources (automate with a nightly scan/AWS Config);
**lifecycle** old S3 data to Glacier; **right-size** via Compute Optimizer; buy Savings
Plans for steady baseline; set **AWS Budgets + anomaly alerts** so next time you're warned
in hours, not at month-end.

**Lesson:** most cost surprises are **data transfer** and **forgotten resources**, not
compute price. Tagging + budgets + endpoints prevent recurrence.

---

### Scenario H — A Security Incident: Leaked Access Key / Public Bucket

**Problem:** GuardDuty alerts that an IAM access key is making API calls from an unusual
country, and a data-scanning tool flags a public S3 bucket.

**Response (Detect → Contain → Eradicate → Recover):**
1. **Detect** — GuardDuty finding (anomalous geolocation/API pattern); Access Analyzer /
   Macie flags the public bucket.
2. **Contain** — immediately **deactivate the leaked key** (or attach a deny-all policy),
   **revoke active sessions** (deny tokens issued before now via `aws:TokenIssueTime`),
   and flip **Block Public Access** on the bucket.
3. **Investigate** — **CloudTrail** shows exactly what the key did (what it read, created,
   or exfiltrated). Scope the blast radius.
4. **Eradicate & Recover** — rotate all potentially exposed credentials, remove any resources
   the attacker created, restore data if tampered.
5. **Prevent recurrence** — kill long-lived keys in favor of **roles/OIDC**; enforce MFA;
   add **SCPs** denying public-bucket settings and requiring encryption; wire GuardDuty →
   EventBridge → an auto-remediation Lambda so containment is automatic next time.

**How we'd know it worked:** CloudTrail shows the key's calls stop; the bucket returns
AccessDenied to anonymous requests; GuardDuty findings resolve.

> This scenario leans on IAM concepts (session revocation, SCPs, roles vs keys) covered in
> depth in **`AWS-IAM-Interview-Prep.md`** — a good example of *why* identity is the
> foundation of cloud security.

---

## 8. Operational / Troubleshooting Playbook

A quick-reference for day-2 symptoms. (Format: symptom → likely causes → first moves.)

| Symptom | Likely causes | First moves |
|---|---|---|
| **Website slow** | Under-provisioned tier; DB bottleneck; no caching; cold starts | Check CloudWatch CPU/latency; add cache/read replicas; scale out; provisioned concurrency |
| **5xx errors spiking** | Backend unhealthy; failed deploy; throttling; dependency down | Check ALB target health & logs; roll back; inspect DLQs; check downstream limits |
| **Database CPU pegged** | Missing index; N+1 queries; no cache; undersized | Performance Insights; add indexes/cache; read replicas; right-size |
| **"Throttling" / 429** | Hit a service limit (Lambda concurrency, DynamoDB capacity, API GW) | Raise limits/quota; add backoff+retry; buffer with SQS; on-demand capacity |
| **AccessDenied** | Missing IAM allow; explicit deny; boundary/SCP; cross-account; KMS gap | Policy Simulator + CloudTrail (shows the denying policy) — see IAM doc §2.15 Scenario H |
| **Costs suddenly up** | NAT/data transfer; idle resources; untiered S3 | Cost Explorer by service/usage type; add endpoints; delete idle; lifecycle — see Scenario G |
| **Can't reach an instance** | Security group; NACL; route table; subnet is private | Check SG inbound rules, NACL, route to IGW/NAT, and which subnet it's in |
| **Data inconsistency** | Eventual consistency; caching; replica lag | Use strongly-consistent reads where needed; check replica lag; cache invalidation |

**General method:** *reproduce → check metrics/logs (CloudWatch) → check recent changes
(CloudTrail/deploys) → form a hypothesis → test one change → verify.* Change one thing at a time.

---

## 9. Cloud Best-Practices Checklist

**Security**
- [ ] Least-privilege IAM; roles over long-lived keys; MFA on humans; no hardcoded secrets.
- [ ] Encrypt at rest (KMS) and in transit (TLS). Block Public Access on S3.
- [ ] CloudTrail on (org-wide), GuardDuty on, secrets in Secrets Manager.

**Reliability**
- [ ] Multi-AZ by default; know your RTO/RPO and have a *tested* DR plan.
- [ ] Health checks, auto scaling, retries with backoff, idempotency, DLQs.
- [ ] Stateless app tiers; loose coupling via queues/events.

**Cost**
- [ ] Tag everything for cost allocation; set Budgets + anomaly alerts.
- [ ] Right-size (Compute Optimizer); Savings Plans for baseline, Spot for stateless.
- [ ] S3 lifecycle tiering; gateway endpoints to avoid NAT charges; kill idle resources.

**Operations**
- [ ] Infrastructure as Code (repeatable, reviewed, versioned) — no click-ops in prod.
- [ ] Central monitoring/alerting (CloudWatch dashboards + alarms).
- [ ] CI/CD with safe deploys (blue/green or canary) and easy rollback.
- [ ] Run game days; document runbooks.

---

## 10. Glossary

- **Availability Zone (AZ):** an isolated data center within a region.
- **Blast radius:** how much is affected when one component fails.
- **CapEx / OpEx:** upfront capital spend vs pay-as-you-go operating spend.
- **CDN:** content delivery network; caches content near users (CloudFront).
- **Cold start:** the extra latency when a serverless function spins up from idle.
- **Elasticity:** automatically scaling capacity up and down with demand.
- **Eventual consistency:** replicas converge to the same value *after a short delay*.
- **Fault tolerance:** the system keeps working despite component failures.
- **High Availability (HA):** minimizing downtime via redundancy.
- **Horizontal scaling (scale out):** adding more machines.
- **Vertical scaling (scale up):** using a bigger machine.
- **Idempotency:** doing an operation twice has the same effect as once (safe retries).
- **IaC (Infrastructure as Code):** defining infra in version-controlled files.
- **Latency:** the time delay before a request gets a response.
- **Least privilege:** granting only the permissions actually needed.
- **Load balancer:** distributes traffic across multiple servers.
- **Managed service:** the provider runs the operational heavy lifting for you.
- **Multi-tenancy:** many customers sharing pooled underlying hardware.
- **NAT Gateway:** lets private-subnet resources reach the internet outbound.
- **Object storage:** storing files as objects with metadata (S3).
- **Presigned URL:** a temporary, permission-scoped URL to an S3 object.
- **Region:** a geographic collection of AZs.
- **RTO / RPO:** how fast you must recover / how much data loss you can tolerate.
- **Serverless:** you run code/data without managing servers; scales to zero.
- **Shared Responsibility Model:** provider secures the cloud; you secure what's in it.
- **Statelessness:** servers hold no per-user state locally.
- **Throttling:** the provider rate-limiting you when you exceed a quota.
- **Vendor lock-in:** dependence on one provider's proprietary services.
- **VPC:** your isolated virtual network in the cloud.

---

## 11. Next Steps

1. **Go deep on identity/security:** read **`AWS-IAM-Interview-Prep.md`** — IAM is the
   foundation everything else rests on, and it's the most-tested topic in interviews.
2. **Build one scenario for real:** pick Scenario A or B and stand it up in a free-tier
   account with Infrastructure as Code. Nothing cements understanding like a working system.
3. **Practice the trade-offs out loud:** for each scenario, explain *why* each service was
   chosen and *what you'd do differently* at 10× scale or 1/10th the budget.

> **The mindset to carry away:** cloud mastery isn't memorizing services — it's reasoning
> about **trade-offs** (cost vs speed vs reliability vs complexity) and **designing for
> failure**. Know *why* each brick exists and *what breaks*, and you can architect anything.
