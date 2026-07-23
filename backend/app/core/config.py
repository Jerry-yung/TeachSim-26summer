from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 根目录 .env（backend/app/core/config.py 向上三级到项目根）
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"

# JWT 密钥强度要求
_JWT_SECRET_MIN_LENGTH = 32
_JWT_SECRET_DEFAULT = "change-me-in-production-use-a-long-random-string"
# 常见弱密钥（开发占位符 / 教程默认值），出现即视为未配置
_JWT_SECRET_WEAK_VALUES = frozenset({
    _JWT_SECRET_DEFAULT,
    "your-secret-key-here",
    "secret",
    "changeme",
    "change-me",
    "test",
    "",
})


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

    jwt_secret: str = "change-me-in-production-use-a-long-random-string"
    # 显式允许使用弱/默认 JWT 密钥（仅供测试或显式开发模式）。
    # 生产环境必须保持 false（默认），否则启动会因密钥强度不足而失败。
    jwt_secret_allow_insecure: bool = False

    upload_dir: str = "uploads"
    ai_service_url: str = "http://localhost:8001"
    ai_timeout_s: float = 30.0
    smtp_host: str = "smtp.163.com"
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_ssl: bool = True
    auth_session_cookie_name: str = "teachsim_session"
    auth_session_ttl_hours: int = 24 * 7
    auth_session_cookie_secure: bool = False
    auth_code_ttl_minutes: int = 10
    auth_code_resend_seconds: int = 60
    auth_code_max_attempts: int = 5
    auth_password_min_length: int = 8

    asr_provider: str = "volcengine"
    # 火山豆包语音极速版 flash —— 旧版控制台：APP ID + Access Token
    volc_asr_app_id: str = ""
    volc_asr_access_token: str = ""
    volc_asr_resource_id: str = "volc.bigasr.auc_turbo"
    # httpx 默认 trust_env=True 会读系统/环境代理；Windows 上错误代理常导致 ConnectError
    # 设为 true 仅在需要走 HTTP(S)_PROXY 或系统代理时
    volc_http_trust_env: bool = False

    # 讯飞 ASR（前端实时听写）— 后端独占密钥，通过 /api/asr/xfyun/sign
    # 接口签发临时 WebSocket URL 给前端，避免密钥被打进客户端 bundle。
    # APP_ID 是公开标识（讯飞控制台的"应用 ID"），可以暴露；
    # API_KEY / API_SECRET 是签名密钥，绝不能暴露。
    xfyun_app_id: str = ""
    xfyun_api_key: str = ""
    xfyun_api_secret: str = ""

    asr_debug_persist: bool = True

    # MiniMax T2A（课中学生语音，后端短连接 WebSocket 代理）
    minimax_api_key: str = ""
    minimax_t2a_ws_url: str = "wss://api.minimaxi.com/ws/v1/t2a_v2"
    minimax_t2a_model: str = "speech-2.6-turbo"
    minimax_t2a_timeout_s: float = 45.0

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

    @model_validator(mode="after")
    def _validate_jwt_secret(self) -> "Settings":
        """
        强制启动期校验 JWT 密钥强度。
        失败立即抛 RuntimeError，避免使用弱密钥裸奔（任意人可伪造 token 冒充用户）。

        要求：
        - 不能是常见的占位符（"change-me-..." / "your-secret-key-here" 等）
        - 长度至少 32 字符（HMAC-SHA256 推荐熵下限）

        逃生通道：测试或显式开发模式可设 jwt_secret_allow_insecure=true 跳过校验。
        """
        if self.jwt_secret_allow_insecure:
            return self
        secret = (self.jwt_secret or "").strip()
        if secret in _JWT_SECRET_WEAK_VALUES:
            raise RuntimeError(
                "JWT_SECRET 仍为占位/默认值，启动已拒绝以避免 token 伪造风险。\n"
                "请在 .env 中设置一个长随机串，例如：\n"
                "  python -c \"import secrets; print(secrets.token_urlsafe(48))\"\n"
                "然后写入：JWT_SECRET=<生成的字符串>\n"
                "（仅本地测试可临时设置 JWT_SECRET_ALLOW_INSECURE=true 跳过此校验）"
            )
        if len(secret) < _JWT_SECRET_MIN_LENGTH:
            raise RuntimeError(
                f"JWT_SECRET 长度不足 {_JWT_SECRET_MIN_LENGTH} 字符（当前 {len(secret)}），"
                "启动已拒绝。HMAC-SHA256 推荐至少 32 字节熵，建议用 "
                "`python -c \"import secrets; print(secrets.token_urlsafe(48))\"` 生成。"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
