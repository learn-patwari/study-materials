[← Previous: How the Cloud Works](03-How-the-Cloud-Works.md) · [Contents](README.md)

# Chapter 4 — The Building Blocks

> *In this chapter:* a friendly tour of the core AWS services. Think of them as **Lego bricks**
> — you'll snap a few together to build real things in Chapter 5 and 7. For each brick we
> answer: *what is it? why does it exist? what would I use it for?*

AWS has 200+ services, but you only need a handful to be dangerous. Here are the ones that
matter, grouped by what they do.

---

## First, the map: Regions and Availability Zones 🌍

Before the bricks, understand *where* they live.

- A **Region** is a geographic location, like Mumbai (`ap-south-1`) or N. Virginia
  (`us-east-1`). You pick a region close to your users (for speed) and that fits any legal
  rules about where data must live.
- Inside each region are **Availability Zones (AZs)** — separate data centers with their own
  power and network. If one AZ has a problem, the others keep running.

> 💡 **Key idea:** Running your app in **multiple AZs** is how you survive a data-center
> failure. It's the cloud's built-in answer to Chapter 1's "single location" pain. Aim for
> "multi-AZ" as your default for anything important.

---

## Compute — *where your code runs* 🖥️

| Brick | What it is | Use it for |
|-------|-----------|------------|
| **EC2** | A virtual computer (server) in the cloud you fully control | Traditional apps, full OS control, long-running work |
| **Lambda** | Runs small pieces of code on demand — no server to manage | Event-driven tasks, APIs, automation; pay per run |
| **Containers** (ECS/EKS/Fargate) | Run apps packaged in portable "containers" | Modern microservices; Fargate = no servers to manage |

> 💡 Beginner rule of thumb: **start with Lambda** (serverless) for small things and **EC2**
> when you need a full server you control. You'll use both in the labs.

---

## Storage — *where your data rests* 📦

There are three shapes of storage. Picking the right one is a classic skill:

| Brick | Think of it as | Use it for |
|-------|----------------|------------|
| **S3** (object storage) | A giant, infinite online folder for files | Images, videos, backups, website files, data — the workhorse |
| **EBS** (block storage) | A hard drive attached to one EC2 server | The disk your EC2 server boots from and stores data on |
| **EFS** (file storage) | A shared network drive many servers can mount | When several servers need the same files at once |

> 💡 **The quick decision:** storing files, backups, or a website? → **S3**. Need a disk for a
> single server? → **EBS**. Need a shared drive for many servers? → **EFS**. You'll use S3 the
> most by far.

**S3 is worth knowing well:** it's incredibly durable (your files are copied many times
automatically), cheap, and can even host a whole website. We host one for free in Chapter 7.

---

## Networking — *how everything connects* 🌐

| Brick | What it is | Use it for |
|-------|-----------|------------|
| **VPC** | Your own private network inside AWS | The "virtual data center" your resources live in |
| **Security Group** | A firewall around a resource | Deciding what traffic is allowed in/out (e.g., "allow web traffic") |
| **Load Balancer (ELB)** | Spreads incoming traffic across many servers | Handling lots of users without overloading one server |
| **CloudFront** | A global content delivery network (CDN) | Caching your content worldwide so it loads fast |
| **Route 53** | AWS's DNS (domain name) service | Pointing `yoursite.com` to your app |

> 💡 **The mental picture:** users → **Route 53** (finds your app) → **CloudFront** (fast
> delivery) → **Load Balancer** (spreads traffic) → your **servers** in a **VPC**, with
> **Security Groups** acting as gates. This layered picture is behind almost every website.

---

## Databases — *organized data, managed for you* 🗄️

| Brick | Type | Use it for |
|-------|------|------------|
| **RDS / Aurora** | Relational (SQL) | Structured data with relationships: orders, users, payments |
| **DynamoDB** | NoSQL (key-value) | Huge scale, simple lookups, super-low latency: profiles, carts |
| **ElastiCache** | In-memory cache | Making things *fast* by remembering recent results |

> 💡 **SQL vs NoSQL in one line:** use **SQL (RDS)** when you need flexible queries and
> relationships; use **NoSQL (DynamoDB)** when you know exactly how you'll look data up and you
> need massive, effortless scale.

---

## Identity & Security — *who is allowed to do what* 🔐

**IAM (Identity and Access Management)** is how you control access to everything above. It's the
lock on your data.

The beginner golden rules:
- **Least privilege** — give each person/app *only* the access it needs, nothing more.
- **Protect the root account** — the all-powerful account owner. Turn on MFA and don't use it
  daily (you'll do this in Chapter 6).
- **Use roles, not shared passwords/keys** where possible.
- **Never put passwords or keys in your code.**

> 👉 IAM is the most important security topic in AWS and the most common thing interviewers
> probe. This book keeps it simple; when you're ready to go deep, read this repo's
> [`AWS-IAM-Interview-Prep.md`](../AWS-IAM-Interview-Prep.md).

---

## The helpers you'll be glad exist 🛠️

| Brick | What it does |
|-------|--------------|
| **CloudWatch** | Monitoring: metrics, logs, dashboards, and **alarms** (we'll use a billing alarm) |
| **CloudTrail** | An audit log of every action taken in your account (who did what, when) |
| **IAM Identity Center** | The modern way to manage human sign-in across accounts |
| **AWS Budgets** | Set spending limits and get alerted — your safety net against surprise bills |

---

## Key Takeaways

- Everything lives in **Regions** (geographic) made of **Availability Zones** (separate data
  centers); use **multiple AZs** for resilience.
- The core bricks: **Compute** (EC2, Lambda, containers), **Storage** (S3, EBS, EFS),
  **Networking** (VPC, Security Groups, Load Balancer, CloudFront, Route 53), **Databases**
  (RDS, DynamoDB, ElastiCache), and **Identity** (IAM).
- Beginners lean on **S3**, **Lambda**, and **IAM** first — exactly what the labs use.
- **IAM controls who can do what** — it's the foundation of keeping your data safe.

---

**What's Next → [Chapter 5: Examples & Walkthroughs](05-Examples-and-Walkthroughs.md)** — let's
snap these bricks together into real projects.
