#!/usr/bin/env python3
# === sim_i2c_timing.py ===
import sys
import os
import time
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hardware.gpio_expander import GPIOExpander
from utils.logger import get_logger

log = get_logger("sim_i2c_timing")

def main():
    gpio = GPIOExpander()
    
    # Time 1000 calls to read_all_detections()
    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        gpio.read_all_detections()
    end = time.perf_counter()
    
    simulated_scan_s = (end - start) / iterations
    
    # Theoretical 24-slot scan at 400 kHz
    # 24 reads, 110 us per read
    theoretical_scan_s = 24 * 110e-6
    
    period_s = 500e-3
    bus_load_percent = (theoretical_scan_s / period_s) * 100
    
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'E1_results')
    os.makedirs(out_dir, exist_ok=True)
    
    csv_path = os.path.join(out_dir, 'T2_timing_budget.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['theoretical_scan', 'simulated_scan', 'period', 'bus_load_percent'])
        writer.writerow([theoretical_scan_s, simulated_scan_s, period_s, bus_load_percent])
        
    summary = (
        f"=== T2 I2C Timing Budget ===\n"
        f"Theoretical scan time : {theoretical_scan_s * 1000:.3f} ms\n"
        f"Simulated scan time   : {simulated_scan_s * 1000:.3f} ms\n"
        f"Slot-monitor period   : {period_s * 1000:.0f} ms\n"
        f"Bus load              : {bus_load_percent:.3f} %\n"
    )
    print(summary)
    
    log_path = os.path.join(out_dir, 'T2_timing.log')
    with open(log_path, 'w') as f:
        f.write(summary)

if __name__ == "__main__":
    main()
