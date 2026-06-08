import csv
from pathlib import Path
from collections import defaultdict

results_dir = r"c:\Users\npach\OneDrive\Documentos\Claude\Projects\Cloud Computing\project\load-tests\results"

# Count total invocations by operation
op_invocations = defaultdict(int)

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
                # Get aggregated row
                if row['Name'] == 'Aggregated' or (row['Name'] and 'Aggregated' in row['Name']):
                    req_count = int(row['Request Count'])
                    op_invocations[operation] += req_count
                    break
    except Exception as e:
        pass

print("Total invocations by operation:")
print(f"  resize: {op_invocations['resize']:,}")
print(f"  grayscale: {op_invocations['grayscale']:,}")
print(f"  edge: {op_invocations['edge']:,}")
print(f"\nReported in document:")
print(f"  resize: 17,342")
print(f"  grayscale: 17,521")
print(f"  edge: 17,409")
