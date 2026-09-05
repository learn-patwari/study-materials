import os
from datetime import datetime, date, timedelta

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

from models import db, Project, Contact, OnCallSchedule, MaintenanceWindow, AlertLog
import notifier

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///oncall.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()


# ── Severity → Priority mapping (mirrors PagerDuty / OpsGenie conventions) ───
SEVERITY_PRIORITY = {
    "critical": "P1",
    "p1": "P1",
    "high": "P1",
    "warning": "P2",
    "p2": "P2",
    "medium": "P2",
    "info": "P3",
    "p3": "P3",
    "low": "P3",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_oncall_contact(project_id: int, for_date: date):
    """Return the Contact on-call for a given date, or None."""
    schedule = OnCallSchedule.query.filter(
        OnCallSchedule.project_id == project_id,
        OnCallSchedule.start_date <= for_date,
        OnCallSchedule.end_date >= for_date,
    ).first()
    return schedule.contact if schedule else None


def is_in_maintenance(project_id: int, at: datetime = None) -> bool:
    at = at or datetime.utcnow()
    return MaintenanceWindow.query.filter(
        MaintenanceWindow.project_id == project_id,
        MaintenanceWindow.start_dt <= at,
        MaintenanceWindow.end_dt >= at,
    ).first() is not None


def check_oncall_gaps():
    """Run daily: notify admins of any project missing on-call for tomorrow."""
    with app.app_context():
        tomorrow = date.today() + timedelta(days=1)
        for project in Project.query.all():
            contact = get_oncall_contact(project.id, tomorrow)
            if contact is None:
                msg = (
                    f"[OnCall Alert] Project '{project.name}' has NO on-call "
                    f"engineer scheduled for {tomorrow.strftime('%d %b %Y')}. "
                    f"Please assign someone immediately."
                )
                try:
                    notifier.send_p2_sms(project.admin_phone, msg)
                except Exception as e:
                    print(f"Gap notify failed for {project.name}: {e}")

                log = AlertLog(
                    project_id=project.id,
                    alert_name="No On-Call Scheduled",
                    severity="warning",
                    priority="P2",
                    action_taken="sms",
                    target_phone=project.admin_phone,
                    status="sent",
                    details=f"No on-call for {tomorrow}",
                )
                db.session.add(log)
        db.session.commit()


scheduler = BackgroundScheduler()
scheduler.add_job(check_oncall_gaps, "cron", hour=8, minute=0)  # run at 08:00 UTC daily
scheduler.start()


# ── Project routes ────────────────────────────────────────────────────────────

@app.route("/api/projects", methods=["GET"])
def list_projects():
    return jsonify([p.to_dict() for p in Project.query.order_by(Project.name).all()])


@app.route("/api/projects", methods=["POST"])
def create_project():
    d = request.get_json()
    p = Project(
        name=d["name"],
        admin_name=d["admin_name"],
        admin_phone=d["admin_phone"],
        admin_email=d.get("admin_email", ""),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201


@app.route("/api/projects/<int:pid>", methods=["PUT"])
def update_project(pid):
    p = Project.query.get_or_404(pid)
    d = request.get_json()
    for field in ("name", "admin_name", "admin_phone", "admin_email", "alerts_enabled"):
        if field in d:
            setattr(p, field, d[field])
    db.session.commit()
    return jsonify(p.to_dict())


@app.route("/api/projects/<int:pid>", methods=["DELETE"])
def delete_project(pid):
    p = Project.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"deleted": pid})


# ── Alert toggle ──────────────────────────────────────────────────────────────

@app.route("/api/projects/<int:pid>/alerts", methods=["POST"])
def toggle_alerts(pid):
    p = Project.query.get_or_404(pid)
    d = request.get_json()
    p.alerts_enabled = bool(d.get("enabled", True))
    db.session.commit()
    return jsonify({"alerts_enabled": p.alerts_enabled})


# ── Contact routes ────────────────────────────────────────────────────────────

@app.route("/api/projects/<int:pid>/contacts", methods=["GET"])
def list_contacts(pid):
    return jsonify([c.to_dict() for c in Contact.query.filter_by(project_id=pid).all()])


@app.route("/api/projects/<int:pid>/contacts", methods=["POST"])
def add_contact(pid):
    Project.query.get_or_404(pid)
    d = request.get_json()
    c = Contact(project_id=pid, name=d["name"], phone=d["phone"], email=d.get("email", ""))
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


@app.route("/api/contacts/<int:cid>", methods=["DELETE"])
def delete_contact(cid):
    c = Contact.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    return jsonify({"deleted": cid})


# ── Schedule routes ───────────────────────────────────────────────────────────

@app.route("/api/projects/<int:pid>/schedules", methods=["GET"])
def list_schedules(pid):
    rows = OnCallSchedule.query.filter_by(project_id=pid).all()
    return jsonify([r.to_dict() for r in rows])


@app.route("/api/projects/<int:pid>/schedules", methods=["POST"])
def add_schedule(pid):
    Project.query.get_or_404(pid)
    d = request.get_json()
    s = OnCallSchedule(
        project_id=pid,
        contact_id=int(d["contact_id"]),
        start_date=date.fromisoformat(d["start_date"]),
        end_date=date.fromisoformat(d["end_date"]),
    )
    db.session.add(s)
    db.session.commit()
    return jsonify(s.to_dict()), 201


@app.route("/api/schedules/<int:sid>", methods=["DELETE"])
def delete_schedule(sid):
    s = OnCallSchedule.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"deleted": sid})


# ── Maintenance window routes ─────────────────────────────────────────────────

@app.route("/api/projects/<int:pid>/maintenance", methods=["GET"])
def list_maintenance(pid):
    rows = MaintenanceWindow.query.filter_by(project_id=pid).all()
    return jsonify([r.to_dict() for r in rows])


@app.route("/api/projects/<int:pid>/maintenance", methods=["POST"])
def add_maintenance(pid):
    Project.query.get_or_404(pid)
    d = request.get_json()
    # datetime-local sends "YYYY-MM-DDTHH:MM" (no seconds); fromisoformat needs seconds
    def parse_dt(s):
        s = s.replace("T", " ")
        if len(s) == 16:
            s += ":00"
        return datetime.fromisoformat(s)

    m = MaintenanceWindow(
        project_id=pid,
        start_dt=parse_dt(d["start_dt"]),
        end_dt=parse_dt(d["end_dt"]),
        reason=d.get("reason", ""),
    )
    db.session.add(m)
    db.session.commit()
    return jsonify(m.to_dict()), 201


@app.route("/api/maintenance/<int:mid>", methods=["DELETE"])
def delete_maintenance(mid):
    m = MaintenanceWindow.query.get_or_404(mid)
    db.session.delete(m)
    db.session.commit()
    return jsonify({"deleted": mid})


# ── Alert log ─────────────────────────────────────────────────────────────────

@app.route("/api/projects/<int:pid>/logs", methods=["GET"])
def list_logs(pid):
    rows = AlertLog.query.filter_by(project_id=pid).order_by(AlertLog.created_at.desc()).limit(100).all()
    return jsonify([r.to_dict() for r in rows])


# ── Grafana webhook receiver ──────────────────────────────────────────────────

@app.route("/grafana/webhook/<int:pid>", methods=["POST"])
def grafana_webhook(pid):
    """
    Configure this URL as a Grafana Contact Point (Webhook).
    Grafana POSTs JSON with alerts[] array. Each alert has labels.severity.
    """
    project = Project.query.get_or_404(pid)
    payload = request.get_json(silent=True) or {}

    alerts = payload.get("alerts", [])
    if not alerts:
        # Some Grafana versions put data at root
        alerts = [payload]

    responses = []
    now = datetime.utcnow()

    for alert in alerts:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        alert_name = labels.get("alertname") or alert.get("title", "Unknown Alert")
        raw_severity = (
            labels.get("severity")
            or labels.get("priority")
            or annotations.get("severity")
            or "warning"
        ).lower()

        priority = SEVERITY_PRIORITY.get(raw_severity, "P2")
        details = annotations.get("summary") or annotations.get("description") or ""

        # Check: alerts disabled for this project?
        if not project.alerts_enabled:
            _log(project.id, alert_name, raw_severity, priority, "disabled", None, "suppressed", "Alerts disabled for project")
            responses.append({"alert": alert_name, "status": "suppressed", "reason": "alerts_disabled"})
            continue

        # Check: active maintenance window?
        if is_in_maintenance(project.id, now):
            _log(project.id, alert_name, raw_severity, priority, "maintenance", None, "suppressed", "In maintenance window")
            responses.append({"alert": alert_name, "status": "suppressed", "reason": "maintenance_window"})
            continue

        # Get on-call contact
        contact = get_oncall_contact(project.id, now.date())
        if contact is None:
            # No on-call → notify admin
            target_phone = project.admin_phone
            msg = f"[{priority}] {alert_name} — No on-call engineer! Admin notified. {details}"
            result = notifier.dispatch(priority, target_phone, f"[NO ONCALL] {alert_name}", details)
            _log(project.id, alert_name, raw_severity, priority, result.get("action"), target_phone, result.get("status", "sent"), "No on-call; admin notified")
        else:
            target_phone = contact.phone
            result = notifier.dispatch(priority, target_phone, alert_name, details)
            _log(project.id, alert_name, raw_severity, priority, result.get("action"), target_phone, result.get("status", "sent"), details)

        responses.append({
            "alert": alert_name,
            "priority": priority,
            "action": result.get("action"),
            "to": target_phone,
            "status": result.get("status"),
        })

    return jsonify({"processed": len(responses), "results": responses})


def _log(project_id, alert_name, severity, priority, action, phone, status, details):
    db.session.add(AlertLog(
        project_id=project_id,
        alert_name=alert_name,
        severity=severity,
        priority=priority,
        action_taken=action,
        target_phone=phone,
        status=status,
        details=details,
    ))
    db.session.commit()


# ── UI ────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
