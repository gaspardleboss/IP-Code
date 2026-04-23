# =============================================================================
# models.py — SQLite schema for the Ly-ion embedded local database.
# All tables are created here via init_db(); call this once at startup.
# =============================================================================

import sqlite3
import config
from utils.logger import get_logger

log = get_logger(__name__)

# Complete DDL executed in order on first run
_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;   -- Write-Ahead Logging for concurrent reads
PRAGMA foreign_keys=ON;

-- -----------------------------------------------------------------------
-- slots: current physical state of every slot in the locker
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS slots (
    slot_id      INTEGER PRIMARY KEY,          -- 1 to 24
    battery_uid  TEXT,                         -- UID of battery in slot, NULL if empty
    is_locked    INTEGER NOT NULL DEFAULT 1,   -- 1=locked, 0=unlocked
    slot_state   TEXT    NOT NULL DEFAULT 'OFF',-- 'READY','FAULT','UNLOCKED','CHARGING','OFF'
    charge_level INTEGER NOT NULL DEFAULT 0,   -- 0-100 % (updated by cloud sync)
    battery_temperature REAL NOT NULL DEFAULT 0.0, -- Battery temperature in Celsius
    is_defective INTEGER NOT NULL DEFAULT 0,   -- 1 if flagged damaged / defective
    last_updated TEXT                          -- ISO-8601 timestamp
);

-- -----------------------------------------------------------------------
-- sessions: rental sessions (both ongoing and closed)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    session_id       TEXT    PRIMARY KEY,      -- UUID from cloud backend
    card_uid         TEXT    NOT NULL,         -- Student RFID card UID
    slot_id          INTEGER NOT NULL,
    battery_uid      TEXT,                     -- Battery UID rented
    start_time       TEXT    NOT NULL,         -- ISO-8601
    end_time         TEXT,                     -- NULL while session is active
    is_synced        INTEGER NOT NULL DEFAULT 0,-- 1 once pushed to cloud
    deposit_charged  INTEGER NOT NULL DEFAULT 0 -- 1 if deposit was held
);

-- -----------------------------------------------------------------------
-- allowed_cards: pre-authorised student cards for offline operation
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS allowed_cards (
    card_uid     TEXT PRIMARY KEY,             -- Student RFID card UID
    student_id   TEXT,                         -- Institution student number
    display_name TEXT,                         -- Student name (for logs)
    is_active    INTEGER NOT NULL DEFAULT 1,   -- 0 if account suspended
    last_synced  TEXT                          -- ISO-8601 timestamp of last cloud sync
);

-- -----------------------------------------------------------------------
-- slot_logs: audit trail of every hardware event
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS slot_logs (
    log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_id    INTEGER NOT NULL,
    event_type TEXT    NOT NULL,   -- INSERT, REMOVE, UNLOCK, LOCK,
                                   -- CHARGE_ANOMALY, DEFECTIVE_FLAG
    timestamp  TEXT    NOT NULL,   -- ISO-8601
    details    TEXT                -- JSON string with extra info
);

-- -----------------------------------------------------------------------
-- sync_queue: pending API calls to flush to cloud when connectivity returns
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_queue (
    queue_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint   TEXT    NOT NULL,   -- Backend API path (e.g. /api/return)
    method     TEXT    NOT NULL,   -- 'POST', 'PUT', 'PATCH'
    payload    TEXT    NOT NULL,   -- JSON string
    created_at TEXT    NOT NULL,   -- ISO-8601
    attempts   INTEGER NOT NULL DEFAULT 0
);
"""

_SEED_SLOTS_SQL = """
INSERT OR IGNORE INTO slots (slot_id, battery_uid, is_locked, slot_state,
                              charge_level, battery_temperature, is_defective, last_updated)
VALUES (?, NULL, 1, 'OFF', 0, 0.0, 0, datetime('now'));
"""


def init_db(db_path: str = None) -> None:
    """
    Create all tables and seed the slots table with rows 1-24 if they
    don't already exist.  Safe to call on every startup.
    """
    db_path = db_path or config.DB_PATH
    try:
        conn = sqlite3.connect(db_path)
        conn.executescript(_SCHEMA_SQL)
        # Pre-populate slot rows 1-24
        for slot_id in range(1, config.NUM_SLOTS + 1):
            conn.execute(_SEED_SLOTS_SQL, (slot_id,))
        conn.commit()
        conn.close()
        log.info("Local database initialised at %s", db_path)
    except Exception as exc:
        log.critical("Failed to initialise database: %s", exc)
        raise
