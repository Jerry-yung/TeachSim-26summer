from __future__ import annotations

import random
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.session import session_scope
from app.models.session_student import SessionStudent

# 固定学生名单（与前端 ClassroomView.vue 对齐）
STUDENT_ROSTER = [
    {"student_id": "student_xm", "student_name": "小明"},
    {"student_id": "student_xw", "student_name": "小闻"},
    {"student_id": "student_xw2", "student_name": "小王"},
    {"student_id": "student_xl", "student_name": "小乐"},
]

# 班级类型 → 学优 / 杠精 / 学困 权重
CLASS_LEVEL_WEIGHTS = {
    "重点班": {"xueyou": 0.60, "gangjing": 0.30, "xuekun": 0.10},
    "普通班": {"xueyou": 0.20, "gangjing": 0.10, "xuekun": 0.70},
    "平行班": {"xueyou": 0.30, "gangjing": 0.20, "xuekun": 0.50},
}

STUDENT_TYPES = ["xueyou", "gangjing", "xuekun"]


def initialize_session_students(
    session_id: uuid.UUID,
    class_level: str,
    db: Session | None = None,
) -> List[SessionStudent]:
    """根据班级类型随机分配学生类型，并写入数据库。"""
    weights_map = CLASS_LEVEL_WEIGHTS.get(class_level)
    if weights_map is None:
        # 默认平行班
        weights_map = CLASS_LEVEL_WEIGHTS["平行班"]

    weights = [weights_map[t] for t in STUDENT_TYPES]
    rng = random.Random(str(session_id))

    assigned_types = rng.choices(STUDENT_TYPES, weights=weights, k=len(STUDENT_ROSTER))

    def _create() -> List[SessionStudent]:
        with session_scope() as s:
            records = []
            for roster, stype in zip(STUDENT_ROSTER, assigned_types):
                rec = SessionStudent(
                    session_id=session_id,
                    student_id=roster["student_id"],
                    student_name=roster["student_name"],
                    student_type=stype,
                    is_hand_raised=False,
                    is_sleeping=False,
                    is_whispering=False,
                )
                s.add(rec)
                records.append(rec)
            s.flush()
            # detach 以便在 session 外使用
            for rec in records:
                s.refresh(rec)
            return records

    if db is not None:
        records = []
        for roster, stype in zip(STUDENT_ROSTER, assigned_types):
            rec = SessionStudent(
                session_id=session_id,
                student_id=roster["student_id"],
                student_name=roster["student_name"],
                student_type=stype,
                is_hand_raised=False,
                is_sleeping=False,
                is_whispering=False,
            )
            db.add(rec)
            records.append(rec)
        db.flush()
        for rec in records:
            db.refresh(rec)
        return records
    else:
        return _create()


def get_session_students(
    session_id: uuid.UUID,
    db: Session,
) -> List[SessionStudent]:
    return (
        db.query(SessionStudent)
        .filter(SessionStudent.session_id == session_id)
        .order_by(SessionStudent.student_id)
        .all()
    )


def get_session_student(
    session_id: uuid.UUID,
    student_id: str,
    db: Session,
) -> SessionStudent | None:
    return (
        db.query(SessionStudent)
        .filter(
            SessionStudent.session_id == session_id,
            SessionStudent.student_id == student_id,
        )
        .first()
    )


def reset_hand_raised(session_id: uuid.UUID, db: Session) -> None:
    db.query(SessionStudent).filter(
        SessionStudent.session_id == session_id,
        SessionStudent.is_hand_raised.is_(True),
    ).update({"is_hand_raised": False}, synchronize_session="fetch")


def set_hand_raised(
    session_id: uuid.UUID,
    student_ids: List[str],
    db: Session,
) -> None:
    if not student_ids:
        return
    db.query(SessionStudent).filter(
        SessionStudent.session_id == session_id,
        SessionStudent.student_id.in_(student_ids),
    ).update({"is_hand_raised": True}, synchronize_session="fetch")


def update_discipline_state(
    session_id: uuid.UUID,
    student_id: str,
    action: str,
    db: Session,
) -> SessionStudent | None:
    """更新纪律状态。

    action: whisper | sleep | start_whisper | start_sleep | cancel_whisper | cancel_sleep
    """
    student = get_session_student(session_id, student_id, db)
    if student is None:
        return None

    if action in ("start_whisper", "whisper"):
        student.is_whispering = True
        student.is_sleeping = False
    elif action in ("start_sleep", "sleep"):
        student.is_sleeping = True
        student.is_whispering = False
    elif action == "cancel_whisper":
        student.is_whispering = False
    elif action == "cancel_sleep":
        student.is_sleeping = False
    elif action == "cancel_all":
        student.is_whispering = False
        student.is_sleeping = False

    return student


def pick_random_students_by_type(
    session_id: uuid.UUID,
    student_type: str,
    count: int,
    db: Session,
    exclude_ids: Optional[List[str]] = None,
) -> List[SessionStudent]:
    """按类型随机挑选指定数量的学生。"""
    query = (
        db.query(SessionStudent)
        .filter(
            SessionStudent.session_id == session_id,
            SessionStudent.student_type == student_type,
            # 互斥：睡觉/交头接耳不参与新一轮挑选
            SessionStudent.is_sleeping.is_(False),
            SessionStudent.is_whispering.is_(False),
        )
    )
    if exclude_ids:
        query = query.filter(SessionStudent.student_id.notin_(exclude_ids))

    candidates = query.all()
    if not candidates:
        return []

    rng = random.Random(str(session_id) + student_type)
    if len(candidates) <= count:
        return candidates

    rng.shuffle(candidates)
    return candidates[:count]


def build_student_states_digest(
    session_students: List[SessionStudent],
) -> List[dict]:
    """构造前端/AI 消费的状态摘要。"""
    return [
        {
            "student_id": s.student_id,
            "student_type": s.student_type,
            "is_hand_raised": s.is_hand_raised,
        }
        for s in session_students
    ]


def build_called_student_digest(
    session_id: uuid.UUID,
    called_student_id: str,
    db: Session,
) -> dict | None:
    """构造 AI Supervisor 期望的 called_student_status_digest。"""
    student = get_session_student(session_id, called_student_id, db)
    if student is None:
        return None
    return {
        "student_id": student.student_id,
        "student_name": student.student_name,
        "student_type": student.student_type,
    }
