# =============================================================================
# card_service.py — RFID card validation logic.
# =============================================================================

from models import db, Student
from utils.logger import get_logger

log = get_logger(__name__)


def validate_card_uid(card_uid: str) -> dict:
    """
    Look up a card UID in the Student table.
    Returns a dict with 'valid', and student info if found.
    """
    student = Student.query.filter_by(card_uid=card_uid, is_active=True).first()
    if not student:
        log.info("Card UID not recognised: %s", card_uid)
        return {"valid": False, "reason": "Card not registered or account inactive"}

    log.info("Card validated: %s → student %s", card_uid, student.student_number)
    return {
        "valid":        True,
        "student_id":   student.id,
        "student_name": student.name,
        "student_number": student.student_number,
        "deposit_balance": float(student.deposit_balance),
        "is_active":    student.is_active,
    }


def get_allowed_cards_list() -> list[dict]:
    """
    Return all active student card UIDs for syncing to the RPi offline cache.
    Only includes students with a registered card_uid.
    """
    students = Student.query.filter(
        Student.is_active == True,
        Student.card_uid.isnot(None),
    ).all()
    return [
        {
            "card_uid":     s.card_uid,
            "student_id":   str(s.student_number),
            "display_name": s.name,
            "is_active":    s.is_active,
        }
        for s in students
    ]
