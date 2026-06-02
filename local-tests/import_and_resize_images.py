"""
Import high-resolution images and create resized versions for testing.

This script:
  1. Reads images from a source directory
  2. Resizes each to three target sizes (small, medium, large)
  3. Saves them to the local-tests/images/ folder structure

Usage:
    python import_and_resize_images.py

Edit SOURCE_DIR below to point to your image folder.
"""

import os
import sys
from pathlib import Path
from PIL import Image

# ============================================================================
# EDIT THIS PATH to your images folder
# ============================================================================
SOURCE_DIR = Path("C:\\Users\\Mathias\\Downloads\\images")

# ============================================================================
# Target sizes and directories
# ============================================================================
HERE = Path(__file__).parent
IMAGES_DIR = HERE / "images"

SIZE_SPECS = {
    "small":  (500, 500),       # ~100 KB JPEG
    "medium": (1500, 1500),     # ~1 MB JPEG
    "large":  (3000, 3000),     # ~5 MB JPEG
}


def resize_image_to(img: Image.Image, target_size: tuple) -> Image.Image:
    """Resize an image to exactly target_size.
    
    Uses smart cropping to avoid stretching:
    - Calculates the scale factor that fits the image without empty space
    - Resizes to that scale
    - Crops from the center to reach exact target dimensions
    """
    # Calculate which scale factor makes the image cover the target completely
    width_ratio = target_size[0] / img.size[0]
    height_ratio = target_size[1] / img.size[1]
    
    # Use the larger ratio so the image covers the entire target area
    scale_factor = max(width_ratio, height_ratio)
    
    # Resize to the scaled dimensions
    new_width = int(img.size[0] * scale_factor)
    new_height = int(img.size[1] * scale_factor)
    
    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Crop from center to reach exact target size
    left = (new_width - target_size[0]) // 2
    top = (new_height - target_size[1]) // 2
    right = left + target_size[0]
    bottom = top + target_size[1]
    
    cropped = resized.crop((left, top, right, bottom))
    return cropped


def main():
    # Check source directory exists
    if not SOURCE_DIR.exists():
        print(f"ERROR: Source directory not found: {SOURCE_DIR}")
        sys.exit(1)
    
    # Find all image files
    supported_formats = (".jpg", ".jpeg", ".png", ".bmp", ".gif")
    image_files = sorted([
        f for f in SOURCE_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in supported_formats
    ])
    
    if not image_files:
        print(f"ERROR: No image files found in {SOURCE_DIR}")
        print(f"Supported formats: {supported_formats}")
        sys.exit(1)
    
    print(f"Found {len(image_files)} images in {SOURCE_DIR}")
    
    # Create output directories
    for size_label in SIZE_SPECS:
        out_dir = IMAGES_DIR / size_label
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output dir: {out_dir}")
    
    # Process each image
    for idx, src_file in enumerate(image_files, start=1):
        print(f"\n[{idx}/{len(image_files)}] Processing {src_file.name}...")
        
        try:
            # Open and convert to RGB (in case of PNG with transparency)
            img = Image.open(src_file).convert("RGB")
            orig_size = img.size
            print(f"  Original size: {orig_size}")
            
            # Create resized versions for each size category
            for size_label, target_dims in SIZE_SPECS.items():
                resized = resize_image_to(img, target_dims)
                
                # Save as JPEG with quality 85 (good balance)
                out_path = IMAGES_DIR / size_label / f"image_{idx:03d}.jpg"
                resized.save(out_path, format="JPEG", quality=85)
                file_size_kb = out_path.stat().st_size / 1024
                
                print(f"    {size_label:6s} -> {target_dims} ({file_size_kb:.1f} KB) → {out_path.name}")
        
        except Exception as e:
            print(f"  ERROR processing {src_file.name}: {e}")
            continue
    
    print("\n✓ Done! Images ready for testing.")
    print(f"  small/  : {len(list(IMAGES_DIR / 'small' / '*.jpg'))} images")
    print(f"  medium/ : {len(list(IMAGES_DIR / 'medium' / '*.jpg'))} images")
    print(f"  large/  : {len(list(IMAGES_DIR / 'large' / '*.jpg'))} images")


if __name__ == "__main__":
    main()
