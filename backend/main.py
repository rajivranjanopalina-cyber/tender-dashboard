import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import init_db
from backend.routers import portals, keywords, tenders, templates, proposals, scraper


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from backend.scheduler import start_scheduler
    start_scheduler()
    yield
    from backend.scheduler import stop_scheduler
    stop_scheduler()


app = FastAPI(title="Tender Dashboard", lifespan=lifespan)

app.include_router(portals.router, prefix="/api/portals", tags=["portals"])
app.include_router(keywords.router, prefix="/api/keywords", tags=["keywords"])
app.include_router(tenders.router, prefix="/api/tenders", tags=["tenders"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(proposals.router, prefix="/api/proposals", tags=["proposals"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
