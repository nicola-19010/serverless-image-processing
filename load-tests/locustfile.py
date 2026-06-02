"""
Locust load test for the 3 image-processing Lambdas.

Usage from the load-tests/ folder:

    # Interactive web UI (good for first runs)
    locust -f locustfile.py --host=https://placeholder.example.com

    # Headless run (used by run_scenarios.bat)
    set OPERATION=grayscale
    set IMAGE_SIZE=medium
    locust -f locustfile.py --host=https://placeholder.example.com ^
        --users 50 --spawn-rate 10 --run-time 5m --headless ^
        --csv results/grayscale_medium_50u

Required environment variables:
    OPERATION   one of: resize, grayscale, edge
    IMAGE_SIZE  one of: small, medium, large

Edit the ENDPOINTS dict below to point at your real API Gateway URLs.
"""

import os
import base64
import random
import glob
from pathlib import Path

from locust import HttpUser, task, between, events

# -----------------------------------------------------------------------------
# Configure your endpoints here. These are the public URLs from API Gateway.
# -----------------------------------------------------------------------------
ENDPOINTS = {
    "resize":    "https://95tj967lqi.execute-api.us-east-1.amazonaws.com/default/resize-fn",
    "grayscale": "https://REPLACE_ME.execute-api.us-east-1.amazonaws.com/default/grayscale-fn",
    "edge":      "https://5sgtof2x3m.execute-api.us-east-1.amazonaws.com/default/edge-fn",
}

# Path where generate_images.py left the test images
IMAGES_ROOT = Path(__file__).parent.parent / "local-tests" / "images"


def _load_images(size_label: str):
    """Read all images in a given size bucket into memory once."""
    files = glob.glob(str(IMAGES_ROOT / size_label / "*.jpg"))
    if not files:
        raise RuntimeError(
            f"No images found in {IMAGES_ROOT / size_label}. "
            f"Did you run 'python local-tests/generate_images.py'?"
        )
    return [Path(f).read_bytes() for f in files]


class ImageProcessingUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        operation = os.environ.get("OPERATION", "grayscale").lower()
        image_size = os.environ.get("IMAGE_SIZE", "medium").lower()

        if operation not in ENDPOINTS:
            raise RuntimeError(
                f"Invalid OPERATION='{operation}'. Use one of: {list(ENDPOINTS)}"
            )
        if image_size not in ("small", "medium", "large"):
            raise RuntimeError(
                f"Invalid IMAGE_SIZE='{image_size}'. Use small, medium or large."
            )

        self.operation = operation
        self.image_size = image_size
        self.target_url = ENDPOINTS[operation]
        self.images_bytes = _load_images(image_size)

        # Pre-encode images to save CPU per request
        self.images_b64 = [
            base64.b64encode(b).decode("utf-8") for b in self.images_bytes
        ]

    @task
    def process_image(self):
        img_b64 = random.choice(self.images_b64)

        payload = {"image": img_b64}
        if self.operation == "resize":
            payload.update({"width": 400, "height": 300})

        # We hit the absolute URL so Locust's --host can be ignored. The "name"
        # parameter groups all requests under a single label in the results.
        with self.client.post(
            self.target_url,
            json=payload,
            name=f"{self.operation}-{self.image_size}",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"HTTP {resp.status_code}: {resp.text[:200]}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    op = os.environ.get("OPERATION", "grayscale")
    size = os.environ.get("IMAGE_SIZE", "medium")
    print(f"\n*** Starting load test: OPERATION={op}, IMAGE_SIZE={size} ***\n")
