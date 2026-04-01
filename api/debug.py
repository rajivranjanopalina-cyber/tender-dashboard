from http.server import BaseHTTPRequestHandler
import json
import traceback
import sys


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        errors = []
        modules = {}

        tests = [
            ("mangum", "from mangum import Mangum"),
            ("sqlalchemy", "import sqlalchemy"),
            ("sqlalchemy_libsql", "import sqlalchemy_libsql"),
            ("fastapi", "from fastapi import FastAPI"),
            ("bcrypt", "import bcrypt"),
            ("pyjwt", "import jwt"),
            ("cryptography", "from cryptography.fernet import Fernet"),
            ("docx", "import docx"),
            ("bs4", "from bs4 import BeautifulSoup"),
            ("backend.database", "from backend.database import Base"),
            ("backend.main", "from backend.main import app"),
        ]

        for name, stmt in tests:
            try:
                exec(stmt)
                modules[name] = "ok"
            except Exception as e:
                modules[name] = f"FAILED: {e}"
                errors.append(f"{name}: {traceback.format_exc()}")

        result = {
            "modules": modules,
            "python": sys.version,
            "errors": errors[:3],
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result, indent=2).encode())
