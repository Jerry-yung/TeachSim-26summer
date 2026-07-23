from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.models.lesson import ClassroomSession, Lesson, SessionTurn

router = APIRouter(prefix="/history", tags=["history"])
_DECISION_LOG_PATH = (
    Path(__file__).resolve().parents[2] / "logs" / "inclass_decisions.jsonl"
)


def _parse_uuid(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="session_id 不是合法 UUID") from exc


def _owned_session_query(db: Session, current_user: User):
    return (
        db.query(ClassroomSession)
        .join(Lesson, Lesson.id == ClassroomSession.lesson_id)
        .filter(Lesson.owner_user_id == current_user.id)
    )


@router.get("/sessions")
def list_history_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    topic: Optional[str] = Query(default=None),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        _owned_session_query(db, current_user)
        .options(joinedload(ClassroomSession.lesson))
        .order_by(ClassroomSession.created_at.desc())
    )
    if topic and topic.strip():
        like_value = f"%{topic.strip()}%"
        query = query.filter(ClassroomSession.lesson.has(Lesson.lesson_topic.ilike(like_value)))
    start_dt = _parse_date_start(start_date)
    end_dt = _parse_date_end(end_date)
    if start_dt is not None:
        query = query.filter(ClassroomSession.created_at >= start_dt)
    if end_dt is not None:
        query = query.filter(ClassroomSession.created_at <= end_dt)

    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    items = []
    for row in rows:
        report = row.report_payload or {}
        hard_stats = report.get("hard_stats") or {}
        items.append(
            {
                "session_id": str(row.id),
                "lesson_id": str(row.lesson_id),
                "lesson_topic": report.get("lesson_topic") or row.lesson.lesson_topic or "未命名课程",
                "subject": report.get("subject") or row.lesson.subject or "通用",
                "class_info": report.get("class_info") or "",
                "created_at": (row.started_at or row.created_at).isoformat(),
                "duration_min": hard_stats.get("total_duration_min") or report.get("duration_min") or 0,
                "overall_level": report.get("overall_level") or "未生成报告",
                "overall_desc": report.get("overall_desc") or report.get("summary") or "暂无总体评价",
                "has_report": bool(row.report_payload),
            }
        )
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/session-dates")
def list_history_session_dates(
    topic: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(
        func.date(func.coalesce(ClassroomSession.started_at, ClassroomSession.created_at))
    ).join(
        Lesson, Lesson.id == ClassroomSession.lesson_id
    ).filter(
        Lesson.owner_user_id == current_user.id
    )
    if topic and topic.strip():
        like_value = f"%{topic.strip()}%"
        query = query.filter(ClassroomSession.lesson.has(Lesson.lesson_topic.ilike(like_value)))
    rows = query.distinct().all()
    values = set()
    for (value,) in rows:
        if value is not None:
            values.add(str(value))
    return {"dates": sorted(values)}


def _parse_date_start(raw: str | None) -> datetime | None:
    if not raw or not raw.strip():
        return None
    try:
        date_value = datetime.fromisoformat(raw.strip()).date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="start_date 格式错误，应为 YYYY-MM-DD") from exc
    return datetime(date_value.year, date_value.month, date_value.day)


def _parse_date_end(raw: str | None) -> datetime | None:
    if not raw or not raw.strip():
        return None
    try:
        date_value = datetime.fromisoformat(raw.strip()).date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="end_date 格式错误，应为 YYYY-MM-DD") from exc
    return datetime(date_value.year, date_value.month, date_value.day) + timedelta(days=1) - timedelta(microseconds=1)


@router.get("/sessions/{session_id}")
def get_history_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        _owned_session_query(db, current_user)
        .filter(ClassroomSession.id == _parse_uuid(session_id))
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="session 不存在")
    if not session.report_payload:
        raise HTTPException(status_code=404, detail="该课堂尚未生成报告")
    return {
        "session_id": str(session.id),
        "lesson_id": str(session.lesson_id),
        "report_payload": session.report_payload,
    }


@router.delete("/sessions/{session_id}")
def delete_history_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        _owned_session_query(db, current_user)
        .filter(ClassroomSession.id == _parse_uuid(session_id))
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="session 不存在")
    db.delete(session)
    db.commit()
    return {"ok": True, "session_id": str(session.id)}


@router.get("/latest-preset")
def get_latest_preset(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        _owned_session_query(db, current_user)
        .options(joinedload(ClassroomSession.lesson))
        .order_by(ClassroomSession.created_at.desc())
        .first()
    )
    if session is None or session.lesson is None:
        return {"has_preset": False, "interview_answers": {}}

    lesson = session.lesson
    prefs = lesson.teaching_preferences or {}
    atmosphere_raw = str(lesson.atmosphere or "").strip()
    if atmosphere_raw == "活跃":
        atmosphere = "活跃互动型"
    elif atmosphere_raw == "均衡":
        atmosphere = "均衡参与型"
    elif atmosphere_raw == "沉闷":
        atmosphere = "沉浸讲解型"
    elif atmosphere_raw in ("沉浸讲授型", "严谨讨论型", "练习主导型"):
        atmosphere = {
            "沉浸讲授型": "沉浸讲解型",
            "严谨讨论型": "活跃互动型",
            "练习主导型": "活跃互动型",
        }[atmosphere_raw]
    else:
        atmosphere = atmosphere_raw or "活跃互动型"

    def _coerce_interview_answer(val, default):
        if val is None:
            return default
        if isinstance(val, list):
            cleaned = [str(x).strip() for x in val if str(x).strip()]
            return cleaned if cleaned else default
        s = str(val).strip()
        if not s:
            return default
        for sep in ("、", ","):
            if sep in s:
                parts = [p.strip() for p in s.split(sep) if p.strip()]
                if len(parts) > 1:
                    return parts
        return s

    duration = prefs.get("duration") or "45 分钟"
    grade = lesson.grade or "高一"
    class_level = lesson.class_level or "普通班"
    student_level = prefs.get("student_level")
    lesson_goal = _coerce_interview_answer(
        prefs.get("primary_goal"),
        "技能掌握与方法运用",
    )
    practice_focus = _coerce_interview_answer(
        prefs.get("breakthrough_focus"),
        "提问质量与互动引导",
    )
    discipline_simulation_level = (
        prefs.get("discipline_simulation_level") or "关闭（不触发）"
    )
    # 与前端问卷顺序一致，避免 Object 迭代顺序导致摘要里「课堂氛围」等错位
    interview_answers = {
        "duration": duration,
        "grade": grade,
        "class_level": class_level,
        **({"student_level": str(student_level).strip()} if student_level else {}),
        "lesson_goal": lesson_goal,
        "practice_focus": practice_focus,
        "discipline_simulation_level": discipline_simulation_level,
        "atmosphere": atmosphere,
    }
    subj = (lesson.subject or "").strip()
    if subj:
        interview_answers["subject"] = subj

    return {
        "has_preset": True,
        "source_session_id": str(session.id),
        "interview_answers": interview_answers,
    }


@router.get("/ability-profile")
def get_ability_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = (
        _owned_session_query(db, current_user)
        .filter(ClassroomSession.report_payload.isnot(None))
        .order_by(ClassroomSession.created_at.desc())
        .all()
    )
    if not sessions:
        return {
            "session_count": 0,
            "updated_at": datetime.now().isoformat(),
            "sections": [],
        }

    session_ids = [str(session.id) for session in sessions]
    teacher_turn_counts = _load_teacher_turn_counts(db, sessions)
    decision_counts = _load_decision_event_counts(set(session_ids))
    per_session = [
        _build_session_metrics(
            session=session,
            teacher_turn_counts=teacher_turn_counts,
            decision_counts=decision_counts,
        )
        for session in sessions
    ]
    recent3 = per_session[:3]

    metric_defs = [
        ("pacing", "avg_speed_wpm", "平均语速", "字/分", True),
        ("pacing", "avg_wait_time_sec", "平均等待时间", "秒", False),
        ("pacing", "avg_duration_min", "平均课堂时长", "分钟", True),
        ("pacing", "overtime_rate", "超时率", "%", False),
        ("interaction", "interaction_quality", "互动质量", "分", True),
        ("interaction", "open_question_ratio", "开放式提问占比", "%", True),
        ("clarity", "content_accuracy", "内容准确", "分", True),
        ("clarity", "syllabus_alignment", "教案贴合度", "分", True),
        ("clarity", "misstatement_rate_per_100", "知识点错误", "/100句", False),
        ("clarity", "ambiguous_rate_per_100", "讲述模糊", "/100句", False),
        ("management", "discipline_events_per_lesson", "纪律事件频次", "次/节", False),
    ]
    title_map = {
        "pacing": "课堂节奏",
        "interaction": "互动组织",
        "clarity": "讲解清晰度",
        "management": "课堂管理",
    }
    sections_bucket = defaultdict(list)
    for section_key, metric_key, label, unit, higher_better in metric_defs:
        all_val = _avg_metric(per_session, metric_key)
        recent_val = _avg_metric(recent3, metric_key)
        sections_bucket[section_key].append(
            {
                "key": metric_key,
                "label": label,
                "value": round(all_val, 2),
                "unit": unit,
                "trend": _detect_trend(
                    all_value=all_val,
                    recent3_value=recent_val,
                    higher_is_better=higher_better,
                ),
                "trend_tone": _trend_tone(
                    all_value=all_val,
                    recent3_value=recent_val,
                    higher_is_better=higher_better,
                ),
            }
        )

    sections = [
        {
            "key": key,
            "title": title_map[key],
            "metrics": sections_bucket.get(key, []),
        }
        for key in ("pacing", "interaction", "clarity", "management")
        if sections_bucket.get(key)
    ]
    return {
        "session_count": len(per_session),
        "updated_at": datetime.now().isoformat(),
        "sections": sections,
    }


def _load_teacher_turn_counts(
    db: Session,
    sessions: list[ClassroomSession],
) -> dict[str, int]:
    ids = [session.id for session in sessions]
    if not ids:
        return {}
    rows = (
        db.query(SessionTurn.session_id, func.count(SessionTurn.id))
        .filter(
            SessionTurn.session_id.in_(ids),
            SessionTurn.role_type == "teacher",
        )
        .group_by(SessionTurn.session_id)
        .all()
    )
    return {str(session_id): int(count or 0) for session_id, count in rows}


def _load_decision_event_counts(session_ids: set[str]) -> dict[str, dict[str, int]]:
    out = {
        session_id: {"ambiguous": 0, "misstatement": 0, "discipline": 0}
        for session_id in session_ids
    }
    if not session_ids or not _DECISION_LOG_PATH.exists():
        return out

    supervisor_state_map = {
        "ambiguous": "ambiguous",
        "misstatement": "misstatement",
        "discipline_sleep": "discipline",
        "discipline_whisper": "discipline",
    }

    try:
        with _DECISION_LOG_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                try:
                    row = json.loads(text)
                except json.JSONDecodeError:
                    continue
                session_id = str(row.get("session_id") or "").strip()
                if session_id not in session_ids:
                    continue
                stage = str(row.get("stage") or "").strip()
                if stage not in {"supervisor_decision", "supervisor_decision_normal_204"}:
                    continue
                response = row.get("response") or {}
                supervisor_raw = row.get("supervisor_raw") or {}
                state = str(
                    (response.get("dialog_state") if isinstance(response, dict) else "")
                    or (supervisor_raw.get("dialog_state") if isinstance(supervisor_raw, dict) else "")
                    or ""
                ).strip()
                mapped = supervisor_state_map.get(state)
                if mapped:
                    out[session_id][mapped] += 1
    except OSError:
        return out
    return out


def _build_session_metrics(
    *,
    session: ClassroomSession,
    teacher_turn_counts: dict[str, int],
    decision_counts: dict[str, dict[str, int]],
) -> dict[str, float]:
    payload = session.report_payload or {}
    hard = payload.get("hard_stats") or {}
    scores = payload.get("scores") or {}
    question_types = payload.get("question_types") or []
    session_id = str(session.id)
    teacher_turn_count = int(teacher_turn_counts.get(session_id) or 0)
    events = decision_counts.get(session_id) or {}

    open_count = 0.0
    total_questions = 0.0
    if isinstance(question_types, list):
        for item in question_types:
            if not isinstance(item, dict):
                continue
            one_count = float(item.get("count") or 0)
            total_questions += one_count
            if str(item.get("type") or "").strip() == "开放式":
                open_count += one_count
    open_question_ratio = (open_count / total_questions * 100.0) if total_questions > 0 else 0.0

    mis_count, amb_count = _count_from_highlight_events(payload.get("highlight_events"))
    discipline_count = int(events.get("discipline") or 0)
    duration_min = float(
        hard.get("total_duration_min") or payload.get("duration_min") or 0
    )
    overtime = 1.0 if bool(payload.get("duration_overtime")) else 0.0

    return {
        "avg_speed_wpm": float(hard.get("avg_speed_wpm") or 0),
        "avg_wait_time_sec": float(hard.get("avg_wait_time_sec") or 0),
        "avg_duration_min": duration_min,
        "overtime_rate": overtime * 100.0,
        "interaction_quality": float(scores.get("interaction_quality") or 0),
        "open_question_ratio": float(open_question_ratio),
        "content_accuracy": float(scores.get("content_accuracy") or 0),
        "syllabus_alignment": float(scores.get("syllabus_alignment") or 0),
        "misstatement_rate_per_100": _rate_per_100(mis_count, teacher_turn_count),
        "ambiguous_rate_per_100": _rate_per_100(amb_count, teacher_turn_count),
        "discipline_events_per_lesson": float(discipline_count),
    }


def _count_from_highlight_events(highlights: Any) -> tuple[int, int]:
    mis = 0
    amb = 0
    if not isinstance(highlights, list):
        return mis, amb
    for item in highlights:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if _is_misstatement_prefix(text):
            mis += 1
        if _is_ambiguous_prefix(text):
            amb += 1
    return mis, amb


def _is_misstatement_prefix(text: str) -> bool:
    normalized = str(text or "").strip().replace("：", ":").lower().replace("\u3000", " ")
    return normalized.startswith("知识点讲述错误") or bool(re.search(r"触发\s*misstatement", normalized))


def _is_ambiguous_prefix(text: str) -> bool:
    normalized = str(text or "").strip().replace("：", ":").lower().replace("\u3000", " ")
    return normalized.startswith("知识点讲述模糊") or bool(re.search(r"触发\s*ambiguous", normalized))


def _rate_per_100(event_count: int, teacher_turn_count: int) -> float:
    if teacher_turn_count <= 0:
        return 0.0
    return float(event_count) / float(teacher_turn_count) * 100.0


def _avg_metric(rows: list[dict[str, float]], key: str) -> float:
    if not rows:
        return 0.0
    values = [float(row.get(key) or 0.0) for row in rows]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _detect_trend(
    *,
    all_value: float,
    recent3_value: float,
    higher_is_better: bool,
) -> str:
    epsilon = 0.1
    base = max(abs(all_value), epsilon)
    delta_abs = recent3_value - all_value
    delta_ratio = delta_abs / base
    if abs(delta_ratio) < 0.12 or abs(delta_abs) < 0.3:
        return "flat"
    return "up" if delta_abs > 0 else "down"


def _trend_tone(
    *,
    all_value: float,
    recent3_value: float,
    higher_is_better: bool,
) -> str:
    delta_abs = recent3_value - all_value
    if abs(delta_abs) < 0.0001:
        return "flat"
    improved = delta_abs > 0 if higher_is_better else delta_abs < 0
    return "good" if improved else "bad"
