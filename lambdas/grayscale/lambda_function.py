"""
AWS Lambda — Image Grayscale

Receives a base64-encoded image, returns the grayscale version as base64.
Designed to run on Python 3.11 with the Pillow layer.

Input event (from API Gateway HTTP API):
    {
      "body": "{\"image\": \"<base64>\"}"
    }

Or direct invocation (no API Gateway):
    {
      "image": "<base64>"
    }

Output:
    {
      "statusCode": 200,
      "headers": {...},
      "body": "{\"operation\": \"grayscale\", \"size_bytes\": 12345,
                \"image\": \"<base64>\"}"
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
        img_data = base64.b64decode(img_b64)
        img = Image.open(io.BytesIO(img_data))
        img_format = img.format or "JPEG"

        # "L" mode is single-channel 8-bit grayscale
        img_gray = img.convert("L")

        output = io.BytesIO()
        img_gray.save(output, format=img_format, quality=85)
        result_bytes = output.getvalue()
        result_b64 = base64.b64encode(result_bytes).decode("utf-8")

        return _ok({
            "operation": "grayscale",
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
