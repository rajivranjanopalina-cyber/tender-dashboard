import requests
from playwright.sync_api import sync_playwright


def fetch_html(url: str, render_js: bool = False, timeout: int = 30) -> str:
    """Fetch HTML from a URL. Uses Playwright for JS-heavy pages, requests otherwise."""
    if render_js:
        return _fetch_with_playwright(url, timeout)
    return _fetch_with_requests(url, timeout)


def _fetch_with_requests(url: str, timeout: int) -> str:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "TenderBot/1.0"})
    response.raise_for_status()
    return response.text


def _fetch_with_playwright(url: str, timeout: int) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
            return page.content()
        finally:
            browser.close()
