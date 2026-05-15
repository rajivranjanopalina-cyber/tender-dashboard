import pytest
from unittest.mock import patch, MagicMock
from backend.scraper.fetcher import fetch_html


def test_insecure_renderer_disables_ssl_verify():
    """fetch_html with renderer='insecure' must call requests.get with verify=False."""
    with patch("backend.scraper.fetcher.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.text = "<html/>"
        mock_resp.raise_for_status = lambda: None
        mock_get.return_value = mock_resp
        fetch_html("https://railtel.in/tenders.html", renderer="insecure")
        _, kwargs = mock_get.call_args
        assert kwargs.get("verify") is False


def test_external_renderer_calls_render_endpoint():
    """fetch_html with renderer='external' must POST to EXTERNAL_RENDERER_URL/render with wait_for."""
    with patch("backend.scraper.fetcher.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        mock_resp.json.return_value = {"html": "<html>rendered</html>"}
        mock_post.return_value = mock_resp
        with patch.dict("os.environ", {"EXTERNAL_RENDERER_URL": "http://renderer:8000"}):
            result = fetch_html("https://example.com", renderer="external", wait_for="table")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://renderer:8000/render"
        assert kwargs["json"]["wait_for"] == "table"
        assert result == "<html>rendered</html>"


def test_default_renderer_uses_ssl_verify():
    """fetch_html with renderer='default' must use verify=True (default)."""
    with patch("backend.scraper.fetcher.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.text = "<html/>"
        mock_resp.raise_for_status = lambda: None
        mock_get.return_value = mock_resp
        fetch_html("https://example.com", renderer="default")
        _, kwargs = mock_get.call_args
        assert kwargs.get("verify", True) is True
