# =============================================================================
# rfid.py — RC522 (MFRC522) RFID reader handler.
# Polls for card presence and returns the UID as a formatted hex string.
# =============================================================================

import time
from utils.logger import get_logger

log = get_logger(__name__)

try:
    from mfrc522 import SimpleMFRC522
    _HARDWARE_AVAILABLE = True
except ImportError:
    # Allow the module to load on a development machine without the library
    _HARDWARE_AVAILABLE = False
    log.warning("mfrc522 library not found — RFID running in STUB mode")


class RFIDReader:
    """
    Wraps the SimpleMFRC522 reader.
    Provides a blocking read_card() and a non-blocking try_read() method.
    """

    def __init__(self):
        if _HARDWARE_AVAILABLE:
            self._reader = SimpleMFRC522()
            log.info("RFID reader initialised (RC522 hardware)")
        else:
            self._reader = None
            log.info("RFID reader initialised (STUB mode)")

    # ------------------------------------------------------------------
    def read_card(self) -> str | None:
        """
        Block until a card is detected, then return its UID as an uppercase
        hex string (e.g. "04 89 7B CD 1D").
        Returns None if an error occurs.
        """
        if not _HARDWARE_AVAILABLE:
            log.debug("RFID stub: no card (hardware unavailable)")
            return None
        try:
            uid, _ = self._reader.read()
            formatted = self._format_uid(uid)
            log.info("RFID card detected: %s", formatted)
            return formatted
        except Exception as exc:
            log.error("RFID read error: %s", exc)
            return None

    # ------------------------------------------------------------------
    def try_read(self) -> str | None:
        """
        Non-blocking card scan.  Returns None immediately if no card is present.
        """
        if not _HARDWARE_AVAILABLE:
            return None
        try:
            uid, _ = self._reader.read_no_block()
            if uid is None:
                return None
            formatted = self._format_uid(uid)
            log.info("RFID card detected: %s", formatted)
            return formatted
        except Exception as exc:
            log.error("RFID try_read error: %s", exc)
            return None

    # ------------------------------------------------------------------
    @staticmethod
    def _format_uid(uid: int) -> str:
        """Convert numeric UID to spaced hex string (e.g. '04 89 7B CD 1D')."""
        hex_str = format(uid, "010X")   # 10 hex chars = 5 bytes
        return " ".join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
