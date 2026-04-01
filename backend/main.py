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

# Startup event as fallback for serverless environments where lifespan may not run
@app.on_event("startup")
def startup_event():
    init_db()

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
