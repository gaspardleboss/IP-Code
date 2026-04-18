#!/usr/bin/env python3
# =============================================================================
# main.py — Ly-ion Embedded Controller entry point.
#
# Starts four daemon threads:
#   Thread 1 — RFID scan loop        (polls RC522 every 200 ms)
#   Thread 2 — Slot monitor loop     (polls detection inputs every 500 ms)
#   Thread 3 — Charging monitor loop (updates LED colours every 60 s)
#   Thread 4 — Cloud sync loop       (syncs with backend every 30 s)
#
# Main thread handles graceful shutdown via SIGTERM / SIGINT.
# =============================================================================

import signal
import sys
import time
import threading

import config
from utils.logger import get_logger
from database.models import init_db
import database.local_db as db
from hardware.rfid import RFIDReader
from hardware.leds import LEDController
from hardware.gpio_expander import GPIOExpander
from hardware.slots import SlotController
import network.api_client as api
import network.sync as sync_module

log = get_logger("main")

# ---------------------------------------------------------------------------
# Global shutdown event — set by the signal handler to stop all threads
# ---------------------------------------------------------------------------
_shutdown = threading.Event()


# ===========================================================================
# RFID card scan handler
# ===========================================================================

def handle_card_scan(uid: str, slot_ctrl: SlotController) -> None:
    """
    Called each time the RC522 reads a card tap.
    Determines whether this is a rental or a return and acts accordingly.
    """
    log.info("Card scanned: %s", uid)

    # --- Check if this card has an active session (i.e. it's a return) ---
    session = db.get_active_session_for_card(uid)
    if session:
        _handle_return(uid, session, slot_ctrl)
    else:
        _handle_rental_request(uid, slot_ctrl)


def _handle_return(uid: str, session: dict, slot_ctrl: SlotController) -> None:
    """Process a battery return for an active session."""
    slot_id = session["slot_id"]
    log.info("Return: card=%s slot=%d session=%s", uid, slot_id, session["session_id"])

    # Confirm battery is physically back in the slot
    if slot_ctrl.is_battery_present(slot_id):
        db.close_session(session["session_id"])
        db.update_slot(slot_id, led_state="WHITE", is_locked=1)
        slot_ctrl.set_led(slot_id, config.COLOR_WHITE)
        db.log_slot_event(slot_id, "INSERT", {"card_uid": uid, "type": "return"})
        db.enqueue_sync("/api/return", "POST", {
            "card_uid":    uid,
            "slot_id":     slot_id,
            "station_id":  config.STATION_ID,
            "session_id":  session["session_id"],
        })
        log.info("Return confirmed for slot %d", slot_id)
    else:
        log.warning("Return attempted but battery not detected in slot %d", slot_id)


def _handle_rental_request(uid: str, slot_ctrl: SlotController) -> None:
    """Process a new rental request for a card that has no active session."""
    # --- Try cloud backend first ---
    result = api.request_rent(uid)
    if result and result.get("slot"):
        slot_id      = result["slot"]
        session_id   = result["session_id"]
        battery_uid  = result.get("battery_uid")
        log.info("Rental approved by cloud: slot=%d session=%s", slot_id, session_id)
        _execute_rental(uid, slot_id, session_id, battery_uid, slot_ctrl)
        return

    # --- Offline fallback: check local allowed_cards ---
    card_info = db.is_card_allowed(uid)
    if not card_info:
        log.warning("Card %s not recognised (offline) — access denied", uid)
        return

    # Find the best available slot (highest charge, not defective)
    available_slots = [
        s for s in db.get_all_slots()
        if s.get("led_state") == "BLUE" and not s.get("is_defective")
    ]
    if not available_slots:
        log.warning("No available slots for offline rental")
        return

    best_slot = max(available_slots, key=lambda s: s.get("charge_level", 0))
    slot_id = best_slot["slot_id"]
    import uuid
    session_id = str(uuid.uuid4())
    log.info("Offline rental approved for card %s → slot %d", uid, slot_id)
    _execute_rental(uid, slot_id, session_id, best_slot.get("battery_uid"), slot_ctrl)

    # Queue the event to be pushed when connectivity returns
    db.enqueue_sync("/api/rent", "POST", {
        "card_uid":    uid,
        "slot_id":     slot_id,
        "station_id":  config.STATION_ID,
        "session_id":  session_id,
        "offline":     True,
    })


def _execute_rental(uid: str, slot_id: int, session_id: str,
                    battery_uid: str | None, slot_ctrl: SlotController) -> None:
    """Persist the session locally and physically unlock the slot."""
    db.create_session(uid, slot_id, battery_uid, session_id)
    db.update_slot(slot_id, led_state="GREEN", is_locked=0)
    db.log_slot_event(slot_id, "UNLOCK", {"card_uid": uid, "session_id": session_id})
    slot_ctrl.unlock(slot_id)   # Energises solenoid + sets LED GREEN


# ===========================================================================
# Thread 1: RFID scan loop
# ===========================================================================

def rfid_loop(rfid: RFIDReader, slot_ctrl: SlotController) -> None:
    log.info("RFID scan loop started")
    last_uid = None
    last_scan_time = 0.0
    DEBOUNCE_S = 2.0   # Ignore re-reads of the same card within 2 seconds

    while not _shutdown.is_set():
        try:
            uid = rfid.try_read()
            now = time.monotonic()
            if uid and (uid != last_uid or (now - last_scan_time) > DEBOUNCE_S):
                last_uid = uid
                last_scan_time = now
                handle_card_scan(uid, slot_ctrl)
        except Exception as exc:
            log.error("RFID loop exception: %s", exc)
        time.sleep(config.RFID_POLL_MS / 1000.0)

    log.info("RFID scan loop stopped")


# ===========================================================================
# Thread 2: Slot monitor loop
# ===========================================================================

def slot_monitor_loop(slot_ctrl: SlotController) -> None:
    """
    Polls all 24 detection inputs every 500 ms.
    Detects battery insertion (LOW→HIGH) and removal (HIGH→LOW).
    """
    log.info("Slot monitor loop started")
    previous_states: dict[int, bool] = {}

    while not _shutdown.is_set():
        try:
            current = slot_ctrl.read_all_detections()
            for slot_id, is_present in current.items():
                prev = previous_states.get(slot_id, None)
                if prev is None:
                    previous_states[slot_id] = is_present
                    continue

                if not prev and is_present:
                    # Battery inserted
                    _on_battery_inserted(slot_id, slot_ctrl)
                elif prev and not is_present:
                    # Battery removed
                    _on_battery_removed(slot_id, slot_ctrl)

                previous_states[slot_id] = is_present
        except Exception as exc:
            log.error("Slot monitor exception: %s", exc)
        time.sleep(0.5)

    log.info("Slot monitor loop stopped")


def _on_battery_inserted(slot_id: int, slot_ctrl: SlotController) -> None:
    log.info("Battery inserted in slot %d", slot_id)
    session = db.get_active_session_for_slot(slot_id)
    if session:
        # Battery returned — close the rental session
        _handle_return(session["card_uid"], session, slot_ctrl)
    else:
        # New battery placed by maintenance — start charging monitoring
        slot_data = db.get_slot(slot_id) or {}
        charge = slot_data.get("charge_level", 0)
        color = config.COLOR_BLUE if charge >= config.BATTERY_CHARGED_THRESHOLD else config.COLOR_WHITE
        db.update_slot(slot_id, led_state="BLUE" if color == config.COLOR_BLUE else "WHITE")
        slot_ctrl.set_led(slot_id, color)
        db.log_slot_event(slot_id, "INSERT", {"source": "maintenance"})


def _on_battery_removed(slot_id: int, slot_ctrl: SlotController) -> None:
    log.info("Battery removed from slot %d", slot_id)
    session = db.get_active_session_for_slot(slot_id)
    if not session:
        # Unauthorized removal — LED RED, log alert
        log.warning("ALERT: Unauthorized battery removal from slot %d!", slot_id)
        db.update_slot(slot_id, led_state="RED", is_defective=1)
        slot_ctrl.set_led(slot_id, config.COLOR_RED)
        db.log_slot_event(slot_id, "REMOVE", {"authorized": False})
    else:
        # Normal rental removal — slot goes GREEN (already set by unlock)
        log.info("Authorized removal: session %s, slot %d", session["session_id"], slot_id)
        db.log_slot_event(slot_id, "REMOVE", {"authorized": True,
                                               "session_id": session["session_id"]})


# ===========================================================================
# Thread 3: Charging monitor loop
# ===========================================================================

def charging_monitor_loop(slot_ctrl: SlotController) -> None:
    """
    Every 60 seconds, refresh LED colours from charge levels stored in DB
    (which are updated by the sync loop from the cloud).
    Also detects charging anomalies based on time thresholds.
    """
    log.info("Charging monitor loop started")
    while not _shutdown.is_set():
        try:
            slots = db.get_all_slots()
            for slot in slots:
                if not slot_ctrl.is_battery_present(slot["slot_id"]):
                    continue
                if slot.get("is_defective"):
                    slot_ctrl.set_led(slot["slot_id"], config.COLOR_RED)
                    continue
                charge = slot.get("charge_level", 0)
                if charge >= config.BATTERY_CHARGED_THRESHOLD:
                    color  = config.COLOR_BLUE
                    state  = "BLUE"
                else:
                    color  = config.COLOR_WHITE
                    state  = "WHITE"
                db.update_slot(slot["slot_id"], led_state=state)
                slot_ctrl.set_led(slot["slot_id"], color)
        except Exception as exc:
            log.error("Charging monitor exception: %s", exc)
        time.sleep(60)

    log.info("Charging monitor loop stopped")


# ===========================================================================
# Thread 4: Cloud sync loop
# ===========================================================================

def sync_loop(slot_ctrl: SlotController) -> None:
    log.info("Sync loop started (interval=%ds)", config.SYNC_INTERVAL)
    while not _shutdown.is_set():
        try:
            sync_module.run_sync_cycle(slot_ctrl)
        except Exception as exc:
            log.error("Sync cycle exception: %s", exc)
        time.sleep(config.SYNC_INTERVAL)

    log.info("Sync loop stopped")


# ===========================================================================
# Signal handler
# ===========================================================================

def _signal_handler(signum, frame):  # noqa: ANN001
    log.info("Shutdown signal received (%s) — stopping threads …", signum)
    _shutdown.set()


# ===========================================================================
# Entry point
# ===========================================================================

def main() -> None:
    log.info("=== Ly-ion Embedded Controller starting ===")

    # Initialise database (creates tables, seeds slot rows)
    init_db()

    # Initialise hardware
    leds  = LEDController()
    gpio  = GPIOExpander()           # Also calls lock_all() internally
    slot_ctrl = SlotController(leds, gpio)
    rfid  = RFIDReader()

    # Register OS signal handlers
    signal.signal(signal.SIGINT,  _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Start background threads
    threads = [
        threading.Thread(target=rfid_loop,             args=(rfid, slot_ctrl),  name="rfid",     daemon=True),
        threading.Thread(target=slot_monitor_loop,     args=(slot_ctrl,),        name="slot-mon", daemon=True),
        threading.Thread(target=charging_monitor_loop, args=(slot_ctrl,),        name="charge",   daemon=True),
        threading.Thread(target=sync_loop,             args=(slot_ctrl,),        name="sync",     daemon=True),
    ]
    for t in threads:
        t.start()

    log.info("All threads started — system operational")

    # Main thread blocks until shutdown signal
    _shutdown.wait()

    log.info("Waiting for threads to finish …")
    for t in threads:
        t.join(timeout=5)

    # Safety: lock all solenoids before exiting
    slot_ctrl.lock_all()
    log.info("=== Ly-ion Embedded Controller stopped ===")
    sys.exit(0)


if __name__ == "__main__":
    main()
