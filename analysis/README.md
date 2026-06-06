# Analysis — folder layout

The analysis is split into 4 sub-folders by **data source**, because the
professor's required metrics come from different places and we want it crystal
clear which chart was generated from which data.

```
analysis/
├── locust/                  ← client-side metrics (already done)
│   ├── analyze_locust.ipynb
│   └── charts/
│       ├── errors_vs_users.png
│       ├── p95_vs_size.png
│       ├── p95_vs_users.png
│       ├── summary_table.csv
│       └── throughput_vs_users.png
│
├── cloudwatch/              ← server-side metrics (REQUIRED by the prof)
│   ├── analyze_cloudwatch.py
│   └── charts/              ← populated after running the script
│
├── cross_reference/         ← Locust vs CloudWatch comparison
│   ├── compare_locust_vs_cloudwatch.py
│   └── charts/              ← populated after running the script
│
└── cost/                    ← 6-month cost projection (R4 requirement)
    ├── cost_projection.py
    └── charts/              ← populated after running the script
```

## Why the split

### `locust/` — End-to-end client-side timings
What we already measured during the 72-scenario battery. Captures the **total
latency from the user's perspective**:

> network upload + API Gateway + cold start + Lambda execution + network download

Already produced 5 charts (response time p95 vs users, throughput, errors, etc).

### `cloudwatch/` — Server-side Lambda metrics
The metrics the professor cites textually in the assignment:

> *"AWS Lambda metrics like concurrency, number of invocations, and duration"*

Locust does **not** give us these — only CloudWatch does. The script in this
folder reads the manually-downloaded CSVs from
`load-tests/results/cloudwatch/` and produces:

- Concurrent executions over time
- Server-side Duration over time + distribution
- Invocations rate over time
- Errors over time
- A summary table (avg / p95 / max Duration, max concurrency, total errors)

### `cross_reference/` — Locust ↔ CloudWatch comparison
For each Locust scenario, computes the **difference** between client-side
response time and server-side Lambda duration. That delta represents network
+ API Gateway + cold-start overhead — a rich finding for the report.

### `cost/` — 6-month cost projection
Required by recommendation R4 of the assignment. Compares Lambda cost vs
EC2 t3.small over a range of monthly image volumes and marks the break-even
point. **Uses the measured Duration from CloudWatch automatically** — so
it should be run **after** `analyze_cloudwatch.py`.

## Order of execution

```cmd
:: Run from project root with the venv active

:: 1. Locust analysis (already done — re-run only if data changed)
jupyter notebook analysis\locust\analyze_locust.ipynb

:: 2. CloudWatch analysis — REQUIRES downloading CSVs first
::    See load-tests\results\cloudwatch\README.md
python analysis\cloudwatch\analyze_cloudwatch.py

:: 3. Cross-reference (Locust vs CloudWatch)
python analysis\cross_reference\compare_locust_vs_cloudwatch.py

:: 4. Cost projection
python analysis\cost\cost_projection.py
```

## Mapping: required deliverable → folder

| Professor's requirement | Where to look |
|---|---|
| Concurrency vs workload | `cloudwatch/charts/concurrent_executions_over_time.png` |
| Number of invocations | `cloudwatch/charts/invocations_over_time.png` + summary table |
| Server-side Duration | `cloudwatch/charts/duration_*.png` + summary table |
| Response time vs workload | `locust/charts/p95_vs_users.png` (end-to-end) + `cross_reference/charts/locust_vs_cloudwatch_p95.png` (decomposed) |
| Response time vs image size | `locust/charts/p95_vs_size.png` |
| 6-month cost vs alternative deployment (R4) | `cost/charts/cost_breakeven.png` |
| Error rate under load | `locust/charts/errors_vs_users.png` + `cloudwatch/charts/errors_over_time.png` |
