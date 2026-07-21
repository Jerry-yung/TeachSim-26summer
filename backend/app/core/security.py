from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

_PWD_CTX = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"
_EXPIRE_DAYS = 30


def hash_password(plain: str) -> str:
    return _PWD_CTX.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _PWD_CTX.verify(plain, hashed)


def create_access_token(data: dict[str, Any]) -> str:
    from app.core.config import get_settings

    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS)
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    from app.core.config import get_settings

    return jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGORITHM])
