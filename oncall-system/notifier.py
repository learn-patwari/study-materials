"""
Priority-based notification dispatcher.

P1  → Phone call (Twilio voice / Exotel)
P2  → SMS (Twilio SMS / Exotel SMS)
P3  → Knox message (Samsung Knox webhook) or fallback webhook
"""
import os
import time
import threading
import requests

PROVIDER = os.getenv("PROVIDER", "twilio")

# ── Twilio helpers ────────────────────────────────────────────────────────────

def _twilio_client():
    from twilio.rest import Client
    return Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))


def _twilio_call(to: str, message: str) -> dict:
    client = _twilio_client()
    twiml = f"<Response><Say>{message}</Say><Pause length='2'/><Say>{message}</Say></Response>"
    call = client.calls.create(
        to=to,
        from_=os.getenv("TWILIO_CALLER_ID"),
        twiml=twiml,
    )
    return {"sid": call.sid, "status": call.status}


def _twilio_sms(to: str, message: str) -> dict:
    client = _twilio_client()
    msg = client.messages.create(
        to=to,
        from_=os.getenv("TWILIO_CALLER_ID"),
        body=message,
    )
    return {"sid": msg.sid, "status": msg.status}


# ── Exotel helpers ────────────────────────────────────────────────────────────

def _exotel_call(to: str, message: str) -> dict:
    sid = os.getenv("EXOTEL_SID")
    key = os.getenv("EXOTEL_API_KEY")
    token = os.getenv("EXOTEL_API_TOKEN")
    subdomain = os.getenv("EXOTEL_SUBDOMAIN", "api.exotel.com")

    resp = requests.post(
        f"https://{key}:{token}@{subdomain}/v1/Accounts/{sid}/Calls/connect.json",
        data={
            "From": to,
            "CallerId": os.getenv("EXOTEL_CALLER_ID"),
            "Url": f"http://my.exotel.com/{sid}/exoml/start_voice/{os.getenv('EXOTEL_APP_ID', '')}",
            "TimeLimit": 30,
            "StatusCallback": os.getenv("BASE_URL", "") + "/api/exotel/callback",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json().get("Call", {})
    return {"sid": data.get("Sid"), "status": data.get("Status")}


def _exotel_sms(to: str, message: str) -> dict:
    sid = os.getenv("EXOTEL_SID")
    key = os.getenv("EXOTEL_API_KEY")
    token = os.getenv("EXOTEL_API_TOKEN")
    subdomain = os.getenv("EXOTEL_SUBDOMAIN", "api.exotel.com")

    resp = requests.post(
        f"https://{key}:{token}@{subdomain}/v1/Accounts/{sid}/Sms/send.json",
        data={
            "From": os.getenv("EXOTEL_CALLER_ID"),
            "To": to,
            "Body": message,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return {"status": "sent"}


# ── Knox P3 ───────────────────────────────────────────────────────────────────

def _knox_message(to_phone: str, message: str) -> dict:
    """
    Samsung Knox Manage push notification.
    Requires KNOX_API_URL and KNOX_API_KEY in env.
    Falls back to a generic webhook if not configured.
    """
    knox_url = os.getenv("KNOX_API_URL")
    knox_key = os.getenv("KNOX_API_KEY")

    if knox_url and knox_key:
        resp = requests.post(
            knox_url,
            headers={"Authorization": f"Bearer {knox_key}", "Content-Type": "application/json"},
            json={"to": to_phone, "message": message, "type": "alert"},
            timeout=10,
        )
        resp.raise_for_status()
        return {"status": "sent", "provider": "knox"}

    # Fallback: generic webhook
    fallback = os.getenv("P3_WEBHOOK_URL")
    if fallback:
        requests.post(fallback, json={"phone": to_phone, "message": message}, timeout=10)
        return {"status": "sent", "provider": "webhook"}

    return {"status": "no_knox_configured"}


# ── Public dispatcher ─────────────────────────────────────────────────────────

def send_p1_call(to: str, message: str) -> dict:
    to = _normalise_india(to)
    if PROVIDER == "exotel":
        return _exotel_call(to, message)
    return _twilio_call(to, message)


def send_p2_sms(to: str, message: str) -> dict:
    to = _normalise_india(to)
    if PROVIDER == "exotel":
        return _exotel_sms(to, message)
    return _twilio_sms(to, message)


def send_p3_knox(to: str, message: str) -> dict:
    return _knox_message(to, message)


def dispatch(priority: str, to_phone: str, alert_name: str, details: str = "") -> dict:
    msg = f"ALERT: {alert_name}. {details}".strip()
    try:
        if priority == "P1":
            return {"action": "call", **send_p1_call(to_phone, msg)}
        elif priority == "P2":
            return {"action": "sms", **send_p2_sms(to_phone, msg)}
        else:
            return {"action": "knox", **send_p3_knox(to_phone, msg)}
    except Exception as e:
        return {"action": priority.lower(), "status": "failed", "error": str(e)}


# ── Util ──────────────────────────────────────────────────────────────────────

def _normalise_india(number: str) -> str:
    number = number.strip().replace(" ", "").replace("-", "")
    if number.startswith("0"):
        return "+91" + number[1:]
    if not number.startswith("+"):
        return "+91" + number
    return number
