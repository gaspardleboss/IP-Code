-- =============================================================================
-- migration.sql — Initial schema for the Ly-ion PostgreSQL database.
-- Executed automatically by the postgres Docker container on first run.
-- Also safe to run manually: psql -U lyion -d lyion_db -f migration.sql
-- =============================================================================

-- Students (institution-adaptable — student_number is the external ID)
CREATE TABLE IF NOT EXISTS students (
    id               SERIAL       PRIMARY KEY,
    card_uid         VARCHAR(32)  UNIQUE,
    student_number   VARCHAR(50)  UNIQUE NOT NULL,
    name             VARCHAR(120) NOT NULL,
    email            VARCHAR(254) UNIQUE,
    password_hash    VARCHAR(256),
    deposit_balance  NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_login       TIMESTAMPTZ
);

-- Batteries (individual power banks)
CREATE TABLE IF NOT EXISTS batteries (
    id                 SERIAL       PRIMARY KEY,
    battery_uid        VARCHAR(32)  UNIQUE NOT NULL,
    charge_level       SMALLINT     NOT NULL DEFAULT 0 CHECK (charge_level BETWEEN 0 AND 100),
    cycle_count        INTEGER      NOT NULL DEFAULT 0,
    health_status      VARCHAR(16)  NOT NULL DEFAULT 'GOOD'
                         CHECK (health_status IN ('GOOD', 'DEGRADED', 'DEFECTIVE')),
    last_charge_start  TIMESTAMPTZ,
    last_charge_end    TIMESTAMPTZ,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Stations (locker units)
CREATE TABLE IF NOT EXISTS stations (
    id              VARCHAR(64)  PRIMARY KEY,
    location_name   VARCHAR(200) NOT NULL,
    qr_code_token   UUID         UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    is_online       BOOLEAN      NOT NULL DEFAULT FALSE,
    last_heartbeat  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Slots (24 per station)
CREATE TABLE IF NOT EXISTS slots (
    id           INTEGER      NOT NULL,
    station_id   VARCHAR(64)  NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    battery_id   INTEGER      REFERENCES batteries(id) ON DELETE SET NULL,
    is_locked    BOOLEAN      NOT NULL DEFAULT TRUE,
    led_state    VARCHAR(10)  NOT NULL DEFAULT 'OFF',
    is_defective BOOLEAN      NOT NULL DEFAULT FALSE,
    last_updated TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, station_id)
);

-- Rental sessions
CREATE TABLE IF NOT EXISTS sessions (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id       INTEGER      NOT NULL REFERENCES students(id),
    slot_id          INTEGER      NOT NULL,
    battery_id       INTEGER      REFERENCES batteries(id),
    start_time       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    end_time         TIMESTAMPTZ,
    deposit_held     NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    deposit_returned BOOLEAN      NOT NULL DEFAULT FALSE,
    status           VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE'
                       CHECK (status IN ('ACTIVE', 'RETURNED', 'OVERDUE', 'LOST'))
);

-- Slot audit log
CREATE TABLE IF NOT EXISTS slot_logs (
    id          SERIAL       PRIMARY KEY,
    slot_id     INTEGER      NOT NULL,
    event_type  VARCHAR(32)  NOT NULL,
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    details     JSONB
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_student_id ON sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status      ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_slot_logs_slot_id    ON slot_logs(slot_id);
CREATE INDEX IF NOT EXISTS idx_students_card_uid    ON students(card_uid);
