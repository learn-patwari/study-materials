[← Previous: Free Tier Setup Guide](06-Free-Tier-Setup-Guide.md) · [Contents](README.md)

# Chapter 7 — Hands-On Labs

> *In this chapter:* four small, free projects that turn everything you've read into muscle
> memory. Each lab follows the same rhythm: **Goal → Steps → Verify → 🧹 Clean up.** Do the
> cleanup every time so nothing keeps costing money.

> ⚠️ **Before you start:** finish [Chapter 6](06-Free-Tier-Setup-Guide.md) — you need your
> account secured, a budget alarm set, and the AWS CLI working (`aws sts get-caller-identity`
> should succeed).

Throughout, replace anything in `<angle brackets>` with your own value. Bucket names must be
**globally unique**, so add something random (like your initials + numbers).

---

## Lab 1 — Host a website on S3 🌐

**Goal:** Put a real web page online using only S3. No servers.

**Steps (using the CLI):**

1. Make a folder and a simple page:
   ```
   $ mkdir my-first-site && cd my-first-site
   $ echo '<h1>Hello, Cloud! 👋</h1><p>My first site on AWS.</p>' > index.html
   ```
2. Create a uniquely-named bucket (pick your own name):
   ```
   $ aws s3 mb s3://<your-initials>-hello-cloud-2026
   ```
3. Upload your page:
   ```
   $ aws s3 cp index.html s3://<your-initials>-hello-cloud-2026/
   ```
4. Turn on static website hosting:
   ```
   $ aws s3 website s3://<your-initials>-hello-cloud-2026/ --index-document index.html
   ```
5. For a personal test site, allow public reads. In the **S3 console**, open your bucket →
   **Permissions** → turn **off** "Block all public access" (confirm the warning), then add
   this **bucket policy** (replace the bucket name):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Sid": "PublicRead",
       "Effect": "Allow",
       "Principal": "*",
       "Action": "s3:GetObject",
       "Resource": "arn:aws:s3:::<your-initials>-hello-cloud-2026/*"
     }]
   }
   ```

**Verify:** In the S3 console, open **Properties → Static website hosting** and click the
**endpoint URL**. Your page loads in the browser. You just hosted a website with no server! 🎉

> 💡 **What you learned:** S3 isn't just file storage — it can serve a whole static site,
> infinitely scalable, for pennies. (In production you'd put **CloudFront** in front for HTTPS
> and speed, and keep the bucket private — see [Chapter 5](05-Examples-and-Walkthroughs.md).)

**🧹 Clean up:**
```
$ aws s3 rm s3://<your-initials>-hello-cloud-2026/ --recursive
$ aws s3 rb s3://<your-initials>-hello-cloud-2026
```

---

## Lab 2 — Your first serverless function (Lambda) ⚡

**Goal:** Run code in the cloud with no server, and see it respond.

**Steps (console — easiest for a first time):**

1. In the console, open **Lambda → Create function**.
2. Choose **Author from scratch**. Name it `hello-function`. Runtime: **Python** (or Node.js).
3. Click **Create function**.
4. In the code editor, replace the handler with:
   ```python
   def lambda_handler(event, context):
       name = event.get("name", "Cloud Learner")
       return {"message": f"Hello, {name}! This ran with no server. 🚀"}
   ```
5. Click **Deploy**.

**Verify:** Click **Test**, create a test event with `{ "name": "Ada" }`, and run it. You'll see
your greeting in the result. Your code ran on AWS-managed infrastructure that appeared on
demand and will vanish when idle — **you pay only for the milliseconds it ran.**

> 💡 **What you learned:** This is **serverless (FaaS)**. The first **1 million requests per
> month are always free.** Add **API Gateway** as a trigger to turn this into a real web API
> (the "contact form" pattern from [Chapter 5](05-Examples-and-Walkthroughs.md)).

**🧹 Clean up:** In the Lambda console, select `hello-function` → **Actions → Delete**.

---

## Lab 3 — Prove your safety net works (Budget alarm) 💰

**Goal:** Confirm the money guardrail from Chapter 6 is active — the most important habit in
the cloud.

**Steps:**
1. Open **Billing and Cost Management → Budgets**.
2. Confirm your **~\$1 cost budget** from Chapter 6 exists and shows your email under alerts.
3. If you skipped it earlier: **Create budget → Cost budget → \$1/month → alert at 80% → your
   email.**
4. Explore **Cost Explorer** to see your (near-zero) spending broken down by service.

**Verify:** Your budget is listed and "active." You'll now get an email if usage ever
approaches your limit.

> 💡 **What you learned:** Cost control isn't an afterthought in the cloud — it's a first-class
> habit. Every professional sets budgets and alarms. Now so do you.

**🧹 Clean up:** Nothing to remove — a budget is free. Keep it running forever.

---

## Lab 4 — Store and read data with the CLI 📦

**Goal:** Practice the everyday loop of putting data in the cloud and getting it back.

**Steps:**
1. Create a bucket:
   ```
   $ aws s3 mb s3://<your-initials>-data-lab-2026
   ```
2. Create and upload a file:
   ```
   $ echo "cloud learning notes" > notes.txt
   $ aws s3 cp notes.txt s3://<your-initials>-data-lab-2026/
   ```
3. List what's in the bucket:
   ```
   $ aws s3 ls s3://<your-initials>-data-lab-2026/
   ```
4. Download it back under a new name:
   ```
   $ aws s3 cp s3://<your-initials>-data-lab-2026/notes.txt downloaded.txt
   ```

**Verify:** `downloaded.txt` exists on your computer with the same contents. You've completed a
full round-trip to cloud storage from the command line.

**🧹 Clean up:**
```
$ aws s3 rm s3://<your-initials>-data-lab-2026/ --recursive
$ aws s3 rb s3://<your-initials>-data-lab-2026
```

---

## Final cleanup check ✅

Run this to confirm you have no leftover buckets that could (eventually) cost money:
```
$ aws s3 ls
```
If the list is empty (or only shows things you intend to keep), you're clean. Also glance at
**Cost Explorer** occasionally — it should stay at or near \$0.

> 💡 **The golden habit:** *build → verify → clean up.* Do the cleanup every single time and the
> cloud stays free for learning.

---

## Key Takeaways

- You **hosted a website (S3)**, **ran serverless code (Lambda)**, **confirmed a budget alarm**,
  and **moved data with the CLI** — the core everyday cloud skills.
- Free-Tier limits are generous (e.g., **1M free Lambda requests/month**); these labs stay well
  inside them.
- **Always clean up** and keep a **budget alarm** — that's how learners keep their bill at \$0.

---

**What's Next → [Chapter 8: Glossary & Next Steps](08-Glossary-and-Next-Steps.md)** — a plain
-English glossary and your roadmap for going deeper.
