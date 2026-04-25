import os
import csv

SUB_PROJECTS = {
    'lyion_embedded': {'.py'},
    'lyion_backend': {'.py'},
    'lyion_app': {'.js', '.jsx', '.ts', '.tsx'}
}
IGNORE_DIRS = {'__pycache__', 'node_modules', '.git', '.venv'}

def count_metrics(file_path, ext):
    loc = 0
    functions = 0
    classes = 0
    todos = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                
                # Check for comments
                is_comment = False
                if ext == '.py':
                    if stripped.startswith('#'):
                        is_comment = True
                elif ext in {'.js', '.jsx', '.ts', '.tsx'}:
                    if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                        is_comment = True
                
                if not is_comment:
                    loc += 1
                
                if 'TODO' in line or 'FIXME' in line:
                    todos += 1
                    
                if ext == '.py':
                    if line.startswith('def '):
                        functions += 1
                    elif line.startswith('class '):
                        classes += 1
    except Exception:
        pass
        
    return loc, functions, classes, todos

def main():
    results = []
    
    totals = {sp: {'loc': 0, 'functions': 0, 'classes': 0, 'todos': 0} for sp in SUB_PROJECTS}
    grand_total_loc = 0
    
    for sp, exts in SUB_PROJECTS.items():
        if not os.path.isdir(sp):
            continue
            
        for root, dirs, files in os.walk(sp):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in exts:
                    path = os.path.join(root, file)
                    loc, f, c, t = count_metrics(path, ext)
                    
                    results.append({
                        'sub_project': sp,
                        'file': path,
                        'loc': loc,
                        'functions': f,
                        'classes': c,
                        'todos': t
                    })
                    
                    totals[sp]['loc'] += loc
                    totals[sp]['functions'] += f
                    totals[sp]['classes'] += c
                    totals[sp]['todos'] += t
                    grand_total_loc += loc
                    
    os.makedirs('E4_results', exist_ok=True)
    with open('E4_results/T7_code_metrics.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['sub_project', 'file', 'loc', 'functions', 'classes', 'todos'])
        writer.writeheader()
        writer.writerows(results)
        
    with open('E4_results/T7_code_metrics_summary.log', 'w') as f:
        f.write("=== Code Metrics Summary ===\n\n")
        for sp, stats in totals.items():
            f.write(f"[{sp}]\n")
            f.write(f"  LOC:       {stats['loc']}\n")
            f.write(f"  Functions: {stats['functions']}\n")
            f.write(f"  Classes:   {stats['classes']}\n")
            f.write(f"  TODOs:     {stats['todos']}\n\n")
            
        f.write(f"GRAND TOTAL LOC: {grand_total_loc}\n")

if __name__ == '__main__':
    main()
