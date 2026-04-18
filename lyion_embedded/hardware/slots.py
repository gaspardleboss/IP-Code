# =============================================================================
# slots.py — High-level slot controller.
# Combines GPIOExpander and LEDController into a unified slot API.
# =============================================================================

import threading
from utils.logger import get_logger
import config
from hardware.leds import LEDController
from hardware.gpio_expander import GPIOExpander

log = get_logger(__name__)


class SlotController:
    """
    Provides slot-level operations: unlock, detect, and LED update.
    Uses LEDController and GPIOExpander internally.
    """

    def __init__(self, leds: LEDController, gpio: GPIOExpander):
        self._leds = leds
        self._gpio = gpio
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Unlock / lock
    # ------------------------------------------------------------------

    def unlock(self, slot_number: int) -> None:
        """
        Unlock a slot: energise solenoid, flash LED green,
        then re-lock solenoid after SOLENOID_UNLOCK_DURATION seconds.
        Runs the solenoid pulse in a background thread so the caller
        is not blocked.
        """
        log.info("SlotController: unlocking slot %d", slot_number)
        self._leds.pulse_slot(slot_number, config.COLOR_GREEN, duration=0.5)
        self._leds.set_slot_color(slot_number, config.COLOR_GREEN)
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
        self._leds.set_all_slots(config.COLOR_OFF)

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
    # LED helpers
    # ------------------------------------------------------------------

    def set_led(self, slot_number: int, color: tuple) -> None:
        self._leds.set_slot_color(slot_number, color)

    def update_leds_from_db(self, slots: list[dict]) -> None:
        """Bulk-update LEDs from DB slot state records."""
        self._leds.update_all_from_db(slots)

    def led_state_for_slot(self, slot: dict) -> tuple:
        """
        Derive the correct LED colour from a slot record dict.
        Dict keys: is_defective, charge_level, led_state.
        """
        if slot.get("is_defective"):
            return config.COLOR_RED
        charge = slot.get("charge_level", 0)
        if charge >= config.BATTERY_CHARGED_THRESHOLD:
            return config.COLOR_BLUE
        return config.COLOR_WHITE
