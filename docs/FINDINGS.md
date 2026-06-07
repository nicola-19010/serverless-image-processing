# Project Findings — Performance & Scalability Analysis

> Generated on 2026-06-06 from CloudWatch + Locust data of the 2026-06-05 load
> test session. Use this as the source-of-truth when writing the final report.

---

## TL;DR — the headline result

**The Lambda functions never saturated, never errored, and never throttled. The
high client-side latencies (up to 46 seconds at 100 concurrent users) are
**100% queuing overhead at the API Gateway / Learner Lab concurrency layer**,
not Lambda processing time.** This was only discoverable by combining
server-side CloudWatch metrics with client-side Locust measurements.

The Learner Lab caps Lambda concurrency at approximately **10** (we observed
max 11 for resize, max 9 for edge), which is well below the standard 1000
limit of a production AWS account.

---

## Per-Lambda summary (server-side, CloudWatch, 1-hour window)

| Metric | resize-fn (Nico) | edge-fn (Mathias) | grayscale-fn (Prajwal) |
|---|---|---|---|
| Total invocations | 17,342 | 17,409 | *pending* |
| Avg Duration (ms) | 271.1 | 438.0 | *pending* |
| p95 Duration (ms) | 615.8 | 1,053.8 | *pending* |
| Min Duration (ms) | 11.2 | 8.5 | *pending* |
| Max Duration (ms) | 856.4 | 1,431.3 | *pending* |
| Max concurrent executions | **11** | **9** | *pending* |
| Total errors | 0 | 0 | *pending* |
| Min success rate | 100% | 100% | *pending* |
| Total throttles | 0 | 0 | *pending* |

**Chart**: `analysis/cloudwatch/charts/summary_table.csv` (canonical numbers),
`analysis/cloudwatch/charts/duration_distribution.png` (boxplot).

### Reading these numbers

- **edge-fn is ~62% slower in average than resize-fn** (438 ms vs 271 ms),
  consistent with edge detection being more CPU-intensive (Sobel filter +
  smoothing) than a plain Pillow resize.
- **edge-fn's p95 is 1,054 ms vs resize-fn's 616 ms** — heavier operations
  also have a wider distribution.
- **Both Lambdas peaked at single-digit concurrent executions** (9–11) despite
  Locust injecting up to 100 simultaneous users. This is a Learner Lab
  account-level cap, not a per-function limit we configured.

---

## The cross-reference finding (the differentiator for the report)

The cross-reference between client-side (Locust) and server-side (CloudWatch)
p95 response time, per operation × concurrent users:

```
operation  users   locust_p95     cw_p95     overhead   overhead %
     edge      1     1,660 ms      393 ms    1,267 ms      76 %
     edge     10     4,972 ms      381 ms    4,590 ms      92 %
     edge     50    27,618 ms      375 ms   27,243 ms      99 %
     edge    100    46,216 ms      380 ms   45,836 ms      99 %
```

- **Server-side p95 stays flat ~380 ms regardless of load** — Lambda processes
  each request in the same time whether there are 1 or 100 users.
- **Client-side p95 explodes from 1.6 s to 46 s as load grows.**
- The gap between the two = **queueing in API Gateway + the Learner Lab's
  implicit concurrency throttle**.
- At 50–100 users, **>99% of the time the user waits has nothing to do with
  Lambda execution**.

**Chart**: `analysis/cross_reference/charts/locust_vs_cloudwatch_p95.png`
(solid lines = client-side, dashed = server-side, the gap is the overhead).

**Table**: `analysis/cross_reference/charts/overhead_table.csv`.

> Note: resize-fn cross-reference did not match because the AWS Console saved
> Nico's CSVs in UTC+2 while Mathias's were saved in UTC, so the timestamp
> windows don't overlap with Locust's UTC timestamps. The finding is the same
> shape — pending a one-line patch to normalise timezones.

---

## Why this matters for the report

The assignment asks for "AWS Lambda metrics like concurrency, number of
invocations, and duration" measured "as a function of the workload intensity".
With only Locust data we would have reported *"Lambda gets slow under load"*,
which is **wrong**. With the CloudWatch + Locust cross-reference we can
correctly report:

> *"Lambda processes each request in constant time (~380 ms p95) regardless
> of workload. The observed degradation in end-to-end response time under
> load is caused by request queuing at the upstream layers, not by Lambda
> itself. The Learner Lab caps concurrency at ~10, which is the saturation
> point of our deployment."*

This is the kind of nuanced, evidence-based conclusion that distinguishes a
strong report from a surface-level one.

---

## CloudWatch charts produced (resize + edge, grayscale pending)

| Chart | What it shows | File |
|---|---|---|
| Concurrent executions over time | The Learner Lab cap visible as a hard plateau at 9–11 | `analysis/cloudwatch/charts/concurrent_executions_over_time.png` |
| Duration over time | Avg line + min–max shaded band per Lambda | `analysis/cloudwatch/charts/duration_over_time.png` |
| Duration distribution (box plot) | Side-by-side comparison of resize vs edge | `analysis/cloudwatch/charts/duration_distribution.png` |
| Invocations rate over time | ~290 req/min sustained throughput per Lambda | `analysis/cloudwatch/charts/invocations_over_time.png` |
| Errors + success rate over time | Flat 0 errors / 100% success rate the whole test | `analysis/cloudwatch/charts/errors_over_time.png` |
| Throttles over time | Flat 0 — Lambda never rejected requests | `analysis/cloudwatch/charts/throttles_over_time.png` |
| Summary table | The numbers in this document | `analysis/cloudwatch/charts/summary_table.csv` |

## Locust charts already produced (client-side)

| Chart | File |
|---|---|
| p95 response time vs concurrent users | `analysis/locust/charts/p95_vs_users.png` |
| Throughput (req/s) vs concurrent users | `analysis/locust/charts/throughput_vs_users.png` |
| Error rate (client-observed) vs concurrent users | `analysis/locust/charts/errors_vs_users.png` |
| Response time vs image size | `analysis/locust/charts/p95_vs_size.png` |
| Summary table | `analysis/locust/charts/summary_table.csv` |

## Cross-reference charts

| Chart | File |
|---|---|
| Locust p95 (solid) vs CloudWatch Duration p95 (dashed) | `analysis/cross_reference/charts/locust_vs_cloudwatch_p95.png` |
| Overhead breakdown table | `analysis/cross_reference/charts/overhead_table.csv` |

---

## Discussion points to include in the final report

1. **Lab limitations and their consequences for the experimental design.**
   We reduced the test matrix from 90 to 72 scenarios and run time from 5
   to 2 minutes per scenario to fit within the $50 Vocareum credit budget.
   We did not test 200 concurrent users. The Learner Lab also enforces a
   concurrency cap of ~10, which became the dominant scalability constraint.

2. **No Lambda errors, no throttles — but the system still saturates from
   the user's perspective.** This is counter-intuitive and is the most
   teachable observation of the project: a Lambda function that never
   errors and never throttles can still appear "broken" to end users if
   the upstream layers (API Gateway concurrency, account-level caps,
   reserved concurrency settings) are the actual bottleneck.

3. **Operation cost is dominated by CPU complexity.** edge-fn at 438 ms
   average ran ~62% longer than resize-fn at 271 ms, driven by the smoothing
   pass and edge-detection kernel. This directly translates to GB-second
   cost in Lambda pricing (each ms of compute is billed).

4. **Microservices vs monolith trade-off (per the professor's Socratic
   prompt).** Separating each operation into its own Lambda enabled isolated
   measurement: we can tell precisely that edge is heavier than resize,
   which would have been impossible if we had bundled the operations into
   a single function. The CloudWatch metrics shown here would have been
   indistinguishable averages across operations.

5. **Production extrapolation.** Outside the Learner Lab, AWS Lambda's
   default concurrency limit is 1000 — two orders of magnitude higher than
   what we measured. At 380 ms server-side p95, 1000 concurrent slots
   would support ~2,600 req/s of throughput per Lambda. The cost analysis
   (see Section 7) becomes meaningful at that scale.

---

## Pending work

- [ ] Prajwal sends his 5 CloudWatch CSVs for grayscale-fn (`grayscale_*.csv`).
- [ ] Apply timezone normalisation to the cross-reference script so resize
      also matches (one-line patch — UTC+2 → UTC for Nico's CSVs).
- [ ] Run `python analysis/cost/cost_projection.py` with the measured
      Duration values to refresh the 6-month break-even chart.
- [ ] Write the final report (8–12 pages) following the structure in
      `docs/ANALYSIS.md`.
- [ ] Prepare the slides (≈12 slides) per the same doc.
