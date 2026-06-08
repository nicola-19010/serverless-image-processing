"""
Cross-reference: Locust (client-side) vs CloudWatch (server-side).

Locust_RT = network_upload + API_Gateway + Lambda_Init + Lambda_Duration + network_download
CloudWatch Duration only measures Lambda_Duration, so:
    overhead = Locust_RT - CloudWatch_Duration

All timestamps are normalised to Europe/Rome (see analysis/_tz_helper.py for
the rationale and auto-detection logic).

Run from project root:
    python analysis\cross_reference\compare_locust_vs_cloudwatch.py
"""

import re
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "analysis"))
from _tz_helper import (
    DISPLAY_TZ, find_header_row, detect_csv_offset_hours, to_display_tz,
)

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


def load_locust_scenarios() -> pd.DataFrame:
    """One row per Locust scenario, with aggregated p95 and time window in Rome time."""
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
        hist_path = LOCUST_DIR / f.name.replace("_stats.csv", "_stats_history.csv")
        start_utc, end_utc = None, None
        if hist_path.exists():
            hdf = pd.read_csv(hist_path)
            if "Timestamp" in hdf.columns and not hdf.empty:
                ts = pd.to_datetime(hdf["Timestamp"], unit="s", utc=True,
                                    errors="coerce").dropna()
                if len(ts) >= 2:
                    start_utc, end_utc = ts.iloc[0], ts.iloc[-1]
        # Convert to display tz for matching against CW
        start = start_utc.tz_convert(DISPLAY_TZ) if start_utc is not None else None
        end = end_utc.tz_convert(DISPLAY_TZ) if end_utc is not None else None
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
            "start_utc": start_utc,  # kept for tz detection
            "end_utc": end_utc,
        })
    return pd.DataFrame(rows)


def _pick_avg_col(cols):
    for c in cols[1:]:
        if any(k in str(c).lower()
               for k in ["promedio", "media", "average", "avg", "mean"]):
            return c
    return cols[1]


def load_cloudwatch_duration(locust_scen: pd.DataFrame) -> dict:
    """For each op, return DataFrame[timestamp(Rome), value] of Duration."""
    out = {}
    for op in OPERATIONS:
        dur_path = CW_DIR / f"{op}_duration.csv"
        inv_path = CW_DIR / f"{op}_invocations.csv"
        if not dur_path.exists() or not inv_path.exists():
            continue
        h = find_header_row(dur_path)
        df = pd.read_csv(dur_path, header=h)
        cols = list(df.columns)
        if len(cols) < 2:
            continue
        avg_col = _pick_avg_col(cols)
        df = df[[cols[0], avg_col]].rename(
            columns={cols[0]: "timestamp", avg_col: "value"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["timestamp", "value"]).sort_values("timestamp")
        if df.empty:
            continue

        op_scen = locust_scen[locust_scen["operation"] == op].dropna(
            subset=["start_utc", "end_utc"])
        if op_scen.empty:
            # Fallback: assume already in Rome
            df["timestamp"] = df["timestamp"].dt.tz_localize(DISPLAY_TZ)
            out[op] = df
            continue
        locust_start = op_scen["start_utc"].min()
        locust_end = op_scen["end_utc"].max()
        locust_mid = locust_start + (locust_end - locust_start) / 2

        offset_h = detect_csv_offset_hours(inv_path, locust_mid)
        df["timestamp"] = to_display_tz(df["timestamp"], offset_h)
        sign = "+" if offset_h > 0 else ""
        print(f"  [{op}] CSV detected as UTC{sign}{offset_h} -> displayed in {DISPLAY_TZ}")
        out[op] = df
    return out


def attach_cloudwatch(scen: pd.DataFrame, cw: dict) -> pd.DataFrame:
    rows = []
    for _, s in scen.iterrows():
        op = s["operation"]
        if op not in cw or pd.isna(s["start_ts"]) or pd.isna(s["end_ts"]):
            rows.append({"avg_cw_ms": None, "p95_cw_ms": None})
            continue
        w = cw[op]
        mask = (w["timestamp"] >= s["start_ts"]) & (w["timestamp"] <= s["end_ts"])
        sub = w.loc[mask, "value"]
        if sub.empty:
            rows.append({"avg_cw_ms": None, "p95_cw_ms": None})
        else:
            rows.append({
                "avg_cw_ms": round(sub.mean(), 1),
                "p95_cw_ms": round(sub.quantile(0.95), 1),
            })
    return pd.concat([scen.reset_index(drop=True),
                      pd.DataFrame(rows)], axis=1)


def plot_overhead(df: pd.DataFrame):
    df = df.dropna(subset=["p95_cw_ms"]).copy()
    if df.empty:
        print("No matching CloudWatch data inside Locust scenario windows.")
        return
    df["overhead_ms"] = df["p95_locust_ms"] - df["p95_cw_ms"]
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
                label=f"{op} - Locust p95 (end-to-end)")
        ax.plot(sub["users"], sub["cw_p95"],
                marker="s", linestyle="--", color=PALETTE[op],
                label=f"{op} - CloudWatch p95 (Lambda only)")
    ax.set_xlabel("Concurrent users")
    ax.set_ylabel("p95 response time (ms)")
    ax.set_title("End-to-end vs server-side p95 - overhead = gap between solid and dashed")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    plt.tight_layout()
    out = CHARTS_DIR / "locust_vs_cloudwatch_p95.png"
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  saved: {out.name}")
    out_csv = CHARTS_DIR / "overhead_table.csv"
    agg.to_csv(out_csv, index=False)
    print(f"  saved: {out_csv.name}")
    print()
    print("--- Network + API Gateway overhead summary ---")
    print(agg.to_string(index=False))


def main():
    scen = load_locust_scenarios()
    print(f"Loaded {len(scen)} Locust scenarios.")
    print(f"Auto-detecting CloudWatch CSV timezones (display tz = {DISPLAY_TZ}):")
    cw = load_cloudwatch_duration(scen)
    if not cw:
        print("No CloudWatch Duration CSVs found in load-tests/results/cloudwatch/.")
        return
    print(f"Loaded CloudWatch Duration for: {list(cw.keys())}")
    merged = attach_cloudwatch(scen, cw)
    plot_overhead(merged)
    print()
    print("Done. Charts in analysis/cross_reference/charts/")


if __name__ == "__main__":
    main()
