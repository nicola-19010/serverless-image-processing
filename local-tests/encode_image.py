"""
Encode an image file as base64 and print it to stdout.

Useful for pasting into Lambda test events:
    python encode_image.py images/medium/image_001.jpg > b64.txt

Or to copy to clipboard on Windows:
    python encode_image.py images/medium/image_001.jpg | clip
"""

import sys
import base64
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python encode_image.py <path-to-image>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
