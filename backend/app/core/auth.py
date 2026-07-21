from __future__ import annotations

from fastapi import Header, HTTPException
from jose import JWTError


def get_current_teacher_id(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_teacher_id: str | None = Header(default=None, alias="X-Teacher-Id"),
) -> str:
    """Extract teacher_id from JWT Bearer token (primary) or X-Teacher-Id header (fallback)."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if token:
            try:
                from app.core.security import decode_token

                payload = decode_token(token)
                teacher_id = str(payload.get("sub", "")).strip()
                if teacher_id:
                    return teacher_id
            except JWTError:
                raise HTTPException(
                    status_code=401, detail="无效的登录凭证，请重新登录"
                )

    # Fallback: plain X-Teacher-Id header (backward compatibility)
    teacher_id = (x_teacher_id or "").strip()
    if not teacher_id:
        raise HTTPException(status_code=401, detail="缺少教师身份，请重新登录")
    return teacher_id
