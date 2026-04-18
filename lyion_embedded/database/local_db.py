# =============================================================================
# local_db.py — Local SQLite read/write functions for the Ly-ion system.
# All functions accept an optional db_path for testability.
# =============================================================================

import sqlite3
import json
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from utils.logger import get_logger
import config

log = get_logger(__name__)


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect(db_path: str = None):
    """Context manager yielding a sqlite3 Connection with row_factory set."""
    db_path = db_path or config.DB_PATH
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ===========================================================================
# Slot read / write
# ===========================================================================

def get_all_slots(db_path: str = None) -> list[dict]:
    """Return all 24 slot rows as a list of dicts."""
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM slots ORDER BY slot_id").fetchall()
    return [dict(r) for r in rows]


def get_slot(slot_id: int, db_path: str = None) -> dict | None:
    """Return a single slot row or None."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM slots WHERE slot_id = ?", (slot_id,)).fetchone()
    return dict(row) if row else None


def update_slot(slot_id: int, db_path: str = None, **fields) -> None:
    """Update arbitrary fields on a slot row.  Always sets last_updated."""
    fields["last_updated"] = _now_iso()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [slot_id]
    with _connect(db_path) as conn:
        conn.execute(f"UPDATE slots SET {set_clause} WHERE slot_id = ?", values)
    log.debug("Slot %d updated: %s", slot_id, fields)


# ===========================================================================
# Session management
# ===========================================================================

def get_active_session_for_card(card_uid: str, db_path: str = None) -> dict | None:
    """Return the ongoing (end_time IS NULL) session for a card UID, or None."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE card_uid = ? AND end_time IS NULL",
            (card_uid,),
        ).fetchone()
    return dict(row) if row else None


def get_active_session_for_slot(slot_id: int, db_path: str = None) -> dict | None:
    """Return the ongoing session for a slot, or None."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE slot_id = ? AND end_time IS NULL",
            (slot_id,),
        ).fetchone()
    return dict(row) if row else None


def create_session(card_uid: str, slot_id: int, battery_uid: str = None,
                   session_id: str = None, db_path: str = None) -> str:
    """Insert a new rental session; return the session_id."""
    sid = session_id or str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO sessions (session_id, card_uid, slot_id, battery_uid,
                                     start_time, end_time, is_synced, deposit_charged)
               VALUES (?, ?, ?, ?, ?, NULL, 0, 0)""",
            (sid, card_uid, slot_id, battery_uid, _now_iso()),
        )
    log.info("Session created: %s | card=%s slot=%d", sid, card_uid, slot_id)
    return sid


def close_session(session_id: str, db_path: str = None) -> None:
    """Set end_time on the given session to mark it as closed."""
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET end_time = ? WHERE session_id = ?",
            (_now_iso(), session_id),
        )
    log.info("Session closed: %s", session_id)


def mark_session_synced(session_id: str, db_path: str = None) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET is_synced = 1 WHERE session_id = ?",
            (session_id,),
        )


def get_unsynced_sessions(db_path: str = None) -> list[dict]:
    """Return all sessions that have not yet been pushed to the cloud."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE is_synced = 0"
        ).fetchall()
    return [dict(r) for r in rows]


# ===========================================================================
# Allowed cards (offline authorisation)
# ===========================================================================

def is_card_allowed(card_uid: str, db_path: str = None) -> dict | None:
    """Return the allowed_cards row for this UID if active, else None."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM allowed_cards WHERE card_uid = ? AND is_active = 1",
            (card_uid,),
        ).fetchone()
    return dict(row) if row else None


def upsert_allowed_cards(cards: list[dict], db_path: str = None) -> None:
    """Bulk upsert a list of allowed-card dicts from cloud sync."""
    with _connect(db_path) as conn:
        for card in cards:
            conn.execute(
                """INSERT INTO allowed_cards (card_uid, student_id, display_name,
                                              is_active, last_synced)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(card_uid) DO UPDATE SET
                       student_id   = excluded.student_id,
                       display_name = excluded.display_name,
                       is_active    = excluded.is_active,
                       last_synced  = excluded.last_synced""",
                (card["card_uid"], card.get("student_id"), card.get("display_name"),
                 card.get("is_active", 1), _now_iso()),
            )
    log.info("Upserted %d allowed cards from cloud", len(cards))


# ===========================================================================
# Slot event logs
# ===========================================================================

def log_slot_event(slot_id: int, event_type: str, details: dict = None,
                   db_path: str = None) -> None:
    """Append an event row to slot_logs."""
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO slot_logs (slot_id, event_type, timestamp, details)
               VALUES (?, ?, ?, ?)""",
            (slot_id, event_type, _now_iso(), json.dumps(details or {})),
        )


# ===========================================================================
# Sync queue
# ===========================================================================

def enqueue_sync(endpoint: str, method: str, payload: dict,
                 db_path: str = None) -> None:
    """Push an API call onto the local sync queue."""
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO sync_queue (endpoint, method, payload, created_at, attempts)
               VALUES (?, ?, ?, ?, 0)""",
            (endpoint, method.upper(), json.dumps(payload), _now_iso()),
        )
    log.debug("Enqueued sync: %s %s", method, endpoint)


def get_pending_sync_items(limit: int = 50, db_path: str = None) -> list[dict]:
    """Return up to `limit` pending sync queue entries."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM sync_queue ORDER BY queue_id LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_sync_item(queue_id: int, db_path: str = None) -> None:
    """Remove a successfully delivered item from the queue."""
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM sync_queue WHERE queue_id = ?", (queue_id,))


def increment_sync_attempts(queue_id: int, db_path: str = None) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE sync_queue SET attempts = attempts + 1 WHERE queue_id = ?",
            (queue_id,),
        )
