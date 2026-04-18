# =============================================================================
# gpio_expander.py — MCP23017 I2C GPIO expander manager.
#
# Hardware mapping (final):
#   CHIP A (0x20) — ALL 16 pins = OUTPUTS → solenoid relays slots 1-16
#       GPA0=slot1 … GPA7=slot8 | GPB0=slot9 … GPB7=slot16
#   CHIP B (0x21) — GPA = 8 OUTPUTS (solenoids 17-24)
#                   GPB = 8 INPUTS  (battery detection 17-24)
#   CHIP C (0x22) — ALL 16 pins = INPUTS → battery detection slots 1-16
#       GPA0=slot1 … GPA7=slot8 | GPB0=slot9 … GPB7=slot16
#
# Detection logic: pin reads HIGH when battery is inserted.
# Solenoid logic:  relay is energised (slot unlocked) when pin is HIGH.
# =============================================================================

import time
import threading
from utils.logger import get_logger
import config

log = get_logger(__name__)

try:
    import board
    import busio
    from adafruit_mcp230xx.mcp23017 import MCP23017
    from digitalio import Direction
    _HARDWARE_AVAILABLE = True
except ImportError:
    _HARDWARE_AVAILABLE = False
    log.warning("adafruit-circuitpython-mcp230xx not found — GPIO expander in STUB mode")


# ---------------------------------------------------------------------------
# Stub classes used when running on a development machine
# ---------------------------------------------------------------------------

class _StubPin:
    def __init__(self, value=False):
        self.value = value
        self.direction = None

class _StubMCP:
    def __init__(self, address):
        self._address = address
        self._pins = [_StubPin() for _ in range(16)]

    def get_pin(self, idx):
        return self._pins[idx]


# ---------------------------------------------------------------------------
# Slot → chip/pin mapping helpers
# ---------------------------------------------------------------------------

def _solenoid_mapping(slot_number: int):
    """
    Return (chip_id, pin_index) for the solenoid relay of the given slot.
    chip_id: 'A' or 'B'
    pin_index: 0-15
    """
    if 1 <= slot_number <= 16:
        return ('A', slot_number - 1)          # CHIP A, pins 0-15
    elif 17 <= slot_number <= 24:
        return ('B', slot_number - 17)          # CHIP B GPA, pins 0-7
    raise ValueError(f"Invalid slot number: {slot_number}")


def _detection_mapping(slot_number: int):
    """
    Return (chip_id, pin_index) for the battery detection input of the given slot.
    chip_id: 'B' (for slots 17-24, GPB) or 'C' (for slots 1-16)
    pin_index: 0-15
    """
    if 1 <= slot_number <= 16:
        return ('C', slot_number - 1)           # CHIP C, pins 0-15
    elif 17 <= slot_number <= 24:
        return ('B_INPUT', slot_number - 17)    # CHIP B GPB (pins 8-15 of MCP B)
    raise ValueError(f"Invalid slot number: {slot_number}")


# ---------------------------------------------------------------------------
# Main expander manager
# ---------------------------------------------------------------------------

class GPIOExpander:
    """
    Manages all three MCP23017 chips.
    Provides high-level unlock/lock/detect methods.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._init_chips()
        self.lock_all()
        log.info("GPIO expander initialised — chips A(0x20), B(0x21), C(0x22)")

    # ------------------------------------------------------------------
    def _init_chips(self):
        if _HARDWARE_AVAILABLE:
            i2c = busio.I2C(board.SCL, board.SDA)
            self._chip_a = MCP23017(i2c, address=config.I2C_CHIP_A)
            self._chip_b = MCP23017(i2c, address=config.I2C_CHIP_B)
            self._chip_c = MCP23017(i2c, address=config.I2C_CHIP_C)

            # CHIP A: all 16 pins = outputs (solenoid relays 1-16)
            for i in range(16):
                pin = self._chip_a.get_pin(i)
                pin.direction = Direction.OUTPUT
                pin.value = False

            # CHIP B: GPA (pins 0-7) = outputs (solenoids 17-24)
            #         GPB (pins 8-15) = inputs (detection 17-24)
            for i in range(8):
                pin = self._chip_b.get_pin(i)
                pin.direction = Direction.OUTPUT
                pin.value = False
            for i in range(8, 16):
                pin = self._chip_b.get_pin(i)
                pin.direction = Direction.INPUT

            # CHIP C: all 16 pins = inputs (detection 1-16)
            for i in range(16):
                pin = self._chip_c.get_pin(i)
                pin.direction = Direction.INPUT
        else:
            self._chip_a = _StubMCP(config.I2C_CHIP_A)
            self._chip_b = _StubMCP(config.I2C_CHIP_B)
            self._chip_c = _StubMCP(config.I2C_CHIP_C)

    # ------------------------------------------------------------------
    def _get_solenoid_pin(self, slot_number: int):
        chip_id, idx = _solenoid_mapping(slot_number)
        if chip_id == 'A':
            return self._chip_a.get_pin(idx)
        else:  # 'B'
            return self._chip_b.get_pin(idx)

    def _get_detection_pin(self, slot_number: int):
        chip_id, idx = _detection_mapping(slot_number)
        if chip_id == 'C':
            return self._chip_c.get_pin(idx)
        else:  # 'B_INPUT' — GPB of chip B, pins offset by 8
            return self._chip_b.get_pin(idx + 8)

    # ------------------------------------------------------------------
    def unlock_slot(self, slot_number: int) -> None:
        """
        Energise the solenoid relay for SOLENOID_UNLOCK_DURATION seconds,
        then de-energise (re-lock).  Blocks for the duration.
        """
        log.info("Unlocking slot %d for %ds", slot_number, config.SOLENOID_UNLOCK_DURATION)
        with self._lock:
            pin = self._get_solenoid_pin(slot_number)
            pin.value = True
        time.sleep(config.SOLENOID_UNLOCK_DURATION)
        with self._lock:
            pin.value = False
        log.info("Slot %d re-locked", slot_number)

    def lock_slot(self, slot_number: int) -> None:
        """Immediately de-energise the solenoid (lock the slot)."""
        with self._lock:
            self._get_solenoid_pin(slot_number).value = False
        log.debug("Slot %d locked", slot_number)

    def lock_all(self) -> None:
        """Safety reset: de-energise every solenoid relay."""
        with self._lock:
            for slot in range(1, config.NUM_SLOTS + 1):
                try:
                    self._get_solenoid_pin(slot).value = False
                except Exception as exc:
                    log.error("lock_all error on slot %d: %s", slot, exc)
        log.info("All slots locked (safety reset)")

    # ------------------------------------------------------------------
    def read_detection(self, slot_number: int) -> bool:
        """
        Return True if a battery is detected in the given slot
        (detection input pin reads HIGH).
        """
        try:
            return bool(self._get_detection_pin(slot_number).value)
        except Exception as exc:
            log.error("Detection read error slot %d: %s", slot_number, exc)
            return False

    def read_all_detections(self) -> dict[int, bool]:
        """Return {slot_number: is_battery_present} for all 24 slots."""
        return {s: self.read_detection(s) for s in range(1, config.NUM_SLOTS + 1)}
