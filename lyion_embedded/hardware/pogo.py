# =============================================================================
# pogo.py — Pogo Pin Controller for battery communication.
# Handles bi-directional communication (telemetry read, LED state write)
# over the pogo pins interface.
# =============================================================================

import time
import threading
from utils.logger import get_logger
import config

log = get_logger(__name__)

class PogoController:
    """
    Handles communication with the battery microcontrollers via Pogo pins.
    Current implementation is a hardware stub representing the digital bus.
    """

    def __init__(self):
        self._lock = threading.Lock()
        log.info("Pogo controller initialised — ready for %d slots", config.NUM_SLOTS)

    def set_state(self, slot_number: int, state: str) -> None:
        """
        Send a state command to the battery to update its built-in LEDs.
        Valid states: CHARGING, READY, UNLOCKED, FAULT, OFF.
        """
        if not (1 <= slot_number <= config.NUM_SLOTS):
            log.warning("set_state: invalid slot %d", slot_number)
            return
        with self._lock:
            # Hardware specific transmission via UART/I2C/1-Wire would happen here.
            log.debug("Pogo: Slot %d state set to %s", slot_number, state)

    def set_all_states(self, state: str) -> None:
        """Broadcast a state to all slots."""
        with self._lock:
            for slot in range(1, config.NUM_SLOTS + 1):
                self.set_state(slot, state)
                
    def update_all_from_db(self, slots: list[dict]) -> None:
        """
        Bulk-update all batteries from a list of slot state dicts.
        Each dict must have 'slot_id' and 'slot_state' keys.
        """
        with self._lock:
            for slot in slots:
                state = slot.get("slot_state", config.POGO_LED_OFF)
                self.set_state(slot["slot_id"], state)
        log.debug("Pogo states updated from DB (%d slots)", len(slots))

    def pulse_state(self, slot_number: int, state: str, duration: float = 1.0) -> None:
        """
        Temporarily set a state for a duration, then the caller should revert it.
        (Note: Unlocking is handled by just sending UNLOCKED, then returning to READY or OFF).
        """
        # Since the battery manages its own pulsing when given the state, 
        # we just send the state and block if needed, but it's better to just send the state.
        self.set_state(slot_number, state)
        time.sleep(duration)
        # Reverting is handled by the caller.

    def read_telemetry(self, slot_number: int) -> dict:
        """
        Read telemetry from a battery via pogo pins.
        Returns a dict: {'charge_level': int, 'temperature': float, 'fault': bool}
        """
        with self._lock:
            # Mock reading telemetry
            # In production, this reads from the actual bus.
            return {
                'charge_level': 85,  # default stub value
                'temperature': 25.0,
                'fault': False
            }
