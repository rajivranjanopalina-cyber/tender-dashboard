import os
import requests


def fetch_html(url: str, renderer: str = "default", timeout: int = 8) -> str:
    """
    Fetch HTML from a URL.
    renderer="default": uses requests (suitable for server-rendered HTML).
    renderer="external": calls EXTERNAL_RENDERER_URL (future, not yet implemented).
    """
    if renderer == "external":
        return _fetch_with_external_renderer(url, timeout)
    return _fetch_with_requests(url, timeout)


def _fetch_with_requests(url: str, timeout: int) -> str:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "TenderBot/1.0"})
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
