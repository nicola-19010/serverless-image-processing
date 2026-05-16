"""
AWS Lambda — Edge Detection

Receives a base64-encoded image, returns an edge-detected version as base64.
Uses Pillow's FIND_EDGES filter (which applies a 3x3 edge-detection kernel
followed by a small post-processing step). This is computationally heavier
than grayscale or resize, which makes it useful for the scalability analysis.

Designed to run on Python 3.11 with the Pillow layer.

Input event (from API Gateway HTTP API):
    {
      "body": "{\"image\": \"<base64>\"}"
    }

Output:
    {
      "statusCode": 200,
      "headers": {...},
      "body": "{\"operation\": \"edge_detection\", \"size_bytes\": 12345,
                \"image\": \"<base64>\"}"
    }
"""

import json
import base64
import io
from PIL import Image, ImageFilter


def lambda_handler(event, context):
    try:
        body = _parse_body(event)

        img_b64 = body["image"]
        img_data = base64.b64decode(img_b64)
        img = Image.open(io.BytesIO(img_data))
        img_format = img.format or "JPEG"

        # Convert to grayscale first (FIND_EDGES works on single-channel images)
        img_gray = img.convert("L")

        # Apply edge detection kernel. To make this heavier (useful for analysis),
        # we run a small smoothing pass first, then the edge filter.
        img_smooth = img_gray.filter(ImageFilter.SMOOTH)
        img_edges = img_smooth.filter(ImageFilter.FIND_EDGES)

        output = io.BytesIO()
        img_edges.save(output, format=img_format, quality=85)
        result_bytes = output.getvalue()
        result_b64 = base64.b64encode(result_bytes).decode("utf-8")

        return _ok({
            "operation": "edge_detection",
            "size_bytes": len(result_bytes),
            "image": result_b64,
        })

    except KeyError as e:
        return _error(400, f"Missing required field: {e}")
    except Exception as e:
        return _error(500, f"Internal error: {type(e).__name__}: {e}")


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
