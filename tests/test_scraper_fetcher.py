from unittest.mock import patch, MagicMock
from backend.scraper.fetcher import fetch_html


def test_fetch_static_html():
    mock_response = MagicMock()
    mock_response.text = "<html><body>Tender List</body></html>"
    mock_response.raise_for_status = MagicMock()
    with patch("backend.scraper.fetcher.requests.get", return_value=mock_response):
        html = fetch_html("https://example.com")
    assert "Tender List" in html


def test_fetch_raises_on_http_error():
    import requests as req
    with patch("backend.scraper.fetcher.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.side_effect = req.HTTPError("404")
        try:
            fetch_html("https://example.com")
            assert False, "Should have raised"
        except Exception as e:
            assert "404" in str(e)


def test_fetch_default_renderer():
    mock_response = MagicMock()
    mock_response.text = "<html><body>Default</body></html>"
    mock_response.raise_for_status = MagicMock()
    with patch("backend.scraper.fetcher.requests.get", return_value=mock_response) as mock_get:
        html = fetch_html("https://example.com", renderer="default")
    assert "Default" in html
    mock_get.assert_called_once()


def test_fetch_external_renderer_raises_when_not_configured():
    import pytest
    with pytest.raises(RuntimeError, match="EXTERNAL_RENDERER_URL not configured"):
        fetch_html("https://example.com", renderer="external")


def test_fetch_passes_timeout():
    mock_response = MagicMock()
    mock_response.text = "<html></html>"
    mock_response.raise_for_status = MagicMock()
    with patch("backend.scraper.fetcher.requests.get", return_value=mock_response) as mock_get:
        fetch_html("https://example.com", timeout=5)
    _, kwargs = mock_get.call_args
    assert kwargs["timeout"] == 5
