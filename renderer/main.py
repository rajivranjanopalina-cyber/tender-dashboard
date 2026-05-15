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


_VALID_WAIT_UNTIL = {"load", "domcontentloaded", "networkidle", "commit"}


class RenderRequest(BaseModel):
    url: str
    wait_for: str = "body"
    timeout: int = 30000
    wait_until: str = "load"

    @field_validator("url")
    @classmethod
    def must_be_http(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("Only http:// and https:// URLs are allowed")
        return v

    @field_validator("wait_until")
    @classmethod
    def must_be_valid_wait_until(cls, v: str) -> str:
        if v not in _VALID_WAIT_UNTIL:
            raise ValueError(f"wait_until must be one of {_VALID_WAIT_UNTIL}")
        return v


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/render")
async def render(req: RenderRequest):
    async with _sem:
        try:
            html = await render_url(req.url, req.wait_for, req.timeout, req.wait_until)
            return {"html": html}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
