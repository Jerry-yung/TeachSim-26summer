from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthContext, get_current_auth
from app.core.config import get_settings
from app.db.session import get_db
from app.models.auth import User
from app.schemas.auth import (
    EmailOnlyRequest,
    LoginRequest,
    OkMessage,
    PasswordResetCompleteRequest,
    RegisterCompleteRequest,
    UserEnvelope,
    VerificationEnvelope,
    VerifyCodeRequest,
)
from app.services.auth import (
    PURPOSE_RESET,
    PURPOSE_SIGNUP,
    clear_session_cookie,
    consume_verification_token,
    create_login_session,
    hash_password,
    normalize_email,
    revoke_all_user_sessions,
    revoke_session,
    send_email_code,
    user_payload,
    utc_now,
    validate_password_strength,
    verify_email_code,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/send-code", response_model=OkMessage)
def register_send_code(
    body: EmailOnlyRequest,
    db: Session = Depends(get_db),
) -> OkMessage:
    email = normalize_email(body.email)
    exists = db.query(User.id).filter(User.email == email).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="该邮箱已注册")

    send_email_code(db, email=email, purpose=PURPOSE_SIGNUP)
    db.commit()
    return OkMessage(message="验证码已发送")


@router.post("/register/verify-code", response_model=VerificationEnvelope)
def register_verify_code(
    body: VerifyCodeRequest,
    db: Session = Depends(get_db),
) -> VerificationEnvelope:
    email = normalize_email(body.email)
    exists = db.query(User.id).filter(User.email == email).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="该邮箱已注册")

    try:
        token, expires_in = verify_email_code(
            db,
            email=email,
            purpose=PURPOSE_SIGNUP,
            code=body.code,
        )
    except HTTPException:
        db.commit()
        raise
    db.commit()
    return VerificationEnvelope(verification_token=token, expires_in=expires_in)


@router.post("/register/complete", response_model=UserEnvelope)
def register_complete(
    body: RegisterCompleteRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> UserEnvelope:
    email = normalize_email(body.email)
    validate_password_strength(body.password, get_settings())
    exists = db.query(User.id).filter(User.email == email).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="该邮箱已注册")

    try:
        consume_verification_token(
            db,
            email=email,
            purpose=PURPOSE_SIGNUP,
            verification_token=body.verification_token,
        )
    except HTTPException:
        db.commit()
        raise

    user = User(
        email=email,
        display_name=body.display_name.strip(),
        role="实习教师",
        password_hash=hash_password(body.password),
        email_verified_at=utc_now(),
        is_active=True,
    )
    db.add(user)
    db.flush()
    create_login_session(db, user=user, request=request, response=response)
    db.commit()
    return UserEnvelope(user=user_payload(user))


@router.post("/login", response_model=UserEnvelope)
def login(
    body: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> UserEnvelope:
    email = normalize_email(body.email)
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    create_login_session(db, user=user, request=request, response=response)
    db.commit()
    return UserEnvelope(user=user_payload(user))


@router.post("/logout", response_model=OkMessage)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> OkMessage:
    revoke_session(auth.auth_session)
    clear_session_cookie(response)
    db.commit()
    return OkMessage(message="已退出登录")


@router.get("/me", response_model=UserEnvelope)
def me(auth: AuthContext = Depends(get_current_auth)) -> UserEnvelope:
    return UserEnvelope(user=user_payload(auth.user))


@router.post("/password-reset/send-code", response_model=OkMessage)
def password_reset_send_code(
    body: EmailOnlyRequest,
    db: Session = Depends(get_db),
) -> OkMessage:
    email = normalize_email(body.email)
    user = db.query(User.id).filter(User.email == email, User.is_active.is_(True)).first()
    if user is not None:
        send_email_code(db, email=email, purpose=PURPOSE_RESET)
        db.commit()
    return OkMessage(message="如果邮箱已注册，验证码会尽快发送")


@router.post("/password-reset/verify-code", response_model=VerificationEnvelope)
def password_reset_verify_code(
    body: VerifyCodeRequest,
    db: Session = Depends(get_db),
) -> VerificationEnvelope:
    email = normalize_email(body.email)
    try:
        token, expires_in = verify_email_code(
            db,
            email=email,
            purpose=PURPOSE_RESET,
            code=body.code,
        )
    except HTTPException:
        db.commit()
        raise
    db.commit()
    return VerificationEnvelope(verification_token=token, expires_in=expires_in)


@router.post("/password-reset/complete", response_model=UserEnvelope)
def password_reset_complete(
    body: PasswordResetCompleteRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> UserEnvelope:
    email = normalize_email(body.email)
    validate_password_strength(body.new_password, get_settings())
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=400, detail="verification_token 无效")

    try:
        consume_verification_token(
            db,
            email=email,
            purpose=PURPOSE_RESET,
            verification_token=body.verification_token,
        )
    except HTTPException:
        db.commit()
        raise

    user.password_hash = hash_password(body.new_password)
    user.email_verified_at = user.email_verified_at or utc_now()
    revoke_all_user_sessions(db, user.id)
    create_login_session(db, user=user, request=request, response=response)
    db.commit()
    return UserEnvelope(user=user_payload(user))
