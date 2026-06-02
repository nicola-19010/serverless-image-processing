"""
Cold-start measurement script.

A cold start happens when AWS Lambda has no warm container ready and has to
launch one from scratch. They take significantly longer than warm invocations.

This script:
  1. Sends 1 request to each of the 3 Lambdas.
  2. Records the response time.
  3. Waits 20 minutes (long enough for AWS to recycle the warm container).
  4. Repeats N_REPETITIONS times.

The data lands in results/cold_starts.csv with columns:
    timestamp, operation, response_time_ms, status_code

Note: this only captures client-observed time. For the actual Init Duration
metric (server-side), you must look at CloudWatch Logs for each Lambda
function and grep for "Init Duration".

Usage:
    cd load-tests
    python cold_start_test.py
"""

import time
import csv
import base64
import datetime
from pathlib import Path

import requests

# Same ENDPOINTS as in locustfile.py — keep these in sync!
ENDPOINTS = {
    "resize":    "https://95tj967lqi.execute-api.us-east-1.amazonaws.com/default/resize-fn",
    "grayscale": "https://REPLACE_ME.execute-api.us-east-1.amazonaws.com/default/grayscale-fn",
    "edge":      "https://5sgtof2x3m.execute-api.us-east-1.amazonaws.com/default/edge-fn",
}

# How many cold-start rounds to do per Lambda
N_REPETITIONS = 10

# Wait time between rounds (AWS keeps containers warm for 5–15 min, so 20 min
# is a safe margin to guarantee a cold start)
WAIT_SECONDS = 20 * 60

# Path to a sample image (small, to make the test cheap)
HERE = Path(__file__).parent
IMAGE_PATH = HERE.parent / "local-tests" / "images" / "small" / "image_001.jpg"

OUT_PATH = HERE / "results" / "cold_starts.csv"


def measure_one(operation: str, url: str, img_b64: str):
    """Send one request and return (status_code, elapsed_ms)."""
    payload = {"image": img_b64}
    if operation == "resize":
        payload.update({"width": 400, "height": 300})

    t0 = time.perf_counter()
    try:
        resp = requests.post(url, json=payload, timeout=60)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return resp.status_code, elapsed_ms
    except requests.RequestException as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return -1, elapsed_ms


def main():
    if not IMAGE_PATH.exists():
        raise SystemExit(
            f"Test image not found at {IMAGE_PATH}. Run "
            f"'python local-tests/generate_images.py' first."
        )

    img_b64 = base64.b64encode(IMAGE_PATH.read_bytes()).decode("utf-8")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "operation", "round", "response_time_ms", "status_code"])

        for rnd in range(1, N_REPETITIONS + 1):
            print(f"\n=== Round {rnd}/{N_REPETITIONS} ===")
            for op, url in ENDPOINTS.items():
                ts = datetime.datetime.now().isoformat(timespec="seconds")
                status, elapsed = measure_one(op, url, img_b64)
                writer.writerow([ts, op, rnd, f"{elapsed:.1f}", status])
                f.flush()
                print(f"  {op}: status={status}, {elapsed:.1f} ms")

            if rnd < N_REPETITIONS:
                print(f"Waiting {WAIT_SECONDS // 60} minutes before next round...")
                time.sleep(WAIT_SECONDS)

    print(f"\nDone. Results: {OUT_PATH}")
    print("Also check CloudWatch Logs for the actual 'Init Duration' values.")


if __name__ == "__main__":
    main()
