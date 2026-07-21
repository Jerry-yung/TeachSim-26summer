from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

_ALGORITHM = "HS256"
_EXPIRE_DAYS = 30
_PASSWORD_SCHEME = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 310000


def _derive_password_key(plain: str, salt_hex: str, iterations: int) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        plain.encode("utf-8"),
        bytes.fromhex(salt_hex),
        iterations,
    )
    return derived.hex()


def hash_password(plain: str) -> str:
    salt_hex = secrets.token_hex(16)
    derived_hex = _derive_password_key(plain, salt_hex, _PASSWORD_ITERATIONS)
    return f"{_PASSWORD_SCHEME}${_PASSWORD_ITERATIONS}${salt_hex}${derived_hex}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        scheme, iterations_raw, salt_hex, expected_hex = hashed.split("$", 3)
        iterations = int(iterations_raw)
    except (AttributeError, TypeError, ValueError):
        return False
    if scheme != _PASSWORD_SCHEME:
        return False
    actual_hex = _derive_password_key(plain, salt_hex, iterations)
    return hmac.compare_digest(actual_hex, expected_hex)


def create_access_token(data: dict[str, Any]) -> str:
    from app.core.config import get_settings

    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS)
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    from app.core.config import get_settings

    return jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGORITHM])
