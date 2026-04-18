# =============================================================================
# session_service.py — Rental session lifecycle logic.
# =============================================================================

from datetime import datetime, timezone
from models import db, Session, Slot, Battery, Student, SlotLog
from flask import current_app
from utils.logger import get_logger

log = get_logger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


def find_best_slot(station_id: str) -> Slot | None:
    """
    Select the slot with the highest-charged, non-defective battery
    at the given station.
    """
    slot = (
        Slot.query
        .join(Battery, Slot.battery_id == Battery.id)
        .filter(
            Slot.station_id   == station_id,
            Slot.is_defective == False,
            Slot.is_locked    == True,
            Battery.health_status == "GOOD",
        )
        .order_by(Battery.charge_level.desc())
        .first()
    )
    return slot


def create_rental_session(student: Student, slot: Slot) -> Session:
    """
    Open a new rental session: hold deposit, mark slot as unlocked.
    """
    deposit = float(current_app.config.get("DEPOSIT_AMOUNT", 5.00))

    session = Session(
        student_id=student.id,
        slot_id=slot.id,
        battery_id=slot.battery_id,
        deposit_held=deposit,
        status="ACTIVE",
    )
    db.session.add(session)

    slot.is_locked  = False
    slot.led_state  = "GREEN"
    slot.last_updated = _utcnow()

    _append_log(slot.id, "UNLOCK", {"session_id": session.id,
                                     "student_id": student.id})
    db.session.commit()
    log.info("Rental created: session=%s slot=%d student=%d",
             session.id, slot.id, student.id)
    return session


def close_rental_session(session: Session, slot: Slot) -> Session:
    """
    Close a rental session: return deposit, lock slot, begin charging monitoring.
    """
    session.end_time        = _utcnow()
    session.status          = "RETURNED"
    session.deposit_returned = True

    slot.is_locked   = True
    slot.led_state   = "WHITE"   # Charging state
    slot.last_updated = _utcnow()

    if slot.battery:
        slot.battery.cycle_count += 1
        slot.battery.last_charge_start = _utcnow()

    _append_log(slot.id, "INSERT", {"session_id": session.id, "type": "return"})
    db.session.commit()
    log.info("Session closed: %s | slot=%d", session.id, slot.id)
    return session


def get_active_session_for_student(student_id: int) -> Session | None:
    return Session.query.filter_by(student_id=student_id, status="ACTIVE").first()


def get_active_session_for_slot(slot_id: int) -> Session | None:
    return Session.query.filter_by(slot_id=slot_id, status="ACTIVE").first()


def _append_log(slot_id: int, event_type: str, details: dict) -> None:
    log_entry = SlotLog(slot_id=slot_id, event_type=event_type, details=details)
    db.session.add(log_entry)
