from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.auth import AuthEmailChallenge, AuthSession, User
from app.services.mailer import MailDeliveryError, send_text_email

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 310000
PURPOSE_SIGNUP = "signup"
PURPOSE_RESET = "reset_password"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(value: str) -> str:
    email = (value or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="邮箱不能为空")
    if len(email) > 320 or not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    return email


def validate_password_strength(
    password: str, settings: Optional[Settings] = None
) -> str:
    cfg = settings or get_settings()
    raw = password or ""
    if len(raw) < cfg.auth_password_min_length:
        raise HTTPException(
            status_code=400,
            detail="密码至少需要 %s 位" % cfg.auth_password_min_length,
        )
    return raw


def _derive_password_key(password: str, salt_hex: str, iterations: int) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        iterations,
    )
    return derived.hex()


def hash_password(password: str) -> str:
    salt_hex = secrets.token_hex(16)
    derived_hex = _derive_password_key(password, salt_hex, PASSWORD_ITERATIONS)
    return "%s$%s$%s$%s" % (
        PASSWORD_SCHEME,
        PASSWORD_ITERATIONS,
        salt_hex,
        derived_hex,
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations_raw, salt_hex, expected_hex = password_hash.split("$", 3)
        iterations = int(iterations_raw)
    except (AttributeError, TypeError, ValueError):
        return False
    if scheme != PASSWORD_SCHEME:
        return False
    actual_hex = _derive_password_key(password, salt_hex, iterations)
    return hmac.compare_digest(actual_hex, expected_hex)


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_code() -> str:
    return "%06d" % secrets.randbelow(1000000)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
    }


def set_session_cookie(
    response: Response, token: str, settings: Optional[Settings] = None
) -> None:
    cfg = settings or get_settings()
    max_age = int(cfg.auth_session_ttl_hours) * 3600
    response.set_cookie(
        key=cfg.auth_session_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=cfg.auth_session_cookie_secure,
        path="/",
    )


def clear_session_cookie(
    response: Response, settings: Optional[Settings] = None
) -> None:
    cfg = settings or get_settings()
    response.delete_cookie(
        key=cfg.auth_session_cookie_name,
        httponly=True,
        samesite="lax",
        secure=cfg.auth_session_cookie_secure,
        path="/",
    )


def create_login_session(
    db: Session,
    *,
    user: User,
    request: Request,
    response: Response,
    settings: Optional[Settings] = None,
) -> AuthSession:
    cfg = settings or get_settings()
    now = utc_now()
    token = generate_token()
    row = AuthSession(
        user_id=user.id,
        session_token_hash=hash_secret(token),
        expires_at=now + timedelta(hours=cfg.auth_session_ttl_hours),
        last_seen_at=now,
        user_agent=(request.headers.get("user-agent") or "")[:1000] or None,
        ip_addr=request.client.host if request.client else None,
    )
    db.add(row)
    set_session_cookie(response, token, cfg)
    return row


def revoke_session(row: AuthSession) -> None:
    if row.revoked_at is None:
        row.revoked_at = utc_now()


def revoke_all_user_sessions(db: Session, user_id) -> None:
    now = utc_now()
    sessions = (
        db.query(AuthSession)
        .filter(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        .all()
    )
    for row in sessions:
        row.revoked_at = now


def send_email_code(
    db: Session,
    *,
    email: str,
    purpose: str,
    settings: Optional[Settings] = None,
) -> None:
    cfg = settings or get_settings()
    now = utc_now()
    active = (
        db.query(AuthEmailChallenge)
        .filter(
            AuthEmailChallenge.email == email,
            AuthEmailChallenge.purpose == purpose,
            AuthEmailChallenge.consumed_at.is_(None),
        )
        .order_by(AuthEmailChallenge.created_at.desc())
        .first()
    )
    if active and active.last_sent_at:
        delta = (now - active.last_sent_at).total_seconds()
        if delta < cfg.auth_code_resend_seconds:
            wait_seconds = int(cfg.auth_code_resend_seconds - delta)
            raise HTTPException(
                status_code=429,
                detail="验证码发送过于频繁，请 %s 秒后重试" % wait_seconds,
            )
    if active and active.consumed_at is None:
        active.consumed_at = now

    code = generate_code()
    challenge = AuthEmailChallenge(
        email=email,
        purpose=purpose,
        code_hash=hash_secret(code),
        verified_token_hash=None,
        expires_at=now + timedelta(minutes=cfg.auth_code_ttl_minutes),
        consumed_at=None,
        attempt_count=0,
        send_count=1,
        last_sent_at=now,
    )
    db.add(challenge)
    db.flush()

    action = "注册" if purpose == PURPOSE_SIGNUP else "重置密码"
    body = (
        "您好，\n\n"
        "您正在进行 TeachSim %s。\n"
        "本次验证码：%s\n"
        "有效时间：%s 分钟。\n"
        "如果不是您本人操作，请忽略这封邮件。\n"
    ) % (action, code, cfg.auth_code_ttl_minutes)
    try:
        send_text_email(
            to_email=email,
            subject="TeachSim 验证码",
            body=body,
            settings=cfg,
        )
    except MailDeliveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def verify_email_code(
    db: Session,
    *,
    email: str,
    purpose: str,
    code: str,
    settings: Optional[Settings] = None,
) -> Tuple[str, int]:
    cfg = settings or get_settings()
    now = utc_now()
    challenge = (
        db.query(AuthEmailChallenge)
        .filter(
            AuthEmailChallenge.email == email,
            AuthEmailChallenge.purpose == purpose,
            AuthEmailChallenge.consumed_at.is_(None),
        )
        .order_by(AuthEmailChallenge.created_at.desc())
        .first()
    )
    if challenge is None or challenge.code_hash is None:
        raise HTTPException(status_code=400, detail="验证码无效")
    if challenge.expires_at <= now:
        challenge.consumed_at = now
        raise HTTPException(status_code=400, detail="验证码已过期")
    if challenge.attempt_count >= cfg.auth_code_max_attempts:
        challenge.consumed_at = now
        raise HTTPException(status_code=400, detail="验证码尝试次数过多，请重新获取")

    if not hmac.compare_digest(challenge.code_hash, hash_secret(code)):
        challenge.attempt_count += 1
        if challenge.attempt_count >= cfg.auth_code_max_attempts:
            challenge.consumed_at = now
        raise HTTPException(status_code=400, detail="验证码错误")

    verification_token = generate_token()
    challenge.code_hash = None
    challenge.verified_token_hash = hash_secret(verification_token)
    ttl = int(max((challenge.expires_at - now).total_seconds(), 0))
    return verification_token, ttl


def consume_verification_token(
    db: Session,
    *,
    email: str,
    purpose: str,
    verification_token: str,
) -> AuthEmailChallenge:
    now = utc_now()
    challenge = (
        db.query(AuthEmailChallenge)
        .filter(
            AuthEmailChallenge.email == email,
            AuthEmailChallenge.purpose == purpose,
            AuthEmailChallenge.consumed_at.is_(None),
            AuthEmailChallenge.verified_token_hash
            == hash_secret(verification_token),
        )
        .order_by(AuthEmailChallenge.created_at.desc())
        .first()
    )
    if challenge is None:
        raise HTTPException(status_code=400, detail="verification_token 无效")
    if challenge.expires_at <= now:
        challenge.consumed_at = now
        raise HTTPException(status_code=400, detail="verification_token 已过期")
    challenge.consumed_at = now
    return challenge
