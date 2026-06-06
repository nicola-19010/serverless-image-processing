# Analysis & Reporting

The analysis is split into 3 data-source tiers + 1 cost tier. See
`analysis/README.md` for the rationale.

```
analysis/
├── locust/             ← client-side timings (already done)
├── cloudwatch/         ← server-side Lambda metrics (REQUIRED by prof)
├── cross_reference/    ← Locust vs CloudWatch
└── cost/               ← 6-month projection (R4 requirement)
```

---

## Step 1 — Locust analysis (already completed)

The Jupyter notebook in `analysis/locust/analyze_locust.ipynb` reads every
`*_stats.csv` from `load-tests/results/` and produces:

- `p95_vs_users.png`
- `throughput_vs_users.png`
- `errors_vs_users.png`
- `p95_vs_size.png`
- `summary_table.csv`

If you need to regenerate them after re-running scenarios:

```cmd
.venv\Scripts\activate
jupyter notebook analysis\locust\analyze_locust.ipynb
```

---

## Step 2 — Download CloudWatch CSVs

For each Lambda (resize-fn, grayscale-fn, edge-fn) export 4 metrics from
the CloudWatch console:

- Invocations (Sum)
- Duration (Average)
- ConcurrentExecutions (Maximum)
- Errors (Sum)

Drop the 12 resulting files into `load-tests/results/cloudwatch/` using the
naming `{operation}_{metric}.csv`. Full step-by-step instructions in
`load-tests/results/cloudwatch/README.md`.

---

## Step 3 — Run the CloudWatch analysis

```cmd
python analysis\cloudwatch\analyze_cloudwatch.py
```

Produces in `analysis/cloudwatch/charts/`:

- `concurrent_executions_over_time.png` ← required by professor
- `duration_over_time.png` ← required
- `duration_distribution.png`
- `invocations_over_time.png` ← required
- `errors_over_time.png`
- `summary_table.csv` (avg / p95 / max Duration, max concurrency, total errors)

---

## Step 4 — Cross-reference Locust vs CloudWatch

```cmd
python analysis\cross_reference\compare_locust_vs_cloudwatch.py
```

Produces:

- `locust_vs_cloudwatch_p95.png` — for each operation × users, plots both the
  client-side p95 (solid line) and server-side p95 (dashed). The gap is the
  network + API Gateway overhead.
- `overhead_table.csv` — same data in tabular form.

---

## Step 5 — Cost projection

```cmd
python analysis\cost\cost_projection.py
```

Uses the measured Duration from CloudWatch automatically (falls back to
default if no CW data is present). Produces:

- `cost_breakeven.png` — Lambda vs EC2 over a range of monthly image volumes,
  with the break-even point marked.
- `cost_table.csv` — same data in tabular form.

---

## Charts you should end up with (master list)

| # | Chart | From | Required? |
|---|---|---|---|
| 1 | Concurrent executions over time | CloudWatch | ✅ Required (prof cites textual) |
| 2 | Server-side Duration over time + distribution | CloudWatch | ✅ Required |
| 3 | Invocations over time | CloudWatch | ✅ Required |
| 4 | Errors over time | CloudWatch | Nice to have |
| 5 | Response time (p95) vs concurrent users | Locust | ✅ Required (response time vs load) |
| 6 | Throughput vs concurrent users | Locust | Recommended |
| 7 | Error rate vs concurrent users | Locust | Recommended |
| 8 | Response time vs image size | Locust | ✅ Required (small/medium/large) |
| 9 | Locust p95 vs CloudWatch p95 (network overhead) | Cross-ref | Bonus, differentiating |
| 10 | Cost projection (Lambda vs EC2) | Cost | ✅ Required (R4) |

---

## Report structure (suggested)

1. **Introduction** (~1 page)
   - Project goals, option chosen, group members
   - Brief description of what was implemented

2. **System architecture** (~2 pages)
   - Diagram: client → API Gateway → 3 Lambdas
   - Why 3 separate Lambdas (microservices principle)
   - Brief description of each operation's algorithm

3. **Experimental design** (~1 page)
   - Image sets and sizes
   - Load levels and reasoning (1, 10, 50, 100 — explain why 200 was dropped)
   - Tools: **CloudWatch (server-side)** + **Locust (client-side)**
   - Scenario matrix table (72 runs)

4. **Server-side results (CloudWatch)** (~2 pages, the heart of the report)
   - Concurrent executions, Invocations, Duration
   - These are the metrics the prof asked for textually

5. **Client-side results (Locust)** (~2 pages)
   - End-to-end p95 vs load, throughput, errors
   - Variation by image size

6. **Cross-reference: overhead analysis** (~1 page)
   - Gap between Locust and CloudWatch p95
   - Discussion: what fraction of total latency is non-Lambda

7. **Cost analysis** (~1 page)
   - 6-month projection chart
   - Break-even point
   - Discussion: when to use Lambda vs EC2

8. **Discussion & limitations** (~1 page)
   - Vocareum credit constraints (200-users dropped, 5 min → 2 min runs)
   - Sandbox limitations
   - What we'd do differently with more time

9. **Conclusions** (~0.5 page)

---

## Presentation slides (15 min)

- 1: Title + group
- 2: Problem statement & option chosen
- 3: Architecture diagram
- 4: Image operations (brief)
- 5: Experimental setup
- 6: Results — server-side (CloudWatch)
- 7: Results — client-side (Locust)
- 8: Results — cross-reference (overhead)
- 9: Cost comparison
- 10: Conclusions
- 11: Limitations & future work
- 12: Q&A placeholder

Each member presents 4 slides. Practice once with a stopwatch.
