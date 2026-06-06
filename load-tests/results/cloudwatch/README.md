# CloudWatch CSV downloads

This folder must contain the CloudWatch metric exports for the 3 Lambda
functions. They are the **server-side** counterpart to the Locust CSVs in
`../` (the parent folder), and they cover the metrics the professor cites
literally in the assignment: concurrency, invocations, duration.

## Files expected (12 CSVs total — 4 per Lambda × 3 Lambdas)

```
cloudwatch/
├── resize_invocations.csv
├── resize_duration.csv
├── resize_concurrent.csv
├── resize_errors.csv
├── grayscale_invocations.csv
├── grayscale_duration.csv
├── grayscale_concurrent.csv
├── grayscale_errors.csv
├── edge_invocations.csv
├── edge_duration.csv
├── edge_concurrent.csv
└── edge_errors.csv
```

## How to download from the AWS Console

For **each Lambda function** (resize-fn, grayscale-fn, edge-fn):

1. AWS Console → **Lambda** → click your function → **Monitor** tab.
2. Click the link **View CloudWatch metrics** (top right).
3. You land in CloudWatch with 4 default graphs already plotted.
4. For **each of the 4 graphs** (Invocations, Duration, Concurrent executions, Errors):
   - Click the graph to enlarge.
   - **Time range** (top right): set to the window when you ran
     `run_scenarios.bat` — e.g. 2026-06-05 from 21:00 to 24:00.
   - **Period** (dropdown): set to **1 minute** (gives finer resolution).
   - **Statistic** to select per metric:
     - Invocations: **Sum**
     - Duration: **Average** (you can also pull p95 / Maximum as separate files if you want richer data)
     - ConcurrentExecutions: **Maximum**
     - Errors: **Sum**
   - Click **Actions → Download as CSV**.
   - Rename the downloaded file using the naming convention above
     (e.g. `resize_duration.csv`) and drop it here.

Repeat for the other two Lambdas. Total: 12 files.

## Time window for our run

Per the user, the Locust battery ran **2026-06-05 from 21:00 to ~24:00 (CLST)**.
Use that range in CloudWatch. AWS Console may show times in your local
timezone — that's fine, the analysis script normalises everything.

## After downloading

Run the analysis script from the project root:

```cmd
python analysis\cloudwatch\analyze_cloudwatch.py
```

Charts and the summary table land in `analysis/cloudwatch/charts/`.
