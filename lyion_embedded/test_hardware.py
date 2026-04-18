#!/usr/bin/env python3
# =============================================================================
# test_hardware.py — Hardware validation script for Ly-ion RPi controller.
#
# Tests (in order):
#   1. LED strip: cycles all 24 LEDs through each colour
#   2. GPIO expanders: reads all detection inputs, prints state table
#   3. Solenoid unlock: pulses each slot relay one by one (prompts for confirm)
#   4. RFID reader: waits for a card tap and prints the UID
#
# Run as: python3 test_hardware.py [--leds] [--gpio] [--solenoids] [--rfid]
# With no arguments, all tests run.
# =============================================================================

import sys
import time
import argparse

# ---------------------------------------------------------------------------
# Ensure the lyion_embedded directory is on sys.path when running standalone
# ---------------------------------------------------------------------------
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from utils.logger import get_logger

log = get_logger("test_hardware")


# ===========================================================================
# Test 1: LED strip
# ===========================================================================
def test_leds():
    from hardware.leds import LEDController
    print("\n=== Test 1: LED strip ===")
    leds = LEDController()

    sequences = [
        ("ALL OFF",   config.COLOR_OFF),
        ("ALL BLUE",  config.COLOR_BLUE),
        ("ALL WHITE", config.COLOR_WHITE),
        ("ALL RED",   config.COLOR_RED),
        ("ALL GREEN", config.COLOR_GREEN),
    ]
    for label, color in sequences:
        print(f"  {label} …", end=" ", flush=True)
        leds.set_all_slots(color)
        time.sleep(1)
        print("OK")

    print("  Cycling slot-by-slot BLUE …")
    leds.set_all_slots(config.COLOR_OFF)
    for slot in range(1, config.NUM_SLOTS + 1):
        leds.set_slot_color(slot, config.COLOR_BLUE)
        time.sleep(0.1)
        leds.set_slot_color(slot, config.COLOR_OFF)

    leds.set_all_slots(config.COLOR_OFF)
    print("LED test PASSED ✓")


# ===========================================================================
# Test 2: GPIO expanders — detection inputs
# ===========================================================================
def test_gpio():
    from hardware.gpio_expander import GPIOExpander
    print("\n=== Test 2: GPIO expanders (detection inputs) ===")
    gpio = GPIOExpander()
    readings = gpio.read_all_detections()

    print(f"  {'Slot':<6} {'Battery present?'}")
    print(f"  {'----':<6} {'-----------------'}")
    for slot_id, present in sorted(readings.items()):
        indicator = "YES (HIGH)" if present else "no  (LOW)"
        print(f"  {slot_id:<6} {indicator}")

    detected_count = sum(readings.values())
    print(f"\n  Total batteries detected: {detected_count} / {config.NUM_SLOTS}")
    print("GPIO detection test PASSED ✓")


# ===========================================================================
# Test 3: Solenoid relay — unlock each slot sequentially
# ===========================================================================
def test_solenoids():
    from hardware.gpio_expander import GPIOExpander
    print("\n=== Test 3: Solenoid relays ===")
    print("  WARNING: This will energise each solenoid relay for 1 second.")
    confirm = input("  Type 'yes' to proceed: ").strip().lower()
    if confirm != "yes":
        print("  Skipped.")
        return

    gpio = GPIOExpander()
    for slot in range(1, config.NUM_SLOTS + 1):
        print(f"  Unlocking slot {slot:>2} …", end=" ", flush=True)
        # Temporarily reduce unlock duration for the test
        original_duration = config.SOLENOID_UNLOCK_DURATION
        config.SOLENOID_UNLOCK_DURATION = 1
        gpio.unlock_slot(slot)
        config.SOLENOID_UNLOCK_DURATION = original_duration
        print("OK")
        time.sleep(0.3)

    print("Solenoid relay test PASSED ✓")


# ===========================================================================
# Test 4: RFID reader
# ===========================================================================
def test_rfid():
    from hardware.rfid import RFIDReader
    print("\n=== Test 4: RFID reader ===")
    print("  Present a student card to the RC522 reader (10-second timeout) …")
    reader = RFIDReader()
    timeout = time.time() + 10
    uid = None
    while time.time() < timeout:
        uid = reader.try_read()
        if uid:
            break
        time.sleep(0.2)

    if uid:
        print(f"  Card detected! UID: {uid}")
        print("RFID test PASSED ✓")
    else:
        print("  No card detected within timeout — RFID test SKIPPED")


# ===========================================================================
# Entry point
# ===========================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ly-ion hardware test suite")
    parser.add_argument("--leds",      action="store_true", help="Run LED test only")
    parser.add_argument("--gpio",      action="store_true", help="Run GPIO detection test only")
    parser.add_argument("--solenoids", action="store_true", help="Run solenoid relay test only")
    parser.add_argument("--rfid",      action="store_true", help="Run RFID reader test only")
    args = parser.parse_args()

    run_all = not any([args.leds, args.gpio, args.solenoids, args.rfid])

    print("=" * 50)
    print("  Ly-ion Hardware Test Suite")
    print("=" * 50)

    try:
        if run_all or args.leds:      test_leds()
        if run_all or args.gpio:      test_gpio()
        if run_all or args.solenoids: test_solenoids()
        if run_all or args.rfid:      test_rfid()
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as exc:
        print(f"\nTest FAILED: {exc}")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("  All selected tests completed.")
    print("=" * 50)
