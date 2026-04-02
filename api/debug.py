from http.server import BaseHTTPRequestHandler
import json
import traceback
import sys
import os


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        results = {}

        # Check env vars (redacted)
        env_keys = [
            "TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN", "SECRET_KEY",
            "DASHBOARD_PASSWORD_HASH", "BLOB_READ_WRITE_TOKEN",
        ]
        for k in env_keys:
            v = os.environ.get(k, "")
            results[k] = f"set ({len(v)} chars)" if v else "NOT SET"

        # Try creating engine and connecting
        try:
            from backend.database import engine
            results["engine_url"] = str(engine.url).split("?")[0]  # hide token
            with engine.connect() as conn:
                from sqlalchemy import text
                row = conn.execute(text("SELECT 1")).fetchone()
                results["db_connect"] = f"ok: {row}"
        except Exception as e:
            results["db_connect"] = f"FAILED: {traceback.format_exc()}"

        # Try init_db
        try:
            from backend.database import init_db
            init_db()
            results["init_db"] = "ok"
        except Exception as e:
            results["init_db"] = f"FAILED: {traceback.format_exc()}"

        # Try importing app
        try:
            from backend.main import app
            results["app_routes"] = len(app.routes)
            results["app_title"] = app.title
        except Exception as e:
            results["app_import"] = f"FAILED: {traceback.format_exc()}"

        # Test password verification
        try:
            import bcrypt
            pw_hash = os.environ.get("DASHBOARD_PASSWORD_HASH", "")
            results["pw_hash_prefix"] = pw_hash[:7] if pw_hash else "NOT SET"
            results["pw_hash_len"] = len(pw_hash)
            results["pw_verify_12345!"] = bcrypt.checkpw(b"12345!", pw_hash.encode())
        except Exception as e:
            results["pw_verify"] = f"FAILED: {e}"

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(results, indent=2).encode())
