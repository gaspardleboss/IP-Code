# Ly-ion — Smart Power Bank Rental System

A complete, production-ready software stack for a 24-slot RFID + QR-code power bank rental locker, designed for university campuses.

---

## Project Structure

```
IP Code/
├── lyion_embedded/       # Raspberry Pi 4 embedded controller (Python)
├── lyion_backend/        # Cloud backend (Flask + PostgreSQL)
├── lyion_app/            # Mobile app (React Native + Expo)
├── setup_rpi.sh          # One-command RPi setup script
├── docker-compose.yml    # Backend deployment (Flask + PostgreSQL + Nginx)
├── nginx.conf            # Nginx reverse proxy config
└── README.md             # This file
```

---

## Quick Start

### 1. Cloud Backend

**Prerequisites:** Docker, Docker Compose

```bash
# 1. Copy and fill in environment variables
cp lyion_backend/.env.example lyion_backend/.env
nano lyion_backend/.env      # Set SECRET_KEY, JWT_SECRET_KEY, STATION_API_KEY

# 2. (Optional) Place TLS certificates
mkdir certs
# Copy lyion.crt and lyion.key into ./certs/

# 3. Start everything
docker-compose up -d

# Verify backend is running
curl http://localhost/api/slots/station-001
```

The backend will be available at `http://localhost` (port 80 → 443 with TLS).
PostgreSQL data is persisted in the `pgdata` Docker volume.

**Import students:**
```bash
# CSV format: student_number,name,email
curl -X POST http://your-backend/api/admin/students/import \
     -H "X-Station-Key: your-station-key" \
     -F "file=@students.csv"
```

---

### 2. Raspberry Pi Embedded Controller

**Prerequisites:** Raspberry Pi 4, Raspberry Pi OS (64-bit), internet connection.

Hardware connections:
| Component | GPIO |
|-----------|------|
| RC522 MOSI | GPIO 10 |
| RC522 MISO | GPIO 9 |
| RC522 SCK  | GPIO 11 |
| RC522 CS   | GPIO 8 |
| RC522 RST  | GPIO 25 |
| WS2812B LEDs | GPIO 18 |
| MCP23017 SDA | GPIO 2 |
| MCP23017 SCL | GPIO 3 |

```bash
# On the Raspberry Pi:
git clone https://your-repo/lyion_embedded /tmp/lyion_repo
cd /tmp/lyion_repo
bash setup_rpi.sh

# Edit the config with your backend URL and API key
nano /home/pi/lyion_embedded/.env

# Start the service
sudo systemctl start lyion_embedded
sudo journalctl -u lyion_embedded -f
```

**Test hardware before going live:**
```bash
cd /home/pi/lyion_embedded
python3 test_hardware.py           # Run all tests
python3 test_hardware.py --leds    # LEDs only
python3 test_hardware.py --rfid    # RFID reader only
python3 test_hardware.py --solenoids  # Relay test (prompts for confirmation)
```

**Embedded `.env` variables:**
```env
BACKEND_URL=https://your-backend-url.com
API_SECRET=your-api-secret-key        # Must match STATION_API_KEY in backend
STATION_ID=station-001
DB_PATH=/home/pi/lyion_embedded/lyion_local.db
LOG_LEVEL=INFO
```

---

### 3. Mobile App

**Prerequisites:** Node.js 18+, Expo CLI (`npm install -g expo-cli`)

```bash
cd lyion_app

# Install dependencies
npm install

# Set your backend URL
nano services/api.js    # Change BACKEND_URL to your deployed backend

# Run in development
npx expo start

# Build for production
npx expo build:android
npx expo build:ios
```

**Expo dependencies used:**
- `expo-camera` / `expo-barcode-scanner` — QR code scanning
- `expo-secure-store` — encrypted JWT token storage
- `@react-navigation/native` + `@react-navigation/native-stack` + `@react-navigation/bottom-tabs`
- `@expo/vector-icons`

Install them:
```bash
npx expo install expo-camera expo-barcode-scanner expo-secure-store \
    @react-navigation/native @react-navigation/native-stack \
    @react-navigation/bottom-tabs @expo/vector-icons \
    react-native-screens react-native-safe-area-context
```

---

## System Flows

### RFID Rental (locker-side)
1. Student taps RFID card on RC522 reader
2. RPi checks local DB for active session → if found, it's a **return**
3. If no session: RPi calls `POST /api/rent` with card UID
4. Backend selects best charged battery, creates session, returns slot number
5. RPi energises solenoid relay → slot unlocks (3 s)
6. LED turns GREEN; student removes battery
7. **Offline fallback**: if backend unreachable, RPi checks local `allowed_cards` table

### RFID Return
1. Student taps card again → RPi finds active session
2. Detection input confirms battery is present in the slot
3. Session closed, LED turns WHITE (charging), event queued for sync

### QR Code Rental (app-side)
1. Student opens app → taps "Scanner" tab
2. Camera scans `lyion://station/<token>` QR code on locker
3. App calls `GET /api/slots/<station_id>` → displays 24-slot grid
4. Student taps a BLUE slot → confirm screen
5. App calls `POST /api/rent` with JWT → backend returns slot number
6. Backend instructs RPi via heartbeat/sync to unlock the slot

---

## Adaptability

The system is designed to work with **any university's student database**:

| Mechanism | Description |
|-----------|-------------|
| CSV import | `POST /api/admin/students/import` — upload `student_number,name,email` CSV |
| JSON sync | `POST /api/admin/students/sync-external` — push JSON from any SIS |
| Env config | School name, logo URL, deposit amount, max rental duration via `.env` |
| Card registration | Students link RFID card once via mobile app (`POST /api/auth/register-card`) |

---

## MCP23017 GPIO Mapping (Final)

| Chip | Address | Port | Direction | Function |
|------|---------|------|-----------|----------|
| CHIP A | 0x20 | GPA (0-7) | OUTPUT | Solenoid relays — slots 1-8 |
| CHIP A | 0x20 | GPB (0-7) | OUTPUT | Solenoid relays — slots 9-16 |
| CHIP B | 0x21 | GPA (0-7) | OUTPUT | Solenoid relays — slots 17-24 |
| CHIP B | 0x21 | GPB (0-7) | INPUT  | Battery detection — slots 17-24 |
| CHIP C | 0x22 | GPA (0-7) | INPUT  | Battery detection — slots 1-8 |
| CHIP C | 0x22 | GPB (0-7) | INPUT  | Battery detection — slots 9-16 |

Detection: pin reads **HIGH** when battery is inserted (pogo pins → optocoupler → HIGH).  
Solenoid: relay energises (unlocks) when pin is set **HIGH**.

---

## LED Colour Codes

| Colour | State |
|--------|-------|
| BLUE (0, 0, 255) | Battery present, charged (>80%) — available to rent |
| WHITE dim (30, 30, 30) | Battery present, currently charging (<80%) |
| RED (255, 0, 0) | Battery present but not rentable (defective / anomaly) |
| GREEN (0, 255, 0) | Slot unlocked — battery removed by user |
| OFF (0, 0, 0) | Slot empty, locked (maintenance) |

---

## Security Notes

- All station-to-backend communication is authenticated with `X-Station-Key`
- Student authentication uses short-lived JWTs (1 h) with refresh tokens (30 d)
- Tokens are stored in `expo-secure-store` (iOS Keychain / Android Keystore)
- No student data is hardcoded; `allowed_cards` is populated via admin API
- The `.env` file is never committed; use `.env.example` as a template

---

## File Reference

| File | Purpose |
|------|---------|
| `lyion_embedded/main.py` | Entry point, 4 threads |
| `lyion_embedded/config.py` | All hardware + network config |
| `lyion_embedded/hardware/rfid.py` | RC522 RFID reader |
| `lyion_embedded/hardware/leds.py` | WS2812B LED controller |
| `lyion_embedded/hardware/gpio_expander.py` | MCP23017 manager |
| `lyion_embedded/hardware/slots.py` | High-level slot API |
| `lyion_embedded/database/models.py` | SQLite schema + init |
| `lyion_embedded/database/local_db.py` | DB read/write functions |
| `lyion_embedded/network/api_client.py` | HTTP client for backend |
| `lyion_embedded/network/sync.py` | Cloud sync logic |
| `lyion_embedded/test_hardware.py` | Hardware validation script |
| `lyion_backend/app.py` | Flask app factory |
| `lyion_backend/models.py` | SQLAlchemy / PostgreSQL models |
| `lyion_backend/routes/auth.py` | Auth endpoints |
| `lyion_backend/routes/rental.py` | Rent / return endpoints |
| `lyion_backend/routes/admin.py` | Admin + CSV import |
| `lyion_backend/routes/sync.py` | RPi sync endpoints |
| `lyion_backend/migration.sql` | PostgreSQL schema DDL |
| `lyion_app/App.js` | React Native root |
| `lyion_app/navigation/AppNavigator.js` | Navigation stack |
| `lyion_app/screens/` | All app screens |
| `lyion_app/components/` | SlotGrid + SlotCard |
| `lyion_app/services/api.js` | Backend API calls |
| `lyion_app/services/auth.js` | JWT storage + refresh |
| `docker-compose.yml` | Docker stack definition |
| `setup_rpi.sh` | RPi one-command setup |
