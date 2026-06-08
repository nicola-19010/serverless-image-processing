"""
CloudWatch analysis - server-side Lambda metrics, normalised to Europe/Rome.

Handles the AWS Console export format which starts with 5 metadata rows
(Id, StatusCode, Messages, Full label, Label) before the actual data, AND
also handles simple 2-column CSVs.

Each CSV's timezone is auto-detected by comparing its busiest minute against
the Locust scenario midpoint for the same operation (see analysis/_tz_helper.py).
All charts and the summary table use Europe/Rome timestamps.

Metrics:
  Invocations (Sum) | Duration (Min/Avg/Max) | ConcurrentExecutions (Max)
  Errors (Sum) + Success rate | Throttles (Sum)
"""

import re
import sys
import glob
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "analysis"))
from _tz_helper import (
    DISPLAY_TZ, find_header_row, detect_csv_offset_hours, to_display_tz,
)

CW_DIR = PROJECT_ROOT / "load-tests" / "results" / "cloudwatch"
LOCUST_DIR = PROJECT_ROOT / "load-tests" / "results"
CHARTS_DIR = HERE / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

OPERATIONS = ["resize", "grayscale", "edge"]
METRICS = ["invocations", "duration", "concurrent", "errors", "throttles"]
PALETTE = {"resize": "#1f77b4", "grayscale": "#2ca02c", "edge": "#d62728"}

STAT_KEYWORDS = {
    "min": ["mínimo", "minimo", "min", "minimum"],
    "avg": ["promedio", "media", "average", "avg", "mean"],
    "max": ["máximo", "maximo", "max", "maximum"],
    "sum": ["suma", "sum", "total"],
    "rate": ["tasa", "rate", "%", "exito", "éxito", "success"],
    "errors": ["errores", "errors", "error", "limitaciones", "throttle"],
}

SCEN = re.compile(
    r"(?P<op>resize|grayscale|edge)_(?P<size>small|medium|large)_"
    r"(?P<u>\d+)u_rep(?P<r>\d+)_stats_history\.csv$"
)


def _classify_column(col_name):
    name = str(col_name).lower()
    if any(kw in name for kw in STAT_KEYWORDS["rate"]):
        return "rate"
    for stat in ["min", "avg", "max", "sum", "errors"]:
        if any(kw in name for kw in STAT_KEYWORDS[stat]):
            return stat
    return "other"


def _locust_midpoint_per_op():
    """Return dict op -> UTC midpoint of all Locust scenarios for that op."""
    mids = {}
    per_op = {}
    for f in glob.glob(str(LOCUST_DIR / "*_stats_history.csv")):
        m = SCEN.search(f)
        if not m:
            continue
        op = m.group("op")
        df = pd.read_csv(f)
        if df.empty or "Timestamp" not in df.columns:
            continue
        ts = pd.to_datetime(df["Timestamp"], unit="s", utc=True, errors="coerce").dropna()
        if ts.empty:
            continue
        per_op.setdefault(op, []).extend([ts.iloc[0], ts.iloc[-1]])
    for op, lst in per_op.items():
        mn, mx = min(lst), max(lst)
        mids[op] = mn + (mx - mn) / 2
    return mids


_OFFSET_CACHE = {}  # op -> offset_h


def _get_offset_for(op, locust_mids):
    if op in _OFFSET_CACHE:
        return _OFFSET_CACHE[op]
    inv = CW_DIR / f"{op}_invocations.csv"
    if not inv.exists() or op not in locust_mids:
        _OFFSET_CACHE[op] = 0
        return 0
    offset = detect_csv_offset_hours(inv, locust_mids[op])
    _OFFSET_CACHE[op] = offset
    return offset


def load_metric(operation, metric, offset_h):
    path = CW_DIR / f"{operation}_{metric}.csv"
    if not path.exists():
        return None
    header_row = find_header_row(path)
    raw = pd.read_csv(path, header=header_row)
    if raw.shape[1] < 2:
        return None
    out = pd.DataFrame()
    naive = pd.to_datetime(raw.iloc[:, 0], errors="coerce")
    out["timestamp"] = to_display_tz(naive, offset_h)
    seen = set()
    for col in raw.columns[1:]:
        kind = _classify_column(col)
        if kind == "other":
            out[col] = pd.to_numeric(raw[col], errors="coerce")
            continue
        if kind in seen:
            continue
        seen.add(kind)
        out[kind] = pd.to_numeric(raw[col], errors="coerce")
    out = out.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return out


def primary_column(df, prefer):
    for stat in prefer:
        if stat in df.columns and df[stat].notna().any():
            return stat
    for c in df.columns:
        if c != "timestamp" and df[c].notna().any():
            return c
    return None


def check_files_present():
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
    return found, missing


def plot_simple_over_time(metric, preferred_stats, title, ylabel, fname, locust_mids):
    fig, ax = plt.subplots(figsize=(11, 5))
    plotted = False
    for op in OPERATIONS:
        offset = _get_offset_for(op, locust_mids)
        df = load_metric(op, metric, offset)
        if df is None or df.empty:
            continue
        col = primary_column(df, preferred_stats)
        if col is None:
            continue
        ax.plot(df["timestamp"], df[col], label=op, color=PALETTE[op], linewidth=1.8)
        plotted = True
    if not plotted:
        plt.close(fig)
        return
    ax.set_xlabel(f"Time ({DISPLAY_TZ})")
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


def plot_duration_with_band(locust_mids):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    plotted = False
    for op in OPERATIONS:
        offset = _get_offset_for(op, locust_mids)
        df = load_metric(op, "duration", offset)
        if df is None or df.empty:
            continue
        avg_col = primary_column(df, ["avg", "sum", "min", "max"])
        if avg_col is None:
            continue
        if "min" in df.columns and "max" in df.columns:
            ax.fill_between(df["timestamp"], df["min"], df["max"],
                            color=PALETTE[op], alpha=0.18,
                            label=f"{op} min-max")
        ax.plot(df["timestamp"], df[avg_col], color=PALETTE[op], linewidth=1.8,
                label=f"{op} {avg_col}")
        plotted = True
    if not plotted:
        plt.close(fig)
        return
    ax.set_xlabel(f"Time ({DISPLAY_TZ})")
    ax.set_ylabel("Duration (ms)")
    ax.set_title("Server-side Lambda Duration over time (avg line, min-max band)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    plt.tight_layout()
    out = CHARTS_DIR / "duration_over_time.png"
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  saved: {out.name}")


def plot_duration_distribution(locust_mids):
    fig, ax = plt.subplots(figsize=(8, 5))
    data, labels = [], []
    for op in OPERATIONS:
        offset = _get_offset_for(op, locust_mids)
        df = load_metric(op, "duration", offset)
        if df is None or df.empty:
            continue
        col = primary_column(df, ["avg", "sum", "max", "min"])
        if col is None:
            continue
        data.append(df[col].dropna())
        labels.append(op)
    if not data:
        plt.close(fig)
        return
    bp = ax.boxplot(data, tick_labels=labels, showfliers=False, patch_artist=True)
    for patch, op in zip(bp["boxes"], labels):
        patch.set_facecolor(PALETTE[op])
        patch.set_alpha(0.6)
    ax.set_ylabel("Duration (ms)")
    ax.set_title("Server-side Lambda Duration distribution")
    ax.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    out = CHARTS_DIR / "duration_distribution.png"
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  saved: {out.name}")


def plot_errors_with_success_rate(locust_mids):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax2 = ax.twinx()
    plotted = False
    has_rate = False
    for op in OPERATIONS:
        offset = _get_offset_for(op, locust_mids)
        df = load_metric(op, "errors", offset)
        if df is None or df.empty:
            continue
        err_col = primary_column(df, ["sum", "errors", "max"])
        if err_col is not None:
            ax.plot(df["timestamp"], df[err_col], color=PALETTE[op], linewidth=1.8,
                    label=f"{op} errors")
            plotted = True
        if "rate" in df.columns and df["rate"].notna().any():
            ax2.plot(df["timestamp"], df["rate"], color=PALETTE[op], linewidth=1.2,
                     linestyle="--", alpha=0.7, label=f"{op} success rate")
            has_rate = True
    if not plotted:
        plt.close(fig)
        return
    ax.set_xlabel(f"Time ({DISPLAY_TZ})")
    ax.set_ylabel("Errors (count)")
    if has_rate:
        ax2.set_ylabel("Success rate (%)")
        ax2.set_ylim(0, 105)
    ax.set_title("Lambda errors and success rate over time")
    lines, labels = ax.get_legend_handles_labels()
    if has_rate:
        l2, lab2 = ax2.get_legend_handles_labels()
        lines += l2
        labels += lab2
    ax.legend(lines, labels, fontsize=8)
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    plt.tight_layout()
    out = CHARTS_DIR / "errors_over_time.png"
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  saved: {out.name}")


def summary_table(locust_mids):
    rows = []
    for op in OPERATIONS:
        offset = _get_offset_for(op, locust_mids)
        row = {"lambda": f"{op}-fn"}
        df = load_metric(op, "invocations", offset)
        if df is not None and not df.empty:
            col = primary_column(df, ["sum", "max"])
            row["total_invocations"] = int(df[col].sum()) if col else None
        else:
            row["total_invocations"] = None
        df = load_metric(op, "duration", offset)
        if df is not None and not df.empty:
            avg_col = primary_column(df, ["avg"])
            row["avg_duration_ms"] = round(df[avg_col].mean(), 1) if avg_col else None
            row["p95_duration_ms"] = round(df[avg_col].quantile(0.95), 1) if avg_col else None
            row["min_duration_ms"] = round(df["min"].min(), 1) if "min" in df.columns else None
            if "max" in df.columns:
                row["max_duration_ms"] = round(df["max"].max(), 1)
            elif avg_col:
                row["max_duration_ms"] = round(df[avg_col].max(), 1)
            else:
                row["max_duration_ms"] = None
        else:
            for k in ("avg_duration_ms", "p95_duration_ms", "min_duration_ms", "max_duration_ms"):
                row[k] = None
        df = load_metric(op, "concurrent", offset)
        if df is not None and not df.empty:
            col = primary_column(df, ["max", "avg"])
            row["max_concurrent_executions"] = int(df[col].max()) if col else None
        else:
            row["max_concurrent_executions"] = None
        df = load_metric(op, "errors", offset)
        if df is not None and not df.empty:
            err_col = primary_column(df, ["sum", "errors", "max"])
            row["total_errors"] = int(df[err_col].sum()) if err_col else 0
            if "rate" in df.columns and df["rate"].notna().any():
                row["min_success_rate_pct"] = round(df["rate"].min(), 2)
            else:
                row["min_success_rate_pct"] = None
        else:
            row["total_errors"] = 0
            row["min_success_rate_pct"] = None
        df = load_metric(op, "throttles", offset)
        if df is not None and not df.empty:
            col = primary_column(df, ["sum", "max"])
            row["total_throttles"] = int(df[col].sum()) if col else 0
        else:
            row["total_throttles"] = 0
        rows.append(row)
    df = pd.DataFrame(rows)
    out = CHARTS_DIR / "summary_table.csv"
    df.to_csv(out, index=False)
    print(f"  saved: {out.name}")
    print()
    print("--- Summary (server-side, CloudWatch) ---")
    print(df.to_string(index=False))
    print()


def main():
    found, missing = check_files_present()
    if found == 0:
        print("No CloudWatch CSVs found. Nothing to do.")
        return
    print(f"Detecting CSV timezones (target display tz = {DISPLAY_TZ}):")
    locust_mids = _locust_midpoint_per_op()
    for op in OPERATIONS:
        offset = _get_offset_for(op, locust_mids)
        sign = "+" if offset > 0 else ""
        print(f"  [{op}] CSV detected as UTC{sign}{offset}")
    print()
    print("Generating charts (all timestamps shown in {}):".format(DISPLAY_TZ))
    plot_simple_over_time(
        "concurrent", ["max", "avg"],
        "Concurrent Lambda executions over time",
        "Concurrent executions (max)",
        "concurrent_executions_over_time.png",
        locust_mids,
    )
    plot_duration_with_band(locust_mids)
    plot_simple_over_time(
        "invocations", ["sum", "max"],
        "Lambda invocations rate over time",
        "Invocations per minute",
        "invocations_over_time.png",
        locust_mids,
    )
    plot_errors_with_success_rate(locust_mids)
    plot_simple_over_time(
        "throttles", ["sum", "max"],
        "Lambda throttled invocations over time",
        "Throttles per minute",
        "throttles_over_time.png",
        locust_mids,
    )
    plot_duration_distribution(locust_mids)
    summary_table(locust_mids)
    print("Done. Charts in analysis/cloudwatch/charts/")


if __name__ == "__main__":
    main()
