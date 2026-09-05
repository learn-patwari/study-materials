import os
import threading
import time
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PROVIDER = os.getenv("PROVIDER", "twilio")  # "twilio" or "exotel"

# --- Twilio ---
def twilio_missed_call(to_number: str):
    from twilio.rest import Client
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

    call = client.calls.create(
        to=to_number,
        from_=os.getenv("TWILIO_CALLER_ID"),
        twiml="<Response><Pause length='4'/></Response>",  # ring for ~4s then drop
    )

    # Hang up after 5 seconds (missed call)
    def hangup():
        time.sleep(5)
        try:
            client.calls(call.sid).update(status="completed")
        except Exception:
            pass

    threading.Thread(target=hangup, daemon=True).start()
    return call.sid


# --- Exotel ---
def exotel_missed_call(to_number: str):
    import requests as req

    sid = os.getenv("EXOTEL_SID")
    key = os.getenv("EXOTEL_API_KEY")
    token = os.getenv("EXOTEL_API_TOKEN")
    subdomain = os.getenv("EXOTEL_SUBDOMAIN", "api.exotel.com")

    resp = req.post(
        f"https://{key}:{token}@{subdomain}/v1/Accounts/{sid}/Calls/connect.json",
        data={
            "From": to_number,
            "CallerId": os.getenv("EXOTEL_CALLER_ID"),
            "TimeLimit": 4,          # auto-hangup after 4 seconds
            "Url": f"https://{subdomain}/v1/Accounts/{sid}/Calls/applet.xml?version=1&CallType=trans",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("Call", {}).get("Sid", "unknown")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/alert", methods=["POST"])
def send_alert():
    data = request.get_json(silent=True) or {}
    number = (data.get("number") or "").strip()

    if not number:
        return jsonify({"error": "number is required"}), 400

    # Normalise to E.164 for India
    if number.startswith("0"):
        number = "+91" + number[1:]
    elif not number.startswith("+"):
        number = "+91" + number

    try:
        if PROVIDER == "exotel":
            sid = exotel_missed_call(number)
        else:
            sid = twilio_missed_call(number)

        return jsonify({"status": "alert_sent", "call_sid": sid, "to": number})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
