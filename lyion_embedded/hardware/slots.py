# =============================================================================
# slots.py — High-level slot controller.
# Combines GPIOExpander and LEDController into a unified slot API.
# =============================================================================

import threading
from utils.logger import get_logger
import config
from hardware.pogo import PogoController
from hardware.gpio_expander import GPIOExpander

log = get_logger(__name__)


class SlotController:
    """
    Provides slot-level operations: unlock, detect, and LED update.
    Uses PogoController and GPIOExpander internally.
    """

    def __init__(self, pogo: PogoController, gpio: GPIOExpander):
        self._pogo = pogo
        self._gpio = gpio
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Unlock / lock
    # ------------------------------------------------------------------

    def unlock(self, slot_number: int) -> None:
        """
        Unlock a slot: energise solenoid, set state UNLOCKED via pogo,
        then re-lock solenoid after SOLENOID_UNLOCK_DURATION seconds.
        Runs the solenoid pulse in a background thread so the caller
        is not blocked.
        """
        log.info("SlotController: unlocking slot %d", slot_number)
        self._pogo.set_state(slot_number, config.POGO_LED_UNLOCKED)
        
        # Run solenoid pulse in background to avoid blocking the RFID loop
        t = threading.Thread(
            target=self._gpio.unlock_slot,
            args=(slot_number,),
            daemon=True,
            name=f"solenoid-{slot_number}",
        )
        t.start()

    def lock(self, slot_number: int) -> None:
        """Immediately lock a slot."""
        self._gpio.lock_slot(slot_number)

    def lock_all(self) -> None:
        """Lock all slots (safety reset)."""
        self._gpio.lock_all()
        self._pogo.set_all_states(config.POGO_LED_OFF)

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def is_battery_present(self, slot_number: int) -> bool:
        """Return True if a battery is detected in the given slot."""
        return self._gpio.read_detection(slot_number)

    def read_all_detections(self) -> dict[int, bool]:
        """Return {slot_number: is_battery_present} for all 24 slots."""
        return self._gpio.read_all_detections()

    # ------------------------------------------------------------------
    # Telemetry and State helpers
    # ------------------------------------------------------------------

    def set_state(self, slot_number: int, state: str) -> None:
        self._pogo.set_state(slot_number, state)

    def update_states_from_db(self, slots: list[dict]) -> None:
        """Bulk-update batteries from DB slot state records."""
        self._pogo.update_all_from_db(slots)

    def read_telemetry(self, slot_number: int) -> dict:
        """Read telemetry data via pogo pins."""
        return self._pogo.read_telemetry(slot_number)
