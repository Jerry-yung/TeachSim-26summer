from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, field_validator


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _normalize_email(value: str) -> str:
    email = (value or "").strip().lower()
    if not email:
        raise ValueError("邮箱不能为空")
    if len(email) > 320 or not EMAIL_RE.match(email):
        raise ValueError("邮箱格式不正确")
    return email


class EmailOnlyRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        return _normalize_email(value)


class VerifyCodeRequest(BaseModel):
    email: str
    code: str

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("code")
    @classmethod
    def _valid_code(cls, value: str) -> str:
        code = (value or "").strip()
        if not re.fullmatch(r"\d{6}", code):
            raise ValueError("验证码必须为 6 位数字")
        return code


class RegisterCompleteRequest(BaseModel):
    email: str
    display_name: str
    password: str
    verification_token: str

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("display_name")
    @classmethod
    def _valid_name(cls, value: str) -> str:
        name = (value or "").strip()
        if not name:
            raise ValueError("姓名不能为空")
        if len(name) > 128:
            raise ValueError("姓名过长")
        return name

    @field_validator("verification_token")
    @classmethod
    def _valid_token(cls, value: str) -> str:
        token = (value or "").strip()
        if not token:
            raise ValueError("verification_token 不能为空")
        return token


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def _valid_password(cls, value: str) -> str:
        password = (value or "").strip()
        if not password:
            raise ValueError("密码不能为空")
        return password


class PasswordResetCompleteRequest(BaseModel):
    email: str
    new_password: str
    verification_token: str

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("verification_token")
    @classmethod
    def _valid_token(cls, value: str) -> str:
        token = (value or "").strip()
        if not token:
            raise ValueError("verification_token 不能为空")
        return token


class UserPayload(BaseModel):
    id: str
    email: str
    display_name: str
    role: str


class UserEnvelope(BaseModel):
    user: UserPayload


class VerificationEnvelope(BaseModel):
    verification_token: str
    expires_in: int


class OkMessage(BaseModel):
    ok: bool = True
    message: Optional[str] = None
