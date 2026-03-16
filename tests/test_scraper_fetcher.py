from unittest.mock import patch, MagicMock
from backend.scraper.fetcher import fetch_html

def test_fetch_static_html():
    mock_response = MagicMock()
    mock_response.text = "<html><body>Tender List</body></html>"
    mock_response.raise_for_status = MagicMock()
    with patch("backend.scraper.fetcher.requests.get", return_value=mock_response):
        html = fetch_html("https://example.com", render_js=False)
    assert "Tender List" in html

def test_fetch_raises_on_http_error():
    import requests as req
    with patch("backend.scraper.fetcher.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.side_effect = req.HTTPError("404")
        try:
            fetch_html("https://example.com", render_js=False)
            assert False, "Should have raised"
        except Exception as e:
            assert "404" in str(e)

def test_fetch_js_rendered(tmp_path):
    with patch("backend.scraper.fetcher.sync_playwright") as mock_pw:
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.content.return_value = "<html><body>JS Content</body></html>"
        mock_browser.chromium.launch.return_value.__enter__ = MagicMock(return_value=mock_browser.chromium.launch.return_value)
        mock_browser.chromium.launch.return_value.__exit__ = MagicMock(return_value=False)
        mock_pw.return_value.__enter__ = MagicMock(return_value=mock_browser)
        mock_pw.return_value.__exit__ = MagicMock(return_value=False)
        mock_browser.chromium.launch.return_value.new_page.return_value = mock_page
        html = fetch_html("https://example.com", render_js=True)
    assert isinstance(html, str)
