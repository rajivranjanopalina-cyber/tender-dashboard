import os
import pytest
from unittest.mock import patch, MagicMock


def test_upload_blob_returns_url():
    os.environ["BLOB_READ_WRITE_TOKEN"] = "test-token"

    from backend.blob_storage import upload_blob

    mock_response = MagicMock()
    mock_response.json.return_value = {"url": "https://blob.vercel-storage.com/test-file.docx"}
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None

    with patch("backend.blob_storage.requests.put", return_value=mock_response):
        url = upload_blob(b"file content", "test-file.docx")
        assert url == "https://blob.vercel-storage.com/test-file.docx"


def test_download_blob_returns_bytes():
    from backend.blob_storage import download_blob

    mock_response = MagicMock()
    mock_response.content = b"file content"
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None

    with patch("backend.blob_storage.requests.get", return_value=mock_response):
        content = download_blob("https://blob.vercel-storage.com/test.docx")
        assert content == b"file content"


def test_upload_blob_uses_auth_header():
    os.environ["BLOB_READ_WRITE_TOKEN"] = "my-token"

    from backend.blob_storage import upload_blob

    mock_response = MagicMock()
    mock_response.json.return_value = {"url": "https://blob.vercel-storage.com/f.docx"}
    mock_response.raise_for_status.return_value = None

    with patch("backend.blob_storage.requests.put", return_value=mock_response) as mock_put:
        upload_blob(b"data", "f.docx")
        call_kwargs = mock_put.call_args.kwargs
        assert "Authorization" in call_kwargs["headers"]
        assert "my-token" in call_kwargs["headers"]["Authorization"]
