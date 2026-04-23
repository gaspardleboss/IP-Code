"""
=============================================================================
sim_db_concurrency.py — E.3 Database Validation: Concurrency benchmark
=============================================================================
"""

import sqlite3
import threading
import time
import random
import csv
import matplotlib.pyplot as plt
import numpy as np

DB_PATH = "/Users/gaspardvanco/Desktop/E3_results/lyion_local_test.db"
CSV_PATH = "/Users/gaspardvanco/Desktop/E3_results/T6_concurrency.csv"
LOG_PATH = "/Users/gaspardvanco/Desktop/E3_results/T6_concurrency.log"
PLOT_PATH = "/Users/gaspardvanco/Desktop/E3_results/Figure_9_concurrency_histogram.png"

def reader_task(results, stop_event):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    count = 0
    busy_count = 0
    
    while count < 1000 and not stop_event.is_set():
        start_t = time.perf_counter()
        try:
            cur.execute("SELECT * FROM slots")
            cur.fetchall()
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e).lower() or 'busy' in str(e).lower():
                busy_count += 1
            # Still record the latency even on failure
        latency_us = (time.perf_counter() - start_t) * 1e6
        results.append(('reader', 'SELECT', latency_us))
        count += 1
        time.sleep(0.001)  # small sleep to avoid completely locking the GIL/CPU
        
    conn.close()
    return count, busy_count

def writer_task(results, stop_event):
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    cur = conn.cursor()
    count = 0
    busy_count = 0
    
    while count < 500 and not stop_event.is_set():
        slot_id = random.randint(1, 24)
        charge = random.randint(0, 100)
        start_t = time.perf_counter()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("UPDATE slots SET charge_level = ? WHERE slot_id = ?", (charge, slot_id))
            conn.commit()
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e).lower() or 'busy' in str(e).lower():
                busy_count += 1
            conn.rollback()
        latency_us = (time.perf_counter() - start_t) * 1e6
        results.append(('writer', 'UPDATE', latency_us))
        count += 1
        time.sleep(0.002)
        
    conn.close()
    return count, busy_count

def run_benchmark():
    random.seed(42)
    
    results = []
    stop_event = threading.Event()
    
    class ThreadResult:
        def __init__(self):
            self.count = 0
            self.busy = 0

    reader_res = ThreadResult()
    writer_res = ThreadResult()

    def r_wrapper():
        c, b = reader_task(results, stop_event)
        reader_res.count = c
        reader_res.busy = b

    def w_wrapper():
        c, b = writer_task(results, stop_event)
        writer_res.count = c
        writer_res.busy = b

    t1 = threading.Thread(target=r_wrapper)
    t2 = threading.Thread(target=w_wrapper)
    
    start_time = time.time()
    t1.start()
    t2.start()
    
    # Wait for 30 seconds or until both threads finish
    while t1.is_alive() or t2.is_alive():
        if time.time() - start_time > 30:
            stop_event.set()
            break
        time.sleep(0.1)
        
    t1.join()
    t2.join()

    # Write CSV
    with open(CSV_PATH, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['thread', 'query_type', 'latency_us'])
        for r in results:
            writer.writerow(r)
            
    # Compute stats
    reader_latencies = [r[2] for r in results if r[0] == 'reader']
    writer_latencies = [r[2] for r in results if r[0] == 'writer']
    
    def calc_stats(latencies):
        if not latencies:
            return 0, 0, 0, 0, 0
        return (
            np.mean(latencies),
            np.median(latencies),
            np.percentile(latencies, 95),
            np.percentile(latencies, 99),
            np.max(latencies)
        )
        
    r_stats = calc_stats(reader_latencies)
    w_stats = calc_stats(writer_latencies)
    
    log_lines = [
        "### Concurrency Benchmark Summary",
        f"**Reader Thread (SELECT)**",
        f"  - Total queries: {reader_res.count} / 1000",
        f"  - Mean latency:   {r_stats[0]:.2f} µs",
        f"  - Median latency: {r_stats[1]:.2f} µs",
        f"  - P95 latency:    {r_stats[2]:.2f} µs",
        f"  - P99 latency:    {r_stats[3]:.2f} µs",
        f"  - Max latency:    {r_stats[4]:.2f} µs",
        f"  - SQLITE_BUSY:    {reader_res.busy}",
        f"**Writer Thread (UPDATE)**",
        f"  - Total queries: {writer_res.count} / 500",
        f"  - Mean latency:   {w_stats[0]:.2f} µs",
        f"  - Median latency: {w_stats[1]:.2f} µs",
        f"  - P95 latency:    {w_stats[2]:.2f} µs",
        f"  - P99 latency:    {w_stats[3]:.2f} µs",
        f"  - Max latency:    {w_stats[4]:.2f} µs",
        f"  - SQLITE_BUSY:    {writer_res.busy}"
    ]
    
    log_text = "\n".join(log_lines)
    print(log_text)
    
    with open(LOG_PATH, "w") as f:
        f.write(log_text + "\n")
        
    # Plot histogram
    plt.figure(figsize=(10, 4), dpi=150)
    plt.hist(reader_latencies, bins=50, alpha=0.5, label='Reader (SELECT)', color='blue')
    plt.hist(writer_latencies, bins=50, alpha=0.5, label='Writer (UPDATE)', color='red')
    plt.xscale('log')
    plt.title("SQLite concurrent read/write latency — WAL mode, 30 s window")
    plt.xlabel("Latency (µs) — log scale")
    plt.ylabel("Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOT_PATH)
    plt.close()

if __name__ == "__main__":
    run_benchmark()
