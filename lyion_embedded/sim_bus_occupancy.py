#!/usr/bin/env python3
# === sim_bus_occupancy.py ===
import os
import sys
import csv
import matplotlib.pyplot as plt

def main():
    duration_s = 600
    bins = [0.0] * duration_s
    
    # Durations in seconds
    slot_monitor_dur = 24 * 110e-6
    charge_monitor_dur = 24 * (110e-6 + 120e-6)
    
    # Add triggers
    for t_ms in range(0, duration_s * 1000, 500):
        bin_idx = t_ms // 1000
        if bin_idx < duration_s:
            bins[bin_idx] += slot_monitor_dur
            
    for t_ms in range(0, duration_s * 1000, 60000):
        bin_idx = t_ms // 1000
        if bin_idx < duration_s:
            bins[bin_idx] += charge_monitor_dur
            
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'E1_results')
    os.makedirs(out_dir, exist_ok=True)
    
    csv_path = os.path.join(out_dir, 'T3_bus_occupancy.csv')
    times_s = list(range(duration_s))
    loads = [b / 1.0 * 100 for b in bins]
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time_s', 'bus_busy_s', 'load_percent'])
        for t, b, l in zip(times_s, bins, loads):
            writer.writerow([t, b, l])
            
    plt.figure(figsize=(10, 4), dpi=150)
    plt.plot(times_s, loads, label='I²C Bus Load')
    plt.title("Simulated I²C bus occupancy — 10 min")
    plt.xlabel("Time (s)")
    plt.ylabel("I²C bus load (%)")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'Figure_8_bus_occupancy.png'))
    
    avg_load = sum(loads) / len(loads)
    peak_load = max(loads)
    print(f"=== T3 Bus Occupancy ===")
    print(f"Average Load : {avg_load:.3f} %")
    print(f"Peak Load    : {peak_load:.3f} %")

if __name__ == "__main__":
    main()
