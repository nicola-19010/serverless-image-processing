import sys
import json
import base64
import time
from pathlib import Path

HERE = Path(__file__).parent
LAMBDA_DIR = HERE.parent / "lambdas" / "grayscale"
sys.path.insert(0, str(LAMBDA_DIR))

from lambda_function import lambda_handler  # noqa: E402


def main():
    # Target the source_images directory directly
    img_dir = HERE / "source_images"
    if not img_dir.exists():
        print(f"ERROR: Directory not found at {img_dir}")
        print("Please make sure your 'source_images' folder exists in this directory.")
        sys.exit(1)

    # Gather all JPG and PNG images in the folder
    images = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.jpeg")) + list(img_dir.glob("*.png"))
    
    if not images:
        print(f"No images found in {img_dir}")
        sys.exit(0)

    print(f"Found {len(images)} images to process in '{img_dir.name}'...\n")

    # Prepare the output directory
    outputs_dir = HERE / "outputs"
    outputs_dir.mkdir(exist_ok=True)

    # Loop through and process every image
    for img_path in images:
        print(f"Processing: {img_path.name} ({img_path.stat().st_size // 1024} KB)")
        
        # Read file and encode to base64
        img_b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
        event = {"body": json.dumps({"image": img_b64})}

        # Invoke the Lambda handler locally
        t0 = time.perf_counter()
        response = lambda_handler(event, None)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        print(f"  -> Status: {response['statusCode']}")
        print(f"  -> Speed:  {elapsed_ms:.1f} ms")

        body = json.loads(response["body"])
        
        if response["statusCode"] == 200:
            # Save using the original filename so images don't overwrite each other
            out_path = outputs_dir / f"grayscale_{img_path.name}"
            out_path.write_bytes(base64.b64decode(body["image"]))
            print(f"  -> Saved:  {out_path.name}")
        else:
            print(f"  -> ERROR:  {body}")
            
        print("-" * 50)

    print(f"\nDone! All outputs saved to: {outputs_dir}/")


if __name__ == "__main__":
    main()
