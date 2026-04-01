#!/usr/bin/env python3
"""
One-time migration script: uploads local template/proposal files to Vercel Blob
and updates database records with the new blob_url.

Requirements:
- Local access to the SQLite database file
- BLOB_READ_WRITE_TOKEN env var set
- Run from the project root directory

Usage: python scripts/migrate_blobs.py /path/to/tender.db
"""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.blob_storage import upload_blob


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Detect column name (file_path or blob_url depending on whether schema migration ran)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(templates)").fetchall()]
    url_col = "blob_url" if "blob_url" in cols else "file_path"

    # Migrate templates
    templates = conn.execute(f"SELECT id, {url_col}, original_filename FROM templates WHERE {url_col} NOT LIKE 'http%'").fetchall()
    for t in templates:
        if not os.path.exists(t[url_col]):
            print(f"  SKIP template {t['id']}: file not found at {t[url_col]}")
            continue
        with open(t[url_col], "rb") as f:
            content = f.read()
        blob_url = upload_blob(content, f"templates/{t['original_filename']}")
        conn.execute(f"UPDATE templates SET {url_col} = ? WHERE id = ?", (blob_url, t["id"]))
        print(f"  OK template {t['id']} -> {blob_url}")

    # Detect column name for proposals
    pcols = [row[1] for row in conn.execute("PRAGMA table_info(proposals)").fetchall()]
    purl_col = "blob_url" if "blob_url" in pcols else "file_path"

    # Migrate proposals
    proposals = conn.execute(f"SELECT id, {purl_col} FROM proposals WHERE {purl_col} NOT LIKE 'http%'").fetchall()
    for p in proposals:
        if not os.path.exists(p[purl_col]):
            print(f"  SKIP proposal {p['id']}: file not found at {p[purl_col]}")
            continue
        with open(p[purl_col], "rb") as f:
            content = f.read()
        blob_url = upload_blob(content, f"proposals/proposal_{p['id']}.docx")
        conn.execute(f"UPDATE proposals SET {purl_col} = ? WHERE id = ?", (blob_url, p["id"]))
        print(f"  OK proposal {p['id']} -> {blob_url}")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/migrate_blobs.py /path/to/tender.db")
        sys.exit(1)
    migrate(sys.argv[1])
