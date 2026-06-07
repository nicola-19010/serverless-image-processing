"""
CloudWatch analysis — server-side Lambda metrics.

Handles the AWS Console export format which starts with 5 metadata rows
(Id, StatusCode, Messages, Full label, Label) before the actual data, AND
also handles simple 2-column CSVs.

Metrics:
  Invocations (Sum) | Duration (Min/Avg/Max) | ConcurrentExecutions (Max)
  Errors (Sum) + Success rate | Throttles (Sum)
"""

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
CW_DIR = PROJECT_ROOT / "load-tests" / "results" / "cloudwatch"
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


def _classify_column(col_name):
    name = str(col_name).lower()
    if any(kw in name for kw in STAT_KEYWORDS["rate"]):
        return "rate"
    for stat in ["min", "avg", "max", "sum", "errors"]:
        if any(kw in name for kw in STAT_KEYWORDS[stat]):
            return stat
    return "other"


def _find_header_row(path):
    """
    AWS Console export starts with 5 metadata rows.  Detect the 'Label' row
    (which has the human-readable stat names) and return its 0-indexed row
    number.  Returns 0 for simple 2-column CSVs where data starts immediately.
    """
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i > 10:
                break
            first_cell = line.split(",", 1)[0].strip().strip('"').lower()
            if first_cell == "label":
                return i
    return 0


def load_metric(operation, metric):
    path = CW_DIR / f"{operation}_{metric}.csv"
    if not path.exists():
        return None
    header_row = _find_header_row(path)
    raw = pd.read_csv(path, header=header_row)
    if raw.shape[1] < 2:
        return None
    out = pd.DataFrame()
    # First column = timestamp
    out["timestamp"] = pd.to_datetime(raw.iloc[:, 0], errors="coerce")
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


def plot_simple_over_time(metric, preferred_stats, title, ylabel, fname):
    fig, ax = plt.subplots(figsize=(11, 5))
    plotted = False
    for op in OPERATIONS:
        df = load_metric(op, metric)
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


def plot_duration_with_band():
    fig, ax = plt.subplots(figsize=(11, 5.5))
    plotted = False
    for op in OPERATIONS:
        df = load_metric(op, "duration")
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
    ax.set_xlabel("Time")
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


def plot_duration_distribution():
    fig, ax = plt.subplots(figsize=(8, 5))
    data, labels = [], []
    for op in OPERATIONS:
        df = load_metric(op, "duration")
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
    bp = ax.boxplot(data, labels=labels, showfliers=False, patch_artist=True)
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


def plot_errors_with_success_rate():
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax2 = ax.twinx()
    plotted = False
    has_rate = False
    for op in OPERATIONS:
        df = load_metric(op, "errors")
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
    ax.set_xlabel("Time")
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


def summary_table():
    rows = []
    for op in OPERATIONS:
        row = {"lambda": f"{op}-fn"}
        df = load_metric(op, "invocations")
        if df is not None and not df.empty:
            col = primary_column(df, ["sum", "max"])
            row["total_invocations"] = int(df[col].sum()) if col else None
        else:
            row["total_invocations"] = None
        df = load_metric(op, "duration")
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
        df = load_metric(op, "concurrent")
        if df is not None and not df.empty:
            col = primary_column(df, ["max", "avg"])
            row["max_concurrent_executions"] = int(df[col].max()) if col else None
        else:
            row["max_concurrent_executions"] = None
        df = load_metric(op, "errors")
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
        df = load_metric(op, "throttles")
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
    print("Generating charts...")
    plot_simple_over_time(
        "concurrent", ["max", "avg"],
        "Concurrent Lambda executions over time",
        "Concurrent executions (max)",
        "concurrent_executions_over_time.png",
    )
    plot_duration_with_band()
    plot_simple_over_time(
        "invocations", ["sum", "max"],
        "Lambda invocations rate over time",
        "Invocations per minute",
        "invocations_over_time.png",
    )
    plot_errors_with_success_rate()
    plot_simple_over_time(
        "throttles", ["sum", "max"],
        "Lambda throttled invocations over time",
        "Throttles per minute",
        "throttles_over_time.png",
    )
    plot_duration_distribution()
    summary_table()
    print("Done. Charts in analysis/cloudwatch/charts/")


if __name__ == "__main__":
    main()
