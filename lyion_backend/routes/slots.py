# =============================================================================
# slots.py — Slot management routes.
# =============================================================================

from flask import Blueprint, request, jsonify, current_app
from models import db, Slot, SlotLog
from utils.logger import get_logger

log = get_logger(__name__)
slots_bp = Blueprint("slots", __name__)


def _require_station_key():
    return request.headers.get("X-Station-Key", "") == current_app.config["STATION_API_KEY"]


# GET /api/slots/<station_id> is in rental.py (co-located with the data flow)

# ---------------------------------------------------------------------------
# GET /api/slots/<station_id>/<int:slot_id> — single slot detail
# ---------------------------------------------------------------------------
@slots_bp.route("/slots/<station_id>/<int:slot_id>", methods=["GET"])
def get_slot(station_id: str, slot_id: int):
    slot = Slot.query.filter_by(station_id=station_id, id=slot_id).first()
    if not slot:
        return jsonify({"error": "Slot not found"}), 404
    return jsonify(slot.to_dict()), 200


# ---------------------------------------------------------------------------
# GET /api/slots/<station_id>/<int:slot_id>/logs — slot audit log
# ---------------------------------------------------------------------------
@slots_bp.route("/slots/<station_id>/<int:slot_id>/logs", methods=["GET"])
def get_slot_logs(station_id: str, slot_id: int):
    limit = min(int(request.args.get("limit", 50)), 500)
    logs = (
        SlotLog.query
        .filter_by(slot_id=slot_id)
        .order_by(SlotLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return jsonify([l.to_dict() for l in logs]), 200
