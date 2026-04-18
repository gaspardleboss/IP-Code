# =============================================================================
# auth.py — Authentication routes: card validation, login, card registration.
# =============================================================================

import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

from models import db, Student
from services.card_service import validate_card_uid
from utils.logger import get_logger

log = get_logger(__name__)
auth_bp = Blueprint("auth", __name__)


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# POST /api/auth/card — validate a physical RFID card (called by RPi)
# ---------------------------------------------------------------------------
@auth_bp.route("/card", methods=["POST"])
def auth_card():
    """Validate a student card UID; used by the RPi for RFID scans."""
    # Verify station API key
    api_key = request.headers.get("X-Station-Key", "")
    if api_key != current_app.config["STATION_API_KEY"]:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    card_uid = data.get("card_uid", "").strip()
    if not card_uid:
        return jsonify({"error": "card_uid is required"}), 400

    result = validate_card_uid(card_uid)
    if not result["valid"]:
        return jsonify({"valid": False, "reason": result.get("reason")}), 200

    # Issue a short-lived JWT for the student (used by mobile app flows)
    token = create_access_token(identity=str(result["student_id"]))
    return jsonify({
        "valid":          True,
        "student_name":   result["student_name"],
        "student_number": result["student_number"],
        "jwt_token":      token,
    }), 200


# ---------------------------------------------------------------------------
# POST /api/auth/login — student login (mobile app)
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a student using student_number + password."""
    data = request.get_json(silent=True) or {}
    student_number = data.get("student_number", "").strip()
    password       = data.get("password", "")

    if not student_number or not password:
        return jsonify({"error": "student_number and password are required"}), 400

    student = Student.query.filter_by(student_number=student_number, is_active=True).first()
    if not student or not student.password_hash:
        return jsonify({"error": "Invalid credentials"}), 401

    if not check_password_hash(student.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    student.last_login = _utcnow()
    db.session.commit()

    access_token  = create_access_token(identity=str(student.id))
    refresh_token = create_refresh_token(identity=str(student.id))

    log.info("Student logged in: %s", student.student_number)
    return jsonify({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "student":       student.to_dict(),
    }), 200


# ---------------------------------------------------------------------------
# POST /api/auth/refresh — refresh access token
# ---------------------------------------------------------------------------
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity     = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({"access_token": access_token}), 200


# ---------------------------------------------------------------------------
# POST /api/auth/register-card — link RFID card to student account
# ---------------------------------------------------------------------------
@auth_bp.route("/register-card", methods=["POST"])
@jwt_required()
def register_card():
    """
    Associate an RFID card UID with the currently authenticated student.
    The student taps their card on the locker which transmits the UID,
    then the mobile app posts it here after the student is logged in.
    """
    student_id = int(get_jwt_identity())
    data       = request.get_json(silent=True) or {}
    card_uid   = data.get("card_uid", "").strip()

    if not card_uid:
        return jsonify({"error": "card_uid is required"}), 400

    # Ensure no other account owns this card
    existing = Student.query.filter_by(card_uid=card_uid).first()
    if existing and existing.id != student_id:
        return jsonify({"error": "This card is already registered to another account"}), 409

    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    student.card_uid = card_uid
    db.session.commit()
    log.info("Card %s registered for student %d", card_uid, student_id)
    return jsonify({"ok": True, "card_uid": card_uid}), 200


# ---------------------------------------------------------------------------
# POST /api/auth/set-password — set/reset password (admin or first-time)
# ---------------------------------------------------------------------------
@auth_bp.route("/set-password", methods=["POST"])
@jwt_required()
def set_password():
    student_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    new_password = data.get("password", "")

    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    student.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({"ok": True}), 200
