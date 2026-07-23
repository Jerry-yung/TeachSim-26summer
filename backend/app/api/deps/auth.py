from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.auth import AuthSession, User
from app.services.auth import hash_secret, utc_now


@dataclass
class AuthContext:
    user: User
    auth_session: AuthSession


def get_current_auth(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthContext:
    settings = get_settings()
    raw_token = request.cookies.get(settings.auth_session_cookie_name)
    if not raw_token:
        raise HTTPException(status_code=401, detail="未登录")

    session_row = (
        db.query(AuthSession)
        .join(User, User.id == AuthSession.user_id)
        .filter(
            AuthSession.session_token_hash == hash_secret(raw_token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utc_now(),
            User.is_active.is_(True),
        )
        .first()
    )
    if session_row is None:
        raise HTTPException(status_code=401, detail="登录态已失效")

    return AuthContext(user=session_row.user, auth_session=session_row)


def get_current_user(ctx: AuthContext = Depends(get_current_auth)) -> User:
    return ctx.user
