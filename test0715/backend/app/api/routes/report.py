import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lesson import ClassroomSession, SessionSegment, SessionTurn
from app.services.ai_client import AIClient, AIServiceError
from app.services.lesson_runtime import build_min_lesson_payload
from app.services.reporting import build_ai_report_fallback, build_report_response

router = APIRouter(tags=["report"])


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
):
    session = db.get(ClassroomSession, _parse_uuid(session_id))
    if session is None:
        raise HTTPException(status_code=404, detail="session 不存在")

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
