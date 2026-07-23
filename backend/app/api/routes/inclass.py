from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.models.lesson import ClassroomSession, Lesson, SessionSegment, SessionTurn
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
from app.services.hand_raise_policy import (
    normalize_atmosphere,
    normalize_question_difficulty,
    select_questioning_hand_raises,
)
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
_LEGACY_TEACHER_ID = "legacy_teacher"

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

# 缓存 lesson 的单页 PPT 上下文，避免重复扫描 slides 列表
_LESSON_SLIDE_CONTEXT_CACHE: dict[tuple[str, int], dict | None] = {}
# 记录每个 session 最近一次使用的页号和 payload，页号不变时直接复用
_SESSION_LAST_UTTERANCE_PPT_CACHE: dict[str, tuple[int, list[dict] | None]] = {}

_NON_SEMANTIC_SHORT_WORDS = {
    "嗯",
    "啊",
    "哦",
    "诶",
    "呃",
    "哎",
    "唉",
    "额",
    "哈",
}
_NON_SEMANTIC_SINGLE_FEEDBACK = {
    "好",
    "对",
    "是",
    "行",
    "可以",
}
_QUESTION_CUES = {
    "为什么",
    "怎么",
    "如何",
    "是否",
    "能不能",
    "谁",
    "哪",
    "多少",
    "是什么",
    "是不是",
}
_TEACHING_ACTION_CUES = {
    "看",
    "讲",
    "答",
    "回答",
    "解释",
    "证明",
    "比较",
    "判断",
    "计算",
    "总结",
    "复述",
    "翻到",
    "继续",
    "停一下",
    "重说一遍",
    "举例",
    "补充",
    "纠错",
    "请说",
    "说一说",
    "说说",
}
_CONTENT_CUES = {
    "函数",
    "三角",
    "勾股",
    "图像",
    "公式",
    "定义",
    "条件",
    "结论",
    "方程",
    "角",
    "几何",
    "代数",
    "步骤",
    "题",
    "页",
    "PPT",
}
_STRUCTURE_CUES = {"因为", "所以", "如果", "那么", "先", "再", "但是", "然后"}


def _normalize_filter_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).strip()


def _is_punctuation_only(text: str) -> bool:
    if not text:
        return True
    return re.fullmatch(r"[，。！？!?、；：,.~`!@#$%^&*()\-_=+\[\]{}\\|/<>\"'“”‘’··…\s]+", text) is not None


def _is_repeated_single_char_noise(text: str) -> bool:
    if len(text) < 4:
        return False
    return len(set(text)) == 1 and text[0] in _NON_SEMANTIC_SHORT_WORDS


def _contains_named_calling_intent(text: str, student_names: list[str]) -> bool:
    action_group = r"(说|回答|你来|请回答|解释|补充|讲一下|来答|来讲)"
    generic_patterns = [
        rf"同学[，,、\s]*(?:你)?(?:来|先)?{action_group}",
        rf"(?:请|麻烦|让)[，,、\s]*同学[，,、\s]*(?:来|先)?{action_group}",
    ]
    for pattern in generic_patterns:
        if re.search(pattern, text):
            return True

    for raw_name in student_names:
        name = str(raw_name or "").strip()
        if not name:
            continue
        n = re.escape(name)
        patterns = [
            rf"{n}(?:同学)?[，,、\s]*(?:你)?(?:来|先)?{action_group}",
            rf"(?:请|麻烦|让)?[，,、\s]*{n}(?:同学)?[，,、\s]*(?:来|先)?{action_group}",
            rf"{n}(?:同学)?[，,、\s]*你说",
            rf"{n}(?:同学)?[，,、\s]*回答",
        ]
        for pattern in patterns:
            if re.search(pattern, text):
                return True
    return False


def should_send_to_supervisor(
    *,
    text: str,
    called_student_id: str | None,
    session_students: list[SessionStudent],
) -> dict:
    normalized = _normalize_filter_text(text)
    called_id = str(called_student_id or "").strip()
    student_names = [str(s.student_name or "").strip() for s in session_students]
    matched_rules: list[str] = []

    if not normalized:
        return {
            "send": False,
            "reason_code": "empty_text",
            "layer": "hard_block",
            "score": 0,
            "normalized_text": normalized,
            "matched_rules": ["empty_text"],
        }
    if _is_punctuation_only(normalized):
        return {
            "send": False,
            "reason_code": "punct_only",
            "layer": "hard_block",
            "score": 0,
            "normalized_text": normalized,
            "matched_rules": ["punct_only"],
        }
    if normalized in _NON_SEMANTIC_SHORT_WORDS and len(normalized) <= 3:
        return {
            "send": False,
            "reason_code": "filler_only_short",
            "layer": "hard_block",
            "score": 0,
            "normalized_text": normalized,
            "matched_rules": ["filler_only_short"],
        }
    if normalized in _NON_SEMANTIC_SINGLE_FEEDBACK:
        return {
            "send": False,
            "reason_code": "single_feedback_only",
            "layer": "hard_block",
            "score": 0,
            "normalized_text": normalized,
            "matched_rules": ["single_feedback_only"],
        }
    if _is_repeated_single_char_noise(normalized):
        return {
            "send": False,
            "reason_code": "repeat_noise",
            "layer": "hard_block",
            "score": 0,
            "normalized_text": normalized,
            "matched_rules": ["repeat_noise"],
        }

    # 语义白名单：命中立即放行
    if re.search(r"[?？]", normalized):
        return {
            "send": True,
            "reason_code": "whitelist_question_mark",
            "layer": "semantic_whitelist",
            "score": 0,
            "normalized_text": normalized,
            "matched_rules": ["question_mark"],
        }
    if any(cue in normalized for cue in _QUESTION_CUES):
        return {
            "send": True,
            "reason_code": "whitelist_question_cue",
            "layer": "semantic_whitelist",
            "score": 0,
            "normalized_text": normalized,
            "matched_rules": ["question_cue"],
        }
    if _contains_named_calling_intent(normalized, student_names):
        return {
            "send": True,
            "reason_code": "whitelist_named_calling",
            "layer": "semantic_whitelist",
            "score": 0,
            "normalized_text": normalized,
            "matched_rules": ["named_calling"],
        }
    if called_id:
        called_student = next((s for s in session_students if s.student_id == called_id), None)
        if called_student and str(called_student.student_name or "").strip() and str(called_student.student_name).strip() in normalized:
            return {
                "send": True,
                "reason_code": "whitelist_called_student_named",
                "layer": "semantic_whitelist",
                "score": 0,
                "normalized_text": normalized,
                "matched_rules": ["called_student_named"],
            }
    if any(cue in normalized for cue in ("我们看", "翻到", "下一题", "这一步", "结论是", "注意这里")):
        return {
            "send": True,
            "reason_code": "whitelist_teaching_progress",
            "layer": "semantic_whitelist",
            "score": 0,
            "normalized_text": normalized,
            "matched_rules": ["teaching_progress"],
        }

    # 打分兜底：低分才拦截，保守放行
    score = 0
    if any(cue in normalized for cue in _TEACHING_ACTION_CUES):
        score += 2
        matched_rules.append("action_cue")
    if any(cue in normalized for cue in _CONTENT_CUES):
        score += 2
        matched_rules.append("content_cue")
    if len(normalized) >= 6:
        score += 1
        matched_rules.append("length_ge_6")
    if any(cue in normalized for cue in _STRUCTURE_CUES):
        score += 1
        matched_rules.append("structure_cue")

    if score >= 2:
        return {
            "send": True,
            "reason_code": "score_pass",
            "layer": "score_fallback",
            "score": score,
            "normalized_text": normalized,
            "matched_rules": matched_rules or ["score_pass"],
        }
    return {
        "send": False,
        "reason_code": "score_block_low_semantics",
        "layer": "score_fallback",
        "score": score,
        "normalized_text": normalized,
        "matched_rules": matched_rules or ["score_block_low_semantics"],
    }


def _log_decision_snapshot(
    *,
    session_id: uuid.UUID,
    stage: str,
    request: InclassUtteranceRequest,
    response: dict | None = None,
    supervisor_payload: dict | None = None,
    supervisor_raw: dict | None = None,
    request_turn_id: str | None = None,
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
                "class_elapsed_sec": request.class_elapsed_sec,
                "slide_no": request.slide_no,
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
        if request_turn_id:
            row["request_turn_id"] = request_turn_id
        _DECISION_LOGGER.info(json.dumps(row, ensure_ascii=False))
    except Exception:
        # 决策日志不可影响主流程
        return


def _log_decision_event(
    *,
    session_id: uuid.UUID,
    stage: str,
    payload: dict,
    note: str | None = None,
) -> None:
    try:
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": str(session_id),
            "stage": stage,
            **payload,
        }
        if note:
            row["note"] = note
        _DECISION_LOGGER.info(json.dumps(row, ensure_ascii=False))
    except Exception:
        return


def _extract_resolved_student_event(student_event: Any) -> dict | None:
    if isinstance(student_event, dict):
        return student_event
    if isinstance(student_event, list):
        for item in student_event:
            if isinstance(item, dict):
                return item
    return None


def _log_resolved_interaction_event(
    *,
    session_id: uuid.UUID,
    stage: str,
    request: InclassUtteranceRequest,
    request_turn_id: str,
    interaction_round_id: str,
    dialog_state: str,
    student_event: Any,
    preset_for_student_id: str | None,
    session_students: list[SessionStudent],
) -> None:
    resolved = _extract_resolved_student_event(student_event)
    if not isinstance(resolved, dict):
        return
    student_id = str(
        resolved.get("student_id")
        or preset_for_student_id
        or ""
    ).strip()
    student_name = ""
    if student_id:
        one = next((s for s in session_students if s.student_id == student_id), None)
        if one is not None:
            student_name = str(one.student_name or "").strip()
    row = {
        "request": {
            "role": request.role,
            "content": request.content,
            "current_timestamp": request.current_timestamp,
            "class_elapsed_sec": request.class_elapsed_sec,
            "slide_no": request.slide_no,
            "called_student_id": request.called_student_id,
        },
        "request_turn_id": request_turn_id,
        "interaction_round_id": interaction_round_id,
        "dialog_state": dialog_state,
        "resolved_student": {
            "student_id": student_id or None,
            "student_name": student_name or None,
            "student_type": resolved.get("student_type"),
            "reply_text": resolved.get("reply_text"),
            "emotion": resolved.get("emotion"),
            "is_proactive_speaking": resolved.get("is_proactive_speaking"),
        },
    }
    _log_decision_event(
        session_id=session_id,
        stage=stage,
        payload=row,
    )


def _parse_uuid(raw: str, name: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{name} 不是合法 UUID") from exc


def _class_time_label(elapsed_sec: int | None) -> str | None:
    if elapsed_sec is None:
        return None
    try:
        sec = max(int(elapsed_sec), 0)
    except (TypeError, ValueError):
        return None
    minutes = sec // 60
    remain = sec % 60
    return f"{minutes:02d}:{remain:02d}"


def _build_question_bundle_title(
    *,
    question_bundle_text: str,
    question_items: list[dict],
    min_len: int = 18,
    max_len: int = 30,
) -> str:
    raw = str(question_bundle_text or "").strip()
    items = []
    for item in question_items or []:
        if not isinstance(item, dict):
            continue
        txt = str(item.get("text") or "").strip()
        if txt:
            items.append(txt)
    if not raw and items:
        raw = "；".join(items)
    if not raw:
        return "连续提问要点梳理与学生回应"

    # 清洗“问题X：”等前缀，优先保留问题核心。
    text = raw
    text = text.replace("\n", "；")
    text = text.replace("？", "；").replace("?", "；")
    text = text.replace("。", "；")
    text = text.replace("，", "，")
    text = text.strip("；，。 ")
    text = re.sub(r"问题\s*\d+\s*[:：]\s*", "", text)
    parts = [p.strip("；，。 ") for p in re.split(r"[；]+", text) if p.strip("；，。 ")]
    if not parts:
        parts = [text]

    core = "；".join(parts[:2])
    if len(parts) > 2:
        core = f"{core}等{len(parts)}问"
    count = max(int(len(items) or 0), 1)
    prefix = "提问" if count <= 1 else "连续提问"
    title = f"{prefix}：{core}"

    # 长度约束到 18~30，过长截断，过短补语义后缀。
    if len(title) > max_len:
        title = title[: max_len - 1].rstrip("；，。 ") + "…"
    if len(title) < min_len:
        suffix = "（核心问题）"
        title = (title + suffix)[:max_len]
    return title


def _get_session_or_404(
    db: Session,
    raw_session_id: str,
    current_user: User,
) -> ClassroomSession:
    # 使用 joinedload 一次性 JOIN 拉取关联的 lesson，避免后续访问 session.lesson
    # 触发 N+1 lazy load。/utterance 是高频接口（每句话一次），未优化前每次至少
    # 2 次 SQL 往返；优化后降为 1 次。
    session = (
        db.query(ClassroomSession)
        .options(joinedload(ClassroomSession.lesson))
        .join(Lesson, Lesson.id == ClassroomSession.lesson_id)
        .filter(
            ClassroomSession.id == _parse_uuid(raw_session_id, "session_id"),
            Lesson.owner_user_id == current_user.id,
        )
        .first()
    )
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
    if body.slide_no:
        return _resolve_slide_context_from_lesson(session, body.slide_no)
    if body.ppt_text:
        return {
            "slide_no": body.slide_no,
            "title": f"第 {body.slide_no or 0} 页",
            "text_blocks": [body.ppt_text],
            "visual_elements": [],
            "summary": body.ppt_text[:120],
        }
    return None


def _resolve_slide_context_from_lesson(
    session: ClassroomSession,
    slide_no: int,
) -> dict | None:
    lesson_id = str(session.lesson_id)
    key = (lesson_id, int(slide_no))
    if key in _LESSON_SLIDE_CONTEXT_CACHE:
        return _LESSON_SLIDE_CONTEXT_CACHE[key]

    resolved: dict | None = None
    if session.lesson.ppt_payload:
        slides = session.lesson.ppt_payload.get("slides") or []
        for slide in slides:
            if int(slide.get("slide_no", 0) or 0) == int(slide_no):
                resolved = copy_slide_without_none(slide)
                break

    _LESSON_SLIDE_CONTEXT_CACHE[key] = resolved
    return resolved


def _resolve_utterance_current_ppt(
    session: ClassroomSession,
    *,
    current_ppt: list[dict] | None,
    slide_no: int | None,
) -> list[dict] | None:
    # 兼容旧前端：若已传 current_ppt，直接复用
    if current_ppt:
        return current_ppt
    # 新流程：仅传 slide_no，由后端根据课前解析结果补全当前页
    if slide_no:
        sid = str(session.id)
        normalized_slide_no = int(slide_no)
        cached = _SESSION_LAST_UTTERANCE_PPT_CACHE.get(sid)
        if cached and cached[0] == normalized_slide_no:
            return cached[1]

        resolved_slide = _resolve_slide_context_from_lesson(session, normalized_slide_no)
        payload = [resolved_slide] if resolved_slide else None
        _SESSION_LAST_UTTERANCE_PPT_CACHE[sid] = (normalized_slide_no, payload)
        return payload
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
    current_user: User = Depends(get_current_user),
):
    session = _get_session_or_404(db, body.session_id, current_user)
    event_ts = parse_iso_datetime(body.current_timestamp)
    role_type = _role_type_from_role(body.role)

    # 1. 保存 turn
    turn = SessionTurn(
        session_id=session.id,
        role_type=role_type,
        role_label=body.role,
        content=body.content,
        event_ts=event_ts,
        class_elapsed_sec=body.class_elapsed_sec,
        slide_no=body.slide_no,
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
    filter_decision = should_send_to_supervisor(
        text=body.content,
        called_student_id=body.called_student_id,
        session_students=session_students,
    )
    filter_payload = {
        "request": {
            "role": body.role,
            "content": body.content,
            "current_timestamp": body.current_timestamp,
            "class_elapsed_sec": body.class_elapsed_sec,
            "slide_no": body.slide_no,
            "called_student_id": body.called_student_id,
        },
        "filter": filter_decision,
    }
    if not filter_decision.get("send", False):
        db.commit()
        _log_decision_event(
            session_id=session.id,
            stage="pre_supervisor_filtered",
            payload=filter_payload,
            note=f"skip supervisor due to {filter_decision.get('reason_code')}",
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    _log_decision_event(
        session_id=session.id,
        stage="pre_supervisor_passed",
        payload=filter_payload,
        note=f"pass supervisor via {filter_decision.get('reason_code')}",
    )

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
    payload = {
        "teacher_text": body.content,
        "class_elapsed_sec": body.class_elapsed_sec,
        "subject": session.lesson.subject,
        "chat_history": _build_chat_history(recent_turns),
        "current_ppt": _resolve_utterance_current_ppt(
            session,
            current_ppt=body.current_ppt,
            slide_no=body.slide_no,
        ),
        "called_student_status_digest": called_student_digest,
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
        lesson_atmosphere = session.lesson.atmosphere if session.lesson else ""
        atmosphere_tier = normalize_atmosphere(lesson_atmosphere)
        raw_difficulty = result.get("question_difficulty")
        difficulty_band = normalize_question_difficulty(raw_difficulty)
        if raw_difficulty is None:
            logging.getLogger(__name__).info(
                "questioning 未返回 question_difficulty，使用 medium；session=%s",
                session.id,
            )
        raised_hand_ids = select_questioning_hand_raises(
            session_id=session.id,
            interaction_round_id=interaction_round_id,
            students=session_students,
            atmosphere=atmosphere_tier,
            difficulty_band=difficulty_band,
        )
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

    # supervisor 判定 normal：前端无需消费标准化 JSON，返回 204 最小响应即可
    if dialog_state == "normal":
        _log_decision_snapshot(
            session_id=session.id,
            stage="supervisor_decision_normal_204",
            request=body,
            supervisor_payload=payload,
            supervisor_raw=result,
            request_turn_id=str(turn.id),
            note="normal state, return 204 no content",
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

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
        request_turn_id=str(turn.id),
        response=resp.model_dump(),
    )
    resolved_stage_map = {
        "ambiguous": "ambiguous_resolved",
        "misstatement": "misstatement_resolved",
        "relay_answer": "relay_answer_resolved",
        "discipline_sleep": "discipline_sleep_resolved",
        "discipline_whisper": "discipline_whisper_resolved",
    }
    resolved_stage = resolved_stage_map.get(dialog_state)
    if resolved_stage:
        _log_resolved_interaction_event(
            session_id=session.id,
            stage=resolved_stage,
            request=body,
            request_turn_id=str(turn.id),
            interaction_round_id=interaction_round_id,
            dialog_state=dialog_state,
            student_event=student_event,
            preset_for_student_id=preset_for_id,
            session_students=session_students,
        )
    return resp


@router.post("/student-reply", response_model=StudentReplyResponse)
async def post_student_reply(
    body: StudentReplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """前端点名后实时获取被点名学生的单条回复。"""
    session = _get_session_or_404(db, body.session_id, current_user)

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
    resolved_current_ppt = _resolve_utterance_current_ppt(
        session,
        current_ppt=body.current_ppt,
        slide_no=body.slide_no,
    )
    if resolved_current_ppt and len(resolved_current_ppt) > 0:
        ppt_slide = resolved_current_ppt[0]
        background["slide_no"] = ppt_slide.get("slide_no")
        background["slides"] = [ppt_slide]

    # 对话历史拆分为 teacher / student utterances
    class_ts = _class_time_label(body.class_elapsed_sec) or body.current_timestamp or ""
    teacher_utterances = []
    student_utterances = []
    for msg in chat_history:
        if msg.get("role") == "teacher":
            teacher_utterances.append({"ts": class_ts, "text": msg.get("content", "")})
        elif msg.get("role") == "student":
            student_utterances.append(
                {
                    "ts": class_ts,
                    "text": msg.get("content", ""),
                    "student_id": "",
                }
            )
    if teacher_utterances:
        background["teacher_utterances_on_slide"] = teacher_utterances
    if student_utterances:
        background["student_utterances_on_slide"] = student_utterances
    bundle_text = str(body.question_bundle_text or "").strip()
    bundle_items = body.question_items or []
    question_count = int(body.question_count or 0)
    if question_count <= 0:
        question_count = max(len(bundle_items), 1)
    if bundle_text or bundle_items:
        background["question_bundle"] = {
            "text": bundle_text,
            "count": question_count,
            "items": bundle_items,
        }

    # 4. 调用 AI 模块生成单条回复
    was_hand_raised = bool(student.is_hand_raised)
    ai_client = AIClient()
    try:
        ai_result = await ai_client.student_reply(
            {
                "student_type": student.student_type,
                "trigger_reason": "teacher_question",
                "is_proactive_speaking": was_hand_raised,
                "background": background,
            }
        )
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    # 只要触发一名学生发言，就清空全班举手状态，避免回答后仍举手
    reset_hand_raised(session.id, db)
    db.commit()

    question_count = int(body.question_count or 0)
    question_items = body.question_items or []
    if question_count <= 0:
        question_count = max(len(question_items), 1)
    question_bundle_text = str(body.question_bundle_text or "").strip()
    bundle_title = _build_question_bundle_title(
        question_bundle_text=question_bundle_text,
        question_items=question_items,
    )
    _log_decision_event(
        session_id=session.id,
        stage="questioning_bundle_resolved",
        payload={
            "request": {
                "student_id": body.student_id,
                "current_timestamp": body.current_timestamp,
                "class_elapsed_sec": body.class_elapsed_sec,
                "slide_no": body.slide_no,
            },
            "bundle": {
                "bundle_title": bundle_title,
                "question_count": question_count,
                "question_bundle_text": question_bundle_text,
                "question_items": question_items,
            },
            "resolved_student_reply": {
                "student_id": student.student_id,
                "student_name": student.student_name,
                "student_type": student.student_type,
                "reply_text": ai_result.get("reply_text", "（无回复）"),
                "emotion": ai_result.get("emotion", "idle"),
                "is_proactive_speaking": ai_result.get(
                    "is_proactive_speaking", was_hand_raised
                ),
            },
        },
    )

    return StudentReplyResponse(
        student_id=student.student_id,
        student_type=student.student_type,
        reply_text=ai_result.get("reply_text", "（无回复）"),
        emotion=ai_result.get("emotion", "idle"),
        is_proactive_speaking=ai_result.get("is_proactive_speaking", was_hand_raised),
    )


@router.get("/student-state/{student_id}", response_model=StudentStateResponse)
def get_student_state(
    student_id: str,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if session_id:
        session = _get_session_or_404(db, session_id, current_user)
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
def get_all_student_states(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session_or_404(db, session_id, current_user)
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
    current_user: User = Depends(get_current_user),
):
    session = _get_session_or_404(db, body.session_id, current_user)
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
    segment_payload = {
        **ai_payload,
        "start_elapsed_sec": body.start_elapsed_sec,
        "end_elapsed_sec": body.end_elapsed_sec,
    }
    if ppt_context:
        ai_payload["ppt_context"] = ppt_context
        segment_payload["ppt_context"] = ppt_context

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
            segment_payload=segment_payload,
        )
        db.add(row)
    else:
        row.start_ts = start_ts
        row.end_ts = end_ts
        row.slide_no = body.slide_no
        row.segment_payload = segment_payload

    ai_client = AIClient()
    try:
        eval_payload = await ai_client.segment_eval(ai_payload)
    except AIServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    row.eval_payload = eval_payload
    db.commit()
    return eval_payload
