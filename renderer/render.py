from playwright.async_api import async_playwright


async def render_url(url: str, wait_for: str = "body", timeout: int = 30000) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,
        )
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=timeout)
        if wait_for and wait_for != "body":
            await page.wait_for_selector(wait_for, timeout=timeout)
        html = await page.content()
        await browser.close()
        return html
