from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lesson import ClassroomSession, SessionSegment, SessionTurn
from app.models.session_student import SessionStudent
from app.schemas.inclass import (
    InclassSegmentRequest,
    InclassUtteranceRequest,
    InclassUtteranceResponse,
    StudentReplyRequest,
    StudentReplyResponse,
    StudentStateItem,
    StudentStateResponse,
)
from app.services.ai_client import AIClient, AIServiceError
from app.services.lesson_runtime import copy_slide_without_none, parse_iso_datetime
from app.services.student_state import (
    build_called_student_digest,
    build_student_states_digest,
    get_session_student,
    get_session_students,
    initialize_session_students,
    pick_random_students_by_type,
    reset_hand_raised,
    set_hand_raised,
    update_discipline_state,
)

router = APIRouter(prefix="/inclass", tags=["inclass"])

_DECISION_LOGGER = logging.getLogger("inclass_decision_snapshot")
if not _DECISION_LOGGER.handlers:
    _log_dir = Path(__file__).resolve().parents[3] / "logs"
    _log_dir.mkdir(parents=True, exist_ok=True)
    _fh = logging.FileHandler(_log_dir / "inclass_decisions.jsonl", encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(message)s"))
    _DECISION_LOGGER.addHandler(_fh)
    _DECISION_LOGGER.setLevel(logging.INFO)
    _DECISION_LOGGER.propagate = False

# 旧格式兼容：当不触发或异常时返回的空响应
EMPTY_SUPERVISOR_RESPONSE = {
    "dialog_state": "normal",
    "should_trigger_student": False,
    "trigger_reason": "none",
    "target_student_type": None,
    "student_event": None,
}

# 兼容前端 discipline_action 写法
DISCIPLINE_ACTION_ALIASES = {
    "whisper": "start_whisper",
    "sleep": "start_sleep",
}


def _log_decision_snapshot(
    *,
    session_id: uuid.UUID,
    stage: str,
    request: InclassUtteranceRequest,
    response: dict | None = None,
    supervisor_payload: dict | None = None,
    supervisor_raw: dict | None = None,
    note: str | None = None,
) -> None:
    try:
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": str(session_id),
            "stage": stage,
            "request": {
                "role": request.role,
                "content": request.content,
                "current_timestamp": request.current_timestamp,
                "called_student_id": request.called_student_id,
                "discipline_student_id": request.discipline_student_id,
                "discipline_action": request.discipline_action,
                "skip_supervisor": request.skip_supervisor,
            },
            "supervisor_payload": supervisor_payload,
            "supervisor_raw": supervisor_raw,
            "response": response,
            "note": note,
        }
        _DECISION_LOGGER.info(json.dumps(row, ensure_ascii=False))
    except Exception:
        # 决策日志不可影响主流程
        return


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


def _build_empty_response(
    session_students: list[SessionStudent],
    interaction_round_id: str | None = None,
) -> InclassUtteranceResponse:
    return InclassUtteranceResponse(
        dialog_state="normal",
        should_trigger_student=False,
        trigger_reason="none",
        target_student_type=None,
        interaction_round_id=interaction_round_id or str(uuid.uuid4()),
        play_mode="immediate",
        raised_hand_student_ids=[],
        preset_for_student_id=None,
        student_states_digest=build_student_states_digest(session_students),
        preset_consumed=False,
        student_event=None,
    )


@router.post("/utterance", response_model=InclassUtteranceResponse)
async def post_utterance(
    body: InclassUtteranceRequest,
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, body.session_id)
    event_ts = parse_iso_datetime(body.current_timestamp)
    role_type = _role_type_from_role(body.role)

    # 1. 保存 turn
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
    if session.status != "active":
        session.status = "active"
    db.flush()

    # 查询全班状态
    session_students = get_session_students(session.id, db)
    interaction_round_id = str(uuid.uuid4())

    # 2. 处理 discipline 事件（前端直接触发，不调用 supervisor）
    if body.discipline_action:
        discipline_action = DISCIPLINE_ACTION_ALIASES.get(
            body.discipline_action, body.discipline_action
        )
        # 优先使用 discipline_student_id，兼容 called_student_id
        target_student_id = body.discipline_student_id or body.called_student_id
        if not target_student_id:
            db.commit()
            return _build_empty_response(session_students, interaction_round_id)

        target_student = get_session_student(session.id, target_student_id, db)
        # 互斥：举手中的学生不能被随机纪律事件命中
        if target_student is not None and target_student.is_hand_raised:
            db.commit()
            resp = _build_empty_response(session_students, interaction_round_id)
            _log_decision_snapshot(
                session_id=session.id,
                stage="discipline_rejected_conflict",
                request=body,
                response=resp.model_dump(),
                note=f"target {target_student_id} is hand_raised, discipline skipped",
            )
            return resp

        # 强制"同一时间只有一个 sleep/whisper"规则：先重置其他学生的状态
        for s in session_students:
            if s.student_id != target_student_id and (s.is_sleeping or s.is_whispering):
                s.is_sleeping = False
                s.is_whispering = False

        # 更新目标学生的状态
        student = update_discipline_state(
            session.id, target_student_id, discipline_action, db
        )
        if student is None:
            db.commit()
            return _build_empty_response(session_students, interaction_round_id)

        # discipline_action 分支只负责状态库写入，不触发 student_event 语音
        db.commit()
        session_students = get_session_students(session.id, db)
        resp = InclassUtteranceResponse(
            dialog_state="normal",
            should_trigger_student=False,
            trigger_reason=discipline_action,
            target_student_type=None,
            interaction_round_id=interaction_round_id,
            play_mode="immediate",
            raised_hand_student_ids=[],
            preset_for_student_id=None,
            student_states_digest=build_student_states_digest(session_students),
            preset_consumed=False,
            student_event=None,
        )
        _log_decision_snapshot(
            session_id=session.id,
            stage="discipline_state_only",
            request=body,
            response=resp.model_dump(),
            note="discipline start/cancel only updates state store",
        )
        return resp

    # 3. 非教师发言或跳过 supervisor
    if role_type != "teacher" or body.skip_supervisor:
        # 学生回答入库后清空举手状态，避免旧轮次举手残留
        if role_type != "teacher":
            reset_hand_raised(session.id, db)
            session_students = get_session_students(session.id, db)
        db.commit()
        resp = _build_empty_response(session_students, interaction_round_id)
        _log_decision_snapshot(
            session_id=session.id,
            stage="skip_supervisor",
            request=body,
            response=resp.model_dump(),
        )
        return resp

    # 4. 正常教师发言流程
    # 4.1 重置举手状态（新一轮开始）
    reset_hand_raised(session.id, db)

    # 4.2 查询最近对话历史
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

    # 4.3 构造 called_student_status_digest（修复字段名不匹配问题）
    called_student_digest = None
    if body.called_student_id:
        called_student_digest = build_called_student_digest(
            session.id, body.called_student_id, db
        )

    # 4.4 构造 supervisor payload
    student_status_digest = build_student_states_digest(session_students)
    payload = {
        "teacher_text": body.content,
        "current_timestamp": body.current_timestamp,
        "subject": session.lesson.subject,
        "chat_history": _build_chat_history(recent_turns),
        "current_ppt": body.current_ppt or None,
        "called_student_status_digest": called_student_digest,
        "student_status_digest": student_status_digest,
    }

    # 4.5 调用 supervisor
    ai_client = AIClient()
    try:
        result = await ai_client.supervisor_decide(payload)
    except AIServiceError as exc:
        db.rollback()
        _log_decision_snapshot(
            session_id=session.id,
            stage="supervisor_error",
            request=body,
            supervisor_payload=payload,
            note=str(exc),
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    dialog_state = result.get("dialog_state", "normal")
    should_trigger = result.get("should_trigger_student", False)
    trigger_reason = result.get("trigger_reason", "none")
    target_type = result.get("target_student_type")
    student_event = result.get("student_event")

    play_mode = "immediate"
    raised_hand_ids: list[str] = []
    preset_for_id: str | None = None

    # 4.6 根据 dialog_state 处理状态与响应格式
    if dialog_state == "questioning" and should_trigger:
        play_mode = "on_call_name"
        # 随机挑 2 个同学举手
        all_students = [
            s.student_id
            for s in session_students
            if (not s.is_sleeping and not s.is_whispering)
        ]
        rng = __import__("random").Random(str(session.id) + interaction_round_id)
        rng.shuffle(all_students)
        raised_hand_ids = all_students[:2]
        if raised_hand_ids:
            set_hand_raised(session.id, raised_hand_ids, db)
        preset_for_id = None

    elif dialog_state == "ambiguous" and should_trigger:
        play_mode = "on_call_name"
        candidates = pick_random_students_by_type(
            session.id, "xuekun", 1, db
        )
        if candidates:
            raised_hand_ids = [candidates[0].student_id]
            set_hand_raised(session.id, raised_hand_ids, db)
            preset_for_id = candidates[0].student_id

    elif dialog_state == "misstatement" and should_trigger:
        play_mode = "on_call_name"
        candidates = pick_random_students_by_type(
            session.id, "gangjing", 1, db
        )
        if candidates:
            raised_hand_ids = [candidates[0].student_id]
            set_hand_raised(session.id, raised_hand_ids, db)
            preset_for_id = candidates[0].student_id

    elif dialog_state == "relay_answer" and should_trigger:
        play_mode = "immediate"
        if body.called_student_id:
            preset_for_id = body.called_student_id
        # relay_answer 不用举手

    elif dialog_state in ("discipline_whisper", "discipline_sleep") and should_trigger:
        play_mode = "immediate"
        # 重置所有 sleep/whisper 状态（前端会 immediate 让学生站起来说完后解除）
        for s in session_students:
            if s.is_sleeping or s.is_whispering:
                s.is_sleeping = False
                s.is_whispering = False
        # 从 student_event 推断 preset_for_student_id
        if student_event and isinstance(student_event, dict):
            preset_for_id = student_event.get("student_id") or body.called_student_id
        else:
            preset_for_id = body.called_student_id
    # normal 或其他状态：保持默认空值

    db.commit()

    # 刷新状态用于响应
    session_students = get_session_students(session.id, db)

    resp = InclassUtteranceResponse(
        dialog_state=dialog_state,
        should_trigger_student=should_trigger,
        trigger_reason=trigger_reason,
        target_student_type=target_type,
        interaction_round_id=interaction_round_id,
        play_mode=play_mode,
        raised_hand_student_ids=raised_hand_ids,
        preset_for_student_id=preset_for_id,
        student_states_digest=build_student_states_digest(session_students),
        preset_consumed=False,
        student_event=student_event,
    )
    _log_decision_snapshot(
        session_id=session.id,
        stage="supervisor_decision",
        request=body,
        supervisor_payload=payload,
        supervisor_raw=result,
        response=resp.model_dump(),
    )
    return resp


@router.post("/student-reply", response_model=StudentReplyResponse)
async def post_student_reply(
    body: StudentReplyRequest,
    db: Session = Depends(get_db),
):
    """前端点名后实时获取被点名学生的单条回复。"""
    session = _get_session_or_404(db, body.session_id)

    # 1. 获取目标学生状态
    student = get_session_student(session.id, body.student_id, db)
    if student is None:
        raise HTTPException(status_code=404, detail="student 不存在")

    # 2. 查询最近 20 轮对话历史
    recent_turns = (
        db.query(SessionTurn)
        .filter(SessionTurn.session_id == session.id)
        .order_by(SessionTurn.event_ts.desc(), SessionTurn.created_at.desc())
        .limit(20)
        .all()
    )
    chat_history = _build_chat_history(recent_turns)

    # 3. 构造 background
    background: dict[str, Any] = {"subject": session.lesson.subject}

    # PPT 上下文
    if body.current_ppt and len(body.current_ppt) > 0:
        ppt_slide = body.current_ppt[0]
        background["slide_no"] = ppt_slide.get("slide_no")
        background["slides"] = [ppt_slide]

    # 对话历史拆分为 teacher / student utterances
    teacher_utterances = []
    student_utterances = []
    for msg in chat_history:
        if msg.get("role") == "teacher":
            teacher_utterances.append(
                {"ts": body.current_timestamp or "", "text": msg.get("content", "")}
            )
        elif msg.get("role") == "student":
            student_utterances.append(
                {
                    "ts": body.current_timestamp or "",
                    "text": msg.get("content", ""),
                    "student_id": "",
                }
            )
    if teacher_utterances:
        background["teacher_utterances_on_slide"] = teacher_utterances
    if student_utterances:
        background["student_utterances_on_slide"] = student_utterances

    # 4. 调用 AI 模块生成单条回复
    ai_client = AIClient()
    try:
        ai_result = await ai_client.student_reply(
            {
                "student_type": student.student_type,
                "trigger_reason": "teacher_question",
                "is_proactive_speaking": student.is_hand_raised,
                "background": background,
            }
        )
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return StudentReplyResponse(
        student_id=student.student_id,
        student_type=student.student_type,
        reply_text=ai_result.get("reply_text", "（无回复）"),
        emotion=ai_result.get("emotion", "idle"),
        is_proactive_speaking=ai_result.get("is_proactive_speaking", student.is_hand_raised),
    )


@router.get("/student-state/{student_id}", response_model=StudentStateResponse)
def get_student_state(
    student_id: str,
    session_id: str | None = None,
    db: Session = Depends(get_db),
):
    if session_id:
        session = _get_session_or_404(db, session_id)
        student = get_session_student(session.id, student_id, db)
        if student is None:
            raise HTTPException(status_code=404, detail="student 不存在")
        return StudentStateResponse(
            student_id=student.student_id,
            student_type=student.student_type,
            is_hand_raised=student.is_hand_raised,
            is_sleeping=student.is_sleeping,
            is_whispering=student.is_whispering,
            student_name=student.student_name,
        )
    # 兼容旧前端（未传 session_id）：返回静态 fallback
    from app.services.defaults import STUDENT_STATES
    state = STUDENT_STATES.get(student_id)
    if state is None:
        raise HTTPException(status_code=404, detail="student 不存在")
    return StudentStateResponse(**state, is_sleeping=False, is_whispering=False, student_name="")


@router.get("/student-states/{session_id}")
def get_all_student_states(session_id: str, db: Session = Depends(get_db)):
    session = _get_session_or_404(db, session_id)
    students = get_session_students(session.id, db)
    return [
        {
            "student_id": s.student_id,
            "student_name": s.student_name,
            "student_type": s.student_type,
            "is_hand_raised": s.is_hand_raised,
            "is_sleeping": s.is_sleeping,
            "is_whispering": s.is_whispering,
        }
        for s in students
    ]


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
    if session.status != "active":
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
