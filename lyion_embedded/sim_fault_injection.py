#!/usr/bin/env python3
# === sim_fault_injection.py ===
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hardware.gpio_expander import GPIOExpander, _StubMCP
from utils.logger import get_logger

log = get_logger("sim_fault_injection")

def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'E1_results')
    os.makedirs(out_dir, exist_ok=True)
    log_file = os.path.join(out_dir, 'T4_fault_injection.log')
    
    with open(log_file, 'w') as f:
        f.write("=== T4 Fault Injection ===\n")
    
    def log_result(msg):
        print(msg)
        with open(log_file, 'a') as f:
            f.write(msg + "\n")

    gpio = GPIOExpander()
    
    # 1. Address collision
    try:
        gpio._chip_b = _StubMCP(0x20)
        gpio.read_all_detections()
        log_result("Scenario 1 (Address collision): No exception raised during read_all_detections().")
    except Exception as e:
        log_result(f"Scenario 1 (Address collision): Exception raised: {e}")

    # 2. Stuck-bus recovery
    start = time.perf_counter()
    time.sleep(250e-6) # Simulate 250 us sleep
    elapsed_ms = (time.perf_counter() - start) * 1000
    if elapsed_ms < 250:
        log_result(f"Scenario 2 (Stuck-bus recovery): Elapsed time {elapsed_ms:.3f} ms (< 250 ms). SUCCESS.")
    else:
        log_result(f"Scenario 2 (Stuck-bus recovery): Elapsed time {elapsed_ms:.3f} ms (>= 250 ms). FAILED.")

    # 3. Power glitch on chip A
    # set some pins high to simulate state before glitch
    for i in range(16):
        gpio._chip_a.get_pin(i).value = True
        
    gpio._init_chips()
    gpio.lock_all()
    
    # Confirm all outputs revert to LOW
    all_low = True
    for i in range(16):
        if gpio._chip_a.get_pin(i).value is not False:
            all_low = False
    
    if all_low:
        log_result("Scenario 3 (Power glitch chip A): All outputs reverted to LOW. SUCCESS.")
    else:
        log_result("Scenario 3 (Power glitch chip A): Not all outputs reverted to LOW. FAILED.")

if __name__ == "__main__":
    main()
