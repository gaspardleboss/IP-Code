import os
import csv

REQUIREMENTS = [
    ("R-FUN-01", "RFID card scan triggers rental", "lyion_embedded/main.py::rfid_loop"),
    ("R-FUN-02", "Solenoid unlocks the assigned slot", "lyion_embedded/hardware/gpio_expander.py::unlock_slot"),
    ("R-FUN-03", "Battery presence is detected on insertion/removal", "lyion_embedded/main.py::slot_monitor_loop"),
    ("R-FUN-04", "Charging state is tracked and exposed via LED", "lyion_embedded/main.py::charging_monitor_loop"),
    ("R-FUN-05", "Rental sessions are persisted locally", "lyion_embedded/database/local_db.py::create_session"),
    ("R-FUN-06", "Local DB synchronises with cloud when online", "lyion_embedded/network/sync.py::run_sync_cycle"),
    ("R-FUN-07", "Offline rental fallback via allowed_cards cache", "lyion_embedded/main.py::_handle_rental_request"),
    ("R-FUN-08", "Cloud REST API exposes rent/return endpoints", "lyion_backend/routes/*"),
    ("R-FUN-09", "Mobile app shows real-time slot availability", "lyion_app/src/screens/*"),
    ("R-FUN-10", "Hardware abstraction allows hardware-less simulation", "lyion_embedded/hardware/gpio_expander.py::_StubMCP"),
    ("R-FUN-11", "Anomalies are logged and slot flagged FAULT", "lyion_embedded/main.py::_on_battery_removed"),
    ("R-FUN-12", "Concurrent threads cooperate without locking the DB", "lyion_embedded/database/models.py (WAL mode)")
]

def check_requirement(module):
    # handle special case where module has space suffix e.g. 'lyion_embedded/database/models.py (WAL mode)'
    actual_module = module.split(' ')[0]
    
    if actual_module.endswith('/*'):
        dir_path = actual_module[:-2]
        if os.path.isdir(dir_path) and any(os.scandir(dir_path)):
            return "VERIFIED"
        elif os.path.isdir(dir_path):
            return "PARTIAL"
        else:
            return "MISSING"
    elif '::' in actual_module:
        file_path, symbol = actual_module.split('::')
        if not os.path.isfile(file_path):
            return "MISSING"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if symbol in content:
                    return "VERIFIED"
                else:
                    return "PARTIAL"
        except Exception:
            return "MISSING"
    else:
        file_path = actual_module
        if not os.path.isfile(file_path):
            return "MISSING"
        try:
            if "(WAL mode)" in module:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "WAL" in content or "wal" in content.lower():
                        return "VERIFIED"
                    else:
                        return "PARTIAL"
            return "VERIFIED"
        except Exception:
            return "MISSING"

def main():
    results = []
    counts = {"VERIFIED": 0, "PARTIAL": 0, "MISSING": 0}
    
    for req_id, req_label, module in REQUIREMENTS:
        status = check_requirement(module)
        results.append({
            'req_id': req_id,
            'req_label': req_label,
            'module': module,
            'status': status
        })
        counts[status] += 1
        
    os.makedirs('E4_results', exist_ok=True)
    with open('E4_results/T8_traceability.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['req_id', 'req_label', 'module', 'status'])
        writer.writeheader()
        writer.writerows(results)
        
    total = len(REQUIREMENTS)
    coverage = (counts['VERIFIED'] / total) * 100 if total > 0 else 0
    
    with open('E4_results/T8_traceability_summary.log', 'w') as f:
        f.write("=== Traceability Summary ===\n\n")
        f.write(f"VERIFIED: {counts['VERIFIED']}\n")
        f.write(f"PARTIAL:  {counts['PARTIAL']}\n")
        f.write(f"MISSING:  {counts['MISSING']}\n\n")
        f.write(f"Overall Coverage: {coverage:.1f}%\n")

if __name__ == '__main__':
    main()
