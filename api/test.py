from fastapi import FastAPI

test_app = FastAPI()

@test_app.get("/api/test")
def test():
    return {"status": "ok", "message": "FastAPI works on Vercel"}

app = test_app
