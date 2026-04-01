import traceback
import sys

_error = None
try:
    from mangum import Mangum
    from backend.main import app as _app
    handler = Mangum(_app, lifespan="off")
except Exception as e:
    _error = f"{e}\n{traceback.format_exc()}"
    print(f"IMPORT ERROR: {_error}", file=sys.stderr)

    from http.server import BaseHTTPRequestHandler

    class handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"error": "{str(_error)[:800]}"}}'.encode())
