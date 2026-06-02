"""
Import high-resolution source images and create resized versions for testing.

This script:
  1. Reads images from a source directory.
  2. Resizes each one to three target sizes (small, medium, large) using
     a cover + center-crop strategy (no stretching).
  3. Saves them under local-tests/images/{small,medium,large}/ as
     image_001.jpg, image_002.jpg, etc.

Default source directory: local-tests/source_images/
You can override it via a CLI argument:

    python import_and_resize_images.py
    python import_and_resize_images.py "C:\\Users\\you\\Downloads\\my_photos"

Why a relative default? Because hard-coding an absolute path forces every
teammate to edit this file before running it. A relative path inside the
project means everyone works the same way: drop the source images into
local-tests/source_images/ and run the script.

The source_images/ folder is in .gitignore — image files are not versioned
in git, only this script is. Each teammate must have a local copy of the
same source images (shared via WhatsApp / Drive / etc.).
"""

import sys
from pathlib import Path
from PIL import Image


HERE = Path(__file__).parent
DEFAULT_SOURCE_DIR = HERE / "source_images"
IMAGES_DIR = HERE / "images"

SIZE_SPECS = {
    "small":  (500, 500),     # ~100 KB JPEG
    "medium": (1500, 1500),   # ~1 MB JPEG
    "large":  (3000, 3000),   # ~5 MB JPEG
}

SUPPORTED_FORMATS = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp")


def cover_crop(img: Image.Image, target_size: tuple) -> Image.Image:
    """
    Resize an image so it fully covers target_size, then center-crop to it.

    This preserves the aspect ratio of the input (no stretching) at the cost
    of cropping the longer edge. Standard thumbnail strategy.
    """
    src_w, src_h = img.size
    tgt_w, tgt_h = target_size

    scale = max(tgt_w / src_w, tgt_h / src_h)
    new_w = int(round(src_w * scale))
    new_h = int(round(src_h * scale))

    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    left = (new_w - tgt_w) // 2
    top = (new_h - tgt_h) // 2
    return resized.crop((left, top, left + tgt_w, top + tgt_h))


def main():
    source_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE_DIR

    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}")
        print()
        print("Either:")
        print(f"  1. Drop your source images into:  {DEFAULT_SOURCE_DIR}")
        print( "  2. Or pass an explicit path, e.g.:")
        print(f"     python import_and_resize_images.py \"C:\\Users\\you\\Downloads\\photos\"")
        sys.exit(1)

    image_files = sorted([
        f for f in source_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS
    ])

    if not image_files:
        print(f"ERROR: No image files found in {source_dir}")
        print(f"Supported formats: {SUPPORTED_FORMATS}")
        sys.exit(1)

    print(f"Found {len(image_files)} source images in {source_dir}")
    print()

    # Prepare output directories
    for size_label in SIZE_SPECS:
        (IMAGES_DIR / size_label).mkdir(parents=True, exist_ok=True)

    # Process each source image
    for idx, src_file in enumerate(image_files, start=1):
        print(f"[{idx}/{len(image_files)}] {src_file.name}")

        try:
            img = Image.open(src_file).convert("RGB")
            print(f"    original: {img.size[0]}x{img.size[1]}")

            for size_label, target_dims in SIZE_SPECS.items():
                cropped = cover_crop(img, target_dims)
                out_path = IMAGES_DIR / size_label / f"image_{idx:03d}.jpg"
                cropped.save(out_path, format="JPEG", quality=85)
                kb = out_path.stat().st_size // 1024
                print(f"    {size_label:6s} -> {target_dims[0]}x{target_dims[1]}  ({kb} KB)")
        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {e}")
            continue

    # Summary
    print()
    print("Done. Final counts:")
    for size_label in SIZE_SPECS:
        n = len(list((IMAGES_DIR / size_label).glob("*.jpg")))
        print(f"  {size_label}: {n} images")


if __name__ == "__main__":
    main()
