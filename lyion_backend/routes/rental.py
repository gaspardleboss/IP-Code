# =============================================================================
# rental.py — Rental and return endpoints (called by RPi station and mobile app).
# =============================================================================

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import db, Student, Session, Slot, SlotLog
from services.card_service import validate_card_uid
from services.session_service import (
    find_best_slot,
    create_rental_session,
    close_rental_session,
    get_active_session_for_student,
    get_active_session_for_slot,
)
from utils.logger import get_logger

log = get_logger(__name__)
rental_bp = Blueprint("rental", __name__)


def _require_station_key():
    """Return True if the request carries a valid station API key."""
    api_key = request.headers.get("X-Station-Key", "")
    return api_key == current_app.config["STATION_API_KEY"]


# ---------------------------------------------------------------------------
# POST /api/rent — initiate a rental (RPi or mobile app)
# ---------------------------------------------------------------------------
@rental_bp.route("/rent", methods=["POST"])
def rent():
    """
    Approve a rental request.
    Can be called by:
      - RPi (using X-Station-Key header + card_uid)
      - Mobile app (using JWT + station_id)
    """
    data = request.get_json(silent=True) or {}
    station_id = data.get("station_id") or current_app.config.get("STATION_ID")

    # --- Identify the student ---
    student = None
    if _require_station_key():
        # RPi path: authenticate via card UID
        card_uid = data.get("card_uid", "").strip()
        if not card_uid:
            return jsonify({"error": "card_uid is required"}), 400
        result = validate_card_uid(card_uid)
        if not result["valid"]:
            return jsonify({"error": result.get("reason", "Unauthorized")}), 403
        student = Student.query.get(result["student_id"])
    else:
        # Mobile app path: JWT authentication
        try:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request()
            student_id = int(get_jwt_identity())
            student = Student.query.get(student_id)
        except Exception:
            return jsonify({"error": "Authentication required"}), 401

    if not student or not student.is_active:
        return jsonify({"error": "Student account inactive"}), 403

    # --- Check no active session already exists ---
    existing = get_active_session_for_student(student.id)
    if existing:
        return jsonify({"error": "You already have an active rental"}), 409

    # --- Select best available slot ---
    slot = find_best_slot(station_id)
    if not slot:
        return jsonify({"error": "No batteries available at this station"}), 503

    # --- Create session ---
    session = create_rental_session(student, slot)

    log.info("Rental approved: student=%d slot=%d session=%s",
             student.id, slot.id, session.id)

    return jsonify({
        "slot":           slot.id,
        "session_id":     session.id,
        "battery_uid":    slot.battery.battery_uid if slot.battery else None,
        "battery_charge": slot.battery.charge_level if slot.battery else 0,
    }), 200


# ---------------------------------------------------------------------------
# POST /api/return — confirm a battery return
# ---------------------------------------------------------------------------
@rental_bp.route("/return", methods=["POST"])
def return_battery():
    """Close an active rental session when the battery is returned."""
    if not _require_station_key():
        # Allow mobile app with JWT for remote return requests
        try:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request()
        except Exception:
            return jsonify({"error": "Authentication required"}), 401

    data       = request.get_json(silent=True) or {}
    slot_id    = data.get("slot_id")
    card_uid   = data.get("card_uid", "").strip()
    session_id = data.get("session_id")

    # Find the active session
    session = None
    if session_id:
        session = Session.query.filter_by(id=session_id, status="ACTIVE").first()
    elif slot_id:
        session = get_active_session_for_slot(slot_id)
    elif card_uid:
        result = validate_card_uid(card_uid)
        if result["valid"]:
            session = get_active_session_for_student(result["student_id"])

    if not session:
        return jsonify({"error": "No active session found"}), 404

    slot = Slot.query.get(session.slot_id)
    if not slot:
        return jsonify({"error": "Slot not found"}), 404

    closed = close_rental_session(session, slot)
    log.info("Return confirmed: session=%s slot=%d", closed.id, slot.id)

    return jsonify({
        "ok":          True,
        "session_id":  closed.id,
        "slot_id":     slot.id,
        "deposit_returned": closed.deposit_returned,
    }), 200


# ---------------------------------------------------------------------------
# GET /api/slots/<station_id> — current slot states for a station
# ---------------------------------------------------------------------------
@rental_bp.route("/slots/<station_id>", methods=["GET"])
def get_slots(station_id: str):
    """Return the state of all 24 slots (used by RPi sync and mobile app)."""
    slots = Slot.query.filter_by(station_id=station_id).order_by(Slot.id).all()
    if not slots:
        return jsonify({"error": "Station not found"}), 404
    return jsonify({"station_id": station_id, "slots": [s.to_dict() for s in slots]}), 200
