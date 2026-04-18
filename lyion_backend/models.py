# =============================================================================
# models.py — SQLAlchemy ORM models for the Ly-ion PostgreSQL database.
# =============================================================================

import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Student — registered users
# ---------------------------------------------------------------------------
class Student(db.Model):
    __tablename__ = "students"

    id             = db.Column(db.Integer,   primary_key=True, autoincrement=True)
    card_uid       = db.Column(db.String(32), unique=True, nullable=True, index=True)
    student_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name           = db.Column(db.String(120), nullable=False)
    email          = db.Column(db.String(254), unique=True, nullable=True)
    password_hash  = db.Column(db.String(256), nullable=True)
    deposit_balance = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    is_active      = db.Column(db.Boolean, default=True, nullable=False)
    created_at     = db.Column(db.DateTime(timezone=True), default=_utcnow)
    last_login     = db.Column(db.DateTime(timezone=True), nullable=True)

    sessions = db.relationship("Session", back_populates="student", lazy="dynamic")

    def to_dict(self):
        return {
            "id":             self.id,
            "student_number": self.student_number,
            "name":           self.name,
            "email":          self.email,
            "deposit_balance": float(self.deposit_balance),
            "is_active":      self.is_active,
            "card_uid":       self.card_uid,
        }


# ---------------------------------------------------------------------------
# Battery — individual power banks
# ---------------------------------------------------------------------------
class Battery(db.Model):
    __tablename__ = "batteries"

    id              = db.Column(db.Integer,   primary_key=True, autoincrement=True)
    battery_uid     = db.Column(db.String(32), unique=True, nullable=False, index=True)
    charge_level    = db.Column(db.Integer, default=0, nullable=False)   # 0-100 %
    cycle_count     = db.Column(db.Integer, default=0, nullable=False)
    health_status   = db.Column(db.String(16), default="GOOD", nullable=False)
                      # 'GOOD' | 'DEGRADED' | 'DEFECTIVE'
    last_charge_start = db.Column(db.DateTime(timezone=True), nullable=True)
    last_charge_end   = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at        = db.Column(db.DateTime(timezone=True), default=_utcnow)

    slot = db.relationship("Slot", back_populates="battery", uselist=False)

    def to_dict(self):
        return {
            "id":            self.id,
            "battery_uid":   self.battery_uid,
            "charge_level":  self.charge_level,
            "cycle_count":   self.cycle_count,
            "health_status": self.health_status,
        }


# ---------------------------------------------------------------------------
# Station — locker station units
# ---------------------------------------------------------------------------
class Station(db.Model):
    __tablename__ = "stations"

    id             = db.Column(db.String(64), primary_key=True)  # e.g. "station-001"
    location_name  = db.Column(db.String(200), nullable=False)
    qr_code_token  = db.Column(db.String(64), unique=True, nullable=False,
                                default=lambda: str(uuid.uuid4()))
    is_online      = db.Column(db.Boolean, default=False, nullable=False)
    last_heartbeat = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at     = db.Column(db.DateTime(timezone=True), default=_utcnow)

    slots = db.relationship("Slot", back_populates="station", lazy="dynamic")

    def to_dict(self):
        return {
            "id":             self.id,
            "location_name":  self.location_name,
            "qr_code_token":  self.qr_code_token,
            "is_online":      self.is_online,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
        }


# ---------------------------------------------------------------------------
# Slot — physical slot in a station
# ---------------------------------------------------------------------------
class Slot(db.Model):
    __tablename__ = "slots"

    id           = db.Column(db.Integer,   primary_key=True)   # 1-24
    station_id   = db.Column(db.String(64), db.ForeignKey("stations.id"), nullable=False)
    battery_id   = db.Column(db.Integer,    db.ForeignKey("batteries.id"), nullable=True)
    is_locked    = db.Column(db.Boolean, default=True, nullable=False)
    led_state    = db.Column(db.String(10), default="OFF", nullable=False)
    is_defective = db.Column(db.Boolean, default=False, nullable=False)
    last_updated = db.Column(db.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    station  = db.relationship("Station", back_populates="slots")
    battery  = db.relationship("Battery", back_populates="slot")
    sessions = db.relationship("Session", back_populates="slot", lazy="dynamic")
    logs     = db.relationship("SlotLog", back_populates="slot", lazy="dynamic")

    def to_dict(self):
        battery_charge = self.battery.charge_level if self.battery else 0
        return {
            "slot_id":      self.id,
            "station_id":   self.station_id,
            "battery_uid":  self.battery.battery_uid if self.battery else None,
            "battery_id":   self.battery_id,
            "charge_level": battery_charge,
            "is_locked":    self.is_locked,
            "led_state":    self.led_state,
            "is_defective": self.is_defective,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


# ---------------------------------------------------------------------------
# Session — rental session
# ---------------------------------------------------------------------------
class Session(db.Model):
    __tablename__ = "sessions"

    id               = db.Column(db.String(36), primary_key=True,
                                  default=lambda: str(uuid.uuid4()))
    student_id       = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    slot_id          = db.Column(db.Integer, db.ForeignKey("slots.id"),    nullable=False)
    battery_id       = db.Column(db.Integer, db.ForeignKey("batteries.id"), nullable=True)
    start_time       = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    end_time         = db.Column(db.DateTime(timezone=True), nullable=True)
    deposit_held     = db.Column(db.Numeric(10, 2), default=0.00)
    deposit_returned = db.Column(db.Boolean, default=False)
    status           = db.Column(db.String(16), default="ACTIVE", nullable=False)
                       # 'ACTIVE' | 'RETURNED' | 'OVERDUE' | 'LOST'

    student = db.relationship("Student", back_populates="sessions")
    slot    = db.relationship("Slot",    back_populates="sessions")
    battery = db.relationship("Battery")

    def to_dict(self):
        return {
            "id":               self.id,
            "student_id":       self.student_id,
            "slot_id":          self.slot_id,
            "battery_id":       self.battery_id,
            "start_time":       self.start_time.isoformat(),
            "end_time":         self.end_time.isoformat() if self.end_time else None,
            "deposit_held":     float(self.deposit_held),
            "deposit_returned": self.deposit_returned,
            "status":           self.status,
        }


# ---------------------------------------------------------------------------
# SlotLog — audit trail
# ---------------------------------------------------------------------------
class SlotLog(db.Model):
    __tablename__ = "slot_logs"

    id         = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    slot_id    = db.Column(db.Integer,  db.ForeignKey("slots.id"), nullable=False)
    event_type = db.Column(db.String(32), nullable=False)
    timestamp  = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    details    = db.Column(db.JSON, nullable=True)   # JSONB in PostgreSQL

    slot = db.relationship("Slot", back_populates="logs")

    def to_dict(self):
        return {
            "id":         self.id,
            "slot_id":    self.slot_id,
            "event_type": self.event_type,
            "timestamp":  self.timestamp.isoformat(),
            "details":    self.details,
        }
