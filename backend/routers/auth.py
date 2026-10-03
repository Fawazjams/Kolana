from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from jwt_auth import create_access_token
from config import get_settings

router = APIRouter()


class TokenRequest(BaseModel):
    wallet: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/auth/token", response_model=TokenResponse)
async def issue_token(body: TokenRequest):
    if not get_settings().jwt_secret:
        raise HTTPException(503, "JWT_SECRET is not configured")
    if not body.wallet.strip():
        raise HTTPException(422, "wallet is required")
    token, expires_in = create_access_token(body.wallet.strip())
    return TokenResponse(access_token=token, expires_in=expires_in)
