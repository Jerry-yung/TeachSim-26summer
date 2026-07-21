from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.teacher import Teacher

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str
    name: str
    password: str
    role: str = "实习教师"

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("用户名不能为空")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码至少需要 6 位")
        return v


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    exists = db.query(Teacher).filter(Teacher.username == body.username).first()
    if exists:
        raise HTTPException(status_code=409, detail="该用户名已被注册")
    teacher = Teacher(
        username=body.username.strip(),
        name=body.name.strip() or body.username.strip(),
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(teacher)
    db.commit()
    return {"ok": True}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    teacher = (
        db.query(Teacher).filter(Teacher.username == body.username.strip()).first()
    )
    if not teacher or not verify_password(body.password, teacher.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(
        {"sub": teacher.username, "name": teacher.name, "role": teacher.role}
    )
    return {
        "token": token,
        "user": {
            "username": teacher.username,
            "name": teacher.name,
            "role": teacher.role,
        },
    }
