import csv
import os
from pathlib import Path

results_dir = r"c:\Users\npach\OneDrive\Documentos\Claude\Projects\Cloud Computing\project\load-tests\results"
total_failures = 0
detail_dict = {}

for csv_file in Path(results_dir).glob("*_failures.csv"):
    file_failures = 0
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                occurrences = int(row.get('Occurrences', 0))
                file_failures += occurrences
                total_failures += occurrences
    except Exception as e:
        pass
    
    if file_failures > 0:
        detail_dict[csv_file.stem] = file_failures

print(f"Total failures across all tests: {total_failures}\n")
print("Files with failures:")
for filename in sorted(detail_dict.keys()):
    print(f"  {filename}: {detail_dict[filename]}")
