"""课中视觉观察 schemas。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class VisualObservationRequest(BaseModel):
    session_id: str
    observation_id: str
    segment_id: Optional[str] = None
    window_start_sec: int = 0
    window_end_sec: int = 15
    slide_no: Optional[int] = None
    # 1-3 张帧图 base64（JPEG），可选——也可通过文件上传
    frames_b64: Optional[List[str]] = None
    # 最近 20 条师生 chat history
    chat_history: List[Dict[str, Any]] = []
    # MediaPipe 预检是否通过（前端自报）
    precheck_passed: bool = True


class VisualObservationResponse(BaseModel):
    observation_id: str
    status: str          # accepted / skipped
    message: str = ""
