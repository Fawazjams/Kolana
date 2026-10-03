import os

os.environ["JWT_SECRET"] = "test-secret-key-0123456789-abcdefghij"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test"

import jwt as pyjwt  # noqa: E402
import pytest  # noqa: E402
from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import config  # noqa: E402
import jwt_auth  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_settings():
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture()
def app_client(monkeypatch):
    """Real app, with startup hooks (Mongo, InsightFace, Gemini) stubbed out."""
    import main

    async def _noop():
        return None

    monkeypatch.setattr(main, "connect_db", _noop)
    monkeypatch.setattr(main, "close_db", _noop)
    monkeypatch.setattr(main, "load_model", lambda: None)
    monkeypatch.setattr(main, "load_gemini", lambda: None)
    with TestClient(main.app) as c:
        yield c


def test_health(app_client):
    r = app_client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_token_endpoint_issues_valid_jwt(app_client):
    r = app_client.post("/api/v1/auth/token", json={"wallet": "WalletABC"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    claims = pyjwt.decode(body["access_token"], "test-secret-key-0123456789-abcdefghij", algorithms=["HS256"])
    assert claims["sub"] == "WalletABC"


def test_token_endpoint_rejects_blank_wallet(app_client):
    assert app_client.post("/api/v1/auth/token", json={"wallet": "  "}).status_code == 422


def _guarded_app() -> TestClient:
    app = FastAPI()

    @app.get("/secret")
    async def secret(wallet=Depends(jwt_auth.require_auth)):
        return {"wallet": wallet}

    return TestClient(app)


def test_enforced_auth_blocks_missing_and_bad_tokens(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    c = _guarded_app()
    assert c.get("/secret").status_code == 401
    assert c.get("/secret", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_enforced_auth_accepts_valid_token(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    token, _ = jwt_auth.create_access_token("WalletXYZ")
    r = _guarded_app().get("/secret", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json() == {"wallet": "WalletXYZ"}


def test_expired_token_is_rejected(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    expired = pyjwt.encode({"sub": "w", "exp": 1}, "test-secret-key-0123456789-abcdefghij", algorithm="HS256")
    r = _guarded_app().get("/secret", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_auth_not_enforced_by_default():
    assert _guarded_app().get("/secret").json() == {"wallet": None}
