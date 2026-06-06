# Work Plan — Cloud Computing Project

This is the master guide. Everyone on the team should follow these phases in order. Each phase has clear deliverables and ownership.

> **Platform note:** All commands assume **Windows 10/11** with PowerShell or Command Prompt.

---

## Phase overview

| Phase | What | Owner | Estimated time |
|---|---|---|---|
| 1 | Local setup | everyone | 30 min |
| 2 | Local development & testing | everyone (own Lambda) | 2–3 h |
| 3 | AWS Learner Lab setup | everyone | 30 min |
| 4 | Deploy Lambda to AWS | each owner | 1 h |
| 5 | Postman manual tests | everyone | 30 min |
| 6 | Load testing with Locust | one person | 4–6 h |
| 7 | Data analysis | one or two | 4 h |
| 8 | Cost projection | one | 1 h |
| 9 | Report + presentation | everyone | 6 h |

Ownership of Lambdas:
- **Nico** → `resize`
- **Prajwal** → `grayscale`
- **Mathias** → `edge`

---

## Phase 1 — Local setup

**Everyone does this.** See `SETUP.md` for the detailed walkthrough. Quick version:

```cmd
:: 1. Make sure Python 3.11 is installed
python --version

:: 2. Clone the repo (skip if already cloned)
git clone <repo-url>
cd project

:: 3. Create a virtual environment
python -m venv .venv

:: 4. Activate it
.venv\Scripts\activate

:: 5. Install dependencies
pip install -r requirements.txt

:: 6. Generate test images
cd local-tests
python generate_images.py
cd ..
```

**Deliverable:** you can run `python local-tests\test_grayscale.py` and it processes an image without errors.

---

## Phase 2 — Local development & testing

**Each person works on their own Lambda.**

1. Open `lambdas\<your-operation>\lambda_function.py`. The code is already there as a working starting point.
2. Read it, understand what it does. Modify if you want, but keep the same input/output structure (base64 image in, base64 image out).
3. Test locally:

```cmd
cd local-tests
python test_<your-operation>.py
```

This runs your Lambda code **without AWS** and saves the output as `output_<operation>.jpg`. Open it to confirm the operation worked visually.

**Deliverable:** an output image that demonstrates your operation worked (e.g., `output_resized.jpg`, `output_grayscale.jpg`, `output_edge.jpg`).

---

## Phase 3 — AWS Learner Lab setup

**Everyone does this once.**

1. Go to AWS Academy in your browser. Open the **AWS Academy Learner Lab** course.
2. Complete the Module Knowledge Check (10 questions, easy — required to unlock the lab).
3. Click **Launch AWS Academy Learner Lab** → press **Start Lab** → wait for green dot → click **AWS** to open the AWS Console.
4. Familiarize yourself: AWS Console → Services → Lambda. Try creating and deleting a "Hello World" Lambda just to get comfortable.
5. **Important:** when you finish a session, press **End Lab** to stop the timer (your work persists, but the timer doesn't burn).

**Deliverable:** you can open the AWS Console from the Learner Lab and you've created at least one test Lambda.

---

## Phase 4 — Deploy your Lambda

See `DEPLOY.md` for the full step-by-step. Short version:

1. In the AWS Console → Lambda → **Create function** → Author from scratch.
2. Name: `<your-operation>-fn` (e.g., `resize-fn`). Runtime: **Python 3.11**. Architecture: **x86_64**.
3. Open the Code tab. Copy the contents of `lambdas\<your-operation>\lambda_function.py` and paste them in. Click Deploy.
4. **Add the Pillow Lambda Layer** (so Pillow is available without packaging):
   - Scroll down to Layers → Add a layer → Specify ARN.
   - Use the ARN from the Klayers project: `arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p311-Pillow:11` (version verified May 2026; if it stops working, look up the latest at https://api.klayers.cloud/api/v2/p3.11/layers/latest/us-east-1/json).
5. Increase memory and timeout: Configuration → General → **Memory: 512 MB**, **Timeout: 30 sec**.
6. Test with the Test tab: paste the content of `lambdas\<your-operation>\test_event.json` and run.
7. **Add API Gateway trigger:** Configuration → Triggers → Add Trigger → API Gateway → HTTP API → Open. Save.
8. Copy the resulting public URL. Send it to the group.

**Deliverable:** the public URL of your Lambda endpoint. The 3 of you each have one URL.

---

## Phase 5 — Postman manual tests

1. Import `postman\CloudComputing.postman_collection.json` into Postman.
2. Edit the collection variables: replace `RESIZE_URL`, `GRAYSCALE_URL`, `EDGE_URL` with the real URLs from Phase 4.
3. Run each request. The collection has automated tests that check status code, response shape, and presence of the base64 image.
4. Look at the Test Results pane: all assertions should pass.

**Deliverable:** all 3 requests return 200 with a valid base64-encoded processed image and all assertions pass.

---

## Phase 6 — Load testing with Locust

See `TESTING.md` for the full method. Summary:

The experimental matrix is:
- **4 concurrency levels:** 1, 10, 50, 100 users
- **3 image sizes:** small, medium, large
- **3 operations:** resize, grayscale, edge
- **2 repetitions per scenario** (for variance estimation)
- **Total: 4 × 3 × 3 × 2 = 72 runs × 2 minutes = ~2.4–3 hours of testing**

*(Optional — not required by the professor)* an isolated cold-start test (~10 runs per Lambda with 20 min delay between them). Skip if you want to stay strictly within the assignment's required metrics (concurrency, invocations, duration).

Edit `load-tests\locustfile.py` to use your 3 endpoints, then run:

```cmd
cd load-tests
run_scenarios.bat
```

That script orchestrates the 72 runs. CSVs land in `load-tests\results\`.

**Deliverable:** the `results/` folder full of CSV files, one set per scenario.

---

## Phase 7 — Data analysis

The analysis is split into **3 data-source tiers + 1 cost tier**. See
`analysis/README.md` for the rationale (TL;DR: Locust gives client-side data,
CloudWatch gives the server-side metrics the professor explicitly required,
and the cross-reference compares them).

### Phase 7A — Locust analysis (client-side, already done in our case)

```cmd
.venv\Scripts\activate
jupyter notebook analysis\locust\analyze_locust.ipynb
```

Generates in `analysis/locust/charts/`:
- p95 response time vs concurrent users
- Throughput (req/s) vs concurrent users
- Error rate vs load
- Response time vs image size

### Phase 7B — CloudWatch analysis (server-side, REQUIRED by the prof)

**First**, download the metric CSVs from the AWS console. See
`load-tests/results/cloudwatch/README.md` for the step-by-step.

**Then** run:

```cmd
python analysis\cloudwatch\analyze_cloudwatch.py
```

Generates in `analysis/cloudwatch/charts/`:
- Concurrent executions over time *(required, prof cites it textually)*
- Server-side Duration over time + distribution *(required)*
- Invocations rate over time *(required)*
- Errors over time
- Summary table (avg / p95 / max Duration, max concurrency, total errors)

### Phase 7C — Cross-reference Locust vs CloudWatch

```cmd
python analysis\cross_reference\compare_locust_vs_cloudwatch.py
```

For each scenario, computes `overhead = Locust_p95 - CloudWatch_Duration_p95`,
which approximates the network + API Gateway + cold-start overhead.

Generates in `analysis/cross_reference/charts/`:
- Side-by-side p95 chart (client-side vs server-side per operation × users)
- `overhead_table.csv` with the breakdown

**Deliverable for Phase 7:** all charts under their respective
`analysis/<source>/charts/` subfolders.

---

## Phase 8 — Cost projection (R4 requirement)

```cmd
python analysis\cost\cost_projection.py
```

The script:
- **Auto-detects the measured Duration** from the CloudWatch CSVs (falls back
  to a default estimate if no CW data is available).
- Calculates 6-month cost on Lambda + API Gateway for monthly volumes from
  10k to 100M images.
- Calculates the equivalent 6-month cost on EC2 t3.small (theoretical baseline).
- Plots both curves on log-scale and marks the break-even point.

**Deliverable:** `analysis/cost/charts/cost_breakeven.png` +
`analysis/cost/charts/cost_table.csv`.

---

## Phase 9 — Report + presentation

Report (8–12 pages):
1. Introduction & objectives
2. Architecture & implementation (one section per Lambda)
3. Experimental design (Locust setup, image sets, scenarios)
4. Results (charts grouped by metric)
5. Cost analysis (break-even point, conclusions)
6. Discussion & limitations

Presentation (15 min, ~12 slides):
- 2 slides intro
- 2 slides architecture
- 4 slides results
- 2 slides cost
- 2 slides conclusion

Each group member must present at least one section. Rehearse at least once.

**Deliverable:** report PDF + slides + uploaded to Classroom 7+ days before the exam.

---

## Daily standup template (optional but recommended)

In WhatsApp or wherever, end of each work day:
- What I did today
- What I'm doing tomorrow
- Blockers

Keeps everyone aligned, prevents last-minute surprises.
