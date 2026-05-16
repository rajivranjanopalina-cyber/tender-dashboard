import os
import requests

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def fetch_html(
    url: str,
    renderer: str = "default",
    timeout: int = 30,
    wait_for: str = "body",
    wait_until: str = "load",
    click_selector: str = "",
    click_wait_for: str = "",
) -> str:
    """
    Fetch rendered HTML from a URL.

    renderer="default"  — standard requests (server-rendered HTML)
    renderer="insecure" — requests with SSL verification disabled (e.g. Railtel)
    renderer="external" — POST to EXTERNAL_RENDERER_URL/render (Playwright service)

    wait_until, click_selector, click_wait_for only apply to the external renderer.
    """
    if renderer == "external":
        return _fetch_with_external_renderer(
            url, timeout, wait_for, wait_until, click_selector, click_wait_for
        )
    if renderer == "insecure":
        return _fetch_with_requests(url, timeout, verify=False)
    return _fetch_with_requests(url, timeout)


def _fetch_with_requests(url: str, timeout: int, verify: bool = True) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        verify=verify,
        headers={
            "User-Agent": _DEFAULT_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    response.raise_for_status()
    return response.text


def _fetch_with_external_renderer(
    url: str,
    timeout: int,
    wait_for: str,
    wait_until: str = "load",
    click_selector: str = "",
    click_wait_for: str = "",
) -> str:
    renderer_url = os.environ.get("EXTERNAL_RENDERER_URL", "")
    if not renderer_url:
        raise RuntimeError("EXTERNAL_RENDERER_URL not configured")
    payload: dict = {
        "url": url,
        "wait_for": wait_for,
        "timeout": timeout * 1000,
        "wait_until": wait_until,
    }
    if click_selector:
        payload["click_selector"] = click_selector
    if click_wait_for:
        payload["click_wait_for"] = click_wait_for
    response = requests.post(
        f"{renderer_url}/render",
        json=payload,
        timeout=timeout + 30,
    )
    response.raise_for_status()
    return response.json()["html"]
