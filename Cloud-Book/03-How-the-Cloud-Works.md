[← Previous: Introduction to the Cloud](02-Introduction-to-the-Cloud.md) · [Contents](README.md)

# Chapter 3 — How the Cloud Works

> *In this chapter:* the two ways people categorize cloud. **Service models** (how much of the
> work the provider does for you) and **deployment models** (where the cloud lives and who
> shares it). Two simple analogies make both stick.

---

## Part 1 — Service Models: how much does the provider do?

Not all cloud is the same. The big question is: **how much of the stack do you manage, and how
much does the provider manage?** The more they handle, the less you worry about — but the less
control you have.

### The "Pizza as a Service" analogy 🍕

Imagine you want to eat pizza. There are four ways to make it happen, each handing off more
work to someone else:

| Way to get pizza | Cloud equivalent | You handle | Provider handles |
|------------------|------------------|------------|------------------|
| Make it from scratch at home | **On-premises** (not cloud) | *Everything* | Nothing |
| Buy take-and-bake, bake at home | **IaaS** | The "cooking" (OS, app, data) | Kitchen (hardware, network) |
| Get it delivered | **PaaS** | Just eating (your app + data) | Cooking + delivery (OS, scaling) |
| Eat at a restaurant | **SaaS** | Nothing — just show up | Everything |

Now the real definitions:

### IaaS — Infrastructure as a Service
You rent the **raw building blocks**: virtual machines, storage, networking. You install and
manage the operating system and everything above it. **Most control, most responsibility.**
- **AWS example:** EC2 (virtual servers).
- **Use when:** you need full control, or you're moving an existing app as-is.

### PaaS — Platform as a Service
You bring your **code**; the platform runs it and handles the servers, patching, and scaling
for you. **Less control, much less to manage.**
- **AWS example:** Elastic Beanstalk, App Runner.
- **Use when:** you want to ship an app fast without babysitting servers.

### SaaS — Software as a Service
Finished software you just **log in and use**. You manage nothing but your own data and settings.
- **Examples:** Gmail, Slack, Salesforce, Netflix.
- **Use when:** the capability isn't something you need to build yourself.

### FaaS / Serverless — the modern favorite
You upload small **functions** (bits of code) that run only when triggered. No servers to
manage at all, it **scales automatically**, and it can **scale to zero** — costing nothing when
idle.
- **AWS example:** Lambda.
- **Use when:** event-driven or spiky work, or you want the least possible operations.

> 💡 **Key idea:** As you go **IaaS → PaaS → SaaS**, you trade **control** for **convenience**.
> A good architect picks the *most managed* option that still meets their needs — why run a
> server if you don't have to?

---

## Part 2 — Deployment Models: where does the cloud live?

The second question is **where** the computing happens and **who shares** the hardware.

| Model | What it is | Good for | The trade-off |
|-------|-----------|----------|---------------|
| **Public cloud** | Shared infrastructure run by AWS/Azure/Google | Most apps — speed, scale, low cost | You don't own the hardware |
| **Private cloud** | Infrastructure dedicated to just your organization | Strict rules, sensitive data | More expensive, you manage more |
| **Hybrid cloud** | Public + private working together | Keep secrets private, burst to public for scale | More complex to connect |
| **Multi-cloud** | Using more than one public provider | Avoiding lock-in, best tool per job | More skills and tools to juggle |

### A quick analogy for deployment models 🏠

- **Public cloud** = living in a well-run **apartment building**. Shared, efficient, someone
  else handles maintenance, you pay only for your unit.
- **Private cloud** = owning a **private house** with your own security fence. Full control and
  privacy, but you pay for and maintain everything.
- **Hybrid** = keeping your valuables in the private house but renting a **storage unit** for
  bulky, occasional stuff.
- **Multi-cloud** = deliberately not putting all your eggs in one landlord's basket.

> 💡 For most people and most projects, **public cloud is the default answer** — it's the
> cheapest, fastest, and most scalable place to start. This book uses AWS's public cloud
> throughout.

---

## Putting the two together

Any real setup is a **combination**: e.g., "we run a **serverless (FaaS)** app on the **public
cloud**," or "a bank runs a sensitive database on a **private cloud** and bursts analytics to
the **public cloud** — a **hybrid** setup using **IaaS and PaaS**." The two dimensions —
*how much the provider does* and *where it runs* — describe almost any architecture.

---

## Key Takeaways

- **Service models** answer *"how much does the provider do?"*: **IaaS** (raw building blocks)
  → **PaaS** (bring code) → **SaaS** (just use it), plus **Serverless/FaaS** (run functions,
  no servers). More managed = more convenient, less control.
- **Deployment models** answer *"where does it live and who shares it?"*: **public** (shared,
  the default), **private** (dedicated), **hybrid** (both), **multi-cloud** (several providers).
- Real systems mix and match. Beginners should default to **public cloud** and the **most
  managed** service that fits.

---

**What's Next → [Chapter 4: The Building Blocks](04-The-Building-Blocks.md)** — the actual AWS
services you'll use, each explained in a sentence or two.
