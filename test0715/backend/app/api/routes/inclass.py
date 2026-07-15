from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lesson import ClassroomSession, SessionSegment, SessionTurn
from app.schemas.inclass import (
    InclassSegmentRequest,
    InclassUtteranceRequest,
    StudentStateResponse,
)
from app.services.ai_client import AIClient, AIServiceError
from app.services.defaults import STUDENT_STATES
from app.services.lesson_runtime import copy_slide_without_none, parse_iso_datetime

router = APIRouter(prefix="/inclass", tags=["inclass"])

EMPTY_SUPERVISOR_RESPONSE = {
    "dialog_state": "normal",
    "should_trigger_student": False,
    "trigger_reason": "none",
    "target_student_type": None,
    "student_event": None,
}


def _parse_uuid(raw: str, name: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{name} 不是合法 UUID") from exc


def _get_session_or_404(db: Session, raw_session_id: str) -> ClassroomSession:
    session = db.get(ClassroomSession, _parse_uuid(raw_session_id, "session_id"))
    if session is None:
        raise HTTPException(status_code=404, detail="session 不存在")
    return session


def _role_type_from_role(role: str) -> str:
    return "teacher" if role.strip().lower() == "teacher" else "student"


def _build_chat_history(turns: list[SessionTurn]) -> list[dict]:
    ordered = sorted(turns, key=lambda item: (item.event_ts, item.created_at))
    history = []
    for turn in ordered:
        history.append(
            {
                "role": "teacher" if turn.role_type == "teacher" else "student",
                "content": turn.content,
            }
        )
    return history


def _resolve_ppt_context(
    session: ClassroomSession,
    body: InclassSegmentRequest,
) -> dict | None:
    if body.ppt_context:
        return body.ppt_context
    if body.current_ppt:
        return body.current_ppt[0]
    if body.slide_no and session.lesson.ppt_payload:
        slides = session.lesson.ppt_payload.get("slides") or []
        for slide in slides:
            if int(slide.get("slide_no", 0) or 0) == int(body.slide_no):
                return copy_slide_without_none(slide)
    if body.ppt_text:
        return {
            "slide_no": body.slide_no,
            "title": f"第 {body.slide_no or 0} 页",
            "text_blocks": [body.ppt_text],
            "visual_elements": [],
            "summary": body.ppt_text[:120],
        }
    return None


@router.post("/utterance")
async def post_utterance(
    body: InclassUtteranceRequest,
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, body.session_id)
    event_ts = parse_iso_datetime(body.current_timestamp)
    role_type = _role_type_from_role(body.role)

    turn = SessionTurn(
        session_id=session.id,
        role_type=role_type,
        role_label=body.role,
        content=body.content,
        event_ts=event_ts,
        called_student_id=body.called_student_id,
    )
    db.add(turn)
    if session.started_at is None:
        session.started_at = event_ts
    session.status = "active"
    db.flush()

    if role_type != "teacher" or body.skip_supervisor:
        db.commit()
        return EMPTY_SUPERVISOR_RESPONSE

    recent_turns = (
        db.query(SessionTurn)
        .filter(
            SessionTurn.session_id == session.id,
            SessionTurn.id != turn.id,
        )
        .order_by(SessionTurn.event_ts.desc(), SessionTurn.created_at.desc())
        .limit(20)
        .all()
    )

    payload = {
        "teacher_text": body.content,
        "current_timestamp": body.current_timestamp,
        "subject": session.lesson.subject,
        "chat_history": _build_chat_history(recent_turns),
        "current_ppt": body.current_ppt or None,
        "called_student_id": body.called_student_id,
    }

    ai_client = AIClient()
    try:
        result = await ai_client.supervisor_decide(payload)
    except AIServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    db.commit()
    return result


@router.get("/student-state/{student_id}", response_model=StudentStateResponse)
def get_student_state(student_id: str):
    state = STUDENT_STATES.get(student_id)
    if state is None:
        raise HTTPException(status_code=404, detail="student 不存在")
    return StudentStateResponse(**state)


@router.post("/segment")
async def post_segment(
    body: InclassSegmentRequest,
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, body.session_id)
    start_ts = parse_iso_datetime(body.start_ts)
    end_ts = parse_iso_datetime(body.end_ts)
    if end_ts < start_ts:
        raise HTTPException(status_code=400, detail="end_ts 不能早于 start_ts")

    if session.started_at is None:
        session.started_at = start_ts
    session.status = "active"

    ppt_context = _resolve_ppt_context(session, body)
    ai_payload = {
        "segment_id": body.segment_id,
        "start_ts": body.start_ts,
        "end_ts": body.end_ts,
        "slide_no": body.slide_no,
        "teacher_utterances": [item.model_dump() for item in body.teacher_utterances],
        "student_utterances": [item.model_dump() for item in body.student_utterances],
    }
    if ppt_context:
        ai_payload["ppt_context"] = ppt_context

    row = (
        db.query(SessionSegment)
        .filter(
            SessionSegment.session_id == session.id,
            SessionSegment.segment_id == body.segment_id,
        )
        .first()
    )
    if row is None:
        row = SessionSegment(
            session_id=session.id,
            segment_id=body.segment_id,
            start_ts=start_ts,
            end_ts=end_ts,
            slide_no=body.slide_no,
            segment_payload=ai_payload,
        )
        db.add(row)
    else:
        row.start_ts = start_ts
        row.end_ts = end_ts
        row.slide_no = body.slide_no
        row.segment_payload = ai_payload

    ai_client = AIClient()
    try:
        eval_payload = await ai_client.segment_eval(ai_payload)
    except AIServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    row.eval_payload = eval_payload
    db.commit()
    return eval_payload
