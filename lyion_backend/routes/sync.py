# =============================================================================
# sync.py — RPi ↔ cloud synchronisation endpoints.
# =============================================================================

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from models import db, Station, Slot, Session, SlotLog
from services.card_service import get_allowed_cards_list
from services.session_service import get_active_session_for_slot, close_rental_session
from utils.logger import get_logger

log = get_logger(__name__)
sync_bp = Blueprint("sync", __name__)


def _require_station_key():
    return request.headers.get("X-Station-Key", "") == current_app.config["STATION_API_KEY"]


# ---------------------------------------------------------------------------
# POST /api/sync/push — RPi pushes offline-accumulated events to cloud
# ---------------------------------------------------------------------------
@sync_bp.route("/push", methods=["POST"])
def sync_push():
    """
    Receive offline events and unsynced sessions from the RPi.
    Returns refreshed slot states and allowed_cards list.
    """
    if not _require_station_key():
        return jsonify({"error": "Unauthorized"}), 401

    data       = request.get_json(silent=True) or {}
    station_id = data.get("station_id")
    events     = data.get("events", [])
    sessions   = data.get("sessions", [])

    if not station_id:
        return jsonify({"error": "station_id is required"}), 400

    # Process offline sessions
    for sess_data in sessions:
        _process_offline_session(sess_data)

    # Process log events
    for event in events:
        _process_event(event)

    db.session.commit()

    # Build response
    slots = Slot.query.filter_by(station_id=station_id).order_by(Slot.id).all()
    allowed_cards = get_allowed_cards_list()

    log.info("Sync push: station=%s events=%d sessions=%d",
             station_id, len(events), len(sessions))

    return jsonify({
        "ok":            True,
        "updated_slots": [s.to_dict() for s in slots],
        "allowed_cards": allowed_cards,
    }), 200


def _process_offline_session(sess_data: dict) -> None:
    """Upsert a session that was created offline."""
    sid = sess_data.get("session_id")
    if not sid:
        return
    existing = Session.query.get(sid)
    if not existing:
        # Re-create the session record
        from models import Student
        from services.card_service import validate_card_uid
        card_uid = sess_data.get("card_uid", "")
        result   = validate_card_uid(card_uid)
        if not result["valid"]:
            log.warning("Offline session %s: card UID not found", sid)
            return
        new_sess = Session(
            id=sid,
            student_id=result["student_id"],
            slot_id=sess_data.get("slot_id"),
            status="RETURNED" if sess_data.get("end_time") else "ACTIVE",
        )
        db.session.add(new_sess)
        log.info("Offline session replayed: %s", sid)


def _process_event(event: dict) -> None:
    """Write a log event received from RPi sync push."""
    slot_id    = event.get("slot_id")
    event_type = event.get("event_type")
    if not slot_id or not event_type:
        return
    entry = SlotLog(
        slot_id=slot_id,
        event_type=event_type,
        details=event.get("details", {}),
    )
    db.session.add(entry)


# ---------------------------------------------------------------------------
# POST /api/sync/heartbeat — station heartbeat + slot state update
# ---------------------------------------------------------------------------
@sync_bp.route("/heartbeat", methods=["POST"])
def heartbeat():
    """Update the station's last_heartbeat and sync slot states."""
    if not _require_station_key():
        return jsonify({"error": "Unauthorized"}), 401

    data       = request.get_json(silent=True) or {}
    station_id = data.get("station_id")
    slot_states = data.get("slot_states", [])

    station = Station.query.get(station_id)
    if not station:
        return jsonify({"error": "Station not found"}), 404

    station.is_online      = True
    station.last_heartbeat = datetime.now(timezone.utc)

    # Update slot states from RPi report
    for slot_data in slot_states:
        slot = Slot.query.filter_by(
            id=slot_data.get("slot_id"),
            station_id=station_id,
        ).first()
        if slot:
            slot.is_locked    = bool(slot_data.get("is_locked", 1))
            slot.led_state    = slot_data.get("led_state", slot.led_state)
            slot.is_defective = bool(slot_data.get("is_defective", 0))

    db.session.commit()
    log.debug("Heartbeat from station %s (%d slots)", station_id, len(slot_states))
    return jsonify({"ok": True}), 200
