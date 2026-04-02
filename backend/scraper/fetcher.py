import os
import requests

# Realistic browser User-Agent so government sites don't block requests
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def fetch_html(url: str, renderer: str = "default", timeout: int = 30) -> str:
    """
    Fetch HTML from a URL.
    renderer="default": uses requests (suitable for server-rendered HTML).
    renderer="external": calls EXTERNAL_RENDERER_URL (future, not yet implemented).
    """
    if renderer == "external":
        return _fetch_with_external_renderer(url, timeout)
    return _fetch_with_requests(url, timeout)


def _fetch_with_requests(url: str, timeout: int) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": _DEFAULT_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    response.raise_for_status()
    return response.text


def _fetch_with_external_renderer(url: str, timeout: int) -> str:
    """Stub for external JS rendering service. Not implemented yet."""
    renderer_url = os.environ.get("EXTERNAL_RENDERER_URL", "")
    if not renderer_url:
        raise RuntimeError("EXTERNAL_RENDERER_URL not configured")
    response = requests.post(
        renderer_url,
        json={"url": url},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json().get("html", "")
