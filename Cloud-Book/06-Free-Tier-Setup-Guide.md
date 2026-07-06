[← Previous: Examples & Walkthroughs](05-Examples-and-Walkthroughs.md) · [Contents](README.md)

# Chapter 6 — Free Tier Setup Guide

> *In this chapter:* create your own AWS account, **secure it properly**, and put safety nets
> in place so you **never get a surprise bill**. This is the most important practical chapter —
> do it carefully once and you're set for every lab that follows.

> ⚠️ **Read this first:** A credit/debit card is required to open an AWS account (for identity
> verification), but everything in this book is designed to stay in the **Free Tier**. We'll
> set up a **budget alarm** so you're warned before spending anything. Follow the cleanup steps
> in Chapter 7 and you should pay **\$0**.

---

## What "Free Tier" actually includes

AWS Free Tier has **three kinds** of free:

| Type | What it means | Examples |
|------|---------------|----------|
| **12 months free** | Free for a year from sign-up, up to limits | 750 hrs/month of a small EC2 server; 5 GB of S3 |
| **Always free** | Free forever, up to limits | 1M Lambda requests/month; 25 GB DynamoDB storage |
| **Trials** | Free for a short period after you first use them | Some specialized services |

> 💡 **Key idea:** "Free Tier" means *free up to a limit*. Go over the limit and you pay for the
> extra. The labs here stay well under the limits, and the budget alarm is your backstop.

---

## Step 1 — Create the account

1. Go to **https://aws.amazon.com/** and click **Create an AWS Account**.
2. Enter your email, a password, and an account name (e.g., `my-learning-account`).
3. Choose **Personal** account type; fill in your details.
4. Enter payment card info (for verification — you won't be charged for Free-Tier usage).
5. Verify your phone number (SMS/call).
6. Choose the **Basic support plan** (it's free).

You now have an account. The email + password you just made is the **root user** — the
all-powerful owner. Next we lock it down.

---

## Step 2 — Secure the root user (do this immediately) 🔐

The root user can do *anything*, including closing the account and spending unlimited money. If
someone steals it, it's game over. So we protect it and then **stop using it for daily work**.

1. Sign in to the **AWS Management Console** as the root user.
2. In the top-right menu, open **Security credentials**.
3. **Enable MFA (Multi-Factor Authentication):**
   - Click **Assign MFA device**.
   - Choose an **authenticator app** (Google Authenticator, Authy, Microsoft Authenticator on
     your phone).
   - Scan the QR code, enter two consecutive codes, and finish.
4. **Do not create access keys for the root user.** (If any exist, delete them.)

> 💡 **Why this matters:** MFA means even if someone learns your password, they can't get in
> without your phone. This single step prevents the most common account takeovers.

---

## Step 3 — Create an everyday admin user (stop using root)

Best practice is to **never use the root user for daily tasks**. Instead, create a separate
identity with admin rights for your normal work. The modern, recommended way is **IAM Identity
Center**; a simpler classic way is an **IAM user**. Either is fine for learning.

**The simple path — an IAM admin user:**
1. In the console, search for and open **IAM**.
2. Go to **Users → Create user**. Name it e.g. `admin-yourname`.
3. Select **Provide user access to the console**, set a password.
4. **Permissions:** attach the **`AdministratorAccess`** policy (fine for a personal learning
   account; in real jobs you'd scope this down — see the
   [IAM deep-dive](../AWS-IAM-Interview-Prep.md)).
5. Create the user, then **sign out of root** and sign back in as this new user for everything
   from now on.
6. Turn on **MFA for this user too** (same steps as above).

> ⚠️ **Watch out:** `AdministratorAccess` is broad — great for a solo learning account, but in
> real teams you grant **least privilege** (only what's needed). This book's companion
> [`AWS-IAM-Interview-Prep.md`](../AWS-IAM-Interview-Prep.md) explains how and why.

---

## Step 4 — Set up a billing alarm (your safety net) 💰

This is the step that lets you relax. We'll tell AWS to email you if spending approaches a
tiny threshold.

**Using AWS Budgets (recommended):**
1. Sign in (as your admin user). Open the **Billing and Cost Management** console.
2. First enable **Receive Billing Alerts** under **Billing Preferences** (if shown).
3. Go to **Budgets → Create budget**.
4. Choose **Cost budget**, and set a small monthly amount — e.g., **\$1.00**.
5. Add an **alert threshold** at, say, **80%** of the budget.
6. Enter your **email** for the alert and finish.

Now if your usage ever heads toward even one dollar, AWS emails you — long before a real bill
appears.

> 💡 **Key idea:** The people who get "surprise" cloud bills are the ones who skipped this step.
> You didn't. You'll get an early warning email with time to react.

---

## Step 5 — Pick your Region

At the top-right of the console you'll see a **Region** selector (e.g., "N. Virginia").
- Pick a region **close to you** for lower latency (e.g., Mumbai `ap-south-1` if you're in
  India).
- **Be consistent** — resources you create in one region won't appear when you're viewing
  another. If something "disappears," check your region first!

---

## Step 6 — Install the AWS CLI (so you can use commands)

The **AWS CLI** lets you control AWS from your terminal — handy for the labs.

1. **Install it** (follow the official instructions for your OS):
   - macOS: `brew install awscli` (or the official installer)
   - Windows: download the AWS CLI MSI installer
   - Linux: use your package manager or the official bundle
2. **Verify the install:**
   ```
   $ aws --version
   ```
3. **Create access keys for your admin user** (IAM → your user → Security credentials →
   Create access key → choose "Command Line Interface"). Copy the **Access key ID** and
   **Secret access key**.
4. **Configure the CLI:**
   ```
   $ aws configure
   AWS Access Key ID [None]: <paste your key id>
   AWS Secret Access Key [None]: <paste your secret>
   Default region name [None]: ap-south-1
   Default output format [None]: json
   ```
5. **Confirm it works** — this asks AWS "who am I?":
   ```
   $ aws sts get-caller-identity
   ```
   You should see your account number and user ARN. 🎉

> ⚠️ **Watch out:** Your **secret access key** is like a password. Never paste it into code,
> screenshots, or public places (like a GitHub repo). If it ever leaks, deactivate it
> immediately in the IAM console.

---

## Your setup checklist ✅

- [ ] AWS account created.
- [ ] Root user has **MFA** enabled and **no access keys**.
- [ ] A separate **admin IAM user** created, with MFA, used for daily work.
- [ ] **Budget alarm** (~\$1) set with email alerts.
- [ ] Region chosen and noted.
- [ ] AWS CLI installed and `aws sts get-caller-identity` works.

If every box is checked, you're ready to build — safely.

---

## Key Takeaways

- The Free Tier is **free up to limits** (12-month, always-free, and trials).
- **Secure root first:** enable MFA, no root access keys, then **stop using root** in favor of
  an admin IAM user (also with MFA).
- A **budget alarm** is your safety net against surprise charges — always set one.
- The **AWS CLI** + `aws configure` lets you drive AWS from the terminal; verify with
  `aws sts get-caller-identity`.

---

**What's Next → [Chapter 7: Hands-On Labs](07-Hands-On-Labs.md)** — let's build and deploy real
things, for free.
