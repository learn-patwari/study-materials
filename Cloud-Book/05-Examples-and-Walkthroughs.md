[← Previous: The Building Blocks](04-The-Building-Blocks.md) · [Contents](README.md)

# Chapter 5 — Examples & Walkthroughs

> *In this chapter:* three real-world examples that snap the Chapter 4 bricks together. We
> won't type commands yet (that's Chapter 7) — here we build the *picture* in your head so the
> hands-on labs feel obvious. For each example: the problem, the design, and *why* each brick
> was chosen.

---

## Example 1 — A personal website (the "Hello, Cloud" project)

**The problem:** You want your portfolio site online, fast everywhere, always up, and
practically free.

**The design:**
```
Visitor → CloudFront (global cache) → S3 (holds your HTML/CSS/images)
Your domain name → Route 53 → CloudFront
```

**Why these bricks:**
- **S3** stores the website files. It's cheap, insanely durable, and can serve a static site
  directly — no server to run or patch.
- **CloudFront** copies your site to edge locations worldwide, so a visitor in Tokyo and one in
  London both get it fast. It also shields S3 and adds HTTPS.
- **Route 53** connects your custom domain (`yourname.com`) to CloudFront.

**What's beautiful about this:** there is **no server**. Nothing to crash, nothing to patch,
and it scales from 1 visitor to 1 million automatically. *You'll build the S3 part of this for
real in [Lab 1](07-Hands-On-Labs.md).*

---

## Example 2 — A serverless contact form (your first "backend")

**The problem:** Your website needs a "Contact us" form that saves messages — but you don't
want to run a server 24/7 just for the occasional message.

**The design:**
```
Form on your site → API Gateway (the front door) → Lambda (runs your code)
                                                  → DynamoDB (saves the message)
```

**Why these bricks:**
- **API Gateway** gives your form a web address to send data to, and handles security and
  traffic limits.
- **Lambda** runs your "save this message" code *only when the form is submitted*. If nobody
  submits anything today, you pay **nothing**.
- **DynamoDB** stores the messages — a serverless database that scales automatically and needs
  no maintenance.

**What's beautiful about this:** the whole backend **scales to zero**. It costs nothing at
rest, handles a sudden flood of submissions automatically, and there's not a single server for
you to manage. *You'll build a Lambda + API Gateway in [Lab 2](07-Hands-On-Labs.md).*

---

## Example 3 — A photo-sharing app that makes thumbnails

**The problem:** Users upload photos; you need to create small "thumbnail" versions
automatically and serve everything fast — without uploads slowing your app down.

**The design:**
```
1. User uploads a photo straight to S3 (your app hands them a secure upload link).
2. S3 sees the new file and automatically triggers a Lambda.
3. Lambda shrinks the image into a thumbnail and saves it back to S3.
4. CloudFront serves the images to everyone, fast.
```

**Why these bricks:**
- Uploading **directly to S3** means your app servers never handle the heavy image files —
  uploads can't overwhelm them.
- **S3 triggering Lambda** is "event-driven" magic: the work happens automatically the instant
  a photo lands, and scales with the number of uploads.
- **CloudFront** delivers images quickly worldwide.

**What's beautiful about this:** it's fully automatic and elastic. One upload or a million
uploads, the same design works, and you pay in proportion to real usage.

---

## Notice the pattern

Across all three examples, the same ideas keep returning — these are the habits of good cloud
design:

| Habit | What it means | Seen in |
|-------|---------------|---------|
| **Prefer managed/serverless** | Let AWS run the servers; you run your app | All three |
| **Scale to zero** | Pay nothing when idle | Examples 2 & 3 |
| **Event-driven** | Work happens automatically in response to events | Example 3 |
| **Elastic by default** | 1 user or 1 million — same design | All three |
| **No single point of failure** | Spread across AWS's resilient infrastructure | All three |

> 💡 **Key idea:** You rarely "invent" cloud architectures from scratch. You **combine a few
> well-understood bricks** into patterns like these. Learn the patterns, and you can design
> most things.

---

## Want the advanced versions of these?

This book keeps examples approachable. For **deeper, production-grade scenarios** — a scalable
e-commerce site, a data analytics pipeline, disaster recovery across regions, a cost
investigation, and a security incident response — see this repo's
[`Cloud-Computing-Study-Guide.md`](../Cloud-Computing-Study-Guide.md), Section 7.

---

## Key Takeaways

- Real cloud apps are **a few bricks combined into patterns**, not exotic inventions.
- **Static site** = S3 + CloudFront + Route 53 (no server at all).
- **Serverless backend** = API Gateway + Lambda + DynamoDB (scales to zero).
- **Event-driven processing** = upload to S3 → triggers Lambda → does work automatically.
- The recurring habits: **managed/serverless, scale-to-zero, event-driven, elastic, resilient.**

---

**What's Next → [Chapter 6: Free Tier Setup Guide](06-Free-Tier-Setup-Guide.md)** — time to
create your own AWS account safely and get ready to build.
