import uuid
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_teacher_id
from app.db.session import get_db
from app.models.lesson import ClassroomSession, SessionSegment, SessionTurn
from app.services.ai_client import AIClient, AIServiceError
from app.services.lesson_runtime import build_min_lesson_payload
from app.services.reporting import build_ai_report_fallback, build_report_response

router = APIRouter(tags=["report"])
_LEGACY_TEACHER_ID = "legacy_teacher"


def _parse_uuid(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="session_id 不是合法 UUID") from exc


@router.get("/report/{session_id}")
async def get_report(
    session_id: str,
    force_refresh: bool = Query(False, alias="force"),
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_teacher_id),
):
    session = db.get(ClassroomSession, _parse_uuid(session_id))
    if session is None:
        raise HTTPException(status_code=404, detail="session 不存在")
    if session.teacher_id not in {teacher_id, _LEGACY_TEACHER_ID}:
        raise HTTPException(status_code=403, detail="无权访问该课堂")

    if session.report_payload and not force_refresh:
        return session.report_payload

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
    )
    session.report_payload = report_payload
    db.commit()
    return report_payload


@router.get("/report/{session_id}/recent5-comparison")
def get_recent5_comparison(
    session_id: str,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_teacher_id),
):
    session = db.get(ClassroomSession, _parse_uuid(session_id))
    if session is None:
        raise HTTPException(status_code=404, detail="session 不存在")
    if session.teacher_id not in {teacher_id, _LEGACY_TEACHER_ID}:
        raise HTTPException(status_code=403, detail="无权访问该课堂")
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
        .filter(
            ClassroomSession.teacher_id.in_([teacher_id, _LEGACY_TEACHER_ID]),
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
                "date": (item.started_at or item.created_at).strftime("%m-%d"),
                "is_current": str(item.id) == str(session.id),
                "avg_speed_wpm": float(hard.get("avg_speed_wpm") or 0),
                "avg_wait_time_sec": float(hard.get("avg_wait_time_sec") or 0),
                "interaction_quality": float(scores.get("interaction_quality") or 0),
                "clarity_issue_count": float(_count_clarity_issues(str(item.id), payload)),
            }
        )

    current = next((p for p in points if p["is_current"]), points[-1])
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
                "session_id": p["session_id"],
                "date": p["date"],
                "value": round(float(p[key]), 2),
                "is_current": bool(p["is_current"]),
            }
            for p in points
        ]
        avg5 = sum(float(p[key]) for p in points) / max(len(points), 1)
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
                "delta_vs_prev": round(current_value - prev_value, 2) if prev_value is not None else None,
            }
        )
    return {
        "sample_size": sample_size,
        "has_history": True,
        "message": "",
        "metrics": metrics,
    }


def _count_clarity_issues(session_id: str, report_payload: dict[str, Any] | None = None) -> int:
    # 按产品约定：近五次对比中的“讲述模糊与错误数”统一来自 report.highlight_events.text 文本匹配。
    # session_id 参数保留仅为函数签名兼容。
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
    t = str(text or "").strip()
    normalized = t.replace("：", ":").lower().replace("\u3000", " ")
    return (
        t.startswith("知识点讲述模糊")
        or t.startswith("知识点讲述错误")
        or bool(re.search(r"触发\s*ambiguous", normalized))
        or bool(re.search(r"触发\s*misstatement", normalized))
    )
