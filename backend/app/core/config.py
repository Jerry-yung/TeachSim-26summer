from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 根目录 .env（backend/app/core/config.py 向上三级到项目根）
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ROOT_ENV),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_host: Optional[str] = None
    postgres_port: int = 5432
    postgres_db: str = "postgres"
    postgres_sslmode: str = "require"

    upload_dir: str = "uploads"
    ai_service_url: str = "http://localhost:8001"
    ai_timeout_s: float = 30.0

    asr_provider: str = "volcengine"
    # 火山豆包语音极速版 flash —— 旧版控制台：APP ID + Access Token
    volc_asr_app_id: str = ""
    volc_asr_access_token: str = ""
    volc_asr_resource_id: str = "volc.bigasr.auc_turbo"
    # httpx 默认 trust_env=True 会读系统/环境代理；Windows 上错误代理常导致 ConnectError
    # 设为 true 仅在需要走 HTTP(S)_PROXY 或系统代理时
    volc_http_trust_env: bool = False

    asr_debug_persist: bool = True

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            url = self.database_url
            if url.startswith("postgresql://"):
                url = "postgresql+psycopg://" + url[len("postgresql://") :]
            elif not url.startswith("postgresql+psycopg://"):
                url = "postgresql+psycopg://" + url
            if "sslmode=" not in url:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}sslmode={self.postgres_sslmode}"
            return url
        if not (
            self.postgres_user and self.postgres_password and self.postgres_host
        ):
            raise ValueError(
                "Set DATABASE_URL or POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST in .env"
            )
        pwd = quote_plus(self.postgres_password or "")
        user = self.postgres_user or ""
        host = self.postgres_host or ""
        return (
            f"postgresql+psycopg://{user}:{pwd}@{host}:"
            f"{self.postgres_port}/{self.postgres_db}"
            f"?sslmode={self.postgres_sslmode}"
        )

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
