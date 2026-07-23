from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


def parse_iso_dt(value: str) -> datetime:
    text = (value or "").strip()
    if not text:
        raise ValueError("时间戳不能为空")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("时间戳必须是合法 ISO8601 字符串") from exc


class InclassUtteranceRequest(BaseModel):
    session_id: str
    role: str
    content: str
    current_timestamp: str
    class_elapsed_sec: Optional[int] = None
    called_student_id: Optional[str] = None
    discipline_student_id: Optional[str] = None  # 前端触发 discipline 时的目标学生
    slide_no: Optional[int] = None
    current_ppt: Optional[List[Dict[str, Any]]] = None
    skip_supervisor: bool = False
    discipline_action: Optional[str] = None  # start_whisper | start_sleep | cancel_whisper | cancel_sleep

    @field_validator("role", "content", "current_timestamp")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("字段不能为空")
        return value.strip()


class SegmentTurnPayload(BaseModel):
    speaker: str
    ts: str
    text: str

    @field_validator("speaker", "ts", "text")
    @classmethod
    def _turn_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("片段字段不能为空")
        return value.strip()


class InclassSegmentRequest(BaseModel):
    session_id: str
    segment_id: str
    start_ts: str
    end_ts: str
    start_elapsed_sec: Optional[int] = None
    end_elapsed_sec: Optional[int] = None
    slide_no: Optional[int] = None
    teacher_utterances: List[SegmentTurnPayload] = Field(default_factory=list)
    student_utterances: List[SegmentTurnPayload] = Field(default_factory=list)
    ppt_context: Optional[Dict[str, Any]] = None
    current_ppt: Optional[List[Dict[str, Any]]] = None
    ppt_text: Optional[str] = None

    @field_validator("session_id", "segment_id", "start_ts", "end_ts")
    @classmethod
    def _segment_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("字段不能为空")
        return value.strip()


class StudentStateItem(BaseModel):
    student_id: str
    student_type: str
    is_hand_raised: bool


class InclassUtteranceResponse(BaseModel):
    dialog_state: str
    should_trigger_student: bool
    trigger_reason: Optional[str] = None
    target_student_type: Optional[str] = None
    interaction_round_id: str
    play_mode: str  # immediate | on_call_name
    raised_hand_student_ids: List[str] = Field(default_factory=list)
    preset_for_student_id: Optional[str] = None
    student_states_digest: List[StudentStateItem] = Field(default_factory=list)
    preset_consumed: bool = False
    student_event: Optional[Any] = None


class StudentStateResponse(BaseModel):
    student_id: str
    student_type: str
    is_hand_raised: bool
    is_sleeping: bool = False
    is_whispering: bool = False
    student_name: str = ""


class StudentReplyRequest(BaseModel):
    session_id: str
    student_id: str
    current_timestamp: str
    class_elapsed_sec: Optional[int] = None
    slide_no: Optional[int] = None
    current_ppt: Optional[List[Dict[str, Any]]] = None
    question_bundle_text: Optional[str] = None
    question_count: Optional[int] = None
    question_items: Optional[List[Dict[str, Any]]] = None


class StudentReplyResponse(BaseModel):
    student_id: str
    student_type: str
    reply_text: str
    emotion: str
    is_proactive_speaking: bool
