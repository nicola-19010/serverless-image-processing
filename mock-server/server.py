"""
Local mock server that wraps the 3 Lambda handlers as HTTP endpoints.

Lets you run the Postman collection (or any HTTP client) locally against
the same code that will run on AWS Lambda, without having to deploy.

Routes:
    POST /resize     -> calls lambdas/resize/lambda_function.lambda_handler
    POST /grayscale  -> calls lambdas/grayscale/lambda_function.lambda_handler
    POST /edge       -> calls lambdas/edge/lambda_function.lambda_handler
    GET  /           -> health check (returns a small status JSON)

The request body is forwarded into the handler under the same "body" key
that AWS API Gateway would use, so the Lambda code runs unchanged.

Run with:
    python mock-server\server.py

Or, from anywhere with the venv active:
    mock-server\run_mock.bat
"""

import sys
import json
import importlib.util
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent
LAMBDAS_DIR = PROJECT_ROOT / "lambdas"

PORT = 5000


def _load_handler(operation: str):
    """Load lambda_handler from lambdas/<operation>/lambda_function.py."""
    module_path = LAMBDAS_DIR / operation / "lambda_function.py"
    if not module_path.exists():
        raise RuntimeError(f"Handler not found at {module_path}")

    # Each Lambda's lambda_function.py is loaded into a unique module name
    # so they don't shadow each other.
    spec = importlib.util.spec_from_file_location(
        f"lambda_{operation}", module_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.lambda_handler


# Pre-load all handlers at startup
HANDLERS = {
    "/resize":    _load_handler("resize"),
    "/grayscale": _load_handler("grayscale"),
    "/edge":      _load_handler("edge"),
}


class MockHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Slightly less noisy logs
        sys.stderr.write(f"[mock] {fmt % args}\n")

    def do_GET(self):
        if self.path in ("/", "/health"):
            self._send_json(200, {
                "status": "ok",
                "endpoints": list(HANDLERS.keys()),
                "message": "Local mock server for the 3 image processing Lambdas",
            })
            return
        self._send_json(404, {"error": f"Unknown path: {self.path}"})

    def do_POST(self):
        if self.path not in HANDLERS:
            self._send_json(404, {"error": f"Unknown endpoint: {self.path}"})
            return

        # Read the request body
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8") if length else ""

        # Build an API-Gateway-like event so the handler runs unchanged
        event = {"body": raw}

        try:
            response = HANDLERS[self.path](event, None)
        except Exception as e:
            self._send_json(500, {"error": f"{type(e).__name__}: {e}"})
            return

        status = response.get("statusCode", 200)
        headers = response.get("headers", {})
        body = response.get("body", "")

        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        if "Content-Type" not in {k.title() for k in headers}:
            self.send_header("Content-Type", "application/json")
        self.end_headers()
        if isinstance(body, str):
            self.wfile.write(body.encode("utf-8"))
        else:
            self.wfile.write(json.dumps(body).encode("utf-8"))

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), MockHandler)
    print("=" * 60)
    print(f"  Mock Lambda server running on http://127.0.0.1:{PORT}")
    print("=" * 60)
    print("Endpoints:")
    for path in HANDLERS:
        print(f"  POST http://127.0.0.1:{PORT}{path}")
    print("Health check:")
    print(f"  GET  http://127.0.0.1:{PORT}/")
    print()
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
