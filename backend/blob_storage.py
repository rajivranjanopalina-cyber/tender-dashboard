import os
import requests


BLOB_API_URL = "https://blob.vercel-storage.com"


def upload_blob(content: bytes, filename: str) -> str:
    """Upload file to Vercel Blob Storage. Returns the public URL."""
    token = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
    resp = requests.put(
        f"{BLOB_API_URL}/{filename}",
        data=content,
        headers={
            "Authorization": f"Bearer {token}",
            "x-content-type": "application/octet-stream",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["url"]


def download_blob(url: str) -> bytes:
    """Download file from Vercel Blob Storage. Returns file bytes."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def delete_blob(url: str) -> None:
    """Delete a file from Vercel Blob Storage."""
    token = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
    requests.post(
        f"{BLOB_API_URL}/delete",
        json={"urls": [url]},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
