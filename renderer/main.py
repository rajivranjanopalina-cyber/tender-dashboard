from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from render import render_url

app = FastAPI(title="Playwright Renderer")


class RenderRequest(BaseModel):
    url: str
    wait_for: str = "body"
    timeout: int = 30000  # ms


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/render")
async def render(req: RenderRequest):
    try:
        html = await render_url(req.url, req.wait_for, req.timeout)
        return {"html": html}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
