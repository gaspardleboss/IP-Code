# =============================================================================
# sync.py — Local ↔ cloud synchronisation logic.
# Runs in a background thread; flushes the sync_queue and refreshes
# allowed_cards + slot states from the cloud backend.
# =============================================================================

from utils.logger import get_logger
import config
import database.local_db as db
import network.api_client as api

log = get_logger(__name__)


def run_sync_cycle(slot_controller=None) -> None:
    """
    Execute one full sync cycle:
    1. Send pending sync_queue items.
    2. Push unsynced sessions.
    3. Fetch updated slot states and refresh LEDs.
    4. Refresh allowed_cards list for offline operation.
    5. Send heartbeat.
    """
    _flush_sync_queue()
    _push_unsynced_sessions()
    _refresh_slot_states(slot_controller)
    _refresh_allowed_cards()
    _send_heartbeat()


# ---------------------------------------------------------------------------

def _flush_sync_queue() -> None:
    """Replay all pending queued API calls (accumulated during offline periods)."""
    items = db.get_pending_sync_items()
    if not items:
        return
    log.info("Flushing %d sync queue items", len(items))
    for item in items:
        import json
        result = api.push_single(
            item["endpoint"],
            item["method"],
            json.loads(item["payload"]),
        )
        if result is not None:
            db.delete_sync_item(item["queue_id"])
            log.debug("Sync item %d delivered", item["queue_id"])
        else:
            db.increment_sync_attempts(item["queue_id"])
            log.warning("Sync item %d failed (attempt %d)", item["queue_id"],
                        item["attempts"] + 1)


def _push_unsynced_sessions() -> None:
    """Push sessions that were created while offline."""
    sessions = db.get_unsynced_sessions()
    if not sessions:
        return
    log.info("Pushing %d unsynced sessions", len(sessions))
    result = api.push_sync(events=[], sessions=sessions)
    if result and result.get("ok"):
        for s in sessions:
            db.mark_session_synced(s["session_id"])
        log.info("All unsynced sessions pushed successfully")
    else:
        log.warning("Session push failed — will retry next cycle")


def _refresh_slot_states(slot_controller) -> None:
    """Fetch latest slot states from cloud and update local DB + LEDs."""
    remote_slots = api.fetch_slot_states()
    if not remote_slots:
        log.debug("Slot state refresh skipped (backend unreachable)")
        return
    for slot in remote_slots:
        db.update_slot(
            slot["slot_id"],
            charge_level=slot.get("charge_level", 0),
            is_defective=slot.get("is_defective", 0),
            battery_uid=slot.get("battery_uid"),
        )
    # Rebuild LED colours from the refreshed DB data
    if slot_controller is not None:
        all_slots = db.get_all_slots()
        slot_controller.update_states_from_db(all_slots)
    log.debug("Slot states refreshed from cloud (%d slots)", len(remote_slots))


def _refresh_allowed_cards() -> None:
    """Download the latest allowed-cards list for offline authorisation."""
    result = api.push_sync(events=[], sessions=[])
    if not result:
        return
    cards = result.get("allowed_cards", [])
    if cards:
        db.upsert_allowed_cards(cards)
        log.info("Allowed cards refreshed: %d entries", len(cards))


def _send_heartbeat() -> None:
    """Ping the backend with current slot states to update last_heartbeat."""
    try:
        slot_states = db.get_all_slots()
        api.send_heartbeat(slot_states)
        log.debug("Heartbeat sent")
    except Exception as exc:
        log.warning("Heartbeat error: %s", exc)
