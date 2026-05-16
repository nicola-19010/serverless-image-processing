"""
AWS Lambda — Image Resize

Receives a base64-encoded image plus target dimensions, returns the resized
image as base64. Designed to run on Python 3.11 with the Pillow layer.

Resize behavior depends on which parameters are sent:
  - width + height  -> resize to exact dimensions (may stretch).
  - width only      -> preserve aspect ratio, scale to that width.
  - height only     -> preserve aspect ratio, scale to that height.
  - neither         -> default to width=800, preserve aspect ratio.

Input event (from API Gateway HTTP API):
    {
      "body": "{\"image\": \"<base64>\", \"width\": 400}"
    }

Or direct invocation (no API Gateway):
    {
      "image": "<base64>",
      "width": 400
    }

Output:
    {
      "statusCode": 200,
      "headers": {...},
      "body": "{\"operation\": \"resize\", \"width\": 400, \"height\": 300,
                \"original_width\": 1500, \"original_height\": 1500,
                \"size_bytes\": 12345, \"image\": \"<base64>\"}"
    }
"""

import json
import base64
import io
from PIL import Image


def lambda_handler(event, context):
    try:
        body = _parse_body(event)

        img_b64 = body["image"]
        target_width = body.get("width")
        target_height = body.get("height")

        img_data = base64.b64decode(img_b64)
        img = Image.open(io.BytesIO(img_data))
        img_format = img.format or "JPEG"
        original_w, original_h = img.size

        # Convert to RGB if needed (some formats need this before saving as JPEG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Decide final dimensions based on what was provided
        new_w, new_h = _compute_dimensions(
            original_w, original_h, target_width, target_height
        )

        img_resized = img.resize((new_w, new_h), Image.LANCZOS)

        output = io.BytesIO()
        img_resized.save(output, format=img_format, quality=85)
        result_bytes = output.getvalue()
        result_b64 = base64.b64encode(result_bytes).decode("utf-8")

        return _ok({
            "operation": "resize",
            "width": new_w,
            "height": new_h,
            "original_width": original_w,
            "original_height": original_h,
            "size_bytes": len(result_bytes),
            "image": result_b64,
        })

    except KeyError as e:
        return _error(400, f"Missing required field: {e}")
    except Exception as e:
        return _error(500, f"Internal error: {type(e).__name__}: {e}")


def _compute_dimensions(orig_w, orig_h, target_w, target_h):
    """
    Decide the final (width, height) for the resize:
      - If both provided  -> use as-is (may stretch).
      - If only one given -> preserve aspect ratio.
      - If neither        -> default to width=800, preserve aspect ratio.
    """
    if target_w is not None and target_h is not None:
        return int(target_w), int(target_h)

    aspect = orig_w / orig_h  # original aspect ratio (w / h)

    if target_w is not None:
        w = int(target_w)
        return w, max(1, int(round(w / aspect)))

    if target_h is not None:
        h = int(target_h)
        return max(1, int(round(h * aspect))), h

    # Neither provided: default width = 800, preserve aspect ratio
    w = 800
    return w, max(1, int(round(w / aspect)))


def _parse_body(event):
    """Handle both API Gateway events and direct invocations."""
    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            return json.loads(body)
        return body
    return event


def _ok(payload):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _error(status, message):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
