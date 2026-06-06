"""
CloudWatch analysis — server-side Lambda metrics.

These are the metrics the professor explicitly listed in the assignment:
  - concurrency (ConcurrentExecutions)
  - number of invocations (Invocations)
  - duration (Duration — actual server-side processing time)
  - number of active Lambda instances as function of workload intensity

We obtain them from CloudWatch (server-side), not Locust (client-side).

How to use
----------
1. Download the CSVs from AWS CloudWatch Console. For each Lambda function
   (resize-fn, grayscale-fn, edge-fn) and each metric, click the "..." menu
   on the metric graph and choose "Download as CSV". You should get these
   files in load-tests/results/cloudwatch/:

       resize_invocations.csv
       resize_duration.csv
       resize_concurrent.csv
       resize_errors.csv
       grayscale_invocations.csv
       grayscale_duration.csv
       grayscale_concurrent.csv
       grayscale_errors.csv
       edge_invocations.csv
       edge_duration.csv
       edge_concurrent.csv
       edge_errors.csv

   See load-tests/results/cloudwatch/README.md for detailed instructions on
   the CloudWatch console.

2. Run this script from the project root:

       python analysis/cloudwatch/analyze_cloudwatch.py

   Charts and tables land in analysis/cloudwatch/charts/.

What CloudWatch CSVs look like
------------------------------
The console exports a 2-column CSV per metric:
    Label,Average
    2026-06-05T21:00:00.000Z,12.34
    2026-06-05T21:01:00.000Z,15.67
    ...

(Sometimes the value column is named "Sum", "Maximum", or "p95" depending on
the statistic selected. The script auto-detects.)
"""

import re
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Paths (resolved relative to this script so it works regardless of cwd)
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
CW_DIR = PROJECT_ROOT / "load-tests" / "results" / "cloudwatch"
CHARTS_DIR = HERE / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

OPERATIONS = ["resize", "grayscale", "edge"]
METRICS = ["invocations", "duration", "concurrent", "errors"]

# Pretty palette consistent with Locust charts
PALETTE = {"resize": "#1f77b4", "grayscale": "#2ca02c", "edge": "#d62728"}


# ---------------------------------------------------------------------------
# CSV loader — tolerant to AWS console export variations
# ---------------------------------------------------------------------------
def load_metric(operation: str, metric: str) -> pd.DataFrame | None:
    """
    Read a CloudWatch CSV. Returns a DataFrame with columns [timestamp, value]
    or None if the file is missing.
    """
    path = CW_DIR / f"{operation}_{metric}.csv"
    if not path.exists():
        return None

    df = pd.read_csv(path)

    # First column = timestamp, second column = metric value
    # AWS calls them inconsistently; just trust the position
    cols = list(df.columns)
    if len(cols) < 2:
        print(f"  WARN: {path.name} has fewer than 2 columns, skipping.")
        return None

    df = df.rename(columns={cols[0]: "timestamp", cols[1]: "value"})
    df = df[["timestamp", "value"]].copy()

    # Parse timestamp (handles ISO 8601 with Z and most other AWS formats)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return df


def check_files_present():
    """Print which CSVs were found / missing."""
    print("=" * 60)
    print("Checking CloudWatch CSV files")
    print("=" * 60)
    found, missing = 0, 0
    for op in OPERATIONS:
        for m in METRICS:
            path = CW_DIR / f"{op}_{m}.csv"
            if path.exists():
                print(f"  [ok] {path.name}")
                found += 1
            else:
                print(f"  [missing] {path.name}")
                missing += 1
    print(f"\n{found} of {found + missing} files present.\n")
    if missing > 0:
        print("Place the missing CSVs in load-tests/results/cloudwatch/ and re-run.")
        print("See load-tests/results/cloudwatch/README.md for instructions.")
    return found, missing


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------
def plot_metric_over_time(metric: str, title: str, ylabel: str, fname: str,
                          aggregate: str = "raw"):
    """
    Plot a single metric (over time) for the 3 Lambdas overlaid.
    `aggregate`:
        "raw"       — plot the value column directly
        "cumsum"    — running sum (for Invocations)
    """
    fig, ax = plt.subplots(figsize=(11, 5))
    plotted = False
    for op in OPERATIONS:
        df = load_metric(op, metric)
        if df is None or df.empty:
            continue
        y = df["value"].cumsum() if aggregate == "cumsum" else df["value"]
        ax.plot(df["timestamp"], y,
                label=op, color=PALETTE[op], linewidth=1.8)
        plotted = True

    if not plotted:
        print(f"  skip: no data for {metric}")
        plt.close(fig)
        return

    ax.set_xlabel("Time")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(title="Lambda")
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    plt.tight_layout()
    out = CHARTS_DIR / fname
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  saved: {out.name}")


def plot_duration_distribution():
    """Histogram-style box plot of Duration per Lambda — server-side."""
    fig, ax = plt.subplots(figsize=(8, 5))
    data, labels = [], []
    for op in OPERATIONS:
        df = load_metric(op, "duration")
        if df is None or df.empty:
            continue
        data.append(df["value"].dropna())
        labels.append(op)
    if not data:
        print("  skip: no duration data")
        plt.close(fig)
        return
    bp = ax.boxplot(data, labels=labels, showfliers=False,
                    patch_artist=True)
    for patch, op in zip(bp["boxes"], labels):
        patch.set_facecolor(PALETTE[op])
        patch.set_alpha(0.6)
    ax.set_ylabel("Duration (ms)")
    ax.set_title("Server-side Lambda Duration distribution (CloudWatch)")
    ax.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    out = CHARTS_DIR / "duration_distribution.png"
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  saved: {out.name}")


def summary_table():
    """One-row-per-Lambda summary that goes into the report."""
    rows = []
    for op in OPERATIONS:
        row = {"lambda": f"{op}-fn"}
        # Invocations: sum
        df = load_metric(op, "invocations")
        row["total_invocations"] = (
            int(df["value"].sum()) if df is not None else None
        )
        # Duration: avg / p95 (approx via quantile of the per-minute samples)
        df = load_metric(op, "duration")
        if df is not None and not df.empty:
            row["avg_duration_ms"] = round(df["value"].mean(), 1)
            row["p95_duration_ms"] = round(df["value"].quantile(0.95), 1)
            row["max_duration_ms"] = round(df["value"].max(), 1)
        else:
            row.update({"avg_duration_ms": None,
                        "p95_duration_ms": None,
                        "max_duration_ms": None})
        # Concurrent executions: max
        df = load_metric(op, "concurrent")
        row["max_concurrent_executions"] = (
            int(df["value"].max()) if df is not None and not df.empty else None
        )
        # Errors: sum
        df = load_metric(op, "errors")
        row["total_errors"] = (
            int(df["value"].sum()) if df is not None and not df.empty else 0
        )
        rows.append(row)

    df = pd.DataFrame(rows)
    out = CHARTS_DIR / "summary_table.csv"
    df.to_csv(out, index=False)
    print(f"  saved: {out.name}")
    print("\n--- Summary (server-side, CloudWatch) ---")
    print(df.to_string(index=False))
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    found, missing = check_files_present()
    if found == 0:
        print("No CloudWatch CSVs found. Nothing to do.")
        return

    print("Generating charts...")

    plot_metric_over_time(
        "concurrent",
        title="Concurrent Lambda executions over time (CloudWatch)",
        ylabel="Concurrent executions (max)",
        fname="concurrent_executions_over_time.png",
    )

    plot_metric_over_time(
        "duration",
        title="Server-side Lambda Duration over time (CloudWatch)",
        ylabel="Duration (ms)",
        fname="duration_over_time.png",
    )

    plot_metric_over_time(
        "invocations",
        title="Lambda invocations rate over time (CloudWatch)",
        ylabel="Invocations per period",
        fname="invocations_over_time.png",
    )

    plot_metric_over_time(
        "errors",
        title="Lambda errors over time (CloudWatch)",
        ylabel="Errors per period",
        fname="errors_over_time.png",
    )

    plot_duration_distribution()
    summary_table()
    print("\nDone. Charts in analysis/cloudwatch/charts/")


if __name__ == "__main__":
    main()
