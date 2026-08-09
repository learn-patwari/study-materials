"""
Run this once to populate DevFlow with realistic sample data so you can
explore the UI without a live Jira / Confluence / Bitbucket connection.

    python seed_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db import database as db

conn = db.get_connection()


def run(sql, params=()):
    conn.execute(sql, params)


def run_many(sql, rows):
    conn.executemany(sql, rows)


# ── Clear existing sample data ────────────────────────────────────────
print("Clearing old data...")
for tbl in [
    "pr_review_comments", "pull_requests",
    "voc_links", "sprints",
    "test_files", "documents", "diagrams", "chat_messages", "tasks", "tickets",
    "bug_analyses", "bug_counts",
]:
    conn.execute(f"DELETE FROM {tbl}")
conn.commit()

# ── Settings ──────────────────────────────────────────────────────────
print("Seeding settings...")
settings = [
    ("jira_url",              "https://jira.example.com"),
    ("jira_token",            "SAMPLE_TOKEN"),
    ("jira_default_project",  "PROJ — Sample Project"),
    ("confluence_url",        "https://confluence.example.com"),
    ("confluence_token",      "SAMPLE_TOKEN"),
    ("confluence_parent_page_id", "123456"),
    ("bitbucket_url",         "https://bitbucket.example.com"),
    ("bitbucket_token",       "SAMPLE_TOKEN"),
    ("ai_base_url",           ""),
    ("ai_api_key",            "sk-placeholder"),
    ("ai_model",              "gpt-4o"),
    ("doc_template",          "## Summary\n{summary}\n\n## Acceptance Criteria\n{criteria}\n\n## Technical Notes\n{notes}"),
    ("sprint_dev_days",       "8"),
    ("sprint_test_days",      "2"),
    ("test_run_command",      "pytest tests/ -v"),
    ("pr_watch_repos",        "PROJ/backend\nPROJ/mobile"),
    ("pr_poll_interval_secs", "120"),
    ("jira_issue_type_srs",   "Story"),
    ("jira_issue_type_sad",   "SAD"),
    ("jira_issue_type_bug",   "Bug"),
    ("jira_issue_type_improvement", "Improvement"),
]
conn.executemany(
    "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", settings
)

# ── Tickets (SRS) ─────────────────────────────────────────────────────
print("Seeding tickets...")
tickets = [
    (
        "PROJ-101",
        "Payment Gateway Integration",
        "The system shall integrate with Stripe to process credit card payments. "
        "It must support both web and mobile checkout flows. Fallback to PayPal if Stripe is unavailable.",
        "We need Stripe support in our checkout service. Both web and mobile must work. "
        "If Stripe is down, fall back to PayPal seamlessly.",
        "ready",
        "",
        "local",
    ),
    (
        "PROJ-98",
        "Auth Revamp — OAuth2 + MFA",
        "Replace the legacy session-based auth with OAuth2 (Google & GitHub providers). "
        "All users must be prompted to enable MFA on next login after the migration.",
        "We are replacing our old cookie auth with OAuth2. Google and GitHub as identity providers. "
        "MFA becomes mandatory for all accounts after rollout.",
        "in_progress",
        "",
        "local",
    ),
    (
        "PROJ-95",
        "Dashboard Performance Optimisation",
        "The main dashboard must load within 2 seconds for datasets up to 100k rows. "
        "Implement server-side pagination and lazy-loading of chart data.",
        "Dashboard is too slow for large accounts. Need server-side pagination and lazy chart loading.",
        "posted",
        "",
        "local",
    ),
    (
        "PROJ-110",
        "Email Notification Service",
        "Send transactional emails for: account creation, password reset, order confirmation, "
        "and weekly digest. Use SendGrid. Allow users to manage notification preferences.",
        "Build a notification service using SendGrid. Cover the main transactional flows and give "
        "users control over what emails they receive.",
        "draft",
        "",
        "local",
    ),
]
conn.executemany(
    "INSERT INTO tickets (jira_key,title,srs_content,description,status,code_source,source_type) "
    "VALUES (?,?,?,?,?,?,?)",
    tickets,
)
conn.commit()

def tid(key):
    return conn.execute("SELECT id FROM tickets WHERE jira_key=?", (key,)).fetchone()[0]

t101 = tid("PROJ-101")
t98  = tid("PROJ-98")
t95  = tid("PROJ-95")
t110 = tid("PROJ-110")

# ── Chat messages ─────────────────────────────────────────────────────
print("Seeding chat messages...")
msgs = [
    (t101, "user",      "We need Stripe support in our checkout service. Both web and mobile must work."),
    (t101, "assistant", "1. Does this apply to mobile checkout as well as web?\n2. What is the fallback if Stripe is unavailable?\n3. Should we store card tokens for repeat purchases?"),
    (t101, "user",      "Yes, both web and mobile. PayPal as fallback. Yes, store tokens for repeat customers."),
    (t101, "assistant", "4. What currency / region support is needed?\n5. Is 3D Secure / SCA compliance required?"),
    (t101, "user",      "Multi-currency (USD, EUR, GBP). Yes, SCA required for EU customers."),
    (t101, "assistant", "✓ I have enough information. Click Generate All to proceed."),

    (t98, "user",      "Replacing cookie auth with OAuth2. Google and GitHub providers. MFA mandatory."),
    (t98, "assistant", "1. Will existing passwords be migrated or invalidated?\n2. Should MFA be TOTP-only or also SMS?"),
    (t98, "user",      "Existing passwords invalidated — force OAuth login. TOTP only (no SMS)."),
    (t98, "assistant", "✓ I have enough information. Click Generate All to proceed."),
]
conn.executemany(
    "INSERT INTO chat_messages (ticket_id,role,content) VALUES (?,?,?)", msgs
)

# ── Tasks ─────────────────────────────────────────────────────────────
print("Seeding tasks...")
tasks = [
    # PROJ-101 tasks
    (t101, "PROJ-101-1", "Integrate Stripe SDK into checkout service",      "alice",  "in_progress", 3.0,  "dev",  "2026-08-01", "2026-08-01"),
    (t101, "PROJ-101-2", "Update checkout API endpoints for card flow",      "alice",  "todo",        5.0,  "dev",  "2026-08-02", "2026-08-02"),
    (t101, "PROJ-101-3", "Add PayPal fallback with retry logic",             "bob",    "todo",        4.0,  "dev",  "2026-08-03", "2026-08-03"),
    (t101, "PROJ-101-4", "Implement card token storage (PCI-DSS scope)",     "alice",  "todo",        3.0,  "dev",  "2026-08-04", "2026-08-04"),
    (t101, "PROJ-101-5", "Multi-currency support + SCA/3DS for EU",          "bob",    "todo",        4.0,  "dev",  "2026-08-05", "2026-08-05"),
    (t101, "PROJ-101-6", "Write unit tests for payment service",             "alice",  "todo",        4.5, "dev",  "2026-08-06", "2026-08-06"),

    # PROJ-98 tasks
    (t98,  "PROJ-98-1",  "Set up OAuth2 provider config (Google + GitHub)",  "carol",  "in_progress", 3.0, "dev",  "2026-08-01", "2026-08-01"),
    (t98,  "PROJ-98-2",  "Migrate user auth middleware to token-based",      "carol",  "todo",        5.0, "dev",  "2026-08-02", "2026-08-03"),
    (t98,  "PROJ-98-3",  "Build TOTP MFA enrolment + verification flow",     "dave",   "todo",        4.0, "dev",  "2026-08-04", "2026-08-04"),
    (t98,  "PROJ-98-4",  "Force MFA prompt on first post-migration login",   "carol",  "todo",        2.0, "dev",  "2026-08-05", "2026-08-05"),
    (t98,  "PROJ-98-5",  "Update API gateway JWT validation",                "dave",   "todo",        3.0, "dev",  "2026-08-06", "2026-08-06"),

    # PROJ-95 tasks (done)
    (t95,  "PROJ-95-1",  "Add server-side pagination to dashboard API",      "alice",  "done",        4.0, "dev",  "2026-07-15", "2026-07-15"),
    (t95,  "PROJ-95-2",  "Lazy-load chart data via WebSocket stream",        "bob",    "done",        5.0, "dev",  "2026-07-16", "2026-07-17"),
    (t95,  "PROJ-95-3",  "Add Redis caching layer for aggregation queries",  "carol",  "done",        4.0, "dev",  "2026-07-18", "2026-07-18"),
    (t95,  "PROJ-95-4",  "Load testing with k6 — 100k row dataset",         "dave",   "done",        2.0, "dev",  "2026-07-21", "2026-07-21"),

    # PROJ-110 tasks
    (t110, "PROJ-110-1", "Set up SendGrid SDK + account config",             "alice",  "todo",        2.0, "dev",  "2026-08-07", "2026-08-07"),
    (t110, "PROJ-110-2", "Design transactional email templates (HTML)",      "bob",    "todo",        3.0, "dev",  "2026-08-07", "2026-08-07"),
    (t110, "PROJ-110-3", "Build notification preferences API + UI",          "carol",  "todo",        4.0, "dev",  "2026-08-08", "2026-08-08"),
]
conn.executemany(
    "INSERT INTO tasks (ticket_id,jira_task_key,title,assignee,status,estimated_hrs,task_type,start_date,end_date) "
    "VALUES (?,?,?,?,?,?,?,?,?)",
    tasks,
)

# ── Documents ─────────────────────────────────────────────────────────
print("Seeding documents...")

desc_101 = """\
## Summary
Integrate Stripe as the primary payment gateway in the checkout service, with
PayPal as an automatic fallback. Support web and mobile flows, multi-currency
(USD / EUR / GBP), card token storage for repeat purchases, and SCA/3DS for EU.

## Acceptance Criteria
- Stripe charges succeed end-to-end on web and mobile
- If Stripe returns a 5xx, checkout transparently retries via PayPal
- Card tokens stored in Vault; raw PANs never logged
- EU customers receive 3DS challenge when required
- All new endpoints covered by unit tests (≥ 85% branch coverage)

## Technical Notes
- Use `stripe-python` SDK v7+; wrap in `PaymentService` facade
- PayPal SDK v2 for fallback; share `PaymentResult` return type
- PCI-DSS: no card data in application logs
- Add `stripe_webhook_secret` to settings for webhook signature validation
"""

sdd_101 = """\
# Software Design Document — PROJ-101 Payment Gateway Integration

## Overview
Add Stripe as the primary processor and PayPal as fallback inside a new
`PaymentService` class. The existing `CheckoutController` delegates to
`PaymentService`; no other callers change.

## Affected Components
| Component | Change |
|---|---|
| `services/payment_service.py` | New file — Stripe + PayPal logic |
| `controllers/checkout.py` | Call `PaymentService.charge()` |
| `models/payment_token.py` | New — encrypted token storage |
| `db/migrations/0042_payment_tokens.sql` | New table |
| `config/settings.py` | Add `STRIPE_KEY`, `PAYPAL_CLIENT_ID/SECRET` |

## Data Flow
```
Client → CheckoutController.process()
           → PaymentService.charge(amount, token, currency, region)
               → StripeClient.charge()   [primary]
               → [on 5xx] PayPalClient.charge()  [fallback]
           → PaymentToken.store(vault_token)
           → OrderService.confirm()
```

## API Changes
`POST /api/checkout` gains optional `save_card: bool` field.
Response adds `payment_method: "stripe"|"paypal"`.

## Error Handling
Stripe 4xx → surface to user (card declined, insufficient funds).
Stripe 5xx → log + retry PayPal silently; surface PayPal errors to user.
Network timeout (10s) on both providers.

## Security Considerations
- API keys in env vars; never in source
- Stripe webhook signature validated with `stripe.Webhook.construct_event`
- Card tokens stored AES-256 encrypted in `payment_tokens` table
"""

docs = [
    (t101, "formatted_desc", desc_101),
    (t101, "sdd",            sdd_101),
    (t98,  "formatted_desc", "## Summary\nOAuth2 migration replacing legacy session auth. Google and GitHub as providers. "
                              "TOTP MFA enforced on first post-migration login.\n\n## Acceptance Criteria\n"
                              "- Google and GitHub OAuth flows work end-to-end\n- MFA enrolment prompted on first login\n"
                              "- Legacy password endpoints removed\n- JWT expiry and refresh implemented"),
    (t95,  "formatted_desc", "## Summary\nDashboard performance optimisation delivering <2s load for 100k-row datasets "
                              "via server-side pagination, Redis caching, and lazy chart loading.\n\n"
                              "## Acceptance Criteria\n- p95 load time < 2s under k6 100k-row test\n"
                              "- Pagination cursor-based (no OFFSET)\n- Charts load on demand via WebSocket"),
]
conn.executemany(
    "INSERT INTO documents (ticket_id,doc_type,content) VALUES (?,?,?)", docs
)

# ── Diagrams ──────────────────────────────────────────────────────────
print("Seeding diagrams...")
mermaid_101 = """\
graph TD
    Client([Web / Mobile Client])
    CC[CheckoutController]
    PS[PaymentService]
    SC[StripeClient]
    PC[PayPalClient]
    PT[(PaymentTokens DB)]
    OS[OrderService]

    Client -->|POST /api/checkout| CC
    CC --> PS
    PS -->|primary| SC
    PS -->|fallback on 5xx| PC
    PS --> PT
    PS --> OS
    SC -->|stripe-python SDK| Stripe((Stripe API))
    PC -->|paypalrestsdk| PayPal((PayPal API))
"""

mermaid_98 = """\
graph TD
    User([User])
    AG[API Gateway]
    AS[AuthService]
    GP[Google Provider]
    GHP[GitHub Provider]
    MFA[MFA / TOTP Service]
    DB[(Users DB)]

    User -->|OAuth redirect| AG
    AG --> AS
    AS -->|OIDC| GP
    AS -->|OIDC| GHP
    AS --> MFA
    AS --> DB
    AG -->|JWT| User
"""

conn.executemany(
    "INSERT INTO diagrams (ticket_id,mermaid_src,drawio_xml,confluence_page_url) VALUES (?,?,?,?)",
    [
        (t101, mermaid_101, "<mxGraphModel/>", "https://confluence.example.com/pages/101"),
        (t98,  mermaid_98,  "<mxGraphModel/>", ""),
    ],
)

# ── Test files ────────────────────────────────────────────────────────
print("Seeding test files...")
test_files = [
    (t101, "test_payment_service.py",
     """\
import pytest
from unittest.mock import patch, MagicMock
from services.payment_service import PaymentService


def test_charge_success_via_stripe():
    with patch("services.payment_service.StripeClient.charge") as mock:
        mock.return_value = {"status": "succeeded", "id": "ch_test123"}
        result = PaymentService().charge(1000, "tok_visa", "USD", "US")
    assert result["payment_method"] == "stripe"
    assert result["status"] == "succeeded"


def test_charge_fallback_to_paypal_on_stripe_5xx():
    with patch("services.payment_service.StripeClient.charge", side_effect=Exception("503")):
        with patch("services.payment_service.PayPalClient.charge") as pp:
            pp.return_value = {"status": "completed", "id": "pp_test456"}
            result = PaymentService().charge(1000, "tok_visa", "USD", "US")
    assert result["payment_method"] == "paypal"


def test_charge_stores_token_when_save_card():
    with patch("services.payment_service.StripeClient.charge") as sc:
        with patch("services.payment_service.PaymentToken.store") as pt:
            sc.return_value = {"status": "succeeded", "vault_token": "vt_abc"}
            PaymentService().charge(500, "tok_mc", "EUR", "DE", save_card=True)
    pt.assert_called_once()


def test_sca_triggered_for_eu_customer():
    with patch("services.payment_service.StripeClient.charge") as sc:
        sc.return_value = {"status": "requires_action", "next_action": {"type": "use_stripe_sdk"}}
        result = PaymentService().charge(200, "tok_eu", "EUR", "DE")
    assert result["status"] == "requires_action"
"""),
    (t101, "test_stripe_client.py",
     """\
import pytest
from unittest.mock import patch
from services.stripe_client import StripeClient


def test_charge_builds_correct_payload():
    with patch("stripe.PaymentIntent.create") as mock:
        mock.return_value = MagicMock(status="succeeded", id="pi_1")
        StripeClient(api_key="sk_test").charge(999, "tok_visa", "usd")
    mock.assert_called_once()
    call_kwargs = mock.call_args[1]
    assert call_kwargs["amount"] == 999
    assert call_kwargs["currency"] == "usd"


def test_charge_raises_on_card_error():
    import stripe
    with patch("stripe.PaymentIntent.create", side_effect=stripe.error.CardError("declined", None, None)):
        with pytest.raises(Exception, match="declined"):
            StripeClient(api_key="sk_test").charge(100, "tok_bad", "usd")
"""),
    (t98, "test_auth_service.py",
     """\
import pytest
from unittest.mock import patch, MagicMock
from services.auth_service import AuthService


def test_google_oauth_returns_jwt():
    with patch("services.auth_service.GoogleOIDCClient.exchange") as mock:
        mock.return_value = {"sub": "g_123", "email": "user@gmail.com"}
        token = AuthService().login_with_provider("google", code="auth_code")
    assert token is not None


def test_mfa_enforced_on_first_login():
    svc = AuthService()
    with patch.object(svc, "_is_mfa_enrolled", return_value=False):
        result = svc.post_login_checks(user_id=42)
    assert result["require_mfa_enrolment"] is True


def test_jwt_contains_expected_claims():
    with patch("services.auth_service.GoogleOIDCClient.exchange") as mock:
        mock.return_value = {"sub": "g_999", "email": "dev@example.com"}
        token = AuthService().login_with_provider("google", code="code")
    import jwt
    payload = jwt.decode(token, options={"verify_signature": False})
    assert "sub" in payload
    assert "exp" in payload
"""),
]
conn.executemany(
    "INSERT INTO test_files (ticket_id,filename,content,coverage_pct) VALUES (?,?,?,?)",
    [(t, f, c, 82.0) for t, f, c in test_files],
)

# ── Sprint ────────────────────────────────────────────────────────────
print("Seeding sprint...")
conn.execute(
    "INSERT INTO sprints (jira_sprint_id,name,start_date,end_date,dev_days,test_days) "
    "VALUES (?,?,?,?,?,?)",
    ("42", "Q3 Sprint 4 — Payment & Auth Hardening", "2026-08-01", "2026-08-14", 8, 2),
)
conn.commit()
sprint_id = conn.execute("SELECT id FROM sprints ORDER BY id DESC LIMIT 1").fetchone()[0]

# VOC links
conn.executemany(
    "INSERT INTO voc_links (sprint_id,voc_jira_key,linked_task_id,notes,logged_hrs) VALUES (?,?,?,?,?)",
    [
        (sprint_id, "VOC-22", None, "Slow checkout on mobile Safari — linked to payment work", 1.5),
        (sprint_id, "VOC-18", None, "Login fails after 30 min session — auth revamp will fix", 0.5),
    ],
)

# ── Pull Requests ─────────────────────────────────────────────────────
print("Seeding pull requests...")
diff_101 = """\
diff --git a/services/payment_service.py b/services/payment_service.py
new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/services/payment_service.py
@@ -0,0 +1,42 @@
+import stripe
+import logging
+from config import settings
+
+logger = logging.getLogger(__name__)
+
+
+class StripeClient:
+    def charge(self, amount, token, currency):
+        resp = stripe.PaymentIntent.create(
+            amount=amount,
+            currency=currency,
+            payment_method=token,
+            confirm=True,
+        )
+        return resp
+
+
+class PayPalClient:
+    def charge(self, amount, token, currency):
+        import requests
+        resp = requests.post(
+            f"{settings.PAYPAL_URL}/v2/checkout/orders",
+            json={"amount": {"value": amount/100, "currency_code": currency}},
+            headers={"Authorization": f"Bearer {settings.PAYPAL_TOKEN}"},
+        )
+        return resp.json()
+
+
+class PaymentService:
+    def charge(self, amount, token, currency, region, save_card=False):
+        try:
+            result = StripeClient().charge(amount, token, currency)
+            result["payment_method"] = "stripe"
+        except Exception as e:
+            logger.warning(f"Stripe failed: {e}, falling back to PayPal")
+            result = PayPalClient().charge(amount, token, currency)
+            result["payment_method"] = "paypal"
+        return result
"""

diff_98 = """\
diff --git a/services/auth_service.py b/services/auth_service.py
index 1111111..2222222 100644
--- a/services/auth_service.py
+++ b/services/auth_service.py
@@ -1,20 +1,55 @@
-import hashlib
-from db import users
+import jwt
+import time
+from services.google_oidc import GoogleOIDCClient
+from services.github_oidc import GitHubOIDCClient
+from services.mfa_service import TOTPService
+from db import users
+
+
+class AuthService:
+    def login_with_provider(self, provider: str, code: str) -> str:
+        if provider == "google":
+            profile = GoogleOIDCClient().exchange(code)
+        elif provider == "github":
+            profile = GitHubOIDCClient().exchange(code)
+        else:
+            raise ValueError(f"Unknown provider: {provider}")
+        user = users.upsert(profile["sub"], profile["email"], provider)
+        return self._issue_jwt(user)
+
+    def post_login_checks(self, user_id: int) -> dict:
+        if not self._is_mfa_enrolled(user_id):
+            return {"require_mfa_enrolment": True}
+        return {}
+
+    def _is_mfa_enrolled(self, user_id: int) -> bool:
+        return users.get(user_id).get("mfa_secret") is not None
+
+    def _issue_jwt(self, user: dict) -> str:
+        payload = {"sub": user["id"], "exp": int(time.time()) + 3600}
+        return jwt.encode(payload, "secret", algorithm="HS256")
"""

prs = [
    ("PROJ/backend", 47, "Add Stripe payment service + PayPal fallback",
     "alice.dev", "feature/PROJ-101-stripe", "main", diff_101, "new"),
    ("PROJ/backend", 45, "OAuth2 migration: replace session auth with JWT",
     "carol.dev", "feature/PROJ-98-oauth", "main", diff_98, "reviewing"),
    ("PROJ/mobile",  12, "Update checkout UI for new payment API",
     "bob.dev", "feature/PROJ-101-mobile-ui", "main",
     "diff --git a/src/checkout/PaymentScreen.tsx b/src/checkout/PaymentScreen.tsx\n"
     "+  const result = await api.post('/api/checkout', { amount, token, save_card: saveCard });\n",
     "new"),
]
conn.executemany(
    "INSERT INTO pull_requests (repo_slug,pr_id,title,author,source_branch,target_branch,diff_text,status) "
    "VALUES (?,?,?,?,?,?,?,?)",
    prs,
)
conn.commit()

# PR review comments for PR #47
pr47_id = conn.execute("SELECT id FROM pull_requests WHERE pr_id=47").fetchone()[0]
comments_47 = [
    (pr47_id, "services/payment_service.py",  9,
     "No timeout is set on the HTTP request inside PayPalClient.charge(). "
     "Omitting a timeout allows the call to block indefinitely under network congestion, "
     "causing request threads to pile up. Set `timeout=(5, 30)` (connect, read).", 1),
    (pr47_id, "services/payment_service.py", 23,
     "The PayPal response is not validated for HTTP error status before returning. "
     "A 4xx or 5xx from PayPal will be silently returned as a successful result. "
     "Call `resp.raise_for_status()` after the POST.", 1),
    (pr47_id, "services/payment_service.py", 33,
     "The broad `except Exception` catch masks all Stripe errors equally. "
     "Card-declined errors (4xx) should surface to the caller rather than falling back "
     "to PayPal — a declined card will also be declined by PayPal. "
     "Catch only `stripe.error.APIConnectionError` and `stripe.error.APIError` for fallback.", 0),
    (pr47_id, "services/payment_service.py", 38,
     "The warning log includes `{e}` which may contain PII (e.g. card-holder name from "
     "Stripe error messages). Sanitise the log line or use a generic message.", 0),
]
conn.executemany(
    "INSERT INTO pr_review_comments (pr_id,file_path,line_num,comment,approved) VALUES (?,?,?,?,?)",
    comments_47,
)

# ── Bug analyses ──────────────────────────────────────────────────────
print("Seeding bug analyses...")
import json as _json
bug_analyses = [
    (
        "BUG-204",
        "Checkout fails on mobile Safari — SameSite cookie issue",
        "When user taps Pay on Safari iOS 17, the request fails with a 422 error. "
        "The session cookie is rejected by Safari due to missing SameSite attribute.",
        "/Users/me/projects/backend",
        "PaymentController.process() at src/controllers/payment.py:84 sets the session cookie "
        "without SameSite=None; Secure, which Safari 17+ requires for cross-site contexts.",
        _json.dumps([{
            "file": "src/controllers/payment.py",
            "lines": "84",
            "change": "Add SameSite=None; Secure to Set-Cookie response header",
            "before": "response.set_cookie('sess', value)",
            "after":  "response.set_cookie('sess', value, samesite='None', secure=True)",
        }]),
        _json.dumps([{
            "test_file": "tests/test_payment_controller.py",
            "test_name": "test_process_cookie_header",
            "risk": "may_fail",
            "reason": "Assertion checks exact cookie header string; new attributes will break match.",
        }]),
        "analysed",
    ),
    (
        "BUG-198",
        "NullPointerException in dashboard aggregation on empty dataset",
        "When a new account has no transactions, the dashboard crashes with NullPointerException "
        "inside DashboardService.aggregate() at line 57.",
        "/Users/me/projects/backend",
        "DashboardService.aggregate() calls .first() on the query result without checking for None. "
        "Empty accounts return None which is then accessed without a null check.",
        _json.dumps([{
            "file": "src/services/dashboard_service.py",
            "lines": "57",
            "change": "Add None guard before accessing query result",
            "before": "row = query.first()\nreturn row.total",
            "after":  "row = query.first()\nif row is None:\n    return 0\nreturn row.total",
        }]),
        _json.dumps([]),
        "analysed",
    ),
]
conn.executemany(
    "INSERT INTO bug_analyses (jira_key,title,description,codebase_path,root_cause,fix_plan_json,test_impact_json,status) "
    "VALUES (?,?,?,?,?,?,?,?)",
    bug_analyses,
)

# ── Bug counts (dashboard widget) ─────────────────────────────────────
print("Seeding bug counts...")
conn.executemany(
    "INSERT INTO bug_counts (project_key,period_days,total,open,in_progress,resolved) VALUES (?,?,?,?,?,?)",
    [
        ("PROJ", 30, 18, 5, 3, 10),
        ("PROJ",  7,  4, 2, 1,  1),
    ],
)

conn.commit()
print()
print("✓ Sample data seeded successfully.")
print("  Run:  python main.py")
print()
print("  Tickets : PROJ-101 (ready), PROJ-98 (in_progress), PROJ-95 (posted), PROJ-110 (draft)")
print("  Sprint  : Q3 Sprint 4 — 2026-08-01 → 2026-08-14  (8 dev / 2 test days)")
print("  PRs     : #47 PROJ/backend (new, 4 review comments), #45 (reviewing), #12 PROJ/mobile (new)")
print("  Bugs    : BUG-204 (Safari cookie), BUG-198 (NullPointer dashboard)")
