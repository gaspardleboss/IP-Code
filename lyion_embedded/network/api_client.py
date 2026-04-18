# =============================================================================
# api_client.py — HTTP client for communicating with the Ly-ion cloud backend.
# All requests carry the station API key in the X-Station-Key header.
# Functions return parsed JSON dicts on success, None on failure.
# =============================================================================

import json
import requests
from requests.exceptions import RequestException
from utils.logger import get_logger
import config

log = get_logger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({
    "X-Station-Key": config.API_SECRET,
    "X-Station-Id":  config.STATION_ID,
    "Content-Type":  "application/json",
    "Accept":        "application/json",
})
_TIMEOUT = 8   # seconds


def _post(endpoint: str, payload: dict) -> dict | None:
    url = f"{config.BACKEND_URL}{endpoint}"
    try:
        resp = _SESSION.post(url, data=json.dumps(payload), timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except RequestException as exc:
        log.warning("POST %s failed: %s", endpoint, exc)
        return None


def _get(endpoint: str, params: dict = None) -> dict | None:
    url = f"{config.BACKEND_URL}{endpoint}"
    try:
        resp = _SESSION.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except RequestException as exc:
        log.warning("GET %s failed: %s", endpoint, exc)
        return None


# ---------------------------------------------------------------------------
# Rental
# ---------------------------------------------------------------------------

def request_rent(card_uid: str) -> dict | None:
    """
    POST /api/rent — ask backend to approve a rental for this card.
    Returns {"slot": N, "session_id": "uuid", "battery_charge": 95}
    or None if unreachable / rejected.
    """
    return _post("/api/rent", {"card_uid": card_uid, "station_id": config.STATION_ID})


def confirm_return(card_uid: str, slot_id: int) -> dict | None:
    """
    POST /api/return — notify backend of a battery return.
    """
    return _post("/api/return", {
        "card_uid":   card_uid,
        "slot_id":    slot_id,
        "station_id": config.STATION_ID,
    })


# ---------------------------------------------------------------------------
# Card validation (used for offline fallback verification)
# ---------------------------------------------------------------------------

def validate_card(card_uid: str) -> dict | None:
    """
    POST /api/auth/card — check whether a card UID is registered.
    Returns {"valid": true/false, ...} or None on network error.
    """
    return _post("/api/auth/card", {
        "card_uid":   card_uid,
        "station_id": config.STATION_ID,
    })


# ---------------------------------------------------------------------------
# Slot status
# ---------------------------------------------------------------------------

def fetch_slot_states() -> list[dict] | None:
    """
    GET /api/slots/<station_id> — fetch current state of all slots.
    Returns list of slot dicts or None on error.
    """
    result = _get(f"/api/slots/{config.STATION_ID}")
    return result.get("slots") if result else None


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def push_sync(events: list[dict], sessions: list[dict]) -> dict | None:
    """
    POST /api/sync/push — flush queued offline events to the cloud.
    Returns {"ok": true, "updated_slots": [...], "allowed_cards": [...]}
    """
    return _post("/api/sync/push", {
        "station_id": config.STATION_ID,
        "events":     events,
        "sessions":   sessions,
    })


def send_heartbeat(slot_states: list[dict]) -> dict | None:
    """
    POST /api/sync/heartbeat — keep the station's last_heartbeat alive.
    """
    return _post("/api/sync/heartbeat", {
        "station_id":  config.STATION_ID,
        "slot_states": slot_states,
    })


def push_single(endpoint: str, method: str, payload: dict) -> dict | None:
    """
    Generic helper for replaying queued sync items with arbitrary endpoints.
    """
    if method.upper() == "POST":
        return _post(endpoint, payload)
    # PUT/PATCH not needed yet but handled gracefully
    log.warning("push_single: unsupported method %s for %s", method, endpoint)
    return None
