# Tender Dashboard — Vercel Enhancement Design

**Date:** 2026-03-31
**Status:** Draft
**Approach:** Enhance existing Python/FastAPI + React project, rearchitect for Vercel serverless deployment

---

## 1. Overview

Enhance the existing tender-dashboard project and rearchitect it for Vercel-only deployment. The current stack (FastAPI + React + SQLite + Docker) is transformed into Vercel Python serverless functions + React static SPA + Turso cloud database + Vercel Blob Storage.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Deployment | Vercel only (free tier) | User requirement |
| Database | Turso (libsql) | SQLite-compatible, minimal code changes |
| Scraping | Hybrid — requests/BS4 now, external renderer pluggable | Gov portals are mostly server-rendered HTML |
| Cron | GitHub Actions → secured endpoint | Free, reliable, lives in same repo |
| Document gen | DOCX only | Removes LibreOffice dependency, users convert locally |
| Auth | Simple password gate + JWT | Lightweight, no user management overhead |
| File storage | Vercel Blob Storage | Free 100MB tier, direct download URLs |
| Backend approach | Python serverless functions | Least code change from existing FastAPI |

---

## 2. Serverless Function Convention

Each `api/*.py` file is a Vercel Python serverless function. The existing FastAPI app is adapted using the `mangum` ASGI adapter pattern. Each file exports a handler:

```python
# api/portals.py
from mangum import Mangum
from backend.app import app  # FastAPI sub-app or full app

handler = Mangum(app)
```

Alternatively, if Mangum proves problematic with Vercel's Python runtime, each file can export a raw handler function following Vercel's convention:

```python
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
```

**Decision:** Try Mangum first (preserves FastAPI routing, middleware, dependency injection). Fall back to raw handlers only if Mangum is incompatible.

### Route Naming Changes

| Current Route | New Route | Reason |
|---|---|---|
| `/api/scraper/*` | `/api/scrape` | Simplified — single endpoint for scrape trigger |
| (none) | `/api/auth` | New — password gate |
| (none) | `/api/health` | New — health check for Turso + Blob connectivity |

---

## 3. Architecture

### Project Structure

```
tender-dashboard/
├── api/                    # Vercel Python serverless functions
│   ├── portals.py          # Portal CRUD
│   ├── keywords.py         # Keyword CRUD
│   ├── tenders.py          # Tender listing/filtering/status
│   ├── templates.py        # Template upload/download
│   ├── proposals.py        # Proposal generation/lifecycle
│   ├── scrape.py           # Manual trigger + cron endpoint
│   └── auth.py             # Password verification + JWT issuance
├── frontend/               # React SPA (Vite build)
│   └── src/
│       ├── pages/          # Dashboard, Scraper, Keywords, Templates, Proposals
│       ├── components/     # Reusable UI components
│       └── api/            # Axios client with JWT interceptor
├── backend/                # Shared Python modules (imported by api/)
│   ├── models.py           # SQLAlchemy models (Turso/libsql)
│   ├── database.py         # Turso connection setup
│   ├── scraper/
│   │   ├── engine.py       # Scraping orchestrator
│   │   ├── fetcher.py      # HTTP fetcher (requests + external renderer interface)
│   │   └── parser.py       # BeautifulSoup HTML parser
│   └── document/
│       ├── generator.py    # DOCX generation orchestrator
│       └── docx_handler.py # Placeholder replacement
├── .github/
│   └── workflows/
│       └── nightly-scrape.yml  # GitHub Actions cron
├── vercel.json             # Routes, rewrites, build config
└── requirements.txt        # Python deps
```

### Request Flow

```
Browser → Vercel CDN → Static frontend (React SPA)
                     → /api/* → Python serverless function → Turso DB
                                                           → Vercel Blob (file ops)

External cron (GitHub Actions, nightly 23:59 IST)
  → POST /api/scrape with X-Scrape-Token header
  → Fan-out: one invocation per active portal (using VERCEL_URL for self-invocation)
```

---

## 4. Database & Storage

### Turso (Cloud SQLite)

Same schema as existing SQLite — Turso is wire-compatible. Connection via `sqlalchemy-libsql` dialect package (the maintained SQLAlchemy dialect for Turso/libsql, supports `mapped_column`, relationships, and standard ORM patterns).

**Full schema (preserving all existing columns):**

- **Portal**: name, url, scrape_config (JSON), password_enc (Fernet-encrypted portal credentials), enabled flag, requires_auth, username, last_scraped_at, created_at
- **Keyword**: value, active flag
- **Tender**: title, description, published_date, deadline, estimated_value, source_url, portal_id, matched_keywords (JSON), status (new/under_review/approved/rejected), notes, scraped_at, last_updated_at
- **Template**: name, description, original_filename, blob_url (Vercel Blob), sha256 (hash for dedup), file_type (hardcoded to "docx"), created_at
- **Proposal**: tender_id, template_id, blob_url (Vercel Blob), status (draft/submitted/won/lost), created_at, updated_at
- **ScrapeLog**: portal_id, run_at, tenders_found, tenders_new, status, error_message

### Schema Changes from Current

- `Template.file_path` → `Template.blob_url` (URL pointing to Vercel Blob)
- `Proposal.file_path` → `Proposal.blob_url` (URL pointing to Vercel Blob)
- `Template.sha256` column name retained (not renamed to `content_hash`)
- `Template.file_type` column retained, hardcoded to `"docx"` for new uploads (preserves backward compatibility)
- `Tender.notes`, `Tender.scraped_at`, `Tender.last_updated_at` retained as-is
- Remove `PRAGMA foreign_keys=ON` (Turso handles constraints via its own config)
- Connection string format: `libsql://your-db.turso.io?authToken=<token>`

### Vercel Blob Storage

- Stores template DOCX files and generated proposal DOCX files
- Free tier: 100MB (sufficient for document storage)
- Direct download URLs — no serverless function needed to serve files
- Upload flow: frontend → `/api/templates` → serverless function stores in Blob → saves URL in Turso

---

## 5. Authentication

### Simple Password Gate

- `DASHBOARD_PASSWORD_HASH` env var stores the bcrypt hash (generated once via `python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"`)
- On login, user submits plaintext password → backend bcrypt-compares against the stored hash
- On successful login: backend returns a signed JWT (HS256, signed with `JWT_SECRET`)
- JWT stored in localStorage, included as `Authorization: Bearer <token>` on all requests
- JWT expiry: 24 hours (7 days if "remember me" checked)
- All `/api/*` endpoints except `/api/auth` require valid JWT
- Invalid/expired JWT → 401 → frontend redirects to login

### Flow

```
User → Login screen → POST /api/auth {password} → JWT token
     → All subsequent requests include Authorization header
     → /api/* validates JWT → proceeds or 401
```

---

## 6. Scraping Engine

### Serverless Adaptation

The scraper is rearchitected for Vercel's 10-second function timeout (Hobby plan):

- `POST /api/scrape` with `portal_id` param: scrapes a single portal (target: under 10s)
- `POST /api/scrape` without `portal_id`: fan-out — fetches all active portals, invokes itself once per portal via HTTP (fire-and-forget, each writes independently to Turso)
- External cron calls the fan-out endpoint

### Timeout & Error Handling

- **Per-portal timeout:** `requests.get()` uses a 8-second timeout to stay within the 10s function limit
- **Pagination limit:** max 3 pages per scrape invocation to avoid timeout; remaining pages scraped on next run
- **Failure handling:** each portal scrape writes its own ScrapeLog entry. If a portal fails, it logs the error and does not affect other portals
- **Retry:** no automatic retry; failed portals are scraped again on next cron run. Users can manually re-trigger from the dashboard
- **Concurrency:** fan-out fires up to 10 concurrent portal scrapes. Vercel Hobby allows ~10 concurrent function executions; if more portals exist, they are batched
- **Self-invocation URL:** fan-out uses `VERCEL_URL` env var (auto-set by Vercel) to construct the URL for per-portal invocations: `https://{VERCEL_URL}/api/scrape?portal_id={id}`

### Security

- Cron endpoint: requires `X-Scrape-Token` header matching `SCRAPE_SECRET` env var (header-based, not query param, to avoid token in logs)
- Manual scrape from dashboard: requires valid JWT (same as all endpoints)

### Scrape Config UX

Dual-mode editor on the Scraper page:

**Form mode (default):** labeled fields:
- Tender list container selector
- Title selector
- Description selector
- Deadline selector
- Estimated value selector
- Source URL / link selector
- Next page button selector (pagination)
- Date format pattern

**Advanced mode:** raw JSON editor (toggle switch), current behavior

Both modes read/write the same `scrape_config` JSON. Form mode provides validation and hints.

### Keyword Matching

- Unchanged: case-insensitive substring match on title + description
- Matched keywords stored in `matched_keywords` JSON array

### Deduplication

- Unchanged: by `source_url`, updates existing tender if found

### Hybrid Rendering

- Default: `requests` + BeautifulSoup
- `scrape_config.renderer` field: `"default"` or `"external"`
- External renderer calls a configurable API (`EXTERNAL_RENDERER_URL` env var)
- External rendering not implemented initially — just the config option for future use

---

## 7. Portal Credential Encryption

The existing `backend/encryption.py` (Fernet + PBKDF2) is **retained** for encrypting portal authentication credentials (`Portal.password_enc`). This is separate from dashboard authentication:

- **Dashboard auth:** bcrypt hash + JWT (Section 5)
- **Portal credentials:** Fernet encryption using `SECRET_KEY` env var (existing behavior, unchanged)

The `SECRET_KEY` env var is added to the Vercel environment alongside other secrets.

---

## 8. UI/UX Enhancements

### Dashboard Page
- Stats cards: Total, New, Approved, Under Review, Rejected
- Tender table with filtering: source portal, keyword, date range, status
- Inline approve/reject with confirmation
- Auto-refresh after scrape completes (poll `GET /api/scrape/status` endpoint which returns latest ScrapeLog per portal)
- Tender detail modal: full description, matched keywords highlighted

### Scraper Page
- Portal cards (not plain table): name, URL, last scraped, status badge, tender count
- Dual-mode config editor (form + JSON toggle)
- "Test Scrape" button: scrapes one portal on demand, shows results preview
- Scrape log history per portal (expandable section)

### Keywords Page
- Bulk add via comma-separated input
- Active/inactive toggle with visual indicator
- Search/filter within keywords list

### Templates Page
- Drag-and-drop upload zone
- Placeholder reference panel (lists available `{{placeholders}}`)
- Template preview: shows placeholder names found in uploaded DOCX

### Proposals Page
- Status pipeline view: Draft → Submitted → Won/Lost
- Link back to source tender
- Download DOCX button
- Regenerate option (re-run with same or different template)

### Global
- Dark theme preserved (#0d0d1a background, #a89cf7 accent)
- Loading spinners and toast notifications
- Responsive layout for tablet/mobile
- Login screen with password input and "remember me" option

---

## 9. Proposal Generation

### Flow

1. User approves tender on Dashboard
2. User clicks "Generate Proposal" → selects template from dropdown
3. `POST /api/proposals` → backend:
   - Fetches template DOCX from Vercel Blob
   - Replaces placeholders with tender + company data
   - Uploads generated DOCX to Vercel Blob
   - Creates Proposal record in Turso
4. User downloads generated DOCX

### Placeholders

| Placeholder | Source |
|---|---|
| `{{tender_title}}` | Tender record |
| `{{tender_description}}` | Tender record |
| `{{tender_deadline}}` | Tender record |
| `{{tender_published_date}}` | Tender record |
| `{{tender_estimated_value}}` | Tender record |
| `{{tender_source_url}}` | Tender record |
| `{{tender_portal_name}}` | Portal record |
| `{{tender_portal_url}}` | Portal record |
| `{{generation_date}}` | System datetime |
| `{{company_name}}` | Env var `COMPANY_NAME` |
| `{{company_address}}` | Env var `COMPANY_ADDRESS` |
| `{{company_contact}}` | Env var `COMPANY_CONTACT` |

### Template Validation
- Must be `.docx` format
- Max file size: 5MB
- SHA256 hash for deduplication (existing behavior)
- Optional: set default template per portal

---

## 10. Deployment & DevOps

### Vercel Configuration

`vercel.json`:
- Python runtime for `/api/*` routes
- Vite build for frontend → static output
- SPA rewrites: all non-api, non-asset routes → `index.html`

### Environment Variables

| Variable | Purpose |
|---|---|
| `TURSO_DATABASE_URL` | Turso connection string |
| `TURSO_AUTH_TOKEN` | Turso authentication |
| `DASHBOARD_PASSWORD_HASH` | Bcrypt hash of login password |
| `SECRET_KEY` | Fernet key for portal credential encryption |
| `JWT_SECRET` | JWT signing key |
| `SCRAPE_SECRET` | Cron endpoint auth token |
| `BLOB_READ_WRITE_TOKEN` | Vercel Blob Storage access |
| `COMPANY_NAME` | Proposal placeholder |
| `COMPANY_ADDRESS` | Proposal placeholder |
| `COMPANY_CONTACT` | Proposal placeholder |
| `EXTERNAL_RENDERER_URL` | (Optional, future) External JS rendering service URL |

### GitHub Repository

- Name: `tender-dashboard`
- Owner: `rajivranjanopalina-cyber`
- Connected to Vercel for auto-deploy on push to `main`

### Nightly Cron (GitHub Actions)

`.github/workflows/nightly-scrape.yml`:
- Schedule: `29 18 * * *` (23:59 IST = 18:29 UTC)
- Job: `curl -X POST -H "X-Scrape-Token: $SCRAPE_SECRET" https://<vercel-url>/api/scrape`
- `SCRAPE_SECRET` stored as GitHub Actions secret

### Build Pipeline

```
git push main
  → Vercel auto-build:
    1. Install Python deps (requirements.txt)
    2. Build React frontend (cd frontend && npm run build)
    3. Deploy serverless functions + static assets
    4. Available at <project>.vercel.app
```

---

### Vercel Configuration (`vercel.json`)

```json
{
  "version": 2,
  "builds": [
    { "src": "api/*.py", "use": "@vercel/python" },
    { "src": "frontend/package.json", "use": "@vercel/static-build", "config": { "distDir": "dist" } }
  ],
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/$1" },
    { "source": "/(.*)", "destination": "/frontend/$1" }
  ]
}
```

---

## 11. Error Handling Strategy

### API Error Responses

All API endpoints return consistent error responses:

```json
{ "detail": "Human-readable error message" }
```

- **400**: Invalid request (bad JSON, missing fields, invalid selectors)
- **401**: Missing/invalid/expired JWT
- **403**: Invalid scrape token
- **404**: Resource not found
- **500**: Internal error (DB unreachable, Blob upload failure)

### Specific Scenarios

| Scenario | Handling |
|---|---|
| Turso unreachable | Return 500 with "Database unavailable", log error |
| Blob upload fails mid-proposal | Return 500, do not create Proposal record (atomic) |
| Scrape finds malformed HTML | Log warning in ScrapeLog, skip unparseable tenders, continue with rest |
| Portal scrape exceeds timeout | `requests` 8s timeout raises exception → logged in ScrapeLog as error |
| JWT validation fails | Return 401, frontend redirects to login |

---

## 12. Migration Plan

### Phase 1: Database Migration (SQLite → Turso)

1. Create Turso database via CLI: `turso db create tender-dashboard`
2. Export existing SQLite data: `sqlite3 tender.db .dump > dump.sql`
3. Adapt dump for Turso compatibility (remove PRAGMAs, adjust syntax if needed)
4. Import into Turso via `turso db shell tender-dashboard < dump.sql`
5. Update `backend/database.py` to use `sqlalchemy-libsql` connection string
6. Update `Template` and `Proposal` models: `file_path` → `blob_url`

### Phase 2: File Migration (Local → Vercel Blob)

1. For each existing template/proposal with a local `file_path`:
   - Upload file to Vercel Blob via API
   - Update the database record with the returned `blob_url`
2. Write a one-time migration script (`scripts/migrate_blobs.py`)

### Phase 3: Serverless Conversion

1. Create `api/*.py` handler files wrapping existing FastAPI routes
2. Add `vercel.json` build configuration
3. Remove APScheduler, Docker, Playwright dependencies
4. Add GitHub Actions cron workflow
5. Test locally with `vercel dev`

### Phase 4: UI Enhancements

1. Add login screen and JWT flow
2. Enhance Dashboard, Scraper, Keywords, Templates, Proposals pages
3. Add scrape config form builder

### Cutover Strategy

- **Hard cutover**: once Vercel deployment is verified working, Docker deployment is deprecated
- The existing Docker setup remains in the repo (in a `docker/` archive directory) for reference but is no longer maintained
- No parallel running of both systems

---

## 13. Blob Storage Monitoring

Vercel Blob free tier is 100MB. To prevent exhaustion:

- Template uploads are limited to 5MB each
- Generated proposals are typically small (under 1MB)
- At ~100 templates + ~500 proposals, storage is well within limits
- If storage approaches 80%, display a warning in the Templates/Proposals UI
- Future: add a cleanup option to delete old draft proposals

---

## 14. Removed Components

The following are removed from the current codebase as they're incompatible with Vercel serverless:

| Component | Replacement |
|---|---|
| APScheduler | GitHub Actions cron → `/api/scrape` |
| Playwright | Removed (hybrid: requests/BS4 default, external renderer pluggable) |
| LibreOffice | Removed (DOCX only, no PDF conversion) |
| SQLite file | Turso cloud database |
| Local file storage | Vercel Blob Storage |
| Docker / docker-compose | Vercel deployment (Docker files archived to `docker/`) |
| `backend/document/pdf_handler.py` | Removed (DOCX only) |

**Note:** `backend/encryption.py` is **retained** for portal credential encryption (see Section 7).

---

## 15. Out of Scope

- User accounts / roles (single password gate only)
- Email notifications
- Full-text search
- Analytics dashboards
- Rate limiting
- Async/concurrent scraping beyond fan-out
- PDF generation
