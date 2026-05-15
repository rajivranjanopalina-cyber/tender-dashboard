import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
import render as render_module
from render import render_url

_sem = asyncio.Semaphore(4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if render_module._browser is not None:
        try:
            await render_module._browser.close()
        except Exception:
            pass


app = FastAPI(title="Playwright Renderer", lifespan=lifespan)


class RenderRequest(BaseModel):
    url: str
    wait_for: str = "body"
    timeout: int = 30000

    @field_validator("url")
    @classmethod
    def must_be_http(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("Only http:// and https:// URLs are allowed")
        return v


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/render")
async def render(req: RenderRequest):
    async with _sem:
        try:
            html = await render_url(req.url, req.wait_for, req.timeout)
            return {"html": html}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
