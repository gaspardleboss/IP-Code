# =============================================================================
# admin.py — Administration endpoints: student import, reports, maintenance.
# =============================================================================

import csv
import io
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from werkzeug.security import generate_password_hash

from models import db, Student, Slot, Session, SlotLog, Battery
from utils.logger import get_logger

log = get_logger(__name__)
admin_bp = Blueprint("admin", __name__)


# ---------------------------------------------------------------------------
# Shared: require the station API key for admin endpoints
# ---------------------------------------------------------------------------
def _require_admin():
    """Allow either the station key or a future admin JWT (extend as needed)."""
    key = request.headers.get("X-Station-Key", "")
    return key == current_app.config["STATION_API_KEY"]


# ---------------------------------------------------------------------------
# POST /api/admin/students/import — CSV bulk upload
# ---------------------------------------------------------------------------
@admin_bp.route("/students/import", methods=["POST"])
def import_students_csv():
    """
    Upload a CSV file with columns: student_number, name, email
    (email is optional). Upserts all rows into the Student table.
    This is the primary adaptation point for any institution.
    """
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded — use multipart/form-data with field 'file'"}), 400

    file = request.files["file"]
    try:
        content = file.stream.read().decode("utf-8-sig")  # Handle BOM from Excel exports
        reader  = csv.DictReader(io.StringIO(content))
        created = 0
        updated = 0
        for row in reader:
            student_number = row.get("student_number", "").strip()
            name           = row.get("name", "").strip()
            email          = row.get("email", "").strip() or None
            if not student_number or not name:
                continue   # Skip malformed rows

            existing = Student.query.filter_by(student_number=student_number).first()
            if existing:
                existing.name  = name
                existing.email = email or existing.email
                updated += 1
            else:
                student = Student(student_number=student_number, name=name, email=email)
                db.session.add(student)
                created += 1

        db.session.commit()
        log.info("CSV import: created=%d updated=%d", created, updated)
        return jsonify({"ok": True, "created": created, "updated": updated}), 200

    except Exception as exc:
        db.session.rollback()
        log.error("CSV import failed: %s", exc)
        return jsonify({"error": f"Import failed: {exc}"}), 500


# ---------------------------------------------------------------------------
# POST /api/admin/students/sync-external — JSON push from external system
# ---------------------------------------------------------------------------
@admin_bp.route("/students/sync-external", methods=["POST"])
def sync_external_students():
    """
    Accept a JSON array of student records from any external information system.
    Upserts all rows, making the backend adaptable to any university database.
    Expected format: [{"student_number": "...", "name": "...", "email": "..."}, ...]
    """
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    students_data = request.get_json(silent=True)
    if not isinstance(students_data, list):
        return jsonify({"error": "Expected a JSON array of student objects"}), 400

    created = updated = errors = 0
    for item in students_data:
        student_number = str(item.get("student_number", "")).strip()
        name           = str(item.get("name", "")).strip()
        email          = item.get("email", "")
        if not student_number or not name:
            errors += 1
            continue
        try:
            existing = Student.query.filter_by(student_number=student_number).first()
            if existing:
                existing.name       = name
                existing.email      = email or existing.email
                existing.is_active  = bool(item.get("is_active", True))
                updated += 1
            else:
                s = Student(student_number=student_number, name=name,
                            email=email or None,
                            is_active=bool(item.get("is_active", True)))
                db.session.add(s)
                created += 1
        except Exception as exc:
            errors += 1
            log.warning("sync-external: skipping %s — %s", student_number, exc)

    db.session.commit()
    log.info("External sync: created=%d updated=%d errors=%d", created, updated, errors)
    return jsonify({"ok": True, "created": created, "updated": updated, "errors": errors}), 200


# ---------------------------------------------------------------------------
# GET /api/admin/reports/usage — usage statistics
# ---------------------------------------------------------------------------
@admin_bp.route("/reports/usage", methods=["GET"])
def usage_report():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    total_sessions   = Session.query.count()
    active_sessions  = Session.query.filter_by(status="ACTIVE").count()
    returned         = Session.query.filter_by(status="RETURNED").count()
    overdue          = Session.query.filter_by(status="OVERDUE").count()
    defective_slots  = Slot.query.filter_by(is_defective=True).count()
    total_students   = Student.query.count()
    active_students  = Student.query.filter_by(is_active=True).count()

    return jsonify({
        "total_sessions":  total_sessions,
        "active_sessions": active_sessions,
        "returned":        returned,
        "overdue":         overdue,
        "defective_slots": defective_slots,
        "total_students":  total_students,
        "active_students": active_students,
    }), 200


# ---------------------------------------------------------------------------
# PUT /api/admin/slots/<slot_id>/flag-defective — mark a slot defective
# ---------------------------------------------------------------------------
@admin_bp.route("/slots/<int:slot_id>/flag-defective", methods=["PUT"])
def flag_defective(slot_id: int):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    slot = Slot.query.get(slot_id)
    if not slot:
        return jsonify({"error": "Slot not found"}), 404

    data     = request.get_json(silent=True) or {}
    defective = bool(data.get("defective", True))
    slot.is_defective = defective
    slot.led_state    = "RED" if defective else "OFF"
    log_entry = SlotLog(slot_id=slot_id, event_type="DEFECTIVE_FLAG",
                        details={"defective": defective})
    db.session.add(log_entry)
    db.session.commit()
    log.info("Slot %d marked defective=%s", slot_id, defective)
    return jsonify({"ok": True, "slot_id": slot_id, "defective": defective}), 200


# ---------------------------------------------------------------------------
# DELETE /api/admin/sessions/<session_id>/force-close
# ---------------------------------------------------------------------------
@admin_bp.route("/sessions/<session_id>/force-close", methods=["DELETE"])
def force_close_session(session_id: str):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    session = Session.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    session.end_time = datetime.now(timezone.utc)
    session.status   = "RETURNED"
    db.session.commit()
    log.info("Force-closed session %s", session_id)
    return jsonify({"ok": True, "session_id": session_id}), 200


# ---------------------------------------------------------------------------
# POST /api/admin/batteries — register a new battery
# ---------------------------------------------------------------------------
@admin_bp.route("/batteries", methods=["POST"])
def add_battery():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    uid  = data.get("battery_uid", "").strip()
    if not uid:
        return jsonify({"error": "battery_uid is required"}), 400

    if Battery.query.filter_by(battery_uid=uid).first():
        return jsonify({"error": "Battery UID already exists"}), 409

    battery = Battery(battery_uid=uid, charge_level=data.get("charge_level", 0))
    db.session.add(battery)
    db.session.commit()
    return jsonify(battery.to_dict()), 201
