from __future__ import annotations

from fastapi import Header, HTTPException


def get_current_teacher_id(
    x_teacher_id: str | None = Header(default=None, alias="X-Teacher-Id"),
) -> str:
    teacher_id = (x_teacher_id or "").strip()
    if not teacher_id:
        raise HTTPException(status_code=401, detail="缺少教师身份，请重新登录")
    return teacher_id

