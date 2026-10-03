import psutil
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import connect_db, close_db
from jwt_auth import require_auth
from services.face_service import load_model, is_model_loaded, _insightface_available
from services.gemini_service import load_gemini
from routers import (
    recognize,
    contacts,
    voice,
    payments,
    sol_price,
    transactions,
    accounts,
    debts,
    proxy,
    auth,
)
from models.schemas import HealthResponse
from config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    load_model()
    load_gemini()
    yield
    await close_db()


app = FastAPI(
    title="KOLANA API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    """Loud per-request logger so we can see exactly what the mobile is doing."""
    path = request.url.path
    # Suppress noise from the constant /incoming polling.
    quiet = path.endswith("/incoming")
    if not quiet:
        print(f"[req] {request.method} {path}  qs={dict(request.query_params)}")
    response = await call_next(request)
    if not quiet:
        print(f"[req] -> {response.status_code} {path}")
    return response

# Local-only routes (need direct MongoDB access for the Kolana ledger).
app.include_router(auth.router, prefix="/api/v1")
_protected = [Depends(require_auth)]  # enforced only when AUTH_REQUIRED=true
app.include_router(transactions.router, prefix="/api/v1", dependencies=_protected)
app.include_router(accounts.router, prefix="/api/v1", dependencies=_protected)
app.include_router(debts.router, prefix="/api/v1", dependencies=_protected)
app.include_router(sol_price.router, prefix="/api/v1")

_settings = get_settings()

# Voice is always served locally — it only needs Gemini + ElevenLabs, not InsightFace.
app.include_router(voice.router, prefix="/api/v1")

if _insightface_available:
    # Production / fully-loaded: serve face-dependent routes locally too.
    app.include_router(recognize.router, prefix="/api/v1")
    app.include_router(contacts.router, prefix="/api/v1")
    app.include_router(payments.router, prefix="/api/v1")
elif _settings.upstream_api_base:
    # Dev box (no InsightFace): forward only face-dependent endpoints to deployed backend.
    print(f"[proxy] InsightFace missing -- forwarding recognize/contacts/payments -> {_settings.upstream_api_base}")
    app.include_router(proxy.router, prefix="/api/v1")
else:
    app.include_router(recognize.router, prefix="/api/v1")
    app.include_router(contacts.router, prefix="/api/v1")
    app.include_router(payments.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health():
    mem = psutil.virtual_memory()
    return HealthResponse(
        status="ok",
        model_loaded=is_model_loaded(),
        memory_percent=mem.percent,
    )


if __name__ == "__main__":
    import uvicorn
    from config import get_settings
    settings = get_settings()
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=True)
