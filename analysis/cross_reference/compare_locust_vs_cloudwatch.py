"""
Cross-reference: Locust (client-side) vs CloudWatch (server-side).

The Locust response time we measure from the client is:

    Locust_RT = network_upload + API_Gateway + Lambda_Init + Lambda_Duration + network_download

CloudWatch Duration only measures Lambda_Duration. So the difference

    overhead = Locust_RT - CloudWatch_Duration

approximates everything that is NOT pure Lambda processing: network round-trip,
API Gateway latency, cold-start delta (if any), and queuing.

This script aligns each Locust scenario (we know when it started and how long
it ran from stats_history.csv) with the corresponding CloudWatch window, and
computes the overhead per (operation, image_size, users).

Run from project root:

    python analysis\cross_reference\compare_locust_vs_cloudwatch.py
"""

import re
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
LOCUST_DIR = PROJECT_ROOT / "load-tests" / "results"
CW_DIR = LOCUST_DIR / "cloudwatch"
CHARTS_DIR = HERE / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

OPERATIONS = ["resize", "grayscale", "edge"]
PALETTE = {"resize": "#1f77b4", "grayscale": "#2ca02c", "edge": "#d62728"}

SCENARIO_RE = re.compile(
    r"(?P<op>resize|grayscale|edge)_"
    r"(?P<size>small|medium|large)_"
    r"(?P<users>\d+)u_"
    r"rep(?P<rep>\d+)_stats\.csv$"
)
HISTORY_RE = re.compile(
    r"(?P<op>resize|grayscale|edge)_"
    r"(?P<size>small|medium|large)_"
    r"(?P<users>\d+)u_"
    r"rep(?P<rep>\d+)_stats_history\.csv$"
)


# ---------------------------------------------------------------------------
# Load Locust scenarios
# ---------------------------------------------------------------------------
def load_locust_scenarios() -> pd.DataFrame:
    """
    One row per Locust scenario, with the aggregated p95 and the time window.
    """
    rows = []
    for f in sorted(LOCUST_DIR.glob("*_stats.csv")):
        m = SCENARIO_RE.search(f.name)
        if not m:
            continue
        try:
            df = pd.read_csv(f)
        except Exception:
            continue
        agg = df[df["Name"] == "Aggregated"]
        if agg.empty:
            continue
        a = agg.iloc[0]

        # Pair with history file to get start/end timestamps
        hist_path = LOCUST_DIR / f.name.replace("_stats.csv", "_stats_history.csv")
        start, end = None, None
        if hist_path.exists():
            hdf = pd.read_csv(hist_path)
            if "Timestamp" in hdf.columns and not hdf.empty:
                ts = pd.to_datetime(hdf["Timestamp"], unit="s", utc=True,
                                    errors="coerce").dropna()
                if len(ts) >= 2:
                    start, end = ts.iloc[0], ts.iloc[-1]

        rows.append({
            "operation": m.group("op"),
            "size": m.group("size"),
            "users": int(m.group("users")),
            "rep": int(m.group("rep")),
            "p95_locust_ms": a.get("95%"),
            "avg_locust_ms": a.get("Average Response Time"),
            "requests": a.get("Request Count"),
            "failures": a.get("Failure Count"),
            "start_ts": start,
            "end_ts": end,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Load CloudWatch duration per Lambda
# ---------------------------------------------------------------------------
def load_cloudwatch_duration() -> dict[str, pd.DataFrame]:
    """Return dict op → DataFrame[timestamp, value] of Duration."""
    out = {}
    for op in OPERATIONS:
        path = CW_DIR / f"{op}_duration.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        cols = list(df.columns)
        if len(cols) < 2:
            continue
        df = df.rename(columns={cols[0]: "timestamp", cols[1]: "value"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["timestamp", "value"]).sort_values("timestamp")
        out[op] = df
    return out


# ---------------------------------------------------------------------------
# Match scenarios with CloudWatch samples inside their time window
# ---------------------------------------------------------------------------
def attach_cloudwatch(scen: pd.DataFrame, cw: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """For each scenario, compute the mean / p95 CloudWatch Duration inside its window."""
    rows = []
    for _, s in scen.iterrows():
        op = s["operation"]
        if op not in cw or pd.isna(s["start_ts"]) or pd.isna(s["end_ts"]):
            rows.append({"avg_cw_ms": None, "p95_cw_ms": None})
            continue
        window = cw[op]
        mask = (window["timestamp"] >= s["start_ts"]) & (window["timestamp"] <= s["end_ts"])
        sub = window.loc[mask, "value"]
        if sub.empty:
            rows.append({"avg_cw_ms": None, "p95_cw_ms": None})
        else:
            rows.append({
                "avg_cw_ms": round(sub.mean(), 1),
                "p95_cw_ms": round(sub.quantile(0.95), 1),
            })
    return pd.concat([scen.reset_index(drop=True),
                      pd.DataFrame(rows)], axis=1)


# ---------------------------------------------------------------------------
# Plot overhead per scenario
# ---------------------------------------------------------------------------
def plot_overhead(df: pd.DataFrame):
    """Side-by-side bars: Locust p95 vs CloudWatch p95, per operation × users."""
    df = df.dropna(subset=["p95_cw_ms"]).copy()
    if df.empty:
        print("No matching CloudWatch data inside Locust scenario windows.")
        return
    df["overhead_ms"] = df["p95_locust_ms"] - df["p95_cw_ms"]

    # Average across image sizes and repetitions to get one bar per (op, users)
    agg = df.groupby(["operation", "users"], as_index=False).agg(
        locust_p95=("p95_locust_ms", "mean"),
        cw_p95=("p95_cw_ms", "mean"),
        overhead=("overhead_ms", "mean"),
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    for op in OPERATIONS:
        sub = agg[agg["operation"] == op].sort_values("users")
        if sub.empty:
            continue
        ax.plot(sub["users"], sub["locust_p95"],
                marker="o", linestyle="-", color=PALETTE[op],
                label=f"{op} — Locust p95 (end-to-end)")
        ax.plot(sub["users"], sub["cw_p95"],
                marker="s", linestyle="--", color=PALETTE[op],
                label=f"{op} — CloudWatch p95 (Lambda only)")
    ax.set_xlabel("Concurrent users")
    ax.set_ylabel("p95 response time (ms)")
    ax.set_title("End-to-end vs server-side p95 — overhead = gap between solid and dashed")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    plt.tight_layout()
    out = CHARTS_DIR / "locust_vs_cloudwatch_p95.png"
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  saved: {out.name}")

    # Save the table too
    out_csv = CHARTS_DIR / "overhead_table.csv"
    agg.to_csv(out_csv, index=False)
    print(f"  saved: {out_csv.name}")
    print("\n--- Network + API Gateway overhead summary ---")
    print(agg.to_string(index=False))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    scen = load_locust_scenarios()
    print(f"Loaded {len(scen)} Locust scenarios.")
    cw = load_cloudwatch_duration()
    if not cw:
        print("No CloudWatch Duration CSVs found in load-tests/results/cloudwatch/.")
        print("Download them first (see load-tests/results/cloudwatch/README.md).")
        return
    print(f"Loaded CloudWatch Duration for: {list(cw.keys())}")
    merged = attach_cloudwatch(scen, cw)
    plot_overhead(merged)
    print("\nDone. Charts in analysis/cross_reference/charts/")


if __name__ == "__main__":
    main()
