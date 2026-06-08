import csv
from pathlib import Path
from collections import defaultdict

results_dir = r"c:\Users\npach\OneDrive\Documentos\Claude\Projects\Cloud Computing\project\load-tests\results"

# Aggregate by operation (resize, grayscale, edge)
operation_data = defaultdict(list)

for csv_file in Path(results_dir).glob("*_stats.csv"):
    # Skip history files
    if "history" in csv_file.name:
        continue
    
    # Extract operation name
    parts = csv_file.stem.split('_')
    operation = parts[0]  # resize, grayscale, or edge
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip aggregated row, only take the named operation
                if row['Name'] != operation + '-' + '-'.join(parts[1:]).rsplit('_', 3)[0]:
                    if row['Name'] and row['Name'] != 'Aggregated':
                        continue
                
                try:
                    p95 = float(row['95%'])
                    req_count = int(row['Request Count'])
                    operation_data[operation].append({
                        'p95': p95,
                        'req_count': req_count,
                        'file': csv_file.name
                    })
                except (ValueError, KeyError):
                    pass
    except Exception as e:
        print(f"Error processing {csv_file.name}: {e}")

print("P95 values by operation:\n")
for op in ['resize', 'grayscale', 'edge']:
    if op in operation_data:
        p95_values = [d['p95'] for d in operation_data[op]]
        req_counts = [d['req_count'] for d in operation_data[op]]
        
        avg_p95 = sum(p95_values) / len(p95_values) if p95_values else 0
        weighted_p95 = sum(p['p95'] * p['req_count'] for p in operation_data[op]) / sum(r['req_count'] for r in operation_data[op]) if req_counts else 0
        
        print(f"{op.upper()}:")
        print(f"  Count: {len(p95_values)} files")
        print(f"  Min p95: {min(p95_values):.1f} ms")
        print(f"  Max p95: {max(p95_values):.1f} ms")
        print(f"  Avg p95: {avg_p95:.1f} ms")
        print(f"  Weighted p95: {weighted_p95:.1f} ms")
        print()
