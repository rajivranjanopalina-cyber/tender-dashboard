import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, AnyHttpUrl, field_validator
from render import render_url

app = FastAPI(title="Playwright Renderer")

_sem = asyncio.Semaphore(4)  # cap concurrent renders


class RenderRequest(BaseModel):
    url: str
    wait_for: str = "body"
    timeout: int = 30000  # ms

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
