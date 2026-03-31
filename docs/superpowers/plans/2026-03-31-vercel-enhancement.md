# Tender Dashboard Vercel Enhancement — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rearchitect the existing tender-dashboard from Docker/SQLite to Vercel serverless with Turso DB, Vercel Blob, JWT auth, and enhanced UI.

**Architecture:** Python serverless functions on Vercel (via FastAPI + Mangum adapter), Turso cloud SQLite database, Vercel Blob Storage for documents, React SPA served as static files. GitHub Actions cron for nightly scraping.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy + sqlalchemy-libsql, Turso, Vercel Blob SDK, bcrypt, PyJWT, React 19, Vite 8, Axios

**Spec:** `docs/superpowers/specs/2026-03-31-tender-dashboard-vercel-enhancement-design.md`

---

## File Structure

### Files to Create

| File | Responsibility |
|---|---|
| `api/index.py` | Single Vercel serverless entry point — mounts full FastAPI app via Mangum (deviation from spec: spec lists separate api/*.py files, but a single entry point is simpler and avoids code duplication since FastAPI handles routing internally) |
| `backend/auth.py` | JWT creation, verification, and password checking |
| `backend/dependencies.py` | FastAPI dependency for JWT auth (reusable across routers) |
| `backend/routers/auth.py` | POST /api/auth login endpoint |
| `backend/routers/health.py` | GET /api/health endpoint |
| `backend/blob_storage.py` | Vercel Blob upload/download/delete helpers |
| `vercel.json` | Vercel build and routing configuration |
| `.github/workflows/nightly-scrape.yml` | GitHub Actions cron for nightly scrape |
| `scripts/migrate_blobs.py` | One-time migration script for local files to Vercel Blob |
| `frontend/src/pages/Login.jsx` | Login page component |
| `frontend/src/components/Toast.jsx` | Toast notification component |
| `frontend/src/components/ScrapeConfigEditor.jsx` | Dual-mode scrape config editor (form + JSON) |
| `frontend/src/components/ConfirmDialog.jsx` | Reusable confirmation dialog |
| `tests/test_auth.py` | Auth endpoint and JWT tests |
| `tests/test_blob_storage.py` | Blob storage helper tests |
| `tests/test_health.py` | Health endpoint tests |

### Files to Modify

| File | Changes |
|---|---|
| `backend/database.py` | Replace SQLite engine with Turso/libsql connection |
| `backend/config.py` | Add new env vars (TURSO_*, JWT_SECRET, etc.), remove DATA_DIR |
| `backend/models.py` | Template.file_path → blob_url, Proposal.file_path → blob_url |
| `backend/schemas.py` | Add auth schemas, update TemplateOut/ProposalOut for blob_url |
| `backend/main.py` | Remove scheduler/static file serving, add auth middleware, add new routers |
| `backend/scraper/engine.py` | Add 8s timeout, 3-page pagination limit, remove Playwright dep |
| `backend/scraper/fetcher.py` | Remove Playwright, add external renderer interface stub |
| `backend/document/generator.py` | Read templates from Blob URL, upload proposals to Blob, remove PDF |
| `backend/document/docx_handler.py` | Add company_* placeholders |
| `backend/routers/templates.py` | Upload to Vercel Blob instead of local filesystem |
| `backend/routers/proposals.py` | Download from Blob, update file_path refs to blob_url |
| `backend/routers/scraper.py` | Replace scheduler calls with direct scrape + fan-out logic |
| `requirements.txt` | Swap deps: remove apscheduler/playwright/pypdf, add mangum/pyjwt/bcrypt/vercel-blob/sqlalchemy-libsql |
| `frontend/src/App.jsx` | Add login gate, toast system, responsive improvements |
| `frontend/src/api/client.js` | Add JWT interceptor + 401 redirect |
| `frontend/src/pages/Dashboard.jsx` | Enhanced filtering, stats cards, auto-refresh |
| `frontend/src/pages/Scraper.jsx` | Portal cards, dual-mode config editor, test scrape |
| `frontend/src/pages/Keywords.jsx` | Bulk add, search/filter |
| `frontend/src/pages/Templates.jsx` | Drag-and-drop, placeholder reference |
| `frontend/src/pages/Proposals.jsx` | Pipeline view, regenerate option |

### Files to Remove/Archive

| File | Action |
|---|---|
| `backend/scheduler.py` | Delete (replaced by cron + API) |
| `backend/document/pdf_handler.py` | Delete (DOCX only) |
| `Dockerfile` | Move to `docker/Dockerfile` |
| `docker-compose.yml` | Move to `docker/docker-compose.yml` |

---

## Chunk 1: Database & Config Migration

### Task 1: Update Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update requirements.txt**

Replace the full contents of `requirements.txt`:

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.36
sqlalchemy-libsql==0.1.0
pydantic==2.9.2
pydantic-settings==2.6.0
beautifulsoup4==4.12.3
requests==2.32.3
python-docx==1.1.2
cryptography==43.0.3
python-multipart==0.0.12
aiofiles==24.1.0
mangum==0.19.0
pyjwt==2.10.1
bcrypt==4.2.1
vercel-blob==0.1.0
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
```

Removed: `apscheduler`, `playwright`, `pypdf`
Added: `sqlalchemy-libsql`, `mangum`, `pyjwt`, `bcrypt`, `vercel-blob`

- [ ] **Step 2: Install new deps**

Run: `cd /Users/rajiv/Desktop/Product-hub/Projects/tender-dashboard && source .venv/bin/activate && pip install -r requirements.txt`
Expected: All packages install successfully

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: update dependencies for Vercel migration

Remove apscheduler, playwright, pypdf.
Add sqlalchemy-libsql, mangum, pyjwt, bcrypt, vercel-blob."
```

---

### Task 2: Update Config for Turso + New Env Vars

**Files:**
- Modify: `backend/config.py`
- Create: `.env.example`

- [ ] **Step 1: Write failing test**

Create `tests/test_config.py`:

```python
import os
import pytest


def test_settings_loads_turso_vars(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://test.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("JWT_SECRET", "jwt-test-secret")
    monkeypatch.setenv("DASHBOARD_PASSWORD_HASH", "$2b$12$fakehash")
    monkeypatch.setenv("SCRAPE_SECRET", "scrape-test-secret")

    # Re-import to pick up new env vars
    import importlib
    import backend.config
    importlib.reload(backend.config)
    s = backend.config.Settings()

    assert s.turso_database_url == "libsql://test.turso.io"
    assert s.turso_auth_token == "test-token"
    assert s.jwt_secret == "jwt-test-secret"
    assert s.dashboard_password_hash == "$2b$12$fakehash"
    assert s.scrape_secret == "scrape-test-secret"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/rajiv/Desktop/Product-hub/Projects/tender-dashboard && source .venv/bin/activate && pytest tests/test_config.py -v`
Expected: FAIL — Settings has no `turso_database_url` field

- [ ] **Step 3: Update backend/config.py**

Replace full contents of `backend/config.py`:

```python
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Turso database
    turso_database_url: str = ""
    turso_auth_token: str = ""

    # Portal credential encryption
    secret_key: str = ""

    # Dashboard auth
    dashboard_password_hash: str = ""
    jwt_secret: str = ""

    # Scraper cron auth
    scrape_secret: str = ""

    # Vercel Blob
    blob_read_write_token: str = ""

    # Company info for proposals
    company_name: str = ""
    company_address: str = ""
    company_contact: str = ""

    # External renderer (future)
    external_renderer_url: str = ""

    # Timezone
    tz: str = "Asia/Kolkata"

    model_config = {"env_file": ".env", "case_sensitive": False}


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

**Note:** All fields default to empty strings instead of being required. This is intentional — the app runs in multiple environments (local dev, Vercel, tests) with different env vars available. Individual features degrade gracefully when their config is missing (e.g., Blob uploads fail with clear error if token is empty). The previous `sys.exit(1)` on missing `SECRET_KEY` is removed since portal credential encryption is only needed when portals have auth enabled.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Update .env.example**

```
SECRET_KEY=change-me-to-a-random-32-char-string
TURSO_DATABASE_URL=libsql://your-db.turso.io
TURSO_AUTH_TOKEN=your-turso-auth-token
JWT_SECRET=change-me-to-a-random-secret
DASHBOARD_PASSWORD_HASH=$2b$12$generate-with-bcrypt
SCRAPE_SECRET=change-me-to-a-random-secret
BLOB_READ_WRITE_TOKEN=vercel-blob-token
COMPANY_NAME=Your Company Name
COMPANY_ADDRESS=Your Company Address
COMPANY_CONTACT=contact@company.com
TZ=Asia/Kolkata
```

- [ ] **Step 6: Commit**

```bash
git add backend/config.py .env.example tests/test_config.py
git commit -m "feat: update config for Turso, JWT, and Vercel env vars"
```

---

### Task 3: Migrate Database Connection to Turso

**Files:**
- Modify: `backend/database.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_database_turso.py`:

```python
import os
import pytest


def test_database_url_uses_turso_when_configured(monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://test.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("SECRET_KEY", "test")

    import importlib
    import backend.config
    importlib.reload(backend.config)

    import backend.database
    importlib.reload(backend.database)

    url = str(backend.database.engine.url)
    assert "libsql" in url or "turso" in url


def test_database_falls_back_to_sqlite_when_no_turso(monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("SECRET_KEY", "test")

    import importlib
    import backend.config
    importlib.reload(backend.config)

    import backend.database
    importlib.reload(backend.database)

    url = str(backend.database.engine.url)
    assert "sqlite" in url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_database_turso.py -v`
Expected: FAIL — database.py doesn't use Turso URL

- [ ] **Step 3: Update backend/database.py**

Replace full contents of `backend/database.py`:

```python
import os
import sys
import tempfile
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _get_database_url() -> str:
    """Use Turso if configured, otherwise fall back to local SQLite."""
    turso_url = os.environ.get("TURSO_DATABASE_URL", "")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN", "")

    if turso_url and turso_token:
        # sqlalchemy-libsql format
        return f"{turso_url}?authToken={turso_token}&secure=true"

    # Fallback to SQLite for local dev/testing
    data_dir = os.environ.get("DATA_DIR", tempfile.mkdtemp(prefix="tender_"))
    os.makedirs(data_dir, exist_ok=True)
    return f"sqlite:///{data_dir}/tender.db"


def _create_engine():
    url = _get_database_url()
    if url.startswith("sqlite"):
        eng = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(eng, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return eng
    else:
        return create_engine(url)


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_database_turso.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/database.py tests/test_database_turso.py
git commit -m "feat: migrate database connection to support Turso with SQLite fallback"
```

---

### Task 4: Update Models for Blob Storage

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/schemas.py`

- [ ] **Step 1: Update Template model — file_path → blob_url**

In `backend/models.py`, change the Template class:

```python
# Change this line:
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
# To:
    blob_url: Mapped[str] = mapped_column(Text, nullable=False)
```

- [ ] **Step 2: Update Proposal model — file_path → blob_url**

In `backend/models.py`, change the Proposal class:

```python
# Change this line:
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
# To:
    blob_url: Mapped[str] = mapped_column(Text, nullable=False)
```

- [ ] **Step 3: Update schemas.py — TemplateOut**

In `backend/schemas.py`, update `TemplateOut`:

```python
class TemplateOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    original_filename: str
    file_type: str
    sha256: str
    is_default: bool
    blob_url: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Update schemas.py — ProposalOut**

In `backend/schemas.py`, update `ProposalOut`:

```python
class ProposalOut(BaseModel):
    id: int
    tender_id: int
    tender_title: str
    template_id: Optional[int]
    template_name: Optional[str]
    blob_url: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Run existing tests to check for breakage**

Run: `pytest tests/ -v --tb=short 2>&1 | head -80`
Expected: Some failures related to `file_path` references — these will be fixed in later tasks

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/schemas.py
git commit -m "feat: rename file_path to blob_url in Template and Proposal models"
```

---

## Chunk 2: Authentication System

### Task 5: Create Auth Module

**Files:**
- Create: `backend/auth.py`
- Test: `tests/test_auth_module.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_auth_module.py`:

```python
import os
import pytest
import bcrypt


def test_verify_password_correct():
    os.environ["JWT_SECRET"] = "test-secret"
    os.environ["DASHBOARD_PASSWORD_HASH"] = bcrypt.hashpw(b"mypassword", bcrypt.gensalt()).decode()

    from backend.auth import verify_password
    assert verify_password("mypassword") is True


def test_verify_password_wrong():
    os.environ["JWT_SECRET"] = "test-secret"
    os.environ["DASHBOARD_PASSWORD_HASH"] = bcrypt.hashpw(b"mypassword", bcrypt.gensalt()).decode()

    from backend.auth import verify_password
    assert verify_password("wrongpassword") is False


def test_create_and_decode_jwt():
    os.environ["JWT_SECRET"] = "test-jwt-secret"

    from backend.auth import create_jwt, decode_jwt
    token = create_jwt(remember_me=False)
    payload = decode_jwt(token)
    assert payload is not None
    assert "exp" in payload


def test_expired_jwt_returns_none():
    os.environ["JWT_SECRET"] = "test-jwt-secret"

    from backend.auth import create_jwt, decode_jwt
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    # Create a token that expired 1 hour ago
    payload = {"exp": datetime.now(timezone.utc) - timedelta(hours=1)}
    token = pyjwt.encode(payload, "test-jwt-secret", algorithm="HS256")
    assert decode_jwt(token) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth_module.py -v`
Expected: FAIL — `backend.auth` module doesn't exist

- [ ] **Step 3: Create backend/auth.py**

```python
import os
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt


def verify_password(plaintext: str) -> bool:
    """Check plaintext password against DASHBOARD_PASSWORD_HASH env var."""
    stored_hash = os.environ.get("DASHBOARD_PASSWORD_HASH", "")
    if not stored_hash:
        return False
    return bcrypt.checkpw(plaintext.encode(), stored_hash.encode())


def create_jwt(remember_me: bool = False) -> str:
    """Create a signed JWT token. 7 days if remember_me, else 24 hours."""
    secret = os.environ.get("JWT_SECRET", "")
    expiry = timedelta(days=7) if remember_me else timedelta(hours=24)
    payload = {
        "exp": datetime.now(timezone.utc) + expiry,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_jwt(token: str) -> dict | None:
    """Decode and verify a JWT token. Returns payload or None if invalid/expired."""
    secret = os.environ.get("JWT_SECRET", "")
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth_module.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/auth.py tests/test_auth_module.py
git commit -m "feat: add auth module with bcrypt password verification and JWT"
```

---

### Task 6: Create Auth Dependency and Router

**Files:**
- Create: `backend/dependencies.py`
- Create: `backend/routers/auth.py`
- Test: `tests/test_auth_router.py`

- [ ] **Step 1: Create backend/dependencies.py**

```python
import os
from fastapi import Depends, HTTPException, Request
from backend.auth import decode_jwt


def require_auth(request: Request) -> dict:
    """
    FastAPI dependency that validates JWT from Authorization header.
    Also accepts X-Scrape-Token header for cron-triggered scrape requests.
    """
    # Allow scrape token auth (for GitHub Actions cron)
    scrape_token = request.headers.get("X-Scrape-Token", "")
    expected_scrape = os.environ.get("SCRAPE_SECRET", "")
    if scrape_token and expected_scrape and scrape_token == expected_scrape:
        return {"auth": "scrape_token"}

    # JWT auth
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]  # Strip "Bearer "
    payload = decode_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload
```

- [ ] **Step 2: Create backend/routers/auth.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.auth import verify_password, create_jwt

router = APIRouter()


class LoginRequest(BaseModel):
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    token: str


@router.post("/auth", response_model=LoginResponse)
def login(data: LoginRequest):
    if not verify_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_jwt(remember_me=data.remember_me)
    return LoginResponse(token=token)
```

- [ ] **Step 3: Write test**

Create `tests/test_auth_router.py`:

```python
import os
import bcrypt
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_env():
    os.environ["SECRET_KEY"] = "test-secret"
    os.environ["JWT_SECRET"] = "test-jwt-secret"
    os.environ["DASHBOARD_PASSWORD_HASH"] = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode()
    yield


@pytest.fixture
def client():
    from backend.main import app
    return TestClient(app)


def test_login_success(client):
    resp = client.post("/api/auth", json={"password": "testpass"})
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong_password(client):
    resp = client.post("/api/auth", json={"password": "wrong"})
    assert resp.status_code == 401


def test_protected_endpoint_without_token(client):
    resp = client.get("/api/keywords")
    assert resp.status_code == 401


def test_protected_endpoint_with_valid_token(client):
    login_resp = client.post("/api/auth", json={"password": "testpass"})
    token = login_resp.json()["token"]
    resp = client.get("/api/keywords", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_auth_router.py -v`
Expected: FAIL — auth router not mounted yet

- [ ] **Step 5: Update backend/main.py to mount auth router and add auth dependency**

Replace full contents of `backend/main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from backend.database import init_db
from backend.dependencies import require_auth
from backend.routers import portals, keywords, tenders, templates, proposals, scraper, auth, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Tender Dashboard", lifespan=lifespan)

# Public routes (no auth)
app.include_router(auth.router, prefix="/api", tags=["auth"])

# Protected routes (require JWT)
protected = [
    (portals.router, "/api/portals", ["portals"]),
    (keywords.router, "/api/keywords", ["keywords"]),
    (tenders.router, "/api/tenders", ["tenders"]),
    (templates.router, "/api/templates", ["templates"]),
    (proposals.router, "/api/proposals", ["proposals"]),
    (scraper.router, "/api/scraper", ["scraper"]),
]

for router, prefix, tags in protected:
    app.include_router(router, prefix=prefix, tags=tags, dependencies=[Depends(require_auth)])
```

**IMPORTANT:** Steps 5 and 6 must be executed together — Step 5 imports `health` which is created in Step 6. Create the health router file FIRST, then replace main.py.

- [ ] **Step 6: Create backend/routers/health.py (do this BEFORE Step 5)**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 7: Add health router to main.py**

Add to the public routes section (after auth router):

```python
app.include_router(health.router, prefix="/api", tags=["health"])
```

- [ ] **Step 8: Run tests**

Run: `pytest tests/test_auth_router.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/dependencies.py backend/routers/auth.py backend/routers/health.py backend/main.py tests/test_auth_router.py
git commit -m "feat: add JWT auth system with login endpoint and route protection"
```

---

## Chunk 3: Vercel Blob Storage & Document Generation

### Task 7: Create Blob Storage Helper

**Files:**
- Create: `backend/blob_storage.py`
- Test: `tests/test_blob_storage.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_blob_storage.py`:

```python
import os
import pytest
from unittest.mock import patch, MagicMock


def test_upload_blob_returns_url():
    os.environ["BLOB_READ_WRITE_TOKEN"] = "test-token"

    from backend.blob_storage import upload_blob

    mock_response = MagicMock()
    mock_response.json.return_value = {"url": "https://blob.vercel-storage.com/test-file.docx"}
    mock_response.status_code = 200

    with patch("backend.blob_storage.requests.put", return_value=mock_response):
        url = upload_blob(b"file content", "test-file.docx")
        assert url == "https://blob.vercel-storage.com/test-file.docx"


def test_download_blob_returns_bytes():
    from backend.blob_storage import download_blob

    mock_response = MagicMock()
    mock_response.content = b"file content"
    mock_response.status_code = 200

    with patch("backend.blob_storage.requests.get", return_value=mock_response):
        content = download_blob("https://blob.vercel-storage.com/test.docx")
        assert content == b"file content"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_blob_storage.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Create backend/blob_storage.py**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_blob_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/blob_storage.py tests/test_blob_storage.py
git commit -m "feat: add Vercel Blob Storage upload/download/delete helpers"
```

---

### Task 8: Update Template Router for Blob Storage

**Files:**
- Modify: `backend/routers/templates.py`

- [ ] **Step 1: Update the template upload endpoint**

In `backend/routers/templates.py`, replace local file writes with Blob uploads. The key changes:

1. Replace `open(file_path, "wb")` with `upload_blob(content, filename)`
2. Store `blob_url` instead of `file_path` in the Template record
3. Replace local file reads (download) with `download_blob(template.blob_url)`

Update the upload endpoint to use:
```python
from backend.blob_storage import upload_blob, download_blob, delete_blob
```

Instead of writing to disk:
```python
blob_url = upload_blob(content, f"templates/{sha_hash}_{file.filename}")
```

Store in model:
```python
template = models.Template(
    name=name,
    description=description,
    original_filename=file.filename,
    blob_url=blob_url,
    file_type="docx",
    sha256=sha_hash,
)
```

Update the download endpoint to fetch from Blob:
```python
@router.get("/{template_id}/download")
def download_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(models.Template).get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    content = download_blob(template.blob_url)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{template.original_filename}"'},
    )
```

Update delete endpoint to remove from Blob:
```python
delete_blob(template.blob_url)
```

- [ ] **Step 2: Run existing template tests**

Run: `pytest tests/ -k template -v`
Expected: Tests may need updating to mock blob_storage calls

- [ ] **Step 3: Commit**

```bash
git add backend/routers/templates.py
git commit -m "feat: update template router to use Vercel Blob Storage"
```

---

### Task 9: Update Document Generator for Blob + Company Placeholders

**Files:**
- Modify: `backend/document/generator.py`
- Modify: `backend/document/docx_handler.py`

- [ ] **Step 1: Update generator.py**

Replace full contents of `backend/document/generator.py`:

```python
import os
from datetime import date
from backend import models
from backend.blob_storage import download_blob, upload_blob


PLACEHOLDER_MAP = {
    "tender_title": lambda t, p: t.title or "",
    "tender_description": lambda t, p: t.description or "",
    "tender_deadline": lambda t, p: t.deadline or "",
    "tender_published_date": lambda t, p: t.published_date or "",
    "tender_estimated_value": lambda t, p: t.estimated_value or "",
    "tender_source_url": lambda t, p: t.source_url or "",
    "tender_portal_name": lambda t, p: p.name if p else "",
    "tender_portal_url": lambda t, p: p.url if p else "",
    "generation_date": lambda t, p: str(date.today()),
    "company_name": lambda t, p: os.environ.get("COMPANY_NAME", ""),
    "company_address": lambda t, p: os.environ.get("COMPANY_ADDRESS", ""),
    "company_contact": lambda t, p: os.environ.get("COMPANY_CONTACT", ""),
}


def _build_placeholders(tender: models.Tender) -> dict[str, str]:
    portal = tender.portal
    return {key: fn(tender, portal) for key, fn in PLACEHOLDER_MAP.items()}


def generate_proposal(tender: models.Tender, template: models.Template) -> str:
    """
    Generate a proposal DOCX from a tender and template.
    Downloads template from Blob, fills placeholders, uploads result to Blob.
    Returns the blob_url of the generated proposal.
    """
    placeholders = _build_placeholders(tender)

    # Download template from Vercel Blob
    template_bytes = download_blob(template.blob_url)

    # Generate DOCX
    from backend.document.docx_handler import fill_docx_template
    output_bytes = fill_docx_template(template_bytes, placeholders)

    # Upload generated proposal to Blob
    filename = f"proposals/proposal_{tender.id}_{template.id}.docx"
    blob_url = upload_blob(output_bytes, filename)

    return blob_url
```

- [ ] **Step 2: Update docx_handler.py to return bytes instead of writing to file**

Change `fill_docx_template` signature to return bytes:

```python
import io
from docx import Document as DocxDocument

_WPS_TXBX = "{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}txbx"
_W_P = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"


def fill_docx_template(template_bytes: bytes, placeholders: dict[str, str]) -> bytes:
    """
    Replace {{placeholder}} occurrences in a DOCX template.
    Returns the filled DOCX as bytes.
    """
    doc = DocxDocument(io.BytesIO(template_bytes))

    for para in doc.paragraphs:
        _replace_in_paragraph(para, placeholders)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _replace_in_paragraph(para, placeholders)

    for section in doc.sections:
        for para in section.header.paragraphs:
            _replace_in_paragraph(para, placeholders)
        for para in section.footer.paragraphs:
            _replace_in_paragraph(para, placeholders)

    from docx.text.paragraph import Paragraph
    for shape in doc.element.body.iter(_WPS_TXBX):
        for para_elem in shape.iter(_W_P):
            para = Paragraph(para_elem, doc)
            _replace_in_paragraph(para, placeholders)

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def _replace_in_paragraph(paragraph, placeholders: dict[str, str]) -> None:
    full_text = paragraph.text
    if "{{" not in full_text:
        return

    new_text = full_text
    for key, value in placeholders.items():
        new_text = new_text.replace(f"{{{{{key}}}}}", value or "")

    if paragraph.runs:
        paragraph.runs[0].text = new_text
        for run in paragraph.runs[1:]:
            run.text = ""
```

- [ ] **Step 3: Delete backend/document/pdf_handler.py**

Run: `rm backend/document/pdf_handler.py`

- [ ] **Step 4: Run tests**

Run: `pytest tests/ -k "proposal or template or document or docx" -v`

- [ ] **Step 5: Commit**

```bash
git add backend/document/generator.py backend/document/docx_handler.py
git rm backend/document/pdf_handler.py
git commit -m "feat: update document generation for Blob storage, add company placeholders, remove PDF"
```

---

### Task 10: Update Proposal Router for Blob Storage

**Files:**
- Modify: `backend/routers/proposals.py`

- [ ] **Step 1: Update proposal creation to use new generator**

The proposal router needs to:
1. Call `generate_proposal()` which now returns a `blob_url`
2. Store `blob_url` instead of `file_path`
3. Download from Blob URL for the download endpoint

Key changes to the create endpoint:
```python
from backend.document.generator import generate_proposal

blob_url = generate_proposal(tender, template)

proposal = models.Proposal(
    tender_id=tender.id,
    template_id=template.id,
    blob_url=blob_url,
    status="draft",
)
```

Key changes to the download endpoint:
```python
from backend.blob_storage import download_blob

content = download_blob(proposal.blob_url)
return Response(
    content=content,
    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    headers={"Content-Disposition": f'attachment; filename="proposal_{proposal.id}.docx"'},
)
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/ -k proposal -v`

- [ ] **Step 3: Commit**

```bash
git add backend/routers/proposals.py
git commit -m "feat: update proposal router for Vercel Blob Storage"
```

---

## Chunk 4: Scraper Rearchitecture

### Task 11: Update Fetcher (Remove Playwright)

**Files:**
- Modify: `backend/scraper/fetcher.py`

- [ ] **Step 1: Replace fetcher.py**

```python
import os
import requests


def fetch_html(url: str, renderer: str = "default", timeout: int = 8) -> str:
    """
    Fetch HTML from a URL.
    renderer="default": uses requests (suitable for server-rendered HTML).
    renderer="external": calls EXTERNAL_RENDERER_URL (future, not yet implemented).
    """
    if renderer == "external":
        return _fetch_with_external_renderer(url, timeout)
    return _fetch_with_requests(url, timeout)


def _fetch_with_requests(url: str, timeout: int) -> str:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "TenderBot/1.0"})
    response.raise_for_status()
    return response.text


def _fetch_with_external_renderer(url: str, timeout: int) -> str:
    """Stub for external JS rendering service. Not implemented yet."""
    renderer_url = os.environ.get("EXTERNAL_RENDERER_URL", "")
    if not renderer_url:
        raise RuntimeError("EXTERNAL_RENDERER_URL not configured")
    response = requests.post(
        renderer_url,
        json={"url": url},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json().get("html", "")
```

- [ ] **Step 2: Commit**

```bash
git add backend/scraper/fetcher.py
git commit -m "feat: replace Playwright with requests-only fetcher, add external renderer stub"
```

---

### Task 12: Update Scraper Engine for Serverless

**Files:**
- Modify: `backend/scraper/engine.py`

- [ ] **Step 1: Update engine.py**

Key changes to `backend/scraper/engine.py`:
1. Add `MAX_PAGES = 3` constant for pagination limit
2. Update `fetch_html` calls to use 8-second timeout
3. Add pagination page counter that stops at MAX_PAGES
4. Remove any threading/locking logic (not needed in serverless)
5. Keep keyword matching and deduplication unchanged

The `scrape_portal` function should:
- Accept a `db` session and `portal_id`
- Fetch HTML with 8s timeout
- Parse with CSS selectors from scrape_config
- Match keywords
- Deduplicate by source_url
- Log results in ScrapeLog
- Limit to 3 pages of pagination

The `run_all_portals` function should remain for backward compatibility but now just loops through active portals calling `scrape_portal`.

- [ ] **Step 2: Run scraper tests**

Run: `pytest tests/ -k scraper -v`

- [ ] **Step 3: Commit**

```bash
git add backend/scraper/engine.py
git commit -m "feat: update scraper engine for serverless (8s timeout, 3-page limit)"
```

---

### Task 13: Update Scraper Router for Fan-Out

**Files:**
- Modify: `backend/routers/scraper.py`

- [ ] **Step 1: Replace scraper router**

Replace full contents of `backend/routers/scraper.py`:

```python
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models
from backend.schemas import ScrapeRunRequest, ScrapeLogOut, PaginatedResponse

router = APIRouter()


def _verify_scrape_token(request: Request):
    """Verify X-Scrape-Token header for cron-triggered scrapes."""
    token = request.headers.get("X-Scrape-Token", "")
    expected = os.environ.get("SCRAPE_SECRET", "")
    if token and token == expected:
        return True
    return False


@router.get("/status")
def get_scrape_status(db: Session = Depends(get_db)):
    """Get latest ScrapeLog per portal."""
    from sqlalchemy import func
    subq = (
        db.query(models.ScrapeLog.portal_id, func.max(models.ScrapeLog.run_at).label("max_run"))
        .group_by(models.ScrapeLog.portal_id)
        .subquery()
    )
    logs = (
        db.query(models.ScrapeLog)
        .join(subq, (models.ScrapeLog.portal_id == subq.c.portal_id) & (models.ScrapeLog.run_at == subq.c.max_run))
        .all()
    )
    return [
        ScrapeLogOut(
            id=log.id, portal_id=log.portal_id,
            portal_name=log.portal.name if log.portal else "",
            run_at=log.run_at, tenders_found=log.tenders_found,
            tenders_new=log.tenders_new, status=log.status,
            error_message=log.error_message,
        ).model_dump()
        for log in logs
    ]


@router.post("/run", status_code=202)
async def trigger_scrape(data: ScrapeRunRequest, request: Request, db: Session = Depends(get_db)):
    """
    Trigger scrape. With portal_id: scrape one portal directly.
    Without portal_id: fan-out to all active portals using async concurrency.
    Also accepts X-Scrape-Token for cron-triggered scrapes (bypasses JWT).
    """
    if data.portal_id:
        # Direct single-portal scrape
        from backend.scraper.engine import scrape_portal
        scrape_portal(portal_id=data.portal_id, db=db)
        return {"message": f"Scrape completed for portal {data.portal_id}"}

    # Fan-out: fire async requests for each active portal
    import asyncio
    portals = db.query(models.Portal).filter(models.Portal.enabled == True).all()
    vercel_url = os.environ.get("VERCEL_URL", "localhost:3000")
    scrape_secret = os.environ.get("SCRAPE_SECRET", "")
    auth_header = request.headers.get("Authorization", "")

    async def fire_scrape(portal_id: int):
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    f"https://{vercel_url}/api/scraper/run",
                    json={"portal_id": portal_id},
                    headers={
                        "Authorization": auth_header,
                        "X-Scrape-Token": scrape_secret,
                    },
                    timeout=1.0,  # Fire and forget
                )
            except (httpx.TimeoutException, httpx.ConnectError):
                pass  # Expected — we fire and forget

    # Process in batches of 10 (Vercel Hobby concurrency limit)
    BATCH_SIZE = 10
    triggered = []
    for i in range(0, len(portals), BATCH_SIZE):
        batch = portals[i:i + BATCH_SIZE]
        await asyncio.gather(*[fire_scrape(p.id) for p in batch])
        triggered.extend([p.id for p in batch])

    return {"message": f"Fan-out triggered for {len(triggered)} portals", "portal_ids": triggered}


@router.get("/logs", response_model=PaginatedResponse)
def list_logs(page: int = 1, page_size: int = 50, portal_id: int = None, db: Session = Depends(get_db)):
    page_size = min(page_size, 200)
    query = db.query(models.ScrapeLog)
    if portal_id:
        query = query.filter(models.ScrapeLog.portal_id == portal_id)
    total = query.count()
    items = (
        query.order_by(models.ScrapeLog.run_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    out = []
    for log in items:
        out.append(ScrapeLogOut(
            id=log.id, portal_id=log.portal_id,
            portal_name=log.portal.name if log.portal else "",
            run_at=log.run_at, tenders_found=log.tenders_found,
            tenders_new=log.tenders_new, status=log.status,
            error_message=log.error_message,
        ).model_dump())
    return PaginatedResponse(items=out, total=total, page=page, page_size=page_size)
```

- [ ] **Step 2: Delete backend/scheduler.py**

Run: `rm backend/scheduler.py`

- [ ] **Step 3: Run tests**

Run: `pytest tests/ -k scraper -v`

- [ ] **Step 4: Commit**

```bash
git add backend/routers/scraper.py
git rm backend/scheduler.py
git commit -m "feat: replace scheduler with fan-out scraper router for serverless"
```

---

## Chunk 5: Vercel Deployment Configuration

### Task 14: Create Vercel Entry Point

**Files:**
- Create: `api/index.py`
- Create: `vercel.json`

- [ ] **Step 1: Create api/index.py**

```python
from mangum import Mangum
from backend.main import app

handler = Mangum(app, lifespan="off")
```

Note: `lifespan="off"` because Vercel serverless functions don't support ASGI lifespan. Table creation must be handled externally (Turso migration in Task 26 Step 4). For local dev, `init_db()` is called via the lifespan. For production Turso, tables are pre-created during migration — `create_all` is a no-op if tables already exist.

Add a startup event as fallback in `backend/main.py`:

```python
@app.on_event("startup")
def startup_event():
    init_db()
```

This ensures tables are created on first cold start even without lifespan support.

- [ ] **Step 2: Update backend/main.py lifespan to handle serverless**

Update the lifespan to be safe when not used:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
```

(Already done — just remove scheduler references which were removed in Task 13)

- [ ] **Step 3: Create vercel.json**

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python",
      "config": { "maxLambdaSize": "50mb" }
    },
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build",
      "config": { "distDir": "dist" }
    }
  ],
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/index.py" },
    { "source": "/(.*)", "destination": "/frontend/$1" }
  ]
}
```

- [ ] **Step 4: Commit**

```bash
git add api/index.py vercel.json
git commit -m "feat: add Vercel serverless entry point and configuration"
```

---

### Task 15: Create GitHub Actions Cron Workflow

**Files:**
- Create: `.github/workflows/nightly-scrape.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
name: Nightly Tender Scrape

on:
  schedule:
    # 23:59 IST = 18:29 UTC
    - cron: '29 18 * * *'
  workflow_dispatch: # Allow manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger nightly scrape
        run: |
          curl -X POST \
            -H "X-Scrape-Token: ${{ secrets.SCRAPE_SECRET }}" \
            -H "Content-Type: application/json" \
            -d '{}' \
            "https://${{ vars.VERCEL_URL }}/api/scraper/run"
        env:
          SCRAPE_SECRET: ${{ secrets.SCRAPE_SECRET }}
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/nightly-scrape.yml
git commit -m "feat: add GitHub Actions nightly scrape cron workflow"
```

---

### Task 15b: Create Blob Migration Script

**Files:**
- Create: `scripts/migrate_blobs.py`

- [ ] **Step 1: Create the migration script**

```python
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

    # Migrate templates
    templates = conn.execute("SELECT id, file_path, original_filename FROM templates WHERE file_path NOT LIKE 'http%'").fetchall()
    for t in templates:
        if not os.path.exists(t["file_path"]):
            print(f"  SKIP template {t['id']}: file not found at {t['file_path']}")
            continue
        with open(t["file_path"], "rb") as f:
            content = f.read()
        blob_url = upload_blob(content, f"templates/{t['original_filename']}")
        conn.execute("UPDATE templates SET file_path = ? WHERE id = ?", (blob_url, t["id"]))
        print(f"  OK template {t['id']} -> {blob_url}")

    # Migrate proposals
    proposals = conn.execute("SELECT id, file_path FROM proposals WHERE file_path NOT LIKE 'http%'").fetchall()
    for p in proposals:
        if not os.path.exists(p["file_path"]):
            print(f"  SKIP proposal {p['id']}: file not found at {p['file_path']}")
            continue
        with open(p["file_path"], "rb") as f:
            content = f.read()
        blob_url = upload_blob(content, f"proposals/proposal_{p['id']}.docx")
        conn.execute("UPDATE proposals SET file_path = ? WHERE id = ?", (blob_url, p["id"]))
        print(f"  OK proposal {p['id']} -> {blob_url}")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/migrate_blobs.py /path/to/tender.db")
        sys.exit(1)
    migrate(sys.argv[1])
```

Note: This script requires local access to both the SQLite file and Vercel Blob credentials (`BLOB_READ_WRITE_TOKEN` env var).

- [ ] **Step 2: Commit**

```bash
git add scripts/migrate_blobs.py
git commit -m "feat: add one-time blob migration script for local files to Vercel Blob"
```

---

### Task 15c: Implement Health Endpoint with Connectivity Checks

**Files:**
- Modify: `backend/routers/health.py`

- [ ] **Step 1: Replace health.py stub with actual connectivity checks**

```python
import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Check Turso DB and Vercel Blob connectivity."""
    checks = {}

    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Check Blob storage (just verify token is set)
    blob_token = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
    checks["blob_storage"] = "ok" if blob_token else "warning: BLOB_READ_WRITE_TOKEN not set"

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

- [ ] **Step 2: Commit**

```bash
git add backend/routers/health.py
git commit -m "feat: implement health endpoint with Turso and Blob connectivity checks"
```

---

### Task 16: Archive Docker Files

**Files:**
- Move: `Dockerfile` → `docker/Dockerfile`
- Move: `docker-compose.yml` → `docker/docker-compose.yml`

- [ ] **Step 1: Create docker directory and move files**

```bash
mkdir -p docker
git mv Dockerfile docker/Dockerfile
git mv docker-compose.yml docker/docker-compose.yml
```

- [ ] **Step 2: Commit**

```bash
git commit -m "chore: archive Docker files to docker/ directory"
```

---

## Chunk 6: Frontend — Auth & Core Enhancements

### Task 17: Add JWT to API Client + Login Page

**Files:**
- Modify: `frontend/src/api/client.js`
- Create: `frontend/src/pages/Login.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Update frontend/src/api/client.js**

```javascript
import axios from 'axios';

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Add JWT token to all requests
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses — redirect to login
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/';
    }
    const message = error.response?.data?.detail || error.response?.data?.error || error.message;
    return Promise.reject(new Error(message));
  }
);

export default client;
```

- [ ] **Step 2: Create frontend/src/pages/Login.jsx**

```jsx
import { useState } from 'react';
import client from '../api/client';

export default function Login({ onLogin }) {
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await client.post('/auth', { password, remember_me: rememberMe });
      localStorage.setItem('token', res.data.token);
      onLogin();
    } catch (err) {
      setError(err.message || 'Invalid password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#0d0d1a', color: '#e0e0e0', fontFamily: 'Inter, system-ui, sans-serif',
    }}>
      <form onSubmit={handleSubmit} style={{
        background: '#1a1a2e', padding: '2.5rem', borderRadius: '12px',
        width: '100%', maxWidth: '400px', boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
      }}>
        <h1 style={{ textAlign: 'center', marginBottom: '0.5rem', color: '#a89cf7' }}>
          Tender Dashboard
        </h1>
        <p style={{ textAlign: 'center', marginBottom: '2rem', color: '#888', fontSize: '0.9rem' }}>
          Enter password to continue
        </p>

        {error && (
          <div style={{
            background: '#ff4d4f22', border: '1px solid #ff4d4f', borderRadius: '6px',
            padding: '0.75rem', marginBottom: '1rem', color: '#ff4d4f', fontSize: '0.85rem',
          }}>
            {error}
          </div>
        )}

        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          autoFocus
          style={{
            width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #333',
            background: '#0d0d1a', color: '#e0e0e0', fontSize: '1rem', marginBottom: '1rem',
            boxSizing: 'border-box',
          }}
        />

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
          />
          <span style={{ fontSize: '0.85rem', color: '#888' }}>Remember me (7 days)</span>
        </label>

        <button
          type="submit"
          disabled={loading || !password}
          style={{
            width: '100%', padding: '0.75rem', borderRadius: '6px', border: 'none',
            background: '#a89cf7', color: '#0d0d1a', fontSize: '1rem', fontWeight: '600',
            cursor: loading ? 'wait' : 'pointer', opacity: loading || !password ? 0.6 : 1,
          }}
        >
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 3: Update frontend/src/App.jsx with login gate**

Wrap the existing App content in an auth check. Add to the top of App.jsx:

```jsx
import { useState, useEffect } from 'react';
import Login from './pages/Login';

// Inside the App component, before rendering tabs:
const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));

const handleLogout = () => {
  localStorage.removeItem('token');
  setIsAuthenticated(false);
};

if (!isAuthenticated) {
  return <Login onLogin={() => setIsAuthenticated(true)} />;
}

// Add a logout button in the nav bar
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.js frontend/src/pages/Login.jsx frontend/src/App.jsx
git commit -m "feat: add login page, JWT auth flow, and route protection in frontend"
```

---

### Task 18: Add Toast Notification Component

**Files:**
- Create: `frontend/src/components/Toast.jsx`

- [ ] **Step 1: Create Toast.jsx**

```jsx
import { useState, useEffect, useCallback, createContext, useContext } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), duration);
  }, []);

  return (
    <ToastContext.Provider value={addToast}>
      {children}
      <div style={{ position: 'fixed', top: '1rem', right: '1rem', zIndex: 9999, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {toasts.map((toast) => (
          <div key={toast.id} style={{
            padding: '0.75rem 1.25rem', borderRadius: '8px', color: '#fff', fontSize: '0.9rem',
            background: toast.type === 'error' ? '#ff4d4f' : toast.type === 'success' ? '#52c41a' : '#1890ff',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)', animation: 'fadeIn 0.2s ease',
          }}>
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
```

- [ ] **Step 2: Wrap App in ToastProvider**

In `App.jsx`, wrap the root component:

```jsx
import { ToastProvider } from './components/Toast';

// In the return:
return (
  <ToastProvider>
    {/* existing app content */}
  </ToastProvider>
);
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Toast.jsx frontend/src/App.jsx
git commit -m "feat: add toast notification system"
```

---

### Task 18b: Create ConfirmDialog Component

**Files:**
- Create: `frontend/src/components/ConfirmDialog.jsx`

- [ ] **Step 1: Create ConfirmDialog.jsx**

```jsx
import { useEffect, useRef } from 'react';

export default function ConfirmDialog({ open, title, message, onConfirm, onCancel }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    if (open) dialogRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div
      ref={dialogRef}
      tabIndex={-1}
      onKeyDown={(e) => e.key === 'Escape' && onCancel()}
      style={{
        position: 'fixed', inset: 0, zIndex: 10000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(0,0,0,0.6)',
      }}
    >
      <div style={{
        background: '#1a1a2e', borderRadius: '12px', padding: '1.5rem',
        maxWidth: '400px', width: '90%', boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
      }}>
        <h3 style={{ margin: '0 0 0.75rem', color: '#e0e0e0' }}>{title || 'Confirm'}</h3>
        <p style={{ color: '#aaa', fontSize: '0.9rem', margin: '0 0 1.5rem' }}>{message}</p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{
              padding: '0.5rem 1rem', borderRadius: '6px', border: '1px solid #333',
              background: 'transparent', color: '#e0e0e0', cursor: 'pointer',
            }}
          >Cancel</button>
          <button
            onClick={onConfirm}
            style={{
              padding: '0.5rem 1rem', borderRadius: '6px', border: 'none',
              background: '#a89cf7', color: '#0d0d1a', cursor: 'pointer', fontWeight: 600,
            }}
          >Confirm</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ConfirmDialog.jsx
git commit -m "feat: add reusable confirmation dialog component"
```

---

### Task 19: Create Scrape Config Editor Component

**Files:**
- Create: `frontend/src/components/ScrapeConfigEditor.jsx`

- [ ] **Step 1: Create ScrapeConfigEditor.jsx**

```jsx
import { useState, useEffect } from 'react';

const FIELD_LABELS = [
  { key: 'list_selector', label: 'Tender List Container', placeholder: 'e.g., table.tenders tbody tr' },
  { key: 'fields.title', label: 'Title Selector', placeholder: 'e.g., td.title' },
  { key: 'fields.description', label: 'Description Selector', placeholder: 'e.g., td.description' },
  { key: 'fields.deadline', label: 'Deadline Selector', placeholder: 'e.g., td.deadline' },
  { key: 'fields.estimated_value', label: 'Estimated Value Selector', placeholder: 'e.g., td.value' },
  { key: 'fields.source_url', label: 'Source URL Selector', placeholder: 'e.g., td a@href' },
  { key: 'next_button', label: 'Next Page Button', placeholder: 'e.g., a.next-page' },
  { key: 'date_format', label: 'Date Format', placeholder: 'e.g., %d/%m/%Y' },
  { key: 'renderer', label: 'Renderer', placeholder: 'default or external' },
];

const inputStyle = {
  width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #333',
  background: '#0d0d1a', color: '#e0e0e0', fontSize: '0.85rem', boxSizing: 'border-box',
};

export default function ScrapeConfigEditor({ value, onChange }) {
  const [mode, setMode] = useState('form'); // 'form' or 'json'
  const [jsonText, setJsonText] = useState(value || '{}');
  const [jsonError, setJsonError] = useState('');

  const config = (() => {
    try { return JSON.parse(value || '{}'); } catch { return {}; }
  })();

  const updateField = (dotPath, val) => {
    const newConfig = { ...config };
    const parts = dotPath.split('.');
    if (parts.length === 2) {
      if (!newConfig[parts[0]]) newConfig[parts[0]] = {};
      newConfig[parts[0]][parts[1]] = val;
    } else {
      newConfig[parts[0]] = val;
    }
    const json = JSON.stringify(newConfig, null, 2);
    setJsonText(json);
    onChange(json);
  };

  const getField = (dotPath) => {
    const parts = dotPath.split('.');
    if (parts.length === 2) return config[parts[0]]?.[parts[1]] || '';
    return config[parts[0]] || '';
  };

  const handleJsonChange = (text) => {
    setJsonText(text);
    try {
      JSON.parse(text);
      setJsonError('');
      onChange(text);
    } catch (e) {
      setJsonError(e.message);
    }
  };

  useEffect(() => {
    setJsonText(value || '{}');
  }, [value]);

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <button
          onClick={() => setMode('form')}
          style={{
            padding: '0.4rem 1rem', borderRadius: '4px', border: '1px solid #333',
            background: mode === 'form' ? '#a89cf7' : 'transparent',
            color: mode === 'form' ? '#0d0d1a' : '#e0e0e0', cursor: 'pointer', fontWeight: 600,
          }}
        >Form</button>
        <button
          onClick={() => setMode('json')}
          style={{
            padding: '0.4rem 1rem', borderRadius: '4px', border: '1px solid #333',
            background: mode === 'json' ? '#a89cf7' : 'transparent',
            color: mode === 'json' ? '#0d0d1a' : '#e0e0e0', cursor: 'pointer', fontWeight: 600,
          }}
        >JSON</button>
      </div>

      {mode === 'form' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {FIELD_LABELS.map(({ key, label, placeholder }) => (
            <div key={key}>
              <label style={{ fontSize: '0.8rem', color: '#888', marginBottom: '0.25rem', display: 'block' }}>
                {label}
              </label>
              <input
                style={inputStyle}
                value={getField(key)}
                onChange={(e) => updateField(key, e.target.value)}
                placeholder={placeholder}
              />
            </div>
          ))}
        </div>
      ) : (
        <div>
          <textarea
            value={jsonText}
            onChange={(e) => handleJsonChange(e.target.value)}
            style={{
              ...inputStyle, minHeight: '250px', fontFamily: 'monospace', resize: 'vertical',
            }}
          />
          {jsonError && <div style={{ color: '#ff4d4f', fontSize: '0.8rem', marginTop: '0.25rem' }}>{jsonError}</div>}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ScrapeConfigEditor.jsx
git commit -m "feat: add dual-mode scrape config editor component (form + JSON)"
```

---

## Chunk 7: Frontend Page Enhancements

### Task 20: Enhance Dashboard Page

**Files:**
- Modify: `frontend/src/pages/Dashboard.jsx`

- [ ] **Step 1: Enhance Dashboard.jsx**

Key enhancements:
1. Add Rejected stat card alongside existing stats
2. Add date range filter (from/to date inputs)
3. Add portal filter dropdown
4. Add keyword filter dropdown
5. Add inline approve/reject buttons with confirmation dialog
6. Add tender detail modal with matched keywords highlighted
7. Add auto-refresh polling after scrape (poll `/api/scraper/status` every 10s during active scrape)
8. Add loading spinner

The implementation should use the existing dark theme styles (#0d0d1a, #1a1a2e, #a89cf7) and build on the existing Dashboard component structure.

- [ ] **Step 2: Test manually in browser**

Run: `cd frontend && npm run dev`
Verify: Dashboard loads with enhanced filtering and stats

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.jsx
git commit -m "feat: enhance dashboard with filters, stats, detail modal, and auto-refresh"
```

---

### Task 21: Enhance Scraper Page

**Files:**
- Modify: `frontend/src/pages/Scraper.jsx`

- [ ] **Step 1: Enhance Scraper.jsx**

Key enhancements:
1. Replace table with portal cards showing: name, URL, last scraped timestamp, enabled badge, tender count
2. Integrate `ScrapeConfigEditor` component for add/edit portal modal
3. Add "Test Scrape" button that calls `POST /api/scraper/run` with `portal_id` and shows preview of results
4. Add expandable scrape log history per portal (fetches `/api/scraper/logs?portal_id=X`)
5. Add loading states and toast notifications

Import the config editor:
```jsx
import ScrapeConfigEditor from '../components/ScrapeConfigEditor';
```

- [ ] **Step 2: Test manually**

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Scraper.jsx
git commit -m "feat: enhance scraper page with portal cards, config editor, and test scrape"
```

---

### Task 22: Enhance Keywords Page

**Files:**
- Modify: `frontend/src/pages/Keywords.jsx`

- [ ] **Step 1: Enhance Keywords.jsx**

Key enhancements:
1. Add bulk add input (comma-separated values) that creates multiple keywords at once
2. Add search/filter input at top of keyword list
3. Improve active/inactive toggle with visual indicator (green/gray dot)
4. Add toast notifications for add/delete/toggle operations

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Keywords.jsx
git commit -m "feat: enhance keywords page with bulk add, search, and visual toggles"
```

---

### Task 23: Enhance Templates Page

**Files:**
- Modify: `frontend/src/pages/Templates.jsx`

- [ ] **Step 1: Enhance Templates.jsx**

Key enhancements:
1. Add drag-and-drop upload zone (ondragover/ondrop events)
2. Add placeholder reference panel showing all available `{{placeholders}}`
3. Update download link to use `blob_url` from API response
4. Add validation feedback (file type, size limit)
5. Add toast notifications

Placeholder reference:
```jsx
const PLACEHOLDERS = [
  '{{tender_title}}', '{{tender_description}}', '{{tender_deadline}}',
  '{{tender_published_date}}', '{{tender_estimated_value}}', '{{tender_source_url}}',
  '{{tender_portal_name}}', '{{tender_portal_url}}', '{{generation_date}}',
  '{{company_name}}', '{{company_address}}', '{{company_contact}}',
];
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Templates.jsx
git commit -m "feat: enhance templates page with drag-drop upload and placeholder reference"
```

---

### Task 24: Enhance Proposals Page

**Files:**
- Modify: `frontend/src/pages/Proposals.jsx`

- [ ] **Step 1: Enhance Proposals.jsx**

Key enhancements:
1. Add status pipeline view (Draft → Submitted → Won/Lost) as horizontal progress indicator
2. Add link back to source tender (clickable tender title)
3. Update download to use `blob_url` from API
4. Add "Regenerate" button that creates a new proposal for the same tender with same or different template
5. Add toast notifications

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Proposals.jsx
git commit -m "feat: enhance proposals page with pipeline view and regenerate option"
```

---

## Chunk 8: Git Push, Vercel Deploy & Final Wiring

### Task 24b: Update .gitignore Before Push

**Files:**
- Modify or create: `.gitignore`

- [ ] **Step 1: Ensure .gitignore excludes secrets and build artifacts**

```
# Environment
.env
.env.local

# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Node
node_modules/
frontend/dist/

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Data
*.db
/data/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore for Vercel deployment"
```

---

### Task 25: Create GitHub Repository and Push

**Files:** None (git operations only)

- [ ] **Step 1: Create GitHub repo**

```bash
cd /Users/rajiv/Desktop/Product-hub/Projects/tender-dashboard
gh repo create rajivranjanopalina-cyber/tender-dashboard --public --source=. --push
```

- [ ] **Step 2: Verify push**

```bash
gh repo view rajivranjanopalina-cyber/tender-dashboard --web
```

- [ ] **Step 3: Set up GitHub Actions secrets**

```bash
gh secret set SCRAPE_SECRET
```
(Will prompt for value — enter a random string)

```bash
gh variable set VERCEL_URL --body "tender-dashboard.vercel.app"
```

---

### Task 26: Deploy to Vercel

- [ ] **Step 1: Install Vercel CLI if needed**

```bash
npm install -g vercel
```

- [ ] **Step 2: Link project and deploy**

```bash
cd /Users/rajiv/Desktop/Product-hub/Projects/tender-dashboard
vercel --prod
```

Follow the prompts to link to your Vercel account and project.

- [ ] **Step 3: Set environment variables in Vercel**

```bash
vercel env add TURSO_DATABASE_URL
vercel env add TURSO_AUTH_TOKEN
vercel env add DASHBOARD_PASSWORD_HASH
vercel env add SECRET_KEY
vercel env add JWT_SECRET
vercel env add SCRAPE_SECRET
vercel env add BLOB_READ_WRITE_TOKEN
vercel env add COMPANY_NAME
vercel env add COMPANY_ADDRESS
vercel env add COMPANY_CONTACT
```

- [ ] **Step 4: Set up Turso database**

```bash
# Install Turso CLI
brew install tursodatabase/tap/turso
turso auth login
turso db create tender-dashboard
turso db show tender-dashboard  # Get the URL
turso db tokens create tender-dashboard  # Get the auth token
```

Use the URL and token for `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`.

- [ ] **Step 5: Redeploy with env vars**

```bash
vercel --prod
```

- [ ] **Step 6: Verify deployment**

Visit `https://tender-dashboard.vercel.app` — should show login page.

---

### Task 27: Final Integration Test

- [ ] **Step 1: Test login flow**

Enter password on login page → should get JWT and see dashboard.

- [ ] **Step 2: Test portal management**

Add a test portal on Scraper page → verify it appears in the list.

- [ ] **Step 3: Test keyword management**

Add keywords → verify bulk add works.

- [ ] **Step 4: Test template upload**

Upload a DOCX template → verify it uploads to Vercel Blob and appears in list.

- [ ] **Step 5: Test proposal generation**

Approve a tender → Generate proposal → Download DOCX → verify placeholders are replaced.

- [ ] **Step 6: Test scrape trigger**

Trigger manual scrape for a portal → verify ScrapeLog is created.

- [ ] **Step 7: Commit any fixes**

```bash
git add -A
git commit -m "fix: integration test fixes"
git push
```
