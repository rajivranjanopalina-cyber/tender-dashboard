import os
from fastapi import HTTPException, Request
from backend.auth import decode_jwt


def require_auth(request: Request) -> dict:
    """
    FastAPI dependency that validates JWT from Authorization header.
    Also accepts X-Scrape-Token header for cron-triggered scrape requests
    on /scraper/ paths only.
    """
    # Allow scrape token auth ONLY for scraper endpoints (GitHub Actions cron)
    scrape_token = request.headers.get("X-Scrape-Token", "")
    expected_scrape = os.environ.get("SCRAPE_SECRET", "")
    if scrape_token and expected_scrape and scrape_token == expected_scrape:
        if "/scraper/" in str(request.url.path):
            return {"auth": "scrape_token"}
        # Scrape token not valid for non-scraper endpoints — fall through to JWT check

    # JWT auth
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]  # Strip "Bearer "
    payload = decode_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload
