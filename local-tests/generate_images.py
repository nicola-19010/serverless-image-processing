"""
Generate test images of three different sizes for load testing.

Creates 10 images in each of three size buckets:
  - small  ~ 100 KB each  (500x500 px)
  - medium ~ 1 MB each   (1500x1500 px)
  - large  ~ 5 MB each   (3000x3000 px)

Images are filled with random noise so they have realistic JPEG compression
characteristics (a flat-color image compresses too much).

Run with:
    python generate_images.py
"""

import os
import random
from pathlib import Path
from PIL import Image

# Number of images per size bucket
N_PER_SIZE = 10

# Output directory (relative to this script)
HERE = Path(__file__).parent
IMAGES_DIR = HERE / "images"

SIZE_SPECS = {
    "small": (500, 500),
    "medium": (1500, 1500),
    "large": (3000, 3000),
}


def make_noise_image(width: int, height: int) -> Image.Image:
    """Create a colored noise image with realistic compression behavior."""
    # Generate random RGB bytes
    n_bytes = width * height * 3
    data = bytes(random.getrandbits(8) for _ in range(n_bytes))
    return Image.frombytes("RGB", (width, height), data)


def main():
    print("Generating test images...")
    for label, (w, h) in SIZE_SPECS.items():
        out_dir = IMAGES_DIR / label
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"  {label} ({w}x{h}):", end=" ", flush=True)
        for i in range(1, N_PER_SIZE + 1):
            img = make_noise_image(w, h)
            out_path = out_dir / f"image_{i:03d}.jpg"
            img.save(out_path, format="JPEG", quality=85)
            print(".", end="", flush=True)

        # Report total disk used by this bucket
        total_kb = sum(f.stat().st_size for f in out_dir.glob("*.jpg")) // 1024
        print(f"  ~{total_kb} KB total ({total_kb // N_PER_SIZE} KB avg)")

    print("\nDone.")


if __name__ == "__main__":
    main()
