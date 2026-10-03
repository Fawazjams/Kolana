"""JWT auth: token issuing plus a FastAPI dependency that enforces it.

Enforcement is controlled by AUTH_REQUIRED (default false) so existing clients keep
working while they migrate to sending Bearer tokens.
"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_settings

_bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


def create_access_token(wallet: str) -> tuple[str, int]:
    settings = get_settings()
    expires = timedelta(minutes=settings.jwt_expire_minutes)
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": wallet, "iat": now, "exp": now + expires},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )
    return token, int(expires.total_seconds())


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return payload["sub"]


async def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str | None:
    """Returns the authenticated wallet, or None when auth is not enforced."""
    if not get_settings().auth_required:
        return None
    if creds is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(creds.credentials)
