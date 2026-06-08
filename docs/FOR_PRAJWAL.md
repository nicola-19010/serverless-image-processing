# Your part — what's left for grayscale-fn

Hey Prajwal, here's what we figured out and what you still need to do.

## Why we need CloudWatch data (not just Locust)

Locust was great for **automating** the load tests against the 3 Lambdas — it
fired 72 scenarios at our endpoints and recorded what each simulated user
experienced. That data is useful, but it has a fundamental limitation: every
time it measures, it mashes together **three things**:

```
network upload  +  Lambda processing  +  network download
```

The professor asked specifically for **AWS Lambda metrics**: concurrency,
number of invocations, and duration. Those numbers only exist server-side,
and only **CloudWatch** publishes them — it measures *just* the Lambda
execution, with no network in the way.

So:

- **Locust** = client-side view ("how long the user waited"). Useful as
  complementary data, not the main source.
- **CloudWatch** = server-side view ("how long Lambda actually worked"). This
  is what the professor explicitly asked for.

When Mathias and I cross-referenced both sources, we found something the
report needs: Lambda never errored, never throttled, and server-side p95 was
flat ~380 ms regardless of load. But client-side p95 grew to **46 seconds**
at 100 users. The "slowness" is **queueing at API Gateway / the Learner Lab
concurrency cap** — not Lambda. We need your grayscale data to confirm the
same pattern in your function.

---

## What you need to do (≈15 min)

### 1. Open the CloudWatch metrics for grayscale-fn

- AWS Console → **Lambda** → click **grayscale-fn** → **Monitor** tab.
- Top right: set the time range to **2026-06-05 21:00:00 → 23:59:59**.
- **IMPORTANT — Timezone**: in the dropdown next to the date pickers, leave
  it on **"Zona horaria local" / "Local timezone"** (the default). Do NOT
  switch it to UTC. Nico and I used local time, so yours has to match for
  the cross-reference to align.

### 2. Download 5 CSVs from CloudWatch

There are **5 different metrics** to download — each becomes its own CSV file.
For each one, follow this 4-click procedure inside the AWS Console:

**Common procedure (do this 5 times, once per metric):**

1. Scroll down the Monitor tab until you see the metric **tiles** (small chart cards).
2. On the tile of the metric you want, click the **⋮ (three vertical dots)** at the top-right of the tile → choose **"View in metrics"**. This opens that single metric in the full CloudWatch Metrics screen.
3. In CloudWatch Metrics, find the table just below the chart with the column **"Statistic"** and **"Period"**. Set them according to the row in the table below.
4. Top-right, click **Actions** → **Download as CSV**. The file lands in your `Downloads` folder.

**Settings per metric:**

| Tile name in Monitor tab | Statistic | Period | Notes |
|---|---|---|---|
| **Invocations** | Sum | 1 minute | only 1 line — straightforward |
| **Duration** | (keep the 3 default lines: Minimum, Average, Maximum) | 1 minute | Do NOT remove any of the 3 lines |
| **Concurrent executions** | Maximum | 1 minute | only 1 line |
| **Error count and success rate** | (keep the 2 default lines: errors + successRate) | 1 minute | Leave the "invocations" line unchecked |
| **Throttles** | Sum | 1 minute | only 1 line |

After step 4 of the common procedure, just go back (browser back button) to the Monitor tab and repeat with the next metric. You should end up with **5 CSV files** in your Downloads folder, one per metric.

### 3. Rename the 5 files

Exactly like this, all lowercase, with underscores:

```
grayscale_invocations.csv
grayscale_duration.csv
grayscale_concurrent.csv
grayscale_errors.csv
grayscale_throttles.csv
```

### 4. Drop them into the repo

After `git pull` to get the latest, place the 5 files in:

```
project\load-tests\results\cloudwatch\
```

### 5. Run the analysis scripts

From the repo root with the venv active:

```cmd
.venv\Scripts\activate
python analysis\cloudwatch\analyze_cloudwatch.py
python analysis\cross_reference\compare_locust_vs_cloudwatch.py
python analysis\cost\cost_projection.py
```

What each one does:

- **analyze_cloudwatch.py** — reads all CSVs (your 5 + Nico's + Mathias's)
  and regenerates the server-side charts with the 3 Lambdas overlaid.
- **compare_locust_vs_cloudwatch.py** — computes the queue/network overhead
  per scenario (the cross-reference finding).
- **cost_projection.py** — recalculates the 6-month cost projection now
  using the real measured Duration.

All charts land in `analysis/<source>/charts/` — they're the figures we'll
paste into the report.

---

## After you finish — commit & push (very important)

The 5 CSV files you just placed in `load-tests/results/cloudwatch/` are new
files that git doesn't know about yet. A normal `git add -u` or "Stage
modified" in VS Code will **not** pick them up. Run these commands
explicitly to make sure they go in:

```cmd
git add load-tests/results/cloudwatch/grayscale_*.csv
git add analysis/
git commit -m "Add grayscale CloudWatch CSVs + regenerated charts"
git push
```

Then send a quick "done" or a screenshot of the script output so I know
the dataset is complete on my end. Once everything is in, Sunday night /
Monday I'll ask Claude to draft a first version of the report using all
this as input. Each of us will then review and edit our own section.
Way faster than starting from zero.

Any questions, ping me.
