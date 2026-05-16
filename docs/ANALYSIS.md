# Analysis & Reporting

How to process the Locust + CloudWatch results into the charts the report needs.

---

## Step 1 — Launch Jupyter

```cmd
.venv\Scripts\activate
cd analysis
jupyter notebook
```

The notebook server opens in your browser. Click `analyze.ipynb`.

---

## Step 2 — Run the notebook top to bottom

The notebook is divided into sections, one per chart. Each section:
- Loads the relevant CSVs from `..\load-tests\results\`
- Combines them into a single dataframe
- Plots the chart
- Saves the chart as PNG to `analysis\charts\`

If a section errors out, it usually means the matching CSV is missing or has fewer rows than expected. Check `..\load-tests\results\` and re-run the missing scenario if needed.

---

## Step 3 — Charts you should end up with

1. **Response time (p95) vs concurrent users** — one line per operation, X = users (1, 10, 50, 100, 200), Y = ms.
2. **Throughput (req/s) vs concurrent users** — same axes.
3. **Error rate vs concurrent users** — same axes, Y = percentage.
4. **Cold start distribution** — histogram of Init Duration per Lambda.
5. **Response time vs image size** — bars grouped by size (small, medium, large) for each operation.
6. **Concurrent executions over time** — from CloudWatch, line chart with time on X.
7. **Cost projection (Lambda vs EC2) vs monthly volume** — log-scale X, two lines, break-even point marked.

---

## Step 4 — Cost projection

Run:

```cmd
cd analysis
python cost_projection.py
```

The script:
- Reads measured duration and memory from the Locust results.
- Calculates Lambda 6-month cost for monthly volumes of 10k, 100k, 1M, and 10M images.
- Calculates EC2 t3.small 6-month cost (constant: $90 + $10 storage = ~$100).
- Solves the equation for the break-even point.
- Saves `charts\cost_breakeven.png` and `charts\cost_table.csv`.

---

## Step 5 — Move charts into the report

Once `analysis\charts\` is populated, drag the PNGs into your Word document or LaTeX source. Each chart needs a caption explaining what it shows.

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
   - Load levels and reasoning (why 1, 10, 50, 100, 200)
   - Tools (Locust + CloudWatch)
   - Scenario matrix table

4. **Results** (~3–4 pages, the heart of the report)
   - One subsection per chart
   - For each: chart + 2–3 sentences interpreting it
   - Highlight where cold starts dominate, where saturation begins, where errors appear

5. **Cost analysis** (~1 page)
   - 6-month projection chart
   - Break-even point
   - Discussion: when to use Lambda vs EC2

6. **Discussion & limitations** (~1 page)
   - What worked well, what didn't
   - Sandbox limitations of the Learner Lab
   - What we'd do differently with more time

7. **Conclusions** (~0.5 page)

---

## Presentation slides (15 min)

- 1: Title + group
- 2: Problem statement & option chosen
- 3: Architecture diagram
- 4: Image operations (brief)
- 5: Experimental setup
- 6: Results — response time
- 7: Results — throughput & errors
- 8: Results — cold starts
- 9: Cost comparison
- 10: Conclusions
- 11: Limitations & future work
- 12: Q&A placeholder

Each member presents 4 slides. Practice once with a stopwatch.
