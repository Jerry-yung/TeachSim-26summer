"""
回归测试：JWT 密钥启动期校验。

为什么这样测：
- Settings 通过 pydantic-settings 自动读取环境变量与 .env，
  本测试文件用 monkeypatch 显式覆写环境变量后**直接实例化 Settings**
  （不走 get_settings() 的 lru_cache，避免污染其他测试）。
- 校验失败应抛 RuntimeError，且消息含可操作指引。
- 不需要导入 routes / FastAPI，避开 Python 3.10+ 语法依赖（同 PR #1 做法）。
"""

from __future__ import annotations

import os
from typing import Iterator

import pytest
from pydantic import ValidationError

from app.core.config import (
    Settings,
    _JWT_SECRET_DEFAULT,
    _JWT_SECRET_MIN_LENGTH,
    _JWT_SECRET_WEAK_VALUES,
)


# ---------- helpers ----------

_STRONG_SECRET = "x" * _JWT_SECRET_MIN_LENGTH  # 32 字符强密钥（用于 happy path）


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """清掉所有可能污染 Settings 的环境变量，让每个测试从干净状态出发。"""
    for key in list(os.environ.keys()):
        if key.startswith(("JWT_", "POSTGRES_", "DATABASE_", "VITE_")):
            monkeypatch.delenv(key, raising=False)
    # Settings 必须能拿到一个 DATABASE_URL 来通过其他校验
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    # 关键：禁用 .env 文件读取，避免本机 .env 注入干扰
    monkeypatch.setenv("PYDANTIC_SETTINGS_DISABLE_ENV_FILE", "1")
    yield


def _make_settings(**overrides) -> Settings:
    """直接构造 Settings，绕开 lru_cache。"""
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


# ---------- tests ----------

def test_default_secret_rejected(clean_env):
    """默认占位符必须导致启动失败 —— 这是本 PR 的核心契约。"""
    with pytest.raises((RuntimeError, ValidationError)) as exc_info:
        _make_settings(jwt_secret=_JWT_SECRET_DEFAULT)
    assert "JWT_SECRET" in str(exc_info.value)


@pytest.mark.parametrize("weak", sorted(v for v in _JWT_SECRET_WEAK_VALUES if v))
def test_known_weak_values_rejected(clean_env, weak: str):
    """常见教程默认值（your-secret-key-here / secret / changeme 等）一律拒绝。"""
    with pytest.raises((RuntimeError, ValidationError)):
        _make_settings(jwt_secret=weak)


def test_empty_secret_rejected(clean_env):
    """空字符串视同未配置。"""
    with pytest.raises((RuntimeError, ValidationError)):
        _make_settings(jwt_secret="")


def test_short_secret_rejected(clean_env):
    """长度 < 32 拒绝。31 字符是边界值。"""
    short = "a" * (_JWT_SECRET_MIN_LENGTH - 1)
    with pytest.raises((RuntimeError, ValidationError)) as exc_info:
        _make_settings(jwt_secret=short)
    msg = str(exc_info.value)
    assert "长度" in msg or "length" in msg.lower()


def test_strong_secret_accepted(clean_env):
    """长度 >= 32 且非弱值 → 启动成功。"""
    s = _make_settings(jwt_secret=_STRONG_SECRET)
    assert s.jwt_secret == _STRONG_SECRET


def test_realistic_random_secret_accepted(clean_env):
    """模拟用户用 `secrets.token_urlsafe(48)` 生成的密钥。"""
    import secrets
    real = secrets.token_urlsafe(48)
    s = _make_settings(jwt_secret=real)
    assert s.jwt_secret == real


def test_allow_insecure_escape_hatch(clean_env):
    """显式开启 jwt_secret_allow_insecure 时允许弱密钥（仅供测试/本地开发）。"""
    s = _make_settings(
        jwt_secret=_JWT_SECRET_DEFAULT,
        jwt_secret_allow_insecure=True,
    )
    assert s.jwt_secret == _JWT_SECRET_DEFAULT
    assert s.jwt_secret_allow_insecure is True


def test_error_message_includes_repair_hint(clean_env):
    """错误消息必须给出生成强密钥的具体命令（可操作性）。"""
    with pytest.raises((RuntimeError, ValidationError)) as exc_info:
        _make_settings(jwt_secret=_JWT_SECRET_DEFAULT)
    msg = str(exc_info.value)
    assert "secrets.token_urlsafe" in msg, "错误消息应包含修复指引"
