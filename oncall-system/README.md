# OnCall Manager

Browser-based on-call scheduling and incident routing system for engineering teams in India.  
Integrates with Grafana alerts and dispatches **P1 voice calls / P2 SMS / P3 Knox messages** to the on-call engineer.

---

## Features

- Multi-project on-call management
- Calendar-based rotation scheduling (date ranges per engineer)
- Daily gap detection — SMS admin if no one is on-call tomorrow
- Grafana webhook receiver with automatic P1/P2/P3 routing by severity label
- Maintenance windows — suppress alerts during planned downtime
- Per-project alert toggle (instant disable for migrations/deploys)
- Full alert log with action taken, target, and status

---

## Phone Carrier Support

### Provider 1 — Twilio (Recommended for getting started)

Twilio uses its own carrier network and connects to all Indian mobile and landline numbers via PSTN interconnects with Jio, Airtel, BSNL, Vi, and others.

**India coverage:**

| Number type | Rate (pay-as-you-go) | Notes |
|---|---|---|
| Mobile (Jio, Airtel, Vi, BSNL) | ~$0.05 / min | All networks supported |
| Landline (BSNL, MTNL) | ~$0.07 / min | Supported |
| SMS (all carriers) | ~$0.01 / message | Requires DLT registration |

**Supported carriers (India):**
- Reliance Jio
- Airtel
- Vodafone Idea (Vi)
- BSNL
- MTNL
- Tata Teleservices (limited areas)

**Setup:**
1. Sign up at [console.twilio.com](https://console.twilio.com)
2. Purchase an India or US caller ID number
3. Copy Account SID and Auth Token

**DLT requirement for SMS:**  
TRAI mandates Distributed Ledger Technology (DLT) registration for all commercial SMS in India. For transactional alerts (not marketing), register your sender ID and template on any telecom operator's DLT portal (Jio, Airtel, or Vi). Twilio's India SMS routes through DLT-registered channels.

---

### Provider 2 — Exotel (Best for India — fully TRAI compliant)

Exotel is an India-native cloud telephony provider. It holds its own telecom licenses and interconnects directly with all Indian operators. Billing is in INR.

**India coverage:**

| Number type | Rate | Notes |
|---|---|---|
| Mobile (all operators) | ₹0.50–1.00 / min | Direct carrier interconnect |
| Landline | ₹0.50–1.00 / min | Supported |
| SMS | ₹0.10–0.25 / message | DLT pre-registered |
| Missed call alert | ₹0.10–0.25 / alert | Purpose-built API |

**Supported carriers (India):**
- Reliance Jio
- Airtel
- Vodafone Idea (Vi)
- BSNL / MTNL
- Tata Teleservices
- ACT Fibernet (VoIP lines)

**Why Exotel over Twilio for India:**
- INR billing — no currency conversion
- DLT registration handled by Exotel for SMS
- Dedicated India support team
- Lower latency (servers in Mumbai/Hyderabad)
- Native missed-call API (zero-cost alert pattern)
- Compliant with TRAI anti-spam regulations out of the box

**Setup:**
1. Sign up at [my.exotel.com](https://my.exotel.com)
2. Complete KYC (PAN + business documents)
3. Purchase a virtual number (VN) — 10-digit 0XXXXXXXXXX format
4. Get API Key, API Token, and SID from the dashboard

---

### Provider 3 — P3 Knox / Fallback Webhook

P3 (info-severity) alerts send a push message rather than a call or SMS to reduce noise.

**Samsung Knox (enterprise devices):**  
Used when your organization manages Android devices via Samsung Knox Manage or Knox Platform for Enterprise. Set `KNOX_API_URL` and `KNOX_API_KEY` to push silent notifications to managed devices.

**Generic webhook fallback:**  
If Knox is not configured, P3 alerts POST to any webhook URL — Slack, Microsoft Teams, PagerDuty, custom service, etc. Set `P3_WEBHOOK_URL` to your preferred endpoint.

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd oncall-system
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Choose provider
PROVIDER=twilio           # or "exotel"

# Twilio credentials
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_CALLER_ID=+91XXXXXXXXXX

# Exotel credentials (if using Exotel)
EXOTEL_SID=your_sid
EXOTEL_API_KEY=your_key
EXOTEL_API_TOKEN=your_token
EXOTEL_SUBDOMAIN=api.exotel.com
EXOTEL_CALLER_ID=0XXXXXXXXXX

# P3 alerts — Samsung Knox or fallback webhook
KNOX_API_URL=https://your-knox-server/api/push
KNOX_API_KEY=your_knox_token
P3_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK

# Public URL of this server (for Exotel callbacks)
BASE_URL=https://your-domain.com
```

### 3. Run

```bash
python app.py
```

Open `http://localhost:5001`

---

## Grafana Integration

In Grafana → **Alerting → Contact Points → New → Webhook**, set:

```
URL: http://your-server:5001/grafana/webhook/<project_id>
HTTP Method: POST
```

Add a `severity` label to your Grafana alert rules:

| Label value | Priority | Action |
|---|---|---|
| `critical`, `p1`, `high` | P1 | 📞 Voice call to on-call engineer |
| `warning`, `p2`, `medium` | P2 | 💬 SMS to on-call engineer |
| `info`, `p3`, `low` | P3 | 📱 Knox push / webhook |

**Example Grafana alert rule label:**
```yaml
labels:
  severity: critical    # triggers P1 voice call
  alertname: pod-crash
```

---

## Alert Routing Logic

```
Grafana fires alert
    ↓
Is project alerts_enabled = false?  →  Suppressed (log)
    ↓
Is there an active maintenance window?  →  Suppressed (log)
    ↓
Is there an on-call engineer scheduled today?
    No  →  P2 SMS to project admin ("no on-call scheduled")
    Yes →  Dispatch by priority:
            P1  →  Voice call  (Twilio / Exotel)
            P2  →  SMS         (Twilio / Exotel)
            P3  →  Knox push   (Knox API / webhook)
```

---

## Indian Phone Number Formats

All formats are accepted and normalised automatically:

| Input | Normalised |
|---|---|
| `9876543210` | `+919876543210` |
| `09876543210` | `+919876543210` |
| `+919876543210` | `+919876543210` |

---

## TRAI Compliance Notes

| Requirement | Twilio | Exotel |
|---|---|---|
| DLT registration for SMS | You register manually on a DLT portal | Handled by Exotel |
| Caller ID verification | Provided number must be verified | VN issued directly |
| DND (Do Not Disturb) registry | Check required for non-transactional use | Automated |
| Transactional SMS template | Register on DLT before sending | Pre-approved templates available |

Transactional alert SMS (OTP, incident alerts) have relaxed DND rules compared to promotional SMS. Both providers support this classification.

---

## Directory Structure

```
oncall-system/
├── app.py              # Flask app — all API routes + Grafana webhook
├── models.py           # SQLAlchemy models (Project, Contact, Schedule, etc.)
├── notifier.py         # P1/P2/P3 dispatch (Twilio, Exotel, Knox)
├── requirements.txt
├── .env.example
└── templates/
    └── index.html      # Single-page frontend
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `flask` | Web framework |
| `flask-sqlalchemy` | ORM + SQLite |
| `apscheduler` | Daily gap-check scheduler (08:00 UTC) |
| `twilio` | Twilio Voice + SMS SDK |
| `requests` | Exotel REST calls + Knox webhook |
| `python-dotenv` | `.env` config loading |
