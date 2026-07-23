from __future__ import annotations

import asyncio
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.models.lesson import (
    ClassroomSession,
    Lesson,
    SessionSegment,
    SessionTurn,
    SessionVisualObservation,
)
from app.services.ai_client import AIClient, AIServiceError
from app.services.lesson_runtime import build_min_lesson_payload, format_display_datetime
from app.services.reporting import (
    build_ai_report_fallback,
    build_report_response,
    merge_visual_into_report_payload,
)

router = APIRouter(tags=["report"])
_VISUAL_VLM_WAIT_TIMEOUT_S = 120.0
_VISUAL_VLM_POLL_INTERVAL_S = 2.0


def _parse_uuid(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="session_id 不是合法 UUID") from exc


def _get_owned_session(
    db: Session,
    session_id: str,
    current_user: User,
) -> Optional[ClassroomSession]:
    return (
        db.query(ClassroomSession)
        .options(joinedload(ClassroomSession.lesson))
        .join(Lesson, Lesson.id == ClassroomSession.lesson_id)
        .filter(
            ClassroomSession.id == _parse_uuid(session_id),
            Lesson.owner_user_id == current_user.id,
        )
        .first()
    )


def _count_visual_observations(db: Session, session_id: uuid.UUID) -> int:
    return (
        db.query(SessionVisualObservation)
        .filter(SessionVisualObservation.session_id == session_id)
        .count()
    )


def _count_visual_pending(db: Session, session_id: uuid.UUID) -> int:
    return (
        db.query(SessionVisualObservation)
        .filter(
            SessionVisualObservation.session_id == session_id,
            SessionVisualObservation.vlm_status == "pending",
        )
        .count()
    )


async def _wait_for_visual_vlm(
    db: Session,
    session_id: uuid.UUID,
    *,
    timeout_s: float = _VISUAL_VLM_WAIT_TIMEOUT_S,
) -> bool:
    """等待本课全部视觉窗口 VLM 分析结束。无视觉记录时立即返回 True。"""
    if _count_visual_observations(db, session_id) == 0:
        return True

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _count_visual_pending(db, session_id) == 0:
            return True
        await asyncio.sleep(_VISUAL_VLM_POLL_INTERVAL_S)
        db.expire_all()
    return False


def _query_visual_observations(db: Session, session_id: uuid.UUID) -> list[SessionVisualObservation]:
    return (
        db.query(SessionVisualObservation)
        .filter(SessionVisualObservation.session_id == session_id)
        .order_by(SessionVisualObservation.window_start_sec.asc())
        .all()
    )


@router.get("/report/{session_id}")
async def get_report(
    session_id: str,
    force_refresh: bool = Query(False, alias="force"),
    wait_for_visual: bool = Query(True, alias="wait_visual"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_owned_session(db, session_id, current_user)
    if session is None:
        raise HTTPException(status_code=404, detail="session 不存在")

    sid = session.id
    visual_wait_timed_out = False
    if wait_for_visual and _count_visual_observations(db, sid) > 0:
        visual_wait_timed_out = not await _wait_for_visual_vlm(db, sid)

    if session.report_payload and not force_refresh:
        visual_obs = _query_visual_observations(db, sid)
        payload = merge_visual_into_report_payload(
            dict(session.report_payload),
            visual_obs,
            session,
        )
        anchor = session.started_at or session.created_at
        if anchor is not None:
            payload["created_at"] = format_display_datetime(anchor)
        if visual_wait_timed_out:
            payload["visual_processing_timed_out"] = True
        prev_visual = (session.report_payload or {}).get("visual_analysis") or {}
        if payload.get("visual_analysis") != prev_visual:
            session.report_payload = payload
            db.commit()
        return payload

    if session.ended_at is None:
        session.ended_at = datetime.now(timezone.utc)
    if session.status != "completed":
        session.status = "completed"

    turns = (
        db.query(SessionTurn)
        .filter(SessionTurn.session_id == session.id)
        .order_by(SessionTurn.event_ts.asc(), SessionTurn.created_at.asc())
        .all()
    )
    segments = (
        db.query(SessionSegment)
        .filter(SessionSegment.session_id == session.id)
        .order_by(SessionSegment.start_ts.asc(), SessionSegment.created_at.asc())
        .all()
    )
    segment_evals = [row.eval_payload for row in segments if row.eval_payload]

    visual_obs = _query_visual_observations(db, sid)

    lesson_json = session.lesson.lesson_payload or build_min_lesson_payload(
        grade=session.lesson.grade,
        subject=session.lesson.subject,
        custom_goal=session.lesson.custom_goal,
        teacher_context=session.lesson.teacher_context,
    )
    if session.lesson.teaching_preferences:
        lesson_json["teaching_preferences"] = session.lesson.teaching_preferences

    ai_client = AIClient()
    try:
        ai_report = await ai_client.generate_report(
            {"lesson_json": lesson_json, "segment_evals": segment_evals}
        )
    except AIServiceError:
        ai_report = build_ai_report_fallback(lesson_json, segment_evals)

    report_payload = build_report_response(
        session=session,
        turns=turns,
        segments=segments,
        lesson_json=lesson_json,
        ai_report=ai_report,
        visual_obs=visual_obs,
    )
    if visual_wait_timed_out:
        report_payload["visual_processing_timed_out"] = True
    session.report_payload = report_payload
    db.commit()
    return report_payload


@router.get("/report/{session_id}/recent5-comparison")
def get_recent5_comparison(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_owned_session(db, session_id, current_user)
    if session is None:
        raise HTTPException(status_code=404, detail="session 不存在")
    if not session.report_payload:
        return {
            "sample_size": 0,
            "has_history": False,
            "message": "暂无历史可比课堂",
            "metrics": [],
        }

    anchor_time = session.created_at
    rows = (
        db.query(ClassroomSession)
        .join(Lesson, Lesson.id == ClassroomSession.lesson_id)
        .filter(
            Lesson.owner_user_id == current_user.id,
            ClassroomSession.report_payload.isnot(None),
            ClassroomSession.created_at <= anchor_time,
        )
        .order_by(ClassroomSession.created_at.desc())
        .limit(5)
        .all()
    )
    rows = list(reversed(rows))
    sample_size = len(rows)
    if sample_size <= 1:
        return {
            "sample_size": sample_size,
            "has_history": False,
            "message": "暂无历史可比课堂",
            "metrics": [],
        }

    points = []
    for item in rows:
        payload = item.report_payload or {}
        hard = payload.get("hard_stats") or {}
        scores = payload.get("scores") or {}
        points.append(
            {
                "session_id": str(item.id),
                "date": format_display_datetime(
                    item.started_at or item.created_at,
                    fmt="%m-%d",
                ),
                "is_current": str(item.id) == str(session.id),
                "avg_speed_wpm": float(hard.get("avg_speed_wpm") or 0),
                "avg_wait_time_sec": float(hard.get("avg_wait_time_sec") or 0),
                "interaction_quality": float(scores.get("interaction_quality") or 0),
                "clarity_issue_count": float(_count_clarity_issues(str(item.id), payload)),
            }
        )

    current = next((item for item in points if item["is_current"]), points[-1])
    prev = points[-2] if len(points) >= 2 else None
    defs = [
        ("avg_speed_wpm", "平均语速", "字/分", False),
        ("avg_wait_time_sec", "平均等待时长", "秒", True),
        ("interaction_quality", "互动质量", "分", True),
        ("clarity_issue_count", "讲述模糊与错误数", "次", False),
    ]
    metrics = []
    for key, label, unit, higher_better in defs:
        series = [
            {
                "session_id": item["session_id"],
                "date": item["date"],
                "value": round(float(item[key]), 2),
                "is_current": bool(item["is_current"]),
            }
            for item in points
        ]
        avg5 = sum(float(item[key]) for item in points) / max(len(points), 1)
        current_value = float(current[key])
        prev_value = float(prev[key]) if prev else None
        metrics.append(
            {
                "key": key,
                "label": label,
                "unit": unit,
                "higher_is_better": higher_better,
                "series": series,
                "current_value": round(current_value, 2),
                "avg5_value": round(avg5, 2),
                "delta_vs_avg5": round(current_value - avg5, 2),
                "prev_value": round(prev_value, 2) if prev_value is not None else None,
                "delta_vs_prev": round(current_value - prev_value, 2)
                if prev_value is not None
                else None,
            }
        )
    return {
        "sample_size": sample_size,
        "has_history": True,
        "message": "",
        "metrics": metrics,
    }


def _count_clarity_issues(
    session_id: str, report_payload: Optional[dict[str, Any]] = None
) -> int:
    _ = session_id
    if isinstance(report_payload, dict):
        highlights = report_payload.get("highlight_events") or []
        if isinstance(highlights, list):
            fallback = 0
            for item in highlights:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or "").strip()
                if _is_clarity_prefix_event(text):
                    fallback += 1
            if fallback > 0:
                return fallback
    return 0


def _is_clarity_prefix_event(text: str) -> bool:
    normalized = str(text or "").strip().replace("：", ":").lower().replace("\u3000", " ")
    return (
        normalized.startswith("知识点讲述模糊")
        or normalized.startswith("知识点讲述错误")
        or bool(re.search(r"触发\s*ambiguous", normalized))
        or bool(re.search(r"触发\s*misstatement", normalized))
    )
