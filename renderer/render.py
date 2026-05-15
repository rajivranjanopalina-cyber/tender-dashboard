from playwright.async_api import async_playwright, Browser

_browser: Browser | None = None


async def get_browser() -> Browser:
    global _browser
    if _browser is None or not _browser.is_connected():
        if _browser is not None:
            try:
                await _browser.close()
            except Exception:
                pass
        p = await async_playwright().start()
        _browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
    return _browser


async def render_url(
    url: str,
    wait_for: str = "body",
    timeout: int = 30000,
    wait_until: str = "load",
) -> str:
    browser = await get_browser()
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        ignore_https_errors=True,
    )
    try:
        page = await context.new_page()
        await page.goto(url, wait_until=wait_until, timeout=timeout)
        if wait_for and wait_for != "body":
            await page.wait_for_selector(wait_for, timeout=timeout)
        return await page.content()
    finally:
        await context.close()
