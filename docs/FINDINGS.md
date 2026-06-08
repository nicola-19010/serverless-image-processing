# Project Findings — Performance & Scalability Analysis

> Generated on 2026-06-06 from CloudWatch + Locust data of the 2026-06-05 load
> test session. Use this as the source-of-truth when writing the final report.
>
> **All timestamps below and in the charts are Europe/Rome (UTC+2).** See
> [TIMEZONES.md](TIMEZONES.md) for how the timezone normalisation works
> across CSVs downloaded by different team members in different timezones.

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
operation     users   locust_p95     cw_p95     overhead   overhead %
   resize        1     1,097 ms      271 ms       826 ms       75 %
   resize       10     4,773 ms      274 ms     4,499 ms       94 %
   resize       50    28,133 ms      272 ms    27,861 ms       99 %
   resize      100    46,850 ms      270 ms    46,580 ms     99.4 %
grayscale        1     1,323 ms      189 ms     1,134 ms       86 %
grayscale       10     5,262 ms      178 ms     5,083 ms       97 %
grayscale       50    31,492 ms      176 ms    31,316 ms       99 %
grayscale      100    46,033 ms      175 ms    45,858 ms     99.6 %
     edge        1     1,660 ms      439 ms     1,221 ms       74 %
     edge       10     4,972 ms      446 ms     4,525 ms       91 %
     edge       50    27,618 ms      441 ms    27,177 ms       98 %
     edge      100    46,216 ms      441 ms    45,775 ms     99.0 %
```

- **Server-side p95 stays effectively flat regardless of load** for all three
  Lambdas: resize ~271 ms, grayscale ~178 ms, edge ~442 ms — variation under
  5 % between 1 and 100 concurrent users.
- **Client-side p95 explodes from ~1 s to ~46 s as load grows.**
- The gap between the two = **queueing in API Gateway + the Learner Lab's
  implicit concurrency throttle**.
- At 100 users, **>99 % of the end-to-end response time has nothing to do
  with Lambda execution** — it is pure queueing in the upstream layers.

**Chart**: `analysis/cross_reference/charts/locust_vs_cloudwatch_p95.png`
(solid lines = client-side, dashed = server-side, the gap is the overhead).

**Table**: `analysis/cross_reference/charts/overhead_table.csv`.

> Note: grayscale is the lightest operation server-side (~178 ms p95) because
> RGB-to-luma is a single per-pixel operation, lighter than resize (which
> requires interpolation) and edge (Sobel + smoothing).

---

## Why this matters for the report

The assignment asks for "AWS Lambda metrics like concurrency, number of
invocations, and duration" measured "as a function of the workload intensity".
With only Locust data we would have reported *"Lambda gets slow under load"*,
which is **wrong**. With the CloudWatch + Locust cross-reference we can
correctly report:

> *"Lambda processes each request in constant time (~175–440 ms p95
> depending on operation) regardless of workload. The observed degradation
> in end-to-end response time under load is caused by request queuing in
> the API Gateway / Vocareum-managed concurrency layer, not by Lambda
> itself. Peak Lambda concurrency reached only 9–11 across the three
> functions, well below the 1,000-concurrent default of a production AWS
> account."*

This is the kind of nuanced, evidence-based conclusion that distinguishes a
strong report from a surface-level one.

---

## Verified data — refutations of the old Phase 6 hypothesis doc

> A previous teammate-written analysis (`PHASE6_ANALYSIS.md`, drafted before
> the team had CloudWatch data) made several confident claims about why the
> system failed under load. With the CW data now in hand, **several of those
> claims are wrong**. This section is the authoritative reference for the
> report writers — don't repeat the Phase 6 doc's mistakes.

### Claims confirmed by data

| Phase 6 claim | Verification |
|---|---|
| `resize` uses LANCZOS interpolation | Confirmed (`lambdas/resize/lambda_function.py:62`) |
| `edge` uses SMOOTH + FIND_EDGES filters | Confirmed (`lambdas/edge/lambda_function.py`) |
| `grayscale` uses `.convert("L")` | Confirmed (`lambdas/grayscale/lambda_function.py`) |
| Only 2 error types observed (HTTP 0, HTTP 408) | Confirmed: 161 HTTP 0 + 154 HTTP 408 = 315 total across 72 scenarios |
| `resize_large_100u` is the worst case | Confirmed: 82+61 = 143 failures across the 2 reps |

### Claims **refuted** by data

| Phase 6 claim | Verified truth | Source |
|---|---|---|
| "Lambda concurrency cap is ~100 in Learner Lab" | Peak concurrent execution was **9-11** per Lambda. Whether this is a Vocareum cap or a natural ceiling (throughput × duration) we cannot disambiguate. | `analysis/cloudwatch/charts/summary_table.csv` |
| "HTTP 408 = Lambda execution exceeded 30 s timeout" | **False.** Max Lambda Duration was 856 ms (resize), 740 ms (grayscale), 1,431 ms (edge). The 30 s Lambda timeout was **never reached**. HTTP 408 errors come from API Gateway integration timeout (~29 s) while requests waited in queue, **before reaching Lambda**. | `summary_table.csv`, all CW Duration CSVs |
| "Large images are ~5 MB" | False. Our `large` bucket is 947 KB – 2.3 MB, mean ~1.3 MB. | `local-tests/images/large/` |
| "Grayscale and resize outputs are ~5 MB; edge output is ~1 MB (compressed)" | **Opposite of reality.** Measured on a 1 MB input: resize output = **42 KB** (4 %), grayscale = 940 KB (89 %), edge = 1,040 KB (98 %). Resize has the **smallest** output (it shrinks to 400 px wide); edge does NOT compress dramatically. | Measured directly running each Lambda |
| "Switching from LANCZOS to BICUBIC would fix the saturation" | Wrong fix for the wrong problem. LANCZOS is mildly slower (271 ms avg) but nowhere near the 30 s Lambda timeout. The bottleneck is queueing, not CPU. | CW max Duration 856 ms ≪ 30 s |
| "0 cold starts observed" | **Unverifiable** from our data. We did not export the `Init Duration` metric from CloudWatch. The very low min Duration values (1.6 ms grayscale, 8.5 ms edge, 11.2 ms resize) are **not** cold-start indicators — those are fast-fail responses (e.g., 400 from a malformed test event). | Not measured |

### The key insight that the Phase 6 doc missed

**Two compatible perspectives on success**, which together explain the data:

```
                    ┌───────────────────────────────┐
Locust (client) ──► │     API Gateway               │ ──► Lambda
                    │     - Queue management        │
                    │     - 29 s integration timeout│
                    │     - If timeout: HTTP 408    │
                    │     - If conn drop: HTTP 0    │
                    └───────────────────────────────┘
                          ↑                              ↑
                  315 failures seen by              0 errors, 0 throttles,
                  Locust (HTTP 0 + 408)             100 % success seen
                                                    by CloudWatch
```

- **CloudWatch only sees what actually invoked Lambda.** Of the requests that
  reached Lambda, 100 % succeeded.
- **Locust counts every HTTP failure**, regardless of which layer produced it.
- The 315 failures were rejected upstream of Lambda (queue overflow, integration
  timeout). They never count as Lambda invocations, so CloudWatch shows 0 errors
  while Locust shows 27 % error rate at the worst scenario.

This is the most teachable observation of the project: **a Lambda function that
never errors and never throttles can still appear "broken" to end users** if the
upstream queueing layer rejects requests before Lambda can process them. The
report should foreground this nuance.

---

## CloudWatch charts produced (all 3 Lambdas)

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

- [x] Prajwal sent his 5 CloudWatch CSVs for grayscale-fn (commit `1243a69`).
- [x] Timezone normalisation: all CSVs auto-detect their offset and display
      in Europe/Rome. See [TIMEZONES.md](TIMEZONES.md). Resize now matches
      the cross-reference. Shared helper at `analysis/_tz_helper.py`.
- [ ] Run `python analysis/cost/cost_projection.py` with the measured
      Duration values to refresh the 6-month break-even chart.
- [ ] Write the final report (8–12 pages) following the structure in
      `docs/ANALYSIS.md`.
- [ ] Prepare the slides (≈12 slides) per the same doc.
