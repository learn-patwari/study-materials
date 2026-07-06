[← Previous: Hands-On Labs](07-Hands-On-Labs.md) · [Contents](README.md)

# Chapter 8 — Glossary & Next Steps

> *In this chapter:* a plain-English glossary of every term this book used, and a clear roadmap
> for where to go now that you've got the foundations *and* hands-on experience.

---

## Plain-English Glossary

- **Availability Zone (AZ):** One of several separate data centers inside a region. Spread your
  app across AZs so one failure doesn't take you down.
- **AWS:** Amazon Web Services — the cloud provider used throughout this book.
- **Billing alarm / Budget:** A rule that emails you if spending approaches a limit you set.
  Your safety net against surprise charges.
- **Blast radius:** How much breaks when one component fails. Good design keeps it small.
- **CapEx vs OpEx:** Big upfront spending (buying hardware) vs pay-as-you-go spending (renting
  cloud). The cloud shifts you from CapEx to OpEx.
- **CDN (CloudFront):** A network that caches your content near users worldwide so it loads
  fast.
- **CLI (Command Line Interface):** Controlling AWS by typing commands in a terminal instead of
  clicking the website.
- **Cloud computing:** Renting computing (servers, storage, etc.) over the internet, on demand,
  paying only for what you use.
- **Container:** A lightweight, portable package of an app and everything it needs to run
  (managed with ECS/EKS/Fargate).
- **DynamoDB:** A serverless NoSQL database for massive scale and fast, simple lookups.
- **EC2:** A virtual server in the cloud that you fully control (Infrastructure as a Service).
- **Elasticity:** Automatically adding capacity when demand rises and removing it when demand
  falls, so you pay for what you actually use.
- **Free Tier:** AWS usage that's free up to certain limits (12-month, always-free, and
  trials).
- **IaaS / PaaS / SaaS:** Service models — renting raw infrastructure / a platform for your code
  / finished software. More managed = less for you to run.
- **IAM (Identity and Access Management):** The system that controls *who can do what* in your
  account. The foundation of cloud security.
- **Lambda:** Runs your code on demand with no servers to manage — "serverless." Pay per run.
- **Least privilege:** Granting only the access that's actually needed — a core security habit.
- **Load balancer:** Spreads incoming traffic across many servers so none is overwhelmed.
- **MFA (Multi-Factor Authentication):** A second login factor (a code from your phone) that
  protects accounts even if a password leaks.
- **Region:** A geographic area (e.g., Mumbai, N. Virginia) made up of multiple AZs.
- **Root user:** The all-powerful account owner. Secure it with MFA and don't use it for daily
  work.
- **S3:** Object storage — a durable, cheap, near-infinite place to store files. Can even host
  static websites.
- **Scale to zero:** A service that costs nothing when it isn't being used (e.g., Lambda).
- **Serverless:** You run code/data without managing servers; it scales automatically.
- **Shared Responsibility Model:** The provider secures *the cloud*; you secure what you put
  *in* it (your data and access).
- **VPC (Virtual Private Cloud):** Your own private network inside AWS where your resources
  live.

---

## Where to go next 🚀

You now have both **understanding** and **hands-on experience**. Here's a sensible path
forward, from this very repository outward.

### 1. Go deeper on concepts and real architectures
Read **[`Cloud-Computing-Study-Guide.md`](../Cloud-Computing-Study-Guide.md)** (in this repo).
It picks up where this book leaves off: deeper service coverage and **eight real-world scenario
case studies** — a scalable e-commerce site, a serverless API, a data pipeline, disaster
recovery, a cloud migration, a cost investigation, and a security incident.

### 2. Master identity and security (the most important topic)
Read **[`AWS-IAM-Interview-Prep.md`](../AWS-IAM-Interview-Prep.md)** (in this repo). Identity
(IAM) is the foundation everything else rests on and the most-tested topic in interviews. This
deep-dive covers policies, roles, permission boundaries, cross-account access, and dozens of
practical scenarios.

### 3. Keep building with your free account
- Turn Lab 2's Lambda into a real web API by adding **API Gateway**.
- Put **CloudFront** in front of your Lab 1 website for HTTPS and speed.
- Try a **DynamoDB** table and read/write items from a Lambda.
- Learn a bit of **Infrastructure as Code** (CloudFormation or Terraform) to create resources
  from files instead of clicking.

### 4. Consider a certification (optional but motivating)
- **AWS Certified Cloud Practitioner** — the perfect next milestone after this book. It
  validates exactly these foundations.
- Later: **Solutions Architect – Associate** for hands-on architecture depth.

### 5. Build the habits that matter
- Always set a **budget alarm**.
- Always **clean up** what you're not using.
- Practice **least privilege** and protect accounts with **MFA**.
- When designing, ask the three questions from the Preface: *What problem does it solve? What's
  the trade-off? What breaks, and how would I know?*

---

## A final word

You started this book at the very beginning — *why does the cloud even exist?* — felt the pains
it solves, learned how it works, met the building blocks, saw them combined into real systems,
and then **created your own account and deployed real things**. That's a complete foundation.

The cloud can look intimidating from the outside because there are so many services. But you've
seen the truth: it's a **small set of well-understood bricks**, combined into **repeatable
patterns**, guided by a few durable **habits and trade-offs**. Learn those, and you can build
almost anything.

Welcome to the cloud. Now go build something. 🚀

---

[← Back to the beginning: Contents](README.md)
