# =============================================================================
# config.py — Ly-ion Embedded System Configuration
# All hardware pin mappings, thresholds, and network parameters.
# Edit this file to adapt the system to different hardware revisions.
# =============================================================================

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Neopixel (WS2812B) LED strip
# ---------------------------------------------------------------------------
NEOPIXEL_PIN = 18          # GPIO pin (PWM-capable) driving the LED data line
NEOPIXEL_COUNT = 24        # Total number of LEDs (one per slot)
NEOPIXEL_BRIGHTNESS = 255  # 0-255 global brightness

# LED color constants (R, G, B)
COLOR_BLUE  = (0,   0,   255)   # Battery present, charged (>80%), available
COLOR_RED   = (255, 0,   0)     # Battery present but NOT rentable
COLOR_GREEN = (0,   255, 0)     # Slot unlocked / battery removed by user
COLOR_WHITE = (30,  30,  30)    # Battery present, currently charging (<80%)
COLOR_OFF   = (0,   0,   0)     # Slot empty and locked (maintenance / no battery)

# ---------------------------------------------------------------------------
# RFID reader (RC522 / MFRC522 via SPI)
# ---------------------------------------------------------------------------
RFID_RST_PIN   = 25   # GPIO reset pin for RC522
RFID_POLL_MS   = 200  # Polling interval in milliseconds

# ---------------------------------------------------------------------------
# I2C GPIO expanders (MCP23017)
# ---------------------------------------------------------------------------
I2C_CHIP_A = 0x20   # CHIP A: all 16 pins = OUTPUTS → solenoid relays slots 1-16
I2C_CHIP_B = 0x21   # CHIP B: GPA = OUTPUTS (solenoids 17-24), GPB = INPUTS (detection 17-24)
I2C_CHIP_C = 0x22   # CHIP C: all 16 pins = INPUTS → battery detection slots 1-16

# ---------------------------------------------------------------------------
# Solenoid relay control
# ---------------------------------------------------------------------------
SOLENOID_UNLOCK_DURATION = 3   # Seconds solenoid stays energised (unlocked)

# ---------------------------------------------------------------------------
# Battery / charging thresholds
# ---------------------------------------------------------------------------
BATTERY_CHARGED_THRESHOLD      = 80      # % — above this = BLUE (ready to rent)
CHARGING_ANOMALY_CURRENT_MIN   = 0.1     # Amps — below this after insertion = anomaly
CHARGING_ANOMALY_TIME_MAX      = 14400   # 4 h in seconds — max normal charge time

# ---------------------------------------------------------------------------
# Slot count
# ---------------------------------------------------------------------------
NUM_SLOTS = 24

# ---------------------------------------------------------------------------
# Network / cloud backend
# ---------------------------------------------------------------------------
BACKEND_URL  = os.getenv("BACKEND_URL",  "http://localhost:5000")
API_SECRET   = os.getenv("API_SECRET",   "change-me-in-production")
STATION_ID   = os.getenv("STATION_ID",   "station-001")
SYNC_INTERVAL = 30   # Seconds between cloud sync cycles

# ---------------------------------------------------------------------------
# Local SQLite database
# ---------------------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", "/home/pi/lyion_embedded/lyion_local.db")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE  = os.getenv("LOG_FILE",  "/home/pi/lyion_embedded/lyion.log")
