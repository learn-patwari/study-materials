# AWS Cloud Interview Preparation — Deep Dive on IAM (8+ Years Experience)

> **Purpose:** A single, deep reference to prepare for senior/staff-level AWS interviews.
> Deepest focus on **IAM** (the part interviewers probe hardest for security-conscious senior roles),
> with genuinely deep coverage of the other AWS services you're expected to know — mechanics,
> security models, trade-offs, and interview scenarios for each.
> Every section ends with **interview questions + practical scenarios and model answers**.

---

## Table of Contents

1. [How to Use This Document](#1-how-to-use-this-document)
2. [IAM — The Deep Dive](#2-iam--the-deep-dive)
   - 2.1 [The Mental Model](#21-the-mental-model)
   - 2.2 [Identities: Users, Groups, Roles](#22-identities-users-groups-roles)
   - 2.3 [Policies — Every Type Explained](#23-policies--every-type-explained)
   - 2.4 [Policy Evaluation Logic (the crown jewel)](#24-policy-evaluation-logic-the-crown-jewel)
   - 2.5 [IAM Roles, Trust Policies & AssumeRole](#25-iam-roles-trust-policies--assumerole)
   - 2.6 [Permission Boundaries](#26-permission-boundaries)
   - 2.7 [Service Control Policies (SCPs) & Organizations](#27-service-control-policies-scps--organizations)
   - 2.8 [Resource-Based Policies & Cross-Account Access](#28-resource-based-policies--cross-account-access)
   - 2.9 [IAM Conditions, Variables & Context Keys](#29-iam-conditions-variables--context-keys)
   - 2.10 [STS Deep Dive](#210-sts-deep-dive)
   - 2.11 [Federation, SSO & OIDC (incl. IRSA & GitHub Actions)](#211-federation-sso--oidc)
   - 2.12 [Instance Profiles & the Metadata Service (IMDSv2)](#212-instance-profiles--imds)
   - 2.13 [Access Analyzer, Credential Reports & Least Privilege](#213-access-analyzer-credential-reports--least-privilege)
   - 2.14 [Common IAM Anti-Patterns & Security Pitfalls](#214-common-iam-anti-patterns--security-pitfalls)
   - 2.15 [IAM Interview Questions & Scenarios](#215-iam-interview-questions--scenarios)
3. [Core AWS Services — Deep Coverage](#3-core-aws-services--deep-coverage)
4. [System Design & Cross-Cutting Concerns](#4-system-design--cross-cutting-concerns)
5. [Rapid-Fire Interview Q&A Bank](#5-rapid-fire-interview-qa-bank)
6. [Final Prep Checklist](#6-final-prep-checklist)

---

## 1. How to Use This Document

At 8 years, interviewers assume you can *use* AWS. They test whether you can **reason about
security boundaries, failure modes, and trade-offs**. IAM is where senior candidates separate
themselves — most people can attach `AdministratorAccess`; few can explain policy evaluation
precedence, permission boundaries vs SCPs, or design secure cross-account access.

**Study strategy:**
- Master Section 2.4 (evaluation logic) cold — it's the single most-asked deep IAM topic.
- Be able to *draw* the difference between identity policy, resource policy, permission boundary, and SCP.
- For every service in Section 3, know: what problem it solves, its security model, its limits, its main trade-off, and one failure story. Each subsection ends with scenario Q&A — rehearse them aloud.
- Practice speaking the scenarios out loud. Interviews reward crisp verbal reasoning.

---

## 2. IAM — The Deep Dive

### 2.1 The Mental Model

IAM answers one question on **every** AWS API call:

> *"Is **this principal** allowed to perform **this action** on **this resource** under **these conditions**?"*

The four nouns map to the four parts of a policy statement:

| Question | Policy element |
|----------|----------------|
| Who? | **Principal** (in resource/trust policies) |
| What action? | **Action** |
| On what? | **Resource** |
| Under what circumstances? | **Condition** |
| Allowed or blocked? | **Effect** (`Allow` / `Deny`) |

**Key truths to internalize:**
- IAM is **global** (not regional). Users, roles, policies exist account-wide.
- IAM is **default-deny**. No explicit `Allow` = implicit deny.
- An **explicit `Deny` always wins** over any `Allow`.
- IAM evaluates the **union of all applicable policies**, then applies deny/boundary/SCP gates.
- Authentication (proving identity) is separate from Authorization (what you can do). IAM does both, but interviewers care most about authorization.

---

### 2.2 Identities: Users, Groups, Roles

**IAM User** — a long-lived identity with permanent credentials (password for console, access key ID + secret for API/CLI). *Senior take:* users are a liability. Every long-lived key is a leak waiting to happen. Prefer roles + federation. Reserve users for break-glass or legacy integrations that genuinely can't federate.

**IAM Group** — a collection of users for attaching policies. Groups **cannot** be a principal (you can't "assume a group"), can't be nested, and roles can't be group members. Purely an admin convenience.

**IAM Role** — an identity with **no long-lived credentials**. It has:
- a **trust policy** (a resource-based policy defining *who can assume it*), and
- one or more **permission policies** (what the role can do once assumed).

When assumed, STS issues **temporary credentials** (access key + secret + session token) that expire (15 min – 12 hr). Roles are the backbone of secure AWS: EC2 instance profiles, Lambda execution roles, cross-account access, federation, service-linked roles — all roles.

**Service-linked role** — a special role predefined by an AWS service (e.g., `AWSServiceRoleForECS`), with a trust policy locked to that service, that the service uses to call other services on your behalf. You can't arbitrarily edit its trust; the service manages its lifecycle.

**Root user** — the account owner. Can do *everything*, including things IAM users can't (close account, change support plan, some billing). Best practice: enable MFA, lock away credentials, never use for daily work, don't create access keys for it.

---

### 2.3 Policies — Every Type Explained

This is the taxonomy senior candidates must recite fluently:

| Policy type | Attached to | Purpose | Grants or limits? |
|-------------|-------------|---------|-------------------|
| **Identity-based policy** | User, group, role | What the identity can do | Grants (Allow/Deny) |
| **Resource-based policy** | A resource (S3 bucket, SQS, SNS, KMS key, Lambda, etc.) | Who can access this resource | Grants (incl. cross-account) |
| **Permission boundary** | User or role | Max permissions the identity *can* have | Limits (a ceiling) |
| **Service Control Policy (SCP)** | OU or account (via Organizations) | Max permissions for the whole account | Limits (a guardrail) |
| **Session policy** | Passed at AssumeRole time | Further scope down a session | Limits |
| **Access Control List (ACL)** | S3 (legacy), some resources | Coarse cross-account grants | Grants (legacy — avoid) |
| **Resource Control Policy (RCP)** | OU/account (Organizations) | Org-wide limit on *resource*-based access | Limits |

**Managed vs inline policies (identity-based):**
- **AWS-managed** — maintained by AWS (e.g., `AmazonS3ReadOnlyAccess`). Convenient, but often too broad.
- **Customer-managed** — you create/version them, reusable across identities. *Preferred* for real workloads.
- **Inline** — embedded directly in a single user/role, 1:1 lifecycle. Use for strict, non-reusable coupling; harder to audit at scale.

**Policy structure (JSON):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowReadOnPrefix",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::my-bucket/team-a/*",
      "Condition": {
        "StringEquals": { "aws:PrincipalTag/team": "team-a" }
      }
    }
  ]
}
```
> `Version` must be `2012-10-17` (the policy language version, **not** a date you pick). `Sid` is an optional label. `NotAction`/`NotResource`/`NotPrincipal` exist but are dangerous — they match everything *except* what's listed and cause accidental over-grants.

---

### 2.4 Policy Evaluation Logic (the crown jewel)

**Memorize this.** When a principal makes a request, IAM evaluates in this effective order and denies unless the request survives every gate:

1. **Explicit Deny** — if *any* applicable policy (identity, resource, boundary, SCP, session) says `Deny`, the request is **denied. Full stop.** Deny always wins.
2. **SCP** (if in an Organization) — the action must be allowed by SCPs on every OU/account in the path. SCPs never *grant*; they only permit or restrict. If SCP doesn't allow it → deny.
3. **Resource-based policy** — an `Allow` here can independently grant access (important for cross-account; see below).
4. **Identity-based policy** — an `Allow` here grants access.
5. **Permission boundary** — the action must be within the boundary. Boundary + identity policy must **both** allow (intersection) for the action to pass (boundary doesn't grant, only caps).
6. **Session policy** — if present, the action must also be allowed by it (further intersection).
7. If nothing explicitly allowed it → **implicit deny**.

**The senior-level nuance — same account vs cross-account:**

- **Same account:** For most services, a request is allowed if **either** the identity policy **or** the resource policy allows it (and no deny/boundary/SCP blocks). They combine as a union. (S3 is the classic example.)
- **Cross-account:** access requires an `Allow` in **both** the identity policy in Account A **and** the resource policy in Account B. Both sides must agree. One side alone is insufficient.

**A precise way to say it in an interview:**
> "Start from implicit deny. An explicit Deny anywhere is final. Otherwise, the request must be permitted by SCPs (in Orgs), fall within the permission boundary and any session policy, and be Allowed by an identity-based or resource-based policy. Same-account, identity-or-resource is enough; cross-account you need both."

**Diagram (verbal):** picture a series of gates. Deny short-circuits to REJECT. Then each restrictive gate (SCP → boundary → session) can only *reject*, never grant. The grant comes from identity/resource policies. The request only passes if it clears every restrictive gate AND at least one grant applies.

---

### 2.5 IAM Roles, Trust Policies & AssumeRole

A role has **two** policy surfaces — don't conflate them:

- **Trust policy** (`AssumeRolePolicyDocument`): *WHO* may assume the role. It's a resource-based policy where the `Principal` is the trusted entity (an account, IAM user/role, an AWS service, or a federated identity provider).
- **Permission policy**: *WHAT* the role can do after assumption.

Example trust policy allowing a specific account's principals to assume, with an external ID:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::111122223333:root" },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": { "sts:ExternalId": "unique-shared-secret-xyz" }
    }
  }]
}
```

**How assumption works:**
1. Principal calls `sts:AssumeRole` (or `AssumeRoleWithSAML` / `AssumeRoleWithWebIdentity`).
2. STS checks the trust policy allows this principal.
3. STS checks the caller's identity policy allows `sts:AssumeRole` on that role ARN (the calling side must also be permitted).
4. STS returns temporary credentials scoped to the role's permissions (optionally narrowed by a session policy).

**Role chaining:** assuming role B from role A. Note: chained role sessions are capped at **1 hour max** regardless of the role's `MaxSessionDuration`. Also, chaining can complicate CloudTrail attribution — use `sts:SourceIdentity` to preserve who the original human was.

**`Principal: {"AWS": "...:root"}`** means "any principal in that account that is *also* granted `sts:AssumeRole` by its own identity policy" — it delegates the fine-grained decision to the trusted account. It does **not** mean the root user only.

---

### 2.6 Permission Boundaries

A permission boundary is a **managed policy attached to a user or role that sets the maximum permissions** that identity can ever have. It does **not** grant anything — the *effective permissions are the intersection* of the identity's policies and the boundary.

**Why they exist (the killer use case): delegated administration.** You let developers create roles (e.g., for their Lambdas) without letting them escalate privileges. You give a developer permission to create roles *only if* they attach a boundary. The boundary caps whatever the created role can do — so even if a dev attaches `AdministratorAccess`, the boundary limits it to, say, S3 + DynamoDB in dev.

**Boundary vs SCP — the classic comparison:**

| | Permission Boundary | SCP |
|---|---|---|
| Scope | A single IAM user/role | Entire account / OU |
| Set by | Account admin | Org (management account) |
| Affects root user? | No | **Yes** (SCPs affect everyone except the management account) |
| Grants? | No, caps only | No, caps only |
| Typical use | Safe delegation of role creation | Org-wide guardrails |

**Effective permission = Identity policy ∩ Boundary ∩ SCP** (minus any explicit deny).

---

### 2.7 Service Control Policies (SCPs) & Organizations

**AWS Organizations** groups accounts into a tree of **Organizational Units (OUs)** under a **management (payer) account**, enabling consolidated billing and org-wide policies.

**SCPs** are guardrails applied to OUs/accounts. Critical properties:
- SCPs **never grant** permissions — they define the *maximum available* permissions. You still need identity policies to actually allow actions.
- SCPs apply to **all principals in member accounts, including the root user** of those accounts.
- SCPs do **not** apply to the **management account** (a key gotcha — never rely on SCPs to constrain the management account; keep workloads out of it).
- SCPs don't affect **service-linked roles**.
- Evaluation: an action must be permitted by the SCP at *every* level of the OU path (root → OU → account).

**Two SCP strategies:**
- **Allow-list** (deny by default): FullAWSAccess is removed; you explicitly allow services. Tight but high-maintenance.
- **Deny-list** (allow by default): start with `FullAWSAccess`, then attach deny SCPs for guardrails (e.g., "deny leaving the org," "deny disabling CloudTrail," "deny actions outside approved regions"). Most common in practice.

Example region-restriction SCP (deny-list style):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyOutsideApprovedRegions",
    "Effect": "Deny",
    "NotAction": ["iam:*", "sts:*", "cloudfront:*", "route53:*", "support:*"],
    "Resource": "*",
    "Condition": {
      "StringNotEquals": { "aws:RequestedRegion": ["us-east-1", "eu-west-1"] }
    }
  }]
}
```
> Global services (IAM, CloudFront, Route 53, etc.) are excluded via `NotAction` because they're pinned to `us-east-1` and would otherwise break.

**RCPs (Resource Control Policies)** are the newer sibling: org-wide *maximum* on resource-based access (e.g., enforce "no S3 bucket in the org may be accessed by a principal outside our org"). Boundary caps identity actions; RCP caps who can touch resources org-wide.

---

### 2.8 Resource-Based Policies & Cross-Account Access

A **resource-based policy** lives *on the resource* and names a `Principal`. Services that support them include S3, SQS, SNS, Lambda, KMS, Secrets Manager, ECR, API Gateway, EventBridge, and more. IAM roles' trust policies are also resource-based policies.

**Why they matter:**
- They enable **cross-account access without role assumption** (e.g., Account B's bucket policy directly allows a role in Account A to `GetObject`).
- Same-account, they *add* to identity permissions (union).
- Cross-account, both the identity policy (A) and resource policy (B) must allow — see §2.4.

**Two ways to do cross-account access — know the trade-off:**
1. **Assume a role** in the target account (`sts:AssumeRole`): the caller *becomes* a principal in Account B. Good when the caller needs many permissions/actions in B; centralizes B's control in one role. CloudTrail shows the assumed-role identity.
2. **Resource-based policy** granting the foreign principal directly: no role switch, the caller keeps its own identity. Good for a single resource/action (e.g., one bucket, one queue). Simpler for narrow grants.

**The Confused Deputy problem & `ExternalId`:** When a third-party (SaaS) service assumes a role in your account on your behalf, an attacker who knows your role ARN could trick the SaaS into accessing your account. The **`ExternalId`** condition (a shared secret you and the vendor agree on) prevents this — the SaaS must present the correct ExternalId, which the attacker doesn't know. For your *own* services, prefer `aws:SourceArn` / `aws:SourceAccount` conditions instead.

---

### 2.9 IAM Conditions, Variables & Context Keys

Conditions are where fine-grained, senior-level control lives. A condition = **operator + key + value**.

**Common global condition keys (`aws:` prefix, available on most requests):**
- `aws:PrincipalArn`, `aws:PrincipalAccount`, `aws:PrincipalOrgID`, `aws:PrincipalTag/<k>`
- `aws:SourceIp`, `aws:VpcSourceIp`, `aws:SourceVpc`, `aws:SourceVpce` (VPC endpoint)
- `aws:RequestedRegion`
- `aws:SecureTransport` (was it HTTPS?)
- `aws:MultiFactorAuthPresent`, `aws:MultiFactorAuthAge`
- `aws:CurrentTime`, `aws:EpochTime`
- `aws:ResourceTag/<k>`, `aws:RequestTag/<k>`, `aws:TagKeys`
- `aws:SourceArn`, `aws:SourceAccount` (confused-deputy protection)
- `aws:userid`, `aws:username`

**Service-specific keys** use the service prefix, e.g. `s3:prefix`, `s3:x-amz-server-side-encryption`, `ec2:InstanceType`, `dynamodb:LeadingKeys`, `kms:ViaService`, `sts:ExternalId`.

**Operators:** `StringEquals`, `StringLike` (wildcards), `StringNotEquals`, `NumericLessThan`, `DateGreaterThan`, `Bool`, `IpAddress`, `ArnLike`, `Null` (key present?), plus `...IfExists` variants and set operators `ForAllValues`/`ForAnyValue` for multi-valued keys.

**IAM policy variables** substitute request context at eval time — powering scalable, self-service patterns:
```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:PutObject"],
  "Resource": "arn:aws:s3:::company-data/${aws:PrincipalTag/team}/*"
}
```
This one statement gives every principal access to *only their own team's prefix* — no per-team policy needed. Another classic: `arn:aws:s3:::app-home/${aws:userid}/*` for per-user home folders.

**ABAC (Attribute-Based Access Control):** grant based on matching **tags** on the principal and the resource, e.g. `"aws:ResourceTag/project": "${aws:PrincipalTag/project}"`. ABAC scales to thousands of resources/teams without policy sprawl (the RBAC alternative needs a new policy per role). Interviewers love "ABAC vs RBAC — when would you use each?" (Answer: RBAC for a small, stable set of well-defined roles; ABAC when you have many teams/projects and want policies to scale automatically as you add tagged resources.)

**`...IfExists` and `Null` gotcha:** `aws:MultiFactorAuthPresent` is **not present** for some credential types (e.g., long-term access keys, service roles), so a naïve `Bool: {"aws:MultiFactorAuthPresent": "true"}` can behave unexpectedly. Use `BoolIfExists` when you mean "if MFA context exists, it must be true."

---

### 2.10 STS Deep Dive

**AWS STS (Security Token Service)** issues short-lived credentials. Core APIs:

| API | Use case |
|-----|----------|
| `AssumeRole` | IAM principal assumes a role (same/cross account) |
| `AssumeRoleWithSAML` | Enterprise SSO via SAML 2.0 IdP (ADFS, Okta) |
| `AssumeRoleWithWebIdentity` | OIDC federation (Cognito, Google, IRSA, GitHub Actions) |
| `GetSessionToken` | Temp creds for an IAM user (often to satisfy MFA) |
| `GetFederationToken` | Temp creds for a federated user (proxy pattern) |
| `GetCallerIdentity` | "Who am I?" — no permissions needed; great for debugging |

**Temporary credentials** = `AccessKeyId` + `SecretAccessKey` + `SessionToken` + `Expiration`. Duration 15 min–12 hr (chained roles capped at 1 hr).

**STS endpoints:** historically global (`sts.amazonaws.com` in us-east-1). Best practice now is **regional STS endpoints** (`sts.<region>.amazonaws.com`) for lower latency and resilience, and so a region outage doesn't break token issuance elsewhere. This matters for interview "resilience" questions.

**Revocation:** you can't directly revoke an issued temporary credential, but you can attach an inline policy to the role that denies all actions for tokens issued before a cutoff time via `aws:TokenIssueTime` (the "revoke sessions" button in the console does exactly this).

**`sts:SourceIdentity`** — set at assume time and *cannot be changed* through role chaining; propagates the original human's identity into CloudTrail across hops. Essential for auditability in role-chaining architectures.

---

### 2.11 Federation, SSO & OIDC

**Why federate:** eliminate long-lived IAM users. Humans authenticate against your IdP (Okta/Entra ID/Google), machines authenticate via OIDC — both exchange a token for short-lived AWS creds via STS.

**Human access — two approaches:**
- **SAML 2.0 federation** (classic): configure the IdP as a SAML provider in IAM, map IdP groups → IAM roles, users get `AssumeRoleWithSAML` creds.
- **AWS IAM Identity Center** (formerly AWS SSO) — the modern, recommended path. Central place to connect an external IdP (or use its built-in directory), define **permission sets** (which become roles provisioned into each account), and give users a portal to pick account+role. Handles multi-account access cleanly. Prefer this over hand-rolled SAML for workforce access.

**Machine/workload OIDC — two must-know patterns for senior interviews:**

1. **IRSA (IAM Roles for Service Accounts) on EKS:** The EKS cluster has an OIDC provider. A Kubernetes ServiceAccount is annotated with a role ARN; the pod gets a projected OIDC token; the AWS SDK calls `AssumeRoleWithWebIdentity` to get creds scoped to that role. Result: **pod-level** IAM, no node-wide credentials, no secrets in the pod. (The newer **EKS Pod Identity** simplifies this further without per-cluster OIDC setup.) The role's trust policy conditions on `system:serviceaccount:<ns>:<sa>` via the OIDC `sub` claim.

2. **GitHub Actions → AWS via OIDC:** Instead of storing long-lived AWS keys in GitHub secrets, register GitHub's OIDC provider in IAM and create a role whose trust policy conditions on `token.actions.githubusercontent.com:sub` (e.g., `repo:org/repo:ref:refs/heads/main`). The workflow requests an OIDC token and assumes the role — **zero stored secrets**. This is a very common modern interview scenario. Be sure to lock the `sub` condition tightly (specific repo + branch/environment) to prevent other repos from assuming your role.

**Amazon Cognito** — identity for *your app's* end users (mobile/web). *User Pools* = authentication (sign-up/sign-in, a user directory, tokens). *Identity Pools (Federated Identities)* = authorization to AWS resources — exchange a user-pool or social token for temporary AWS creds via STS. Don't confuse the two: User Pool authenticates, Identity Pool grants AWS access.

---

### 2.12 Instance Profiles & IMDS

**Instance profile** = the container that delivers a role to an EC2 instance. You attach a *role*; EC2 wraps it in an instance profile of the same name. Apps on the instance get temporary creds automatically via the **Instance Metadata Service (IMDS)** — no keys on disk. The SDK's default credential provider chain fetches and auto-rotates them.

**IMDSv1 vs IMDSv2 — a guaranteed security question:**
- **IMDSv1**: simple request/response at `http://169.254.169.254/...`. Vulnerable to **SSRF** — a web-app SSRF flaw can trick the server into fetching the metadata endpoint and leaking the instance's role credentials (this was the root cause of the 2019 Capital One breach).
- **IMDSv2**: session-oriented. You must first `PUT` to get a token (with `X-aws-ec2-metadata-token-ttl-seconds`), then send that token as a header on GETs. The required `PUT` + custom header defeats most SSRF (which can only do simple GETs) and the default hop limit of 1 stops the token being relayed through a proxy/container. **Enforce IMDSv2** (`HttpTokens: required`) org-wide via SCP or account defaults.

**Credential provider chain (order the SDK searches):** env vars → shared config/credentials file → SSO/web identity token → container creds (ECS/EKS) → **IMDS**. Knowing this order explains "why is my app using the wrong credentials?" debugging.

---

### 2.13 Access Analyzer, Credential Reports & Least Privilege

Senior engineers are expected to *operationalize* least privilege, not just preach it:

- **IAM Access Analyzer** — uses automated reasoning (provable security) to find resources shared **outside your account/org** (public S3 buckets, roles assumable externally, etc.). Also generates **policy from CloudTrail activity** (right-size an over-broad policy to what was actually used) and does **policy validation/checks** (lint + "no new access" checks in CI/CD).
- **Credential report** — CSV of all users: password age, MFA status, access-key age/last-used. Perfect for audits ("find keys older than 90 days," "users without MFA").
- **Access Advisor / last-accessed data** — shows which services a role/user actually used and when. The primary tool for pruning unused permissions.
- **`iam:PassRole`** — the sleeper permission. To hand a role to a service (launch EC2 with a role, deploy a Lambda with an execution role), you need `iam:PassRole` for that role. Over-broad `PassRole` (`Resource: *`) is a **privilege-escalation vector**: a user who can pass any role to a service they control can gain that role's permissions. Always scope `PassRole` to specific role ARNs and use `iam:PassedToService` conditions.

**Least-privilege workflow to describe in interviews:**
1. Start deny-all; grant nothing.
2. Run the workload, capture actions from CloudTrail.
3. Use Access Analyzer policy generation to draft a tight policy.
4. Add condition keys (source VPC/IP, MFA, tags) to constrain further.
5. Attach a permission boundary so future edits can't exceed the ceiling.
6. Continuously prune with Access Advisor last-accessed data.

---

### 2.14 Common IAM Anti-Patterns & Security Pitfalls

Be ready to *spot the smell* — interviewers love "what's wrong with this policy?"

- `Action: "*"` + `Resource: "*"` on a human or service (unbounded admin).
- Long-lived IAM user access keys in code, CI, or `.env` files (use roles/OIDC).
- `iam:PassRole` with `Resource: "*"` (privilege escalation).
- Wildcard `iam:*` or `iam:CreatePolicyVersion`/`iam:AttachUserPolicy` granted to non-admins → self-escalation.
- Trusting `"AWS": "*"` in a resource/trust policy without conditions → anyone, anywhere.
- Relying on SCPs to constrain the **management account** (they don't).
- Using `NotAction`/`NotPrincipal` casually → accidental broad grants.
- No `ExternalId` on third-party assume-role trust → confused deputy.
- MFA condition using `Bool` instead of `BoolIfExists` → unintended lockouts/bypass.
- Leaving IMDSv1 enabled → SSRF credential theft.
- Not enabling CloudTrail org-wide, or letting member accounts disable it (guard with SCP).
- Bucket policy `Principal: "*"` without `aws:SourceVpce`/`aws:PrincipalOrgID` → public data.

---

### 2.15 IAM Interview Questions & Scenarios

#### Conceptual (rapid depth checks)

**Q1. Walk me through IAM policy evaluation when identity, resource, boundary, and SCP all apply.**
A: Default implicit deny. Any explicit Deny anywhere → denied, final. Then the request must be within SCPs (Orgs), within the permission boundary, within any session policy — these only restrict. The grant must come from an identity-based *or* resource-based Allow. Same account: identity-or-resource is enough. Cross-account: both sides must allow. Effective perms = identity ∩ boundary ∩ SCP, minus explicit denies.

**Q2. Permission boundary vs SCP — when do you reach for each?**
A: Boundary caps a *single* user/role and is set by an account admin — ideal for safely delegating role creation to developers. SCP caps an *entire account/OU*, set by the Org management account, and applies even to the account's root user — ideal for org-wide guardrails (region lock, deny disabling CloudTrail). Neither grants; both cap. I'd use them together: SCPs for the org perimeter, boundaries so devs can self-serve roles without escalating.

**Q3. Difference between an IAM role's trust policy and its permission policy?**
A: Trust policy = a resource-based policy on the role saying *who* may assume it (the `Principal`). Permission policy = *what* the role can do once assumed. Assumption requires the trust policy to allow the caller AND the caller's identity policy to allow `sts:AssumeRole`.

**Q4. What does `Principal: {"AWS": "arn:aws:iam::123:root"}` in a trust policy mean?**
A: It delegates to account 123 — any principal in 123 that its *own* identity policy also permits to call `sts:AssumeRole` on this role. It is not limited to the root user; it means "the whole account, subject to that account's IAM."

**Q5. How do temporary credentials differ from IAM user access keys, and why prefer them?**
A: Temp creds (from STS) include a session token and auto-expire (15 min–12 hr); they're issued on demand and don't persist. User keys are long-lived and, if leaked, valid until manually rotated. Temp creds shrink the blast radius, support just-in-time access, and enable federation. At scale I'd eliminate user keys entirely in favor of roles + OIDC/SSO.

#### Practical scenarios (the ones that separate seniors)

**Scenario A — Cross-account data access.**
*"Team A in Account 111 needs read access to a specific S3 prefix in Account 222's bucket. Design it two ways and pick one."*
A: **Option 1 — Assume role:** create a role in 222 with an S3 read policy scoped to `arn:aws:s3:::bucket/team-a/*`; trust policy allows the Team A role in 111 (with `aws:PrincipalOrgID` condition). Team A's identity policy allows `sts:AssumeRole` on that role. **Option 2 — Bucket policy:** 222's bucket policy directly allows the Team A role ARN to `s3:GetObject` on that prefix; Team A's identity policy also allows it (cross-account needs both sides). I'd pick the **bucket policy** here since it's a single resource + read-only — simpler, no role switch. If Team A needed many actions across many resources in 222, I'd pick the assume-role model to centralize control. Add `aws:PrincipalOrgID` and enforce encryption + `aws:SecureTransport`.

**Scenario B — Third-party SaaS wants access to your account.**
*"A monitoring vendor asks you to create a role they can assume. What do you require?"*
A: A role with least-privilege read-only permissions, trust policy naming the vendor's AWS account as principal, and crucially an **`sts:ExternalId`** condition matching a unique secret the vendor generates per customer — this defeats the confused-deputy attack. I'd also scope with `aws:SourceArn` if applicable, enable CloudTrail on the role's activity, and review the vendor's requested actions rather than granting their default template blindly.

**Scenario C — Developers must create Lambda roles without escalating.**
A: Permission boundaries. Grant devs `iam:CreateRole`/`iam:PutRolePolicy` **only with a condition requiring** a specific boundary policy be attached (`iam:PermissionsBoundary` condition key). The boundary caps any created role to, say, dev-scoped S3/DynamoDB/logs. Even if a dev attaches AdministratorAccess, the intersection with the boundary limits real power. Also scope their `iam:PassRole` to roles carrying that boundary.

**Scenario D — Kill long-lived keys in CI/CD.**
*"Our GitHub Actions pipeline uses a stored AWS access key. Fix it."*
A: Set up **GitHub OIDC federation**: register `token.actions.githubusercontent.com` as an IAM OIDC provider, create a deploy role whose trust policy conditions on `token.actions.githubusercontent.com:aud = sts.amazonaws.com` and `:sub = repo:org/repo:ref:refs/heads/main` (or a specific environment). The workflow requests an OIDC token and calls `AssumeRoleWithWebIdentity` — no stored secret. Lock the `sub` tightly so other repos/branches can't assume it; scope the role to only the deploy actions.

**Scenario E — Enforce MFA for sensitive actions.**
A: Add a condition `"BoolIfExists": {"aws:MultiFactorAuthPresent": "true"}` (use *IfExists* to avoid breaking non-MFA credential types), or gate on `aws:MultiFactorAuthAge` for freshness. For self-service, a common pattern: allow users to manage their own MFA device unauthenticated, but deny most other actions unless MFA is present. Enforce org-wide via SCP for the most destructive actions.

**Scenario F — "This EC2 app's credentials were stolen via SSRF."**
A: Root cause is almost certainly **IMDSv1**. Remediate: enforce **IMDSv2** (`HttpTokens: required`, hop limit 1), rotate/revoke the leaked session (deny by `aws:TokenIssueTime`), tighten the instance role to least privilege, and fix the SSRF in the app. Prevent recurrence: SCP requiring IMDSv2 on launch, Config rule to detect IMDSv1-enabled instances.

**Scenario G — Region lockdown for compliance.**
A: Attach a deny SCP on the OU denying all actions when `aws:RequestedRegion` isn't in the approved list, excluding global services via `NotAction` (IAM, CloudFront, Route 53, STS, Support). Test in a sandbox OU first; watch for global-service breakage and STS regional endpoints.

**Scenario H — "A user has an Allow for `s3:*` but still gets AccessDenied. Why?"**
A: Candidate causes, in order: (1) an explicit **Deny** somewhere — identity, bucket policy, boundary, or SCP; (2) a **permission boundary** that doesn't include the action; (3) an **SCP** blocking it; (4) cross-account where the **resource policy** doesn't also allow it; (5) a **session policy** narrowing it; (6) a **KMS** permission gap (bucket is SSE-KMS and the user lacks `kms:Decrypt`); (7) a condition key not satisfied (e.g., missing `aws:SecureTransport`/VPCe). I'd use the **IAM Policy Simulator** and **CloudTrail** (which shows the deny and often the reason) to pinpoint it.

**Scenario I — ABAC at scale.**
*"You have 200 project teams and don't want 200 policies. Design access."*
A: **ABAC.** Tag principals with `project=<x>` and resources with `project=<x>`. One policy: `"StringEquals": {"aws:ResourceTag/project": "${aws:PrincipalTag/project}"}`. Adding a new team is just tagging — no new policy. Enforce tag-on-create with a condition requiring `aws:RequestTag/project`, and protect the `project` tag from being changed by non-admins (`aws:TagKeys` deny). Contrast with RBAC, which would need a role/policy per team.

**Scenario J — Auditing who did what across chained roles.**
A: Enable **`sts:SourceIdentity`** at the first assume so the original human's identity survives every role-chain hop in CloudTrail. Require it via a trust-policy condition (`sts:SourceIdentity` present). Combine with CloudTrail org trail + Athena to trace a specific action back to a person even through multiple assumptions.

---

## 3. Core AWS Services — Deep Coverage

> IAM stays the deepest topic, but you're expected to reason with real depth across the platform.
> For each area: the mechanics that matter, the security model, the trade-offs, and interview Q&A.

### 3.1 Compute

**EC2 (Elastic Compute Cloud)** — VMs you fully control.
- **Instance types** are families tuned to a workload: `t`/`m` (general/burstable), `c` (compute), `r`/`x` (memory), `p`/`g`/`inf` (GPU/ML), `i`/`d` (storage). At senior level, be able to reason "memory-bound app → r-family; steady CPU → avoid `t` burstable credits."
- **Burstable (T) instances** earn CPU credits when idle and spend them under load; running out drops you to baseline (or bills "unlimited mode"). A classic prod outage cause: a T instance exhausting credits.
- **Purchasing:** On-Demand (flexible, priciest), **Reserved/Savings Plans** (1–3 yr commit, up to ~72% off), **Spot** (spare capacity up to ~90% off but can be reclaimed with a 2-min warning — great for stateless/fault-tolerant/batch), Dedicated Hosts/Instances (compliance, licensing).
- **Placement groups:** *cluster* (low-latency, same rack — HPC), *spread* (max hardware isolation — critical instances), *partition* (large distributed systems like Kafka/HDFS).
- **Auto Scaling Group (ASG):** launch template + scaling policies (target-tracking, step, scheduled) + health checks; integrates with ELB. Understand desired/min/max, cooldowns, lifecycle hooks, and warm pools.
- **Storage:** instance store (ephemeral, physically attached, lost on stop) vs EBS (network, persistent).
- **Security:** instance profile/role (never store keys), Security Groups, **IMDSv2** (see §2.12), User Data for bootstrap.
- **Gotcha:** SGs are **stateful** (return traffic auto-allowed) and allow-only; **NACLs** are subnet-level, **stateless** (must allow return traffic explicitly), and support deny rules.

**Lambda (serverless functions).**
- Event-driven; you pay per request + GB-seconds. Max **15-min** timeout, up to 10 GB memory (CPU scales with memory), 512 MB–10 GB `/tmp`.
- **Two IAM surfaces:** *execution role* (what the function may do) and *resource policy* (who/what may invoke it — e.g., allow S3/EventBridge/API Gateway).
- **Cold starts:** first invocation (or scale-out) pays init cost; mitigate with **Provisioned Concurrency** or SnapStart (Java). VPC-attached Lambdas historically added ENI cold-start latency (now much improved via Hyperplane ENIs).
- **Concurrency:** account-level limit (default 1,000); **reserved concurrency** caps/guarantees a function; unreserved is shared. Throttling → `429`.
- **Patterns:** async (SNS/S3/EventBridge → internal queue, 2 retries + DLQ), sync (API Gateway/ALB), stream (Kinesis/DynamoDB Streams — poll-based, batch, ordered per shard).
- **Gotcha:** idempotency (retries mean at-least-once); don't hold DB connections carelessly (use RDS Proxy); package size limits (250 MB unzipped, or container images up to 10 GB).

**Containers — ECS / EKS / Fargate.**
- **ECS** — AWS-native orchestrator. **Two IAM roles you must not confuse:** the **task role** (permissions your *app code* uses) and the **task execution role** (what the ECS agent uses to pull images from ECR and read secrets/logs). Put app permissions on the *task role*, never the EC2 instance role.
- **EKS** — managed Kubernetes. Pod-level IAM via **IRSA** or **EKS Pod Identity** (see §2.11). Control-plane auth maps IAM principals to K8s RBAC (`aws-auth` ConfigMap / access entries).
- **Fargate** — serverless data plane for ECS/EKS: no nodes to manage, per-task isolation (own kernel), pay per vCPU/GB-second. Trade-off: less control, can't use privileged/DaemonSet-style patterns, sometimes pricier at steady high utilization than EC2.
- **ECR** — container registry with image scanning, lifecycle policies, resource policies for cross-account pulls.

**Beanstalk / App Runner / Lightsail** — increasing abstraction. Beanstalk provisions the EC2/ASG/ELB for you from your code; App Runner is fully managed container-to-URL; Lightsail is simplified VPS pricing.

**Compute Interview Q&A:**
- *Spot vs On-Demand vs Reserved — design a cost-efficient fleet.* → Baseline steady load on Savings Plans/Reserved, elastic layer on On-Demand, stateless/batch on Spot with capacity-optimized allocation + On-Demand fallback in the ASG mixed-instances policy.
- *Your T3 web tier slows down under sustained traffic — why?* → CPU-credit exhaustion; switch to unlimited mode or an M/C instance.
- *When Lambda over ECS/Fargate?* → Spiky/event-driven, sub-15-min, want zero infra; choose containers for long-running, custom runtimes, high steady throughput, or when cold starts are unacceptable.
- *How do you give a Lambda access to an RDS in a private subnet?* → Attach the Lambda to the VPC/private subnets, SG allowing it to the DB SG, use RDS Proxy for connection pooling, execution role for any AWS calls.

### 3.2 Storage

**S3 (Simple Storage Service)** — object storage, 11 9's durability.
- **Storage classes:** Standard, Intelligent-Tiering (auto-moves by access pattern — safe default when unsure), Standard-IA, One Zone-IA, Glacier Instant/Flexible/Deep Archive. **Lifecycle policies** transition/expire objects to cut cost.
- **Consistency:** now **strong read-after-write** for all operations (old "eventual consistency" answers are outdated — say strong).
- **Security (a top interview area):**
  - **Block Public Access** (account + bucket level, on by default) — the master switch that overrides permissive policies/ACLs.
  - **Bucket policy** (resource-based) + **identity policy** union (same-account) — see §2.4/§2.8.
  - **ACLs are legacy** — disable them via **Object Ownership = Bucket owner enforced**; use policies instead.
  - **Encryption:** SSE-S3 (AES-256, AWS keys), **SSE-KMS** (customer/AWS-managed KMS keys, adds audit + access control + throttling considerations), SSE-C (you supply the key), or client-side. SSE-S3 is now applied by default to new objects.
  - **Access patterns:** presigned URLs (time-limited delegated access), VPC endpoints (`aws:SourceVpce`), CloudFront + **OAC** (Origin Access Control) to keep the bucket private, S3 Access Points (per-app policies), Access Grants (map IdP identities to prefixes).
- **Performance:** ~3,500 PUT/5,500 GET per prefix per second, scales automatically with more prefixes; multipart upload for large objects; S3 Transfer Acceleration; byte-range fetches.
- **Data protection:** **Versioning** (recover overwrites/deletes), **MFA Delete**, **Object Lock** (WORM — compliance/governance mode for immutability), **Replication** (CRR cross-region / SRR same-region, needs versioning).
- **Gotcha:** SSE-KMS objects require the reader to also have `kms:Decrypt` on the key — a very common "why AccessDenied on a readable bucket" cause.

**EBS (Elastic Block Store)** — network block volumes for EC2.
- Types: `gp3` (default SSD, decouples IOPS/throughput from size — prefer over gp2), `io1/io2` (provisioned IOPS, io2 Block Express for extreme), `st1`/`sc1` (throughput/cold HDD).
- **AZ-scoped** — to move across AZ/region you snapshot (snapshots live in S3, are incremental) and restore. Encryption via KMS (encrypt-by-default account setting recommended). Multi-Attach for io2 (cluster filesystems only).

**Other storage:** **EFS** (elastic NFS, multi-AZ, shared across many EC2/Lambda), **FSx** (Windows/NetApp ONTAP/Lustre for HPC), **Storage Gateway** (hybrid on-prem↔cloud), **AWS Backup** (centralized backup policies across services).

**Storage Interview Q&A:**
- *Design cost-optimal storage for logs written daily, read heavily for 30 days, rarely after.* → S3 Standard → lifecycle to Standard-IA at 30d → Glacier Flexible at 90d → expire at 1–7 yr per compliance; enable versioning + Object Lock if immutability required.
- *Bucket is readable but users get AccessDenied on objects — why?* → SSE-KMS without `kms:Decrypt`, or explicit deny, or Block Public Access, or the object owner is a different account (Object Ownership).
- *Make an S3 bucket reachable only from your VPC.* → Gateway VPC endpoint + bucket policy condition `aws:SourceVpce`; deny everything else.
- *How does CloudFront serve a private bucket?* → OAC signs requests to the origin; bucket policy allows only the CloudFront distribution; Block Public Access stays on.

### 3.3 Networking

**VPC (Virtual Private Cloud)** — your isolated software-defined network.
- **CIDR** block (e.g., /16), carved into **subnets** (each in one AZ). **Public subnet** = has a route to an **Internet Gateway (IGW)**; **private subnet** = no direct IGW route.
- **Egress from private subnets:** **NAT Gateway** (managed, in a public subnet, AZ-redundant — deploy one per AZ for HA) or NAT instance (legacy/cheap). IPv6 uses an **egress-only IGW**.
- **Routing:** each subnet → a **route table**. Longest-prefix match wins.
- **Firewalls (know both cold):**
  - **Security Group** — instance/ENI level, **stateful**, allow-rules only, can reference other SGs (powerful for tiered architectures: "web SG allowed to app SG on 8080").
  - **NACL** — subnet level, **stateless** (need explicit inbound *and* outbound rules, including ephemeral ports for return traffic), supports deny, evaluated by rule number.
- **DNS:** `enableDnsSupport` + `enableDnsHostnames`; Route 53 Resolver for hybrid DNS.

**Connectivity patterns:**
- **VPC Peering** — 1:1, non-transitive, no overlapping CIDRs. Fine for a few VPCs.
- **Transit Gateway (TGW)** — hub-and-spoke router connecting many VPCs + on-prem; transitive; the scaler for large multi-VPC/multi-account networks.
- **PrivateLink / VPC Endpoints** — private access without traversing the internet:
  - **Gateway endpoints** (S3 & DynamoDB only) — route-table entries, **free**.
  - **Interface endpoints** — ENIs powered by PrivateLink for most services + your own services; hourly + data cost. Security lever: `aws:SourceVpce` conditions.
- **Hybrid:** **Direct Connect** (dedicated private line, consistent latency) vs **Site-to-Site VPN** (encrypted over internet, quick/cheap); often DX + VPN backup.

**Edge & DNS:**
- **Route 53** — DNS + health-checked routing policies: **simple, weighted** (A/B, canary), **latency**, **failover** (active-passive), **geolocation/geoproximity**, **multivalue**. Alias records point to AWS resources for free.
- **CloudFront** — global CDN; caches at edge, integrates **WAF**, **Shield**, OAC, Lambda@Edge/CloudFront Functions for edge logic. Lowers latency + offloads origin + absorbs DDoS.
- **Global Accelerator** — anycast static IPs routing over the AWS backbone (TCP/UDP, non-HTTP) — different from CloudFront (content caching).

**Load balancing (ELB):**
- **ALB** (L7) — HTTP/HTTPS, host/path routing, target groups, WebSockets, redirects, auth integration, WAF attach. Most web apps.
- **NLB** (L4) — TCP/UDP, ultra-low latency, millions of RPS, **static/Elastic IP**, preserves source IP, PrivateLink front.
- **GWLB** (L3/4) — inserts virtual appliances (firewalls/IDS) transparently via GENEVE.

**Networking Interview Q&A:**
- *SG vs NACL — give a case where you'd need a NACL.* → SGs are your default (stateful, simpler). Use NACLs for subnet-wide **deny** (block a malicious IP range) or a coarse extra layer, remembering to allow ephemeral return ports.
- *Private subnet instances need to download OS patches — how?* → NAT Gateway in a public subnet (per-AZ for HA) + default route to it; or VPC endpoints for AWS-native package mirrors.
- *Three VPCs across two accounts must all talk to each other — peering or TGW?* → TGW: peering is non-transitive and O(n²) to mesh; TGW gives a central hub with route control and scales.
- *Design private, no-internet access from EC2 to S3 + DynamoDB + Secrets Manager.* → Gateway endpoints for S3 & DynamoDB (free), interface endpoints for Secrets Manager/STS/etc., lock with `aws:SourceVpce`.
- *Preserve client source IP to your backend and need a static IP — which LB?* → NLB.

### 3.4 Databases

**RDS / Aurora (managed relational).**
- Engines: MySQL, PostgreSQL, MariaDB, Oracle, SQL Server; **Aurora** (MySQL/PostgreSQL-compatible, AWS-built).
- **HA:** **Multi-AZ** = synchronous standby in another AZ with automatic failover (DR/availability, *not* read scaling). **Read Replicas** = asynchronous, for read scaling (and can be promoted). Aurora has one primary + up to 15 low-lag replicas over a shared distributed storage layer.
- **Aurora internals worth knowing:** storage is 6 copies across 3 AZs, self-healing, auto-scaling to 128 TiB; fast failover (replicas share storage — no data copy); **Aurora Serverless v2** auto-scales capacity in fine ACU steps; **Global Database** for cross-region DR with ~1s replication.
- **Security:** encryption at rest (KMS, set at creation — can't toggle later without snapshot/restore), TLS in transit, **IAM database authentication** (short-lived token instead of a password — great for eliminating stored DB creds), Secrets Manager rotation, in private subnets with SG scoping.
- **Ops:** automated backups + PITR (point-in-time recovery), manual snapshots (persist beyond retention), Performance Insights, **RDS Proxy** (connection pooling — essential for Lambda/serverless).
- **Gotcha:** Multi-AZ ≠ read scaling; enabling encryption after creation requires a snapshot→restore.

**DynamoDB (serverless NoSQL).**
- Key-value + document; single-digit-ms at any scale. **Data model is everything:** partition key (hash) determines the physical partition; optional sort key enables range queries; design for your **access patterns** (single-table design), not normalization.
- **Indexes:** **LSI** (same partition key, alternate sort key — must be created at table creation, shares throughput) vs **GSI** (different partition/sort key, own throughput, eventually consistent).
- **Capacity:** on-demand (spiky/unknown) vs provisioned (predictable, cheaper, + auto scaling). Watch **hot partitions** (uneven key distribution) — adaptive capacity helps but design keys to spread load.
- **Features:** **Streams** (change data capture → Lambda/Kinesis), **TTL** (auto-expire items), **Global Tables** (multi-region active-active), **DAX** (in-memory cache, microsecond reads), transactions, PITR.
- **Fine-grained IAM:** `dynamodb:LeadingKeys` restricts a principal to items whose partition key matches their identity — true row-level security (e.g., multi-tenant apps).
- **Gotcha:** you can't efficiently query on non-key attributes without a GSI; strongly-consistent reads cost 2× and aren't available on GSIs.

**Other data stores (know when to reach for each):**
- **ElastiCache** — Redis (rich structures, persistence, pub/sub, cluster mode) / Memcached (simple, multi-threaded). Caching, sessions, leaderboards, rate limiting. Cache strategies: lazy-loading vs write-through; TTL + eviction.
- **Redshift** — columnar MPP data warehouse; Spectrum queries S3 directly; RA3 separates compute/storage. OLAP, not OLTP.
- **Athena** — serverless SQL directly over S3 (Presto/Trino); pay per data scanned — partition + columnar (Parquet) to cut cost. Pairs with Glue Data Catalog.
- **OpenSearch** — search/log analytics. **DocumentDB** (Mongo-compatible), **Neptune** (graph), **Keyspaces** (Cassandra), **Timestream** (time-series), **MemoryDB** (durable Redis).

**Database Interview Q&A:**
- *Multi-AZ vs Read Replica?* → Multi-AZ = synchronous, automatic failover, availability/DR, same endpoint. Read Replica = asynchronous, read scaling, separate endpoint, manual promotion. They solve different problems; often used together.
- *SQL vs DynamoDB for a new service?* → DynamoDB when access patterns are known/simple, need massive scale + predictable low latency, and can denormalize; relational when you need flexible ad-hoc queries, joins, transactions across entities, strong consistency by default.
- *Your DynamoDB table throttles under load despite high provisioned capacity — why?* → Hot partition: skewed partition key concentrating traffic. Fix by choosing a higher-cardinality/composite key or write-sharding.
- *Eliminate stored DB passwords in your app.* → IAM database authentication (token-based) or Secrets Manager with automatic rotation + RDS Proxy.
- *Cheap ad-hoc analytics over TBs of S3 logs?* → Athena over Parquet with partitioning; catalog in Glue; no cluster to run.

### 3.5 Messaging, Streaming & Integration

- **SQS** — durable queue, decoupling & load-leveling. **Standard** (at-least-once, best-effort order, near-unlimited throughput) vs **FIFO** (exactly-once processing, strict order, 300–3,000 msg/s with batching). **Visibility timeout** (hides a message while a consumer works — tune to processing time), **DLQ** (after N failed receives), **long polling** (reduce empty receives), 14-day max retention, 256 KB max (larger via S3 pointer).
- **SNS** — pub/sub fan-out to many subscribers (SQS, Lambda, HTTP, email, SMS); **SNS→SQS fan-out** is a canonical pattern (one publish, many durable queues). Message filtering, FIFO topics, DLQs.
- **EventBridge** — serverless event bus with content-based routing rules, schema registry, **cross-account/partner events**, scheduler, and pipes (source→filter→enrich→target). Preferred over SNS when you need rich routing/filtering and SaaS integrations.
- **Kinesis** — real-time streaming. **Data Streams** (sharded, ordered per shard, replay within retention, consumer-managed — millisecond) vs **Data Firehose** (fully managed delivery to S3/Redshift/OpenSearch with buffering/transform, near-real-time). Shard = 1 MB/s in, 2 MB/s out; **enhanced fan-out** for many consumers. Compare to Kafka (MSK) for higher control.
- **Step Functions** — visual state-machine orchestration (retries, parallel, map, choice, error handling). **Standard** (long-running, exactly-once, up to 1 yr) vs **Express** (high-volume, short, at-least-once). Use for coordinating multi-step workflows instead of chaining Lambdas by hand.
- **MSK** (managed Kafka), **AppFlow** (SaaS data transfer), **API Gateway** (REST/HTTP/WebSocket front door with auth, throttling, caching, usage plans).

**Messaging Interview Q&A:**
- *SQS vs SNS vs EventBridge — pick one.* → SQS = one producer, buffered work for consumers to pull. SNS = push fan-out to many subscribers, low latency. EventBridge = event routing/filtering across services & accounts with schema + SaaS integration. Combine (SNS→SQS, or EventBridge→SQS) as needed.
- *Guarantee ordered, exactly-once order processing.* → FIFO SQS with a message group ID per entity (order preserved within group, parallelism across groups) + idempotent consumers.
- *Decouple a spiky producer from a slow consumer without losing messages.* → SQS as a buffer; consumer auto-scales on queue depth (ApproximateNumberOfMessages); DLQ for poison messages; tune visibility timeout.
- *Standard vs Express Step Functions?* → Standard for durable, long, auditable workflows (exactly-once); Express for high-throughput short-lived (event processing) at lower cost, at-least-once.

### 3.6 Security, Identity-Adjacent & Governance

- **KMS** — managed encryption keys. The **key policy is a resource policy and is the root of trust** — an IAM policy alone can't grant use of a key unless the key policy allows it (or delegates to IAM via the `kms:*`/account-root statement). Know **envelope encryption** (KMS encrypts a data key; the data key encrypts the data — used everywhere), CMK types (customer-managed vs AWS-managed vs AWS-owned), **grants** (temporary programmatic delegation), key rotation, multi-Region keys, and `kms:ViaService` (restrict a key to use only via S3/EBS/etc.). **CloudHSM** for single-tenant FIPS 140-2 Level 3 hardware you control.
- **Secrets Manager vs SSM Parameter Store** — Secrets Manager: built-in **rotation** (Lambda), cross-account/region replication, higher cost. Parameter Store: cheap/free tier, hierarchical params, `SecureString` via KMS, no native rotation. Choose Secrets Manager when rotation matters (DB creds), Parameter Store for config + simple secrets.
- **CloudTrail** — records API calls (management + optional data events). Best practice: **org-wide trail** → central logging account S3 bucket (KMS-encrypted, MFA/Object-Lock protected), **log-file validation** on, guard against tampering with SCP. This is your forensic backbone.
- **Config** — records resource configuration + evaluates **rules** (managed/custom) for compliance; conformance packs; auto-remediation. Answers "was this ever misconfigured, and when?"
- **CloudWatch** — metrics, **Logs** (+ Logs Insights queries), **alarms**, dashboards, **Events** (now EventBridge), **X-Ray** for distributed tracing. Composite alarms + anomaly detection at senior level.
- **GuardDuty** (ML threat detection from CloudTrail/VPC/DNS logs — no agents), **Security Hub** (aggregates findings + CIS/AWS benchmarks), **Macie** (PII discovery in S3), **Inspector** (automated vuln scanning of EC2/ECR/Lambda), **Detective** (investigation graphs), **WAF** (L7 rules, rate-based, managed rule groups) + **Shield/Shield Advanced** (DDoS), **Network Firewall** (VPC-level stateful IDS/IPS).
- **Control Tower** — automated landing zone (multi-account baseline: Organizations + SSO + guardrails + centralized logging). **Landing Zone Accelerator** for regulated scale.

**Security/Governance Interview Q&A:**
- *An IAM policy grants `kms:Decrypt` but the user still can't decrypt — why?* → The **key policy** doesn't allow that principal (or doesn't delegate to IAM). KMS auth needs the key policy's blessing.
- *Secrets Manager vs Parameter Store for DB creds?* → Secrets Manager for automatic rotation + replication; Parameter Store if you'll rotate manually and want minimal cost.
- *Ensure no member account can disable CloudTrail.* → Org trail managed centrally + an SCP denying `cloudtrail:StopLogging`/`DeleteTrail`; alert on GuardDuty/Config drift.
- *Detect credential compromise & data exfiltration automatically.* → GuardDuty (anomalous API/geolocation, exfiltration findings) → Security Hub → EventBridge → automated response (disable key, isolate instance).

### 3.7 Well-Architected, IaC & Delivery

- **Well-Architected Framework — 6 pillars:** Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability. Framing design answers around these signals seniority; know a lever or two per pillar.
- **IaC:** **CloudFormation** (declarative YAML/JSON, stacks, StackSets for multi-account/region, change sets, drift detection), **CDK** (imperative code → CFN), **Terraform** (multi-cloud, state files — know remote state + locking). SAM for serverless.
- **CI/CD:** CodePipeline (orchestration), CodeBuild (build/test), CodeDeploy (blue/green & canary to EC2/ECS/Lambda), CodeArtifact, plus deployment strategies: **rolling, blue/green, canary** — be able to compare rollback speed and blast radius.
- **Cost:** Savings Plans/Reserved for steady load, Spot for stateless, S3 lifecycle tiering, right-sizing (Compute Optimizer), tagging for cost allocation, budgets/anomaly detection, NAT Gateway & cross-AZ data transfer as sneaky cost drivers.

**Delivery Interview Q&A:**
- *Blue/green vs canary deployment?* → Blue/green swaps all traffic to a parallel environment (instant rollback, double cost briefly). Canary shifts a small % first, watches metrics, then ramps (limits blast radius, slower). Choose by risk tolerance and cost.
- *Manage identical infra across 50 accounts/regions.* → CloudFormation **StackSets** (or Terraform with per-account workspaces/pipelines) driven from a management/delegated admin account; parameterize per environment.
- *Biggest hidden AWS costs you watch?* → Cross-AZ/inter-region data transfer, idle NAT Gateways, over-provisioned EBS/RDS, unattached EIPs, S3 in Standard that should be tiered, forgotten dev environments.

---

## 4. System Design & Cross-Cutting Concerns

Senior interviews often end with an open design. Anchor answers in these:

- **Multi-account strategy:** separate accounts per environment/team/blast-radius (Orgs + Control Tower). Centralized logging account, security tooling account, network account. SCP guardrails on OUs. This is *the* modern best practice — mention it.
- **Least privilege + zero standing access:** short-lived creds everywhere, JIT access via Identity Center, break-glass roles with heavy alerting.
- **Encryption everywhere:** at rest (KMS) + in transit (TLS), enforced by policy conditions (`aws:SecureTransport`, `s3:x-amz-server-side-encryption`).
- **Defense in depth:** SG + NACL + WAF + private subnets + VPC endpoints + IAM + KMS — no single control is the whole answer.
- **Observability & audit:** org-wide CloudTrail → S3 (immutable, KMS, log validation) → Athena/Security Hub; GuardDuty on.
- **Resilience:** multi-AZ by default, multi-region for critical; regional STS endpoints; understand RTO/RPO trade-offs (backup/restore → pilot light → warm standby → active-active).
- **Cost:** right-sizing, Savings Plans/Reserved, S3 lifecycle tiering, spot for stateless, tagging for cost allocation.

---

## 5. Rapid-Fire Interview Q&A Bank

- **IAM regional or global?** Global.
- **Can a group be a principal?** No.
- **Deny vs Allow precedence?** Explicit Deny always wins.
- **Do SCPs grant permissions?** No — they only cap.
- **Do SCPs affect the management account?** No.
- **Does a permission boundary grant anything?** No — it's a ceiling (intersection).
- **Same-account: identity or resource policy enough?** Yes, either. **Cross-account?** Need both.
- **Max session for a chained role?** 1 hour.
- **What API for OIDC federation?** `AssumeRoleWithWebIdentity`.
- **What stops the confused deputy?** `ExternalId` (third parties) / `aws:SourceArn`+`aws:SourceAccount` (own services).
- **Permission needed to give a role to a service?** `iam:PassRole` (scope it!).
- **IMDSv2 defends against?** SSRF credential theft.
- **KMS access requires?** The key policy to allow it (not IAM alone).
- **Tool to find externally-shared resources?** IAM Access Analyzer.
- **Right-size an over-broad policy from usage?** Access Analyzer policy generation + Access Advisor last-accessed.
- **User Pool vs Identity Pool?** Authentication vs AWS-resource authorization.
- **ABAC key mechanism?** Match principal tags to resource tags via policy variables.
- **Where do you put `${aws:PrincipalTag/team}`?** In the Resource ARN / Condition for per-tenant scoping.
- **Debug AccessDenied tools?** Policy Simulator + CloudTrail (shows the denying policy).
- **Best practice for workforce multi-account access?** IAM Identity Center + permission sets.

---

## 6. Final Prep Checklist

- [ ] Recite policy evaluation logic (§2.4) from memory, including same- vs cross-account.
- [ ] Draw the 4-way diagram: identity policy vs resource policy vs boundary vs SCP.
- [ ] Explain boundary vs SCP with a delegation example.
- [ ] Explain trust policy vs permission policy and the two-sided assume-role check.
- [ ] Design cross-account access two ways and justify the choice.
- [ ] Explain ExternalId / confused deputy.
- [ ] Explain GitHub OIDC and IRSA end to end (no stored secrets).
- [ ] Explain IMDSv1 → IMDSv2 and the Capital One lesson.
- [ ] Explain `iam:PassRole` as a privilege-escalation vector.
- [ ] Explain ABAC vs RBAC and when each wins.
- [ ] Walk through a least-privilege operational workflow (CloudTrail → Access Analyzer → boundaries).
- [ ] Have one real story: an IAM problem you debugged or a permission model you designed.
- [ ] Be able to spot 5+ anti-patterns in a bad policy on sight.

---

*Good luck. If you can hold your own on Sections 2.4–2.11 and the scenarios in 2.15, you're interviewing above the bar for most senior AWS roles.*
