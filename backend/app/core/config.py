from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import json

_PREDEFINED_ZONES_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "predefined_zones.json"
)


class Settings(BaseSettings):
    # Runtime mode
    app_mode: str = "prod"
    enable_startup_seed: bool = False
    enable_demo_routes: bool = False
    enable_predefined_zones: bool = True
    predefined_zones_json: str = "[]"

    # Copernicus credentials (optional for demo mode)
    copernicus_username: str = ""
    copernicus_password: str = ""

    # MongoDB (required — must be a real connection string)
    mongodb_uri: str = ""
    db_name: str = "foresence"

    # Cloudflare R2 (optional — falls back to local static files)
    cloudflare_r2_access_key: str = "demo"
    cloudflare_r2_secret_key: str = "demo"
    cloudflare_r2_bucket_name: str = "foresence-images"
    cloudflare_r2_endpoint: str = "https://demo.r2.cloudflarestorage.com"
    cloudflare_r2_public_url: str = "https://demo.r2.dev"

    # Redis (optional — falls back to in-memory locks)
    upstash_redis_url: str = ""

    # SendGrid (optional — emails skipped if not set)
    sendgrid_api_key: str = "SG.demo"
    alert_from_email: str = "demo@demo.com"

    # Scan config
    scan_interval_hours: int = 12
    ndvi_drop_threshold: float = 0.15
    confidence_threshold: float = 0.70

    # CORS
    cors_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5173"

    @field_validator("app_mode")
    @classmethod
    def validate_app_mode(cls, v: str) -> str:
        value = v.strip().lower()
        if value not in {"prod", "demo"}:
            raise ValueError("app_mode must be either 'prod' or 'demo'")
        return value

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def predefined_zones(self) -> List[dict]:
        """Load zones from app/data/predefined_zones.json, else from PREDEFINED_ZONES_JSON env."""
        if _PREDEFINED_ZONES_FILE.is_file():
            try:
                with open(_PREDEFINED_ZONES_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    return data
            except Exception:
                pass
        try:
            data = json.loads(self.predefined_zones_json or "[]")
            return data if isinstance(data, list) else []
        except Exception:
            return []

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
