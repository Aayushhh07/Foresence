from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os


class Settings(BaseSettings):
    # Copernicus credentials
    copernicus_username: str
    copernicus_password: str

    # MongoDB
    mongodb_uri: str
    db_name: str = "foresence"

    # Cloudflare R2
    cloudflare_r2_access_key: str
    cloudflare_r2_secret_key: str
    cloudflare_r2_bucket_name: str = "foresence-images"
    cloudflare_r2_endpoint: str
    cloudflare_r2_public_url: str

    # Redis
    upstash_redis_url: str

    # SendGrid
    sendgrid_api_key: str
    alert_from_email: str

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
