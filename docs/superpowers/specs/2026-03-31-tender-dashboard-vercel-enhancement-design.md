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

## 2. Architecture

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
  → POST /api/scrape?token=SCRAPE_SECRET
  → Fan-out: one invocation per active portal
```

---

## 3. Database & Storage

### Turso (Cloud SQLite)

Same schema as existing SQLite — Turso is wire-compatible:

- **Portal**: name, url, scrape_config (JSON), auth credentials (encrypted), enabled flag
- **Keyword**: value, active flag
- **Tender**: title, description, deadline, estimated_value, source_url, portal_id, matched_keywords (JSON), status (new/under_review/approved/rejected)
- **Template**: name, description, blob_url (Vercel Blob), content_hash (SHA256), created_at
- **Proposal**: tender_id, template_id, blob_url (Vercel Blob), status (draft/submitted/won/lost), created_at
- **ScrapeLog**: portal_id, run_at, tenders_found, tenders_new, status, error_message

### Schema Changes from Current

- `Template.file_path` → `Template.blob_url` (URL pointing to Vercel Blob)
- `Proposal.file_path` → `Proposal.blob_url` (URL pointing to Vercel Blob)
- Remove `PRAGMA foreign_keys=ON` (Turso handles constraints differently)
- Connection via `libsql-experimental` Python package with SQLAlchemy dialect

### Vercel Blob Storage

- Stores template DOCX files and generated proposal DOCX files
- Free tier: 100MB (sufficient for document storage)
- Direct download URLs — no serverless function needed to serve files
- Upload flow: frontend → `/api/templates` → serverless function stores in Blob → saves URL in Turso

---

## 4. Authentication

### Simple Password Gate

- Single shared password, stored as Vercel env var `DASHBOARD_PASSWORD`
- Hashed at runtime using bcrypt for verification
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

## 5. Scraping Engine

### Serverless Adaptation

The scraper is rearchitected for Vercel's 10-second function timeout:

- `POST /api/scrape` with `portal_id` param: scrapes a single portal (fits within 10s)
- `POST /api/scrape` without `portal_id`: fan-out — fetches all active portals, invokes itself once per portal via HTTP
- External cron calls the fan-out endpoint

### Security

- Cron endpoint: requires `token` query param matching `SCRAPE_SECRET` env var
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

## 6. UI/UX Enhancements

### Dashboard Page
- Stats cards: Total, New, Approved, Under Review, Rejected
- Tender table with filtering: source portal, keyword, date range, status
- Inline approve/reject with confirmation
- Auto-refresh after scrape completes (poll scrape status)
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

## 7. Proposal Generation

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

## 8. Deployment & DevOps

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
| `DASHBOARD_PASSWORD` | Login password |
| `JWT_SECRET` | JWT signing key |
| `SCRAPE_SECRET` | Cron endpoint auth token |
| `BLOB_READ_WRITE_TOKEN` | Vercel Blob Storage access |
| `COMPANY_NAME` | Proposal placeholder |
| `COMPANY_ADDRESS` | Proposal placeholder |
| `COMPANY_CONTACT` | Proposal placeholder |

### GitHub Repository

- Name: `tender-dashboard`
- Owner: `rajivranjanopalina-cyber`
- Connected to Vercel for auto-deploy on push to `main`

### Nightly Cron (GitHub Actions)

`.github/workflows/nightly-scrape.yml`:
- Schedule: `30 18 * * *` (23:59 IST = 18:29 UTC, rounded to 18:30)
- Job: `curl -X POST https://<vercel-url>/api/scrape?token=$SCRAPE_SECRET`
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

## 9. Removed Components

The following are removed from the current codebase as they're incompatible with Vercel serverless:

| Component | Replacement |
|---|---|
| APScheduler | GitHub Actions cron → `/api/scrape` |
| Playwright | Removed (hybrid: requests/BS4 default, external renderer pluggable) |
| LibreOffice | Removed (DOCX only, no PDF conversion) |
| SQLite file | Turso cloud database |
| Local file storage | Vercel Blob Storage |
| Docker / docker-compose | Vercel deployment |
| `backend/encryption.py` | Simplified — JWT + bcrypt for auth |
| `backend/document/pdf_handler.py` | Removed (DOCX only) |

---

## 10. Out of Scope

- User accounts / roles (single password gate only)
- Email notifications
- Full-text search
- Analytics dashboards
- Rate limiting
- Async/concurrent scraping beyond fan-out
- PDF generation
