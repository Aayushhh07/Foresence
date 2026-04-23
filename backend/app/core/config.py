from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os


class Settings(BaseSettings):
    # Copernicus credentials (optional for demo mode)
    copernicus_username: str = "demo"
    copernicus_password: str = "demo"

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

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
