from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017/kolana"
    gemini_api_key: str = ""
    elevenlabs_api_key: str = ""
    coingecko_api_url: str = "https://api.coingecko.com/api/v3"
    insightface_model: str = "buffalo_l"
    port: int = 8000
    # JWT auth. Set JWT_SECRET to enable /auth/token; AUTH_REQUIRED=true enforces it.
    jwt_secret: str = ""
    jwt_expire_minutes: int = 60
    auth_required: bool = False
    solana_rpc_url: str = "https://api.devnet.solana.com"
    solana_cluster: str = "devnet"
    # Upstream backend that has heavy deps (InsightFace, etc.).
    # If set, recognize/voice/contacts/payments calls are proxied there.
    upstream_api_base: str = "http://134.209.216.232:8000/api/v1"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
