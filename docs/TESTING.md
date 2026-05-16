# Testing — Postman + Locust

Two layers of testing:
- **Postman**: manual sanity-check that each endpoint works after deploying.
- **Locust**: automated load testing for the actual performance evaluation.

---

## Postman — manual smoke tests

### Step 1 — Install Postman

Download from https://www.postman.com/downloads/ (free).

### Step 2 — Import the collection

1. Open Postman → **File** → **Import**.
2. Drop in `postman\CloudComputing.postman_collection.json`.
3. The collection appears in the left sidebar as "Cloud Computing Project".

### Step 3 — Configure URLs

1. Right-click the collection → **Edit**.
2. Go to the **Variables** tab.
3. Replace the placeholder values with the real URLs you got from API Gateway:
   - `resize_url` → your Nico's URL
   - `grayscale_url` → your Prajwal's URL
   - `edge_url` → your Mathias's URL
4. Save.

### Step 4 — Run a request

1. Open one of the 3 requests (e.g., **Grayscale**).
2. Click **Send**.
3. Look at the response: should be `200 OK` with a JSON body containing `operation`, `size_bytes`, and `image` (a long base64 string).
4. Look at the **Test Results** tab below: all 4 automated assertions should be green.

### Step 5 — Run the full collection

1. Click the collection in the sidebar.
2. Click **Run collection** (top right).
3. All 3 requests run sequentially with their tests.

If all 3 pass: ✅ the deployments are healthy and ready for load testing.

---

## Locust — load testing

### Step 1 — Edit the Locust file

Open `load-tests\locustfile.py`. At the top there's a dictionary `ENDPOINTS`. Replace the three URLs with the ones from Phase 4 (the same you put in Postman).

### Step 2 — Smoke test (single user)

Before running the full battery, verify Locust can hit the endpoints:

```cmd
cd load-tests
locust -f locustfile.py --host=https://<any-of-your-URLs-host-part>
```

A web UI opens at http://localhost:8089. Set:
- Number of users: 1
- Spawn rate: 1
- Host: leave whatever you set

Click **Start swarm**. Watch the request rate and response time. If it works, stop after 30 seconds.

### Step 3 — Run the full scenario battery

The matrix is:
- 5 concurrency levels: **1, 10, 50, 100, 200 users**
- 3 image sizes: **small, medium, large**
- 3 operations: **resize, grayscale, edge**
- 2 repetitions

That's 90 runs × 5 minutes each ≈ 7.5 hours total. You don't need to be present — the batch script orchestrates everything.

```cmd
cd load-tests
run_scenarios.bat
```

Each run produces 4 CSVs in `load-tests\results\`:
- `<scenario>_stats.csv` (summary)
- `<scenario>_stats_history.csv` (over time)
- `<scenario>_failures.csv`
- `<scenario>_exceptions.csv`

### Step 4 — Cold start measurement (separate test)

Cold starts only happen after Lambda has been idle ~10–15 min. Run a dedicated script:

```cmd
cd load-tests
python cold_start_test.py
```

This script invokes each Lambda once, waits 20 minutes, invokes again, repeats 10 times per Lambda. It logs Init Duration from CloudWatch into `results\cold_starts.csv`.

This takes a long time (≈ 10 hours total). Run it overnight or split across days.

### Step 5 — Download CloudWatch metrics

In addition to Locust's client-side data, you want CloudWatch's server-side view (concurrent executions, init duration, memory used).

```cmd
cd load-tests
python download_cloudwatch_metrics.py --start "YYYY-MM-DD HH:MM" --end "YYYY-MM-DD HH:MM"
```

Downloads metrics for the 3 Lambdas to `results\cloudwatch_<lambda>.csv`.

(This requires AWS CLI credentials configured — see SETUP if you want to use it; otherwise you can manually export metrics from the CloudWatch console.)

---

## Tips

- **Be respectful with the load**: 200 users for 5 minutes is plenty. Don't push higher unless you really want to stress-test. The Learner Lab may throttle you.
- **Don't run multiple scenarios in parallel**: they'll interfere with each other.
- **Watch the credit counter** in Vocareum during testing. If it drops fast, stop and investigate.
- **End Lab when done**. Always.

---

## Next step

Go to `ANALYSIS.md` to process the results into charts.
