"""Data models.

Privacy design: `Sample` is the anonymized record that feeds the dashboard. It holds
NO phone number, name or exact coordinates (coordinates are rounded to ~1 km).
Exact location only appears in the responder-facing `Alert.message`.
"""
from datetime import datetime, timezone

import bcrypt
from flask_login import UserMixin

from .extension import db, login_manager


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Calibration(db.Model):
    # Table to store the decision thresholds and reference chart hash for each calibration.
    __tablename__ = "calibrations"

    calibration_id = db.Column(db.Integer, primary_key=True)
    thresholds = db.Column(db.JSON, nullable=False)  # JSON object of decision thresholds
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    chart_hash = db.Column(db.String(64), nullable=False)  # SHA256 of the reference chart
    calibrated_by = db.Column(db.String(120), nullable=False)  # name of the person who calibrated

class GuidanceContent(db.Model):
    # Table to store guidance content for each language and content type (safe, risky, unsafe).
    __tablename__ = "guidance_content"

    guidance_id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(4), nullable=False, index=True)  # en | bem | nya
    content_type = db.Column(db.String(16), nullable=False, index=True)  # safe | risky | unsafe
    content = db.Column(db.Text, nullable=False)
    reviewed_by = db.Column(db.String(120), nullable=False)  # name of the person who reviewed
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

class AuditLog(db.Model):
    # Table to store audit logs of user actions for accountability.
    __tablename__ = "audit_logs"

    audit_log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(64), nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False)

class Sample(db.Model):
    # Table to store anonymized water quality test results. This is the main record that feeds the dashboard.
    __tablename__ = "samples"

    sample_id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    channel = db.Column(db.String(8), nullable=False)          # web | ussd | sms
    language = db.Column(db.String(4), nullable=False)         # en | bem | nya
    nitrate_mgl = db.Column(db.Float)
    ph = db.Column(db.Float)
    bacteria_positive = db.Column(db.Boolean)
    result = db.Column(db.String(8), nullable=False, index=True)  # safe | risky | unsafe
    reasons = db.Column(db.String(255), default="")            # comma-separated codes
    lat_coarse = db.Column(db.Float)                           # rounded to 2 decimals
    lon_coarse = db.Column(db.Float)
    district = db.Column(db.String(64))
    rainfall_mm_72h = db.Column(db.Float)
    mining_km = db.Column(db.Float)

    alerts = db.relationship("Alert", backref="sample", lazy=True)


class Responder(db.Model):
    """Community Health Worker or WASH officer who receives Unsafe alerts."""
    # Table to store responders who receive alerts. This table is separate from `User` to allow for different roles and access levels.
    __tablename__ = "responders"

    responder_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(8), nullable=False, index=True)  # chw | wash
    phone = db.Column(db.String(20), nullable=False)            # E.164, e.g. +2609XXXXXXXX
    district = db.Column(db.String(64), index=True)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    active = db.Column(db.Boolean, default=True, nullable=False)


class Alert(db.Model):
    """Alert sent to a responder when an Unsafe sample is reported."""
    __tablename__ = "alerts"

    alert_id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey("samples.sample_id"), nullable=False)
    responder_id = db.Column(db.Integer, db.ForeignKey("responders.responder_id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(8), nullable=False)            # sent | failed
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    
    # Relationship to Responder
    responder = db.relationship("Responder")


class User(UserMixin, db.Model):
    # Table to store users who can log in to the dashboard/admin interface. This is separate from `Responder` to allow for different roles and access levels.
    """Dashboard/admin login for Council, WWF, Ministry and project staff."""
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.LargeBinary(60), nullable=False)
    role = db.Column(db.String(8), nullable=False, default="viewer")  # viewer | admin

    # Password handling
    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.password_hash)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))
