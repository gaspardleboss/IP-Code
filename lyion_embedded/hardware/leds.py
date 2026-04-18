# =============================================================================
# leds.py — WS2812B Neopixel LED strip controller.
# Controls 24 LEDs (one per slot) via the rpi_ws281x library on GPIO 18.
# =============================================================================

import time
import threading
from utils.logger import get_logger
import config

log = get_logger(__name__)

try:
    from rpi_ws281x import PixelStrip, Color
    _HARDWARE_AVAILABLE = True
except ImportError:
    _HARDWARE_AVAILABLE = False
    log.warning("rpi_ws281x not found — LED controller running in STUB mode")

    # Minimal stubs so the rest of the code still imports cleanly
    def Color(r, g, b):  # noqa: N802
        return (r, g, b)

    class PixelStrip:  # type: ignore
        def __init__(self, *args, **kwargs):
            self._pixels = [(0, 0, 0)] * config.NEOPIXEL_COUNT

        def begin(self):
            pass

        def setPixelColor(self, idx, color):
            self._pixels[idx] = color

        def show(self):
            log.debug("LED STUB show: %s", self._pixels)

        def __len__(self):
            return config.NEOPIXEL_COUNT


class LEDController:
    """
    Thread-safe LED strip controller.
    All slot numbers are 1-indexed (1–24); internally converted to 0-indexed.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._strip = PixelStrip(
            config.NEOPIXEL_COUNT,
            config.NEOPIXEL_PIN,
            800_000,   # LED signal frequency (Hz)
            5,         # DMA channel
            False,     # Invert signal
            config.NEOPIXEL_BRIGHTNESS,
            0,         # Channel
        )
        self._strip.begin()
        self.set_all_slots(config.COLOR_OFF)
        log.info("LED controller initialised — %d LEDs on GPIO %d",
                 config.NEOPIXEL_COUNT, config.NEOPIXEL_PIN)

    # ------------------------------------------------------------------
    def set_slot_color(self, slot_number: int, color: tuple) -> None:
        """Set a single slot LED to the given (R, G, B) colour."""
        if not (1 <= slot_number <= config.NUM_SLOTS):
            log.warning("set_slot_color: invalid slot %d", slot_number)
            return
        idx = slot_number - 1
        with self._lock:
            self._strip.setPixelColor(idx, Color(*color))
            self._strip.show()

    # ------------------------------------------------------------------
    def set_all_slots(self, color: tuple) -> None:
        """Set all slot LEDs to the same colour."""
        with self._lock:
            for idx in range(config.NEOPIXEL_COUNT):
                self._strip.setPixelColor(idx, Color(*color))
            self._strip.show()

    # ------------------------------------------------------------------
    def update_all_from_db(self, slots: list[dict]) -> None:
        """
        Bulk-update all LEDs from a list of slot state dicts.
        Each dict must have 'slot_id' and 'led_state' keys.
        """
        color_map = {
            "BLUE":  config.COLOR_BLUE,
            "RED":   config.COLOR_RED,
            "GREEN": config.COLOR_GREEN,
            "WHITE": config.COLOR_WHITE,
            "OFF":   config.COLOR_OFF,
        }
        with self._lock:
            for slot in slots:
                idx = slot["slot_id"] - 1
                color = color_map.get(slot.get("led_state", "OFF"), config.COLOR_OFF)
                self._strip.setPixelColor(idx, Color(*color))
            self._strip.show()
        log.debug("LED strip updated from DB (%d slots)", len(slots))

    # ------------------------------------------------------------------
    def pulse_slot(self, slot_number: int, color: tuple, duration: float = 1.0,
                   hz: float = 4.0) -> None:
        """
        Blink a slot LED at `hz` frequency for `duration` seconds.
        Runs in the calling thread (use a background thread if needed).
        """
        interval = 1.0 / (hz * 2)
        end_time = time.time() + duration
        on = True
        while time.time() < end_time:
            self.set_slot_color(slot_number, color if on else config.COLOR_OFF)
            on = not on
            time.sleep(interval)
