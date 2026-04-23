"""
=============================================================================
sim_db_seed.py — E.3 Database Validation: Seed script
Builds a deterministic test dataset in a fresh SQLite file.
=============================================================================
"""

import sqlite3
import random
import uuid
from datetime import datetime, timedelta
import os
import json

from database import models
import config

DB_PATH = "/Users/gaspardvanco/Desktop/E3_results/lyion_local_test.db"
SUMMARY_PATH = "/Users/gaspardvanco/Desktop/E3_results/T5_seed_summary.log"

def run_seed():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    # 0. Initialize Schema
    models.init_db(db_path=DB_PATH)
    random.seed(42)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Seed Allowed Cards (30 students)
    for i in range(1, 31):
        card_uid = f"CARD-{i:03d}"
        student_id = f"STU-{random.randint(1000, 9999)}"
        display_name = f"Student {i}"
        last_synced = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO allowed_cards (card_uid, student_id, display_name, is_active, last_synced) VALUES (?, ?, ?, 1, ?)",
            (card_uid, student_id, display_name, last_synced)
        )

    # 2. Seed Batteries (20 batteries into 20 of the 24 slots)
    brackets = [
        (0, 25), (25, 50), (50, 80), (80, 100)
    ]
    battery_charge_levels = []
    for min_c, max_c in brackets:
        for _ in range(5):
            battery_charge_levels.append(random.randint(min_c, max_c))
    
    random.shuffle(battery_charge_levels)
    
    slot_ids = list(range(1, 25))
    random.shuffle(slot_ids)
    
    for i, charge in enumerate(battery_charge_levels):
        slot_id = slot_ids[i]
        battery_uid = f"BAT-{i+1:03d}"
        cur.execute(
            "UPDATE slots SET battery_uid = ?, charge_level = ? WHERE slot_id = ?",
            (battery_uid, charge, slot_id)
        )

    # 3. Seed Sessions (50 historical sessions over last 30 days)
    # 35 RETURNED, 10 ACTIVE, 3 OVERDUE, 2 LOST
    session_types = (
        ['RETURNED'] * 35 +
        ['ACTIVE'] * 10 +
        ['OVERDUE'] * 3 +
        ['LOST'] * 2
    )
    random.shuffle(session_types)
    
    now = datetime.utcnow()
    
    for stype in session_types:
        session_id = str(uuid.uuid4())
        card_uid = f"CARD-{random.randint(1, 30):03d}"
        slot_id = random.randint(1, 24)
        battery_uid = f"BAT-{random.randint(1, 20):03d}"
        
        if stype == 'RETURNED':
            start_time = now - timedelta(days=random.randint(1, 30), hours=random.randint(1, 10))
            end_time = start_time + timedelta(hours=random.randint(1, 24))
            is_synced = 1
            deposit_charged = 0
            cur.execute(
                "INSERT INTO sessions (session_id, card_uid, slot_id, battery_uid, start_time, end_time, is_synced, deposit_charged) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, card_uid, slot_id, battery_uid, start_time.isoformat(), end_time.isoformat(), is_synced, deposit_charged)
            )
        elif stype == 'ACTIVE':
            start_time = now - timedelta(hours=random.randint(1, 40))
            is_synced = 0
            deposit_charged = 0
            cur.execute(
                "INSERT INTO sessions (session_id, card_uid, slot_id, battery_uid, start_time, end_time, is_synced, deposit_charged) VALUES (?, ?, ?, ?, ?, NULL, ?, ?)",
                (session_id, card_uid, slot_id, battery_uid, start_time.isoformat(), is_synced, deposit_charged)
            )
        elif stype == 'OVERDUE':
            start_time = now - timedelta(hours=random.randint(49, 100))
            is_synced = 0
            deposit_charged = 0
            cur.execute(
                "INSERT INTO sessions (session_id, card_uid, slot_id, battery_uid, start_time, end_time, is_synced, deposit_charged) VALUES (?, ?, ?, ?, ?, NULL, ?, ?)",
                (session_id, card_uid, slot_id, battery_uid, start_time.isoformat(), is_synced, deposit_charged)
            )
        elif stype == 'LOST':
            start_time = now - timedelta(days=random.randint(5, 30))
            end_time = start_time + timedelta(days=2) # e.g. marked lost after 48h
            is_synced = 1
            deposit_charged = 1
            cur.execute(
                "INSERT INTO sessions (session_id, card_uid, slot_id, battery_uid, start_time, end_time, is_synced, deposit_charged) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, card_uid, slot_id, battery_uid, start_time.isoformat(), end_time.isoformat(), is_synced, deposit_charged)
            )

    # 4. Seed Slot Logs (200 events)
    event_types = ['INSERT', 'REMOVE', 'UNLOCK', 'LOCK', 'CHARGE_ANOMALY', 'DEFECTIVE_FLAG']
    for _ in range(200):
        slot_id = random.randint(1, 24)
        evt = random.choice(event_types)
        timestamp = (now - timedelta(days=random.randint(0, 30), minutes=random.randint(0, 60))).isoformat()
        details = json.dumps({"note": "simulated event"}) if evt in ['CHARGE_ANOMALY', 'DEFECTIVE_FLAG'] else "{}"
        cur.execute(
            "INSERT INTO slot_logs (slot_id, event_type, timestamp, details) VALUES (?, ?, ?, ?)",
            (slot_id, evt, timestamp, details)
        )

    conn.commit()

    # Get row counts
    tables = ['slots', 'allowed_cards', 'sessions', 'slot_logs', 'sync_queue']
    counts = {}
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        counts[t] = cur.fetchone()[0]

    conn.close()

    summary_lines = [
        "### Database Seed Summary (SQLite)",
        f"- `slots`: {counts['slots']} rows (1 station equivalent)",
        f"- `allowed_cards`: {counts['allowed_cards']} rows",
        f"- `sessions`: {counts['sessions']} rows",
        f"- `slot_logs`: {counts['slot_logs']} rows",
        f"- `sync_queue`: {counts['sync_queue']} rows",
        "- `batteries`: 20 (represented within `slots` table)"
    ]
    summary_text = "\n".join(summary_lines)
    
    print(summary_text)
    
    with open(SUMMARY_PATH, "w") as f:
        f.write(summary_text + "\n")

if __name__ == "__main__":
    run_seed()
