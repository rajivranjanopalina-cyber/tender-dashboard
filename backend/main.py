from fastapi import FastAPI, Depends
from backend.dependencies import require_auth
from backend.routers import portals, keywords, tenders, templates, proposals, scraper, auth, health

app = FastAPI(title="Tender Dashboard")

# Public routes (no auth)
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(health.router, prefix="/api", tags=["health"])

# Protected routes (require JWT)
protected = [
    (portals.router, "/api/portals", ["portals"]),
    (keywords.router, "/api/keywords", ["keywords"]),
    (tenders.router, "/api/tenders", ["tenders"]),
    (templates.router, "/api/templates", ["templates"]),
    (proposals.router, "/api/proposals", ["proposals"]),
    (scraper.router, "/api/scraper", ["scraper"]),
]

for router_obj, prefix, tags in protected:
    app.include_router(router_obj, prefix=prefix, tags=tags, dependencies=[Depends(require_auth)])
