from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    admin_name = db.Column(db.String(120), nullable=False)
    admin_phone = db.Column(db.String(20), nullable=False)
    admin_email = db.Column(db.String(120), nullable=False)
    alerts_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contacts = db.relationship("Contact", backref="project", lazy=True, cascade="all, delete")
    schedules = db.relationship("OnCallSchedule", backref="project", lazy=True, cascade="all, delete")
    maintenance_windows = db.relationship("MaintenanceWindow", backref="project", lazy=True, cascade="all, delete")
    alert_logs = db.relationship("AlertLog", backref="project", lazy=True, cascade="all, delete")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "admin_name": self.admin_name,
            "admin_phone": self.admin_phone,
            "admin_email": self.admin_email,
            "alerts_enabled": self.alerts_enabled,
            "created_at": self.created_at.isoformat(),
        }


class Contact(db.Model):
    __tablename__ = "contacts"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
        }


class OnCallSchedule(db.Model):
    __tablename__ = "oncall_schedules"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contact = db.relationship("Contact", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "contact_id": self.contact_id,
            "contact_name": self.contact.name if self.contact else None,
            "contact_phone": self.contact.phone if self.contact else None,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }


class MaintenanceWindow(db.Model):
    __tablename__ = "maintenance_windows"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    start_dt = db.Column(db.DateTime, nullable=False)
    end_dt = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "start_dt": self.start_dt.isoformat(),
            "end_dt": self.end_dt.isoformat(),
            "reason": self.reason,
        }


class AlertLog(db.Model):
    __tablename__ = "alert_logs"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    alert_name = db.Column(db.String(255))
    severity = db.Column(db.String(50))
    priority = db.Column(db.String(10))   # P1 / P2 / P3
    action_taken = db.Column(db.String(50))  # call / sms / knox / suppressed
    target_phone = db.Column(db.String(20))
    status = db.Column(db.String(50))     # sent / failed / suppressed
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "alert_name": self.alert_name,
            "severity": self.severity,
            "priority": self.priority,
            "action_taken": self.action_taken,
            "target_phone": self.target_phone,
            "status": self.status,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
        }
