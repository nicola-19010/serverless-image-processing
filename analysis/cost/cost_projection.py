"""
6-month cost projection: AWS Lambda vs EC2 t3.small.

The script:
  1. Reads the measured Duration from CloudWatch (if available) — otherwise
     falls back to a default estimate.
  2. Defines pricing constants for both architectures (us-east-1, on-demand).
  3. Computes the 6-month cost for monthly image volumes from 10k to 100M.
  4. Solves for the break-even point where Lambda cost equals EC2 cost.
  5. Plots both curves on a log-scale X axis and saves charts/cost_breakeven.png.

Usage (from project root):
    python analysis/cost/cost_projection.py
"""

import csv
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
CW_DIR = PROJECT_ROOT / "load-tests" / "results" / "cloudwatch"
CHARTS_DIR = HERE / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

# -----------------------------------------------------------------------------
# Inputs
# -----------------------------------------------------------------------------
DEFAULT_DURATION_S = 0.5                 # fallback if no CloudWatch data
LAMBDA_MEMORY_MB = 512                   # memory configured on the Lambda
MONTHS = 6                               # projection horizon
OPERATIONS = ["resize", "grayscale", "edge"]


def measured_duration_seconds():
    """
    Read CloudWatch Duration CSVs (if present) and return the average duration
    in seconds across all 3 Lambdas. Falls back to DEFAULT_DURATION_S.
    """
    values = []
    for op in OPERATIONS:
        path = CW_DIR / f"{op}_duration.csv"
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path)
            cols = list(df.columns)
            if len(cols) >= 2:
                v = pd.to_numeric(df[cols[1]], errors="coerce").dropna()
                if not v.empty:
                    values.append(v.mean())
        except Exception:
            pass
    if values:
        avg_ms = sum(values) / len(values)
        print(f"Using measured average Duration from CloudWatch: {avg_ms:.1f} ms "
              f"(across {len(values)} Lambda(s)).")
        return avg_ms / 1000.0
    print(f"No CloudWatch Duration data found. Using default: {DEFAULT_DURATION_S} s.")
    return DEFAULT_DURATION_S


AVG_DURATION_S = measured_duration_seconds()

# -----------------------------------------------------------------------------
# AWS Lambda pricing (us-east-1, x86, on-demand) — May 2026 list prices
# -----------------------------------------------------------------------------
LAMBDA_REQUEST_PRICE_PER_M = 0.20        # USD per 1 million requests
LAMBDA_GB_SECOND_PRICE = 0.0000166667    # USD per GB-second

# -----------------------------------------------------------------------------
# API Gateway HTTP API pricing
# -----------------------------------------------------------------------------
API_GW_PRICE_PER_M = 1.00                # USD per 1 million requests (HTTP API)

# -----------------------------------------------------------------------------
# EC2 t3.small pricing (us-east-1, on-demand)
# -----------------------------------------------------------------------------
EC2_T3_SMALL_HOURLY = 0.0208             # USD per hour
EC2_HOURS_PER_MONTH = 730                # AWS standard
EC2_EBS_STORAGE_USD_MONTH = 1.50         # ~15 GB gp3 storage
EC2_DATA_TRANSFER_USD_MONTH = 1.00       # rough estimate


def lambda_cost(images_per_month: int) -> float:
    """6-month cost of Lambda + API Gateway for a given monthly image volume."""
    total_invocations = images_per_month * MONTHS

    # Lambda costs
    request_cost = (total_invocations / 1_000_000) * LAMBDA_REQUEST_PRICE_PER_M
    gb_seconds = total_invocations * AVG_DURATION_S * (LAMBDA_MEMORY_MB / 1024)
    compute_cost = gb_seconds * LAMBDA_GB_SECOND_PRICE

    # API Gateway costs (HTTP API)
    api_cost = (total_invocations / 1_000_000) * API_GW_PRICE_PER_M

    return request_cost + compute_cost + api_cost


def ec2_cost(images_per_month: int) -> float:
    """6-month cost of EC2 t3.small running the same workload.

    EC2 cost is flat — it doesn't scale with volume (we assume one instance
    is enough for the workload up to its capacity). We add modest storage
    and transfer costs.
    """
    compute_per_month = EC2_T3_SMALL_HOURLY * EC2_HOURS_PER_MONTH
    monthly_total = compute_per_month + EC2_EBS_STORAGE_USD_MONTH + EC2_DATA_TRANSFER_USD_MONTH
    return monthly_total * MONTHS


def find_breakeven(volumes_per_month, lambda_costs, ec2_costs):
    """Find the volume at which the two curves cross (Lambda = EC2)."""
    for i in range(1, len(volumes_per_month)):
        if lambda_costs[i-1] < ec2_costs[i-1] and lambda_costs[i] >= ec2_costs[i]:
            # Linear interpolation between the two surrounding points
            v0, v1 = volumes_per_month[i-1], volumes_per_month[i]
            d0 = lambda_costs[i-1] - ec2_costs[i-1]
            d1 = lambda_costs[i] - ec2_costs[i]
            t = -d0 / (d1 - d0)
            return v0 + t * (v1 - v0)
    return None


def main():
    # Range of monthly image volumes (log-spaced for plotting)
    volumes = np.logspace(4, 8, 100).astype(int)   # 10k → 100M images/month

    lambda_costs = np.array([lambda_cost(v) for v in volumes])
    ec2_costs = np.array([ec2_cost(v) for v in volumes])

    breakeven = find_breakeven(volumes, lambda_costs, ec2_costs)

    # ---- Save the data as CSV for the report ----
    csv_path = CHARTS_DIR / "cost_table.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["images_per_month", "lambda_6mo_usd", "ec2_6mo_usd"])
        for v, lc, ec in zip(volumes, lambda_costs, ec2_costs):
            w.writerow([int(v), f"{lc:.2f}", f"{ec:.2f}"])
    print(f"Cost table saved to: {csv_path}")

    # ---- Plot ----
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(volumes, lambda_costs, label="AWS Lambda", linewidth=2)
    ax.plot(volumes, ec2_costs, label="EC2 t3.small (baseline)", linewidth=2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Images per month")
    ax.set_ylabel(f"6-month cost (USD)")
    ax.set_title("Cost projection: Lambda vs EC2 over 6 months")
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    ax.legend()

    if breakeven is not None:
        be_cost = lambda_cost(int(breakeven))
        ax.axvline(breakeven, color="red", linestyle=":", alpha=0.7)
        ax.annotate(
            f"Break-even\n~{int(breakeven):,} images/month\n~${be_cost:.0f}",
            xy=(breakeven, be_cost),
            xytext=(breakeven * 1.3, be_cost * 0.4),
            arrowprops={"arrowstyle": "->", "color": "red"},
            fontsize=10,
        )
        print(f"Break-even point: ~{int(breakeven):,} images/month")
    else:
        print("No break-even point found in the analyzed range.")

    out_path = CHARTS_DIR / "cost_breakeven.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"Chart saved to: {out_path}")

    # ---- Print summary table ----
    print("\nSample cost projections (6-month):")
    print(f"{'Images/month':>15} {'Lambda USD':>12} {'EC2 USD':>10}")
    print("-" * 41)
    for v in [10_000, 100_000, 1_000_000, 10_000_000, 100_000_000]:
        lc = lambda_cost(v)
        ec = ec2_cost(v)
        winner = "Lambda" if lc < ec else "EC2"
        print(f"{v:>15,} {lc:>12.2f} {ec:>10.2f}  (winner: {winner})")


if __name__ == "__main__":
    main()
