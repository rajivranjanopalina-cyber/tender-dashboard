from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.auth import verify_password, create_jwt

router = APIRouter()


class LoginRequest(BaseModel):
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    token: str


@router.post("/auth", response_model=LoginResponse)
def login(data: LoginRequest):
    if not verify_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_jwt(remember_me=data.remember_me)
    return LoginResponse(token=token)
