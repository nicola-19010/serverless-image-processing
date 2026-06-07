from PIL import Image
import sys

try:
    img = Image.open(sys.argv[1])
    print(f"Format: {img.format}")
    print(f"Mode: {img.mode}")
    print(f"Size: {img.size}")
except Exception as e:
    print(f"Error: {e}")
