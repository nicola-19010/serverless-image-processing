"""
Local test for the resize Lambda — runs the handler without AWS.

The Lambda supports three modes:
  --width N             preserve aspect ratio, scale to width N
  --height N            preserve aspect ratio, scale to height N
  --width N --height M  force exact dimensions (may stretch)

Examples:
    python test_resize.py                              (default: width=400, proportional)
    python test_resize.py --size large --width 800
    python test_resize.py --width 400 --height 300     (stretch)
"""

import sys
import json
import base64
import time
import argparse
from pathlib import Path

HERE = Path(__file__).parent
LAMBDA_DIR = HERE.parent / "lambdas" / "resize"
sys.path.insert(0, str(LAMBDA_DIR))

from lambda_function import lambda_handler  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", default="medium", choices=["small", "medium", "large"])
    parser.add_argument("--image", default="image_001.jpg")
    parser.add_argument("--width", type=int, default=400,
                        help="Target width (default 400)")
    parser.add_argument("--height", type=int, default=None,
                        help="Target height. If omitted, aspect ratio is preserved.")
    args = parser.parse_args()

    img_path = HERE / "images" / args.size / args.image
    if not img_path.exists():
        print(f"ERROR: image not found at {img_path}")
        print("Did you run 'python generate_images.py' first?")
        sys.exit(1)

    print(f"Loading {img_path} ({img_path.stat().st_size // 1024} KB)...")
    img_b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")

    request = {"image": img_b64, "width": args.width}
    if args.height is not None:
        request["height"] = args.height

    event = {"body": json.dumps(request)}

    mode = "proportional" if args.height is None else f"exact ({args.width}x{args.height})"
    print(f"Invoking resize Lambda handler (mode: {mode})...")
    t0 = time.perf_counter()
    response = lambda_handler(event, None)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"Status: {response['statusCode']}")
    print(f"Elapsed: {elapsed_ms:.1f} ms")

    body = json.loads(response["body"])
    if response["statusCode"] != 200:
        print("ERROR:", body)
        sys.exit(1)

    outputs_dir = HERE / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    out_path = outputs_dir / "output_resized.jpg"
    out_path.write_bytes(base64.b64decode(body["image"]))

    meta = {k: v for k, v in body.items() if k != "image"}
    print("Response:", json.dumps(meta, indent=2))
    print(f"Output saved to: {out_path}")


if __name__ == "__main__":
    main()
