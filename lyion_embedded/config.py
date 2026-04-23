# =============================================================================
# config.py — Ly-ion Embedded System Configuration
# All hardware pin mappings, thresholds, and network parameters.
# Edit this file to adapt the system to different hardware revisions.
# =============================================================================

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Pogo Pin LED State Constants
# ---------------------------------------------------------------------------
POGO_LED_READY     = "READY"     # Battery charged (>80%) - Blue solid
POGO_LED_FAULT     = "FAULT"     # Defective / Anomaly - Red flashing
POGO_LED_UNLOCKED  = "UNLOCKED"  # Slot unlocked - Green solid
POGO_LED_CHARGING  = "CHARGING"  # Charging (<80%) - Cyan pulsed
POGO_LED_OFF       = "OFF"       # Unused / slot empty

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
