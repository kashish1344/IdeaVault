from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file so it works regardless of CWD
# (config.py lives at backend/app/core/config.py → project root .env)
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",   # ignore unknown keys like OLLAMA_BASE_URL, OUTPUT_DIR
    )

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    secret_key: str = "dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # Database
    database_url: str = "postgresql+asyncpg://ideavault:password@localhost:5432/ideavault"
    sync_database_url: str = "postgresql+psycopg://ideavault:password@localhost:5432/ideavault"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "ideavault"
    minio_secure: bool = False

    # Rate limiting
    rate_limit_tokens: float = 10.0
    rate_limit_refill_rate: float = 1.0
    rate_limit_capacity: float = 20.0

    # Cache
    lru_cache_capacity: int = 512
    bloom_filter_capacity: int = 100_000
    bloom_filter_error_rate: float = 0.01

    # Generation
    default_image_model: str = "black-forest-labs/flux-schnell"
    default_video_model: str = "wan-video/wan2.1-t2v-480p"
    max_concurrent_jobs: int = 4
    job_timeout_seconds: int = 300

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
