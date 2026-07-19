from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InitLessonResponse(BaseModel):
    lesson_id: str
    session_id: Optional[str] = None
    status: str = "processing"
    message: str = "教案上传成功，正在后台提取知识点"


class LessonStatusResponse(BaseModel):
    lesson_id: str
    embedding_status: str
    lesson_topic: str
    subject: str
    subject_icon: str
    knowledge_points_preview: List[Dict[str, Any]]
    teacher_questions: List[Dict[str, Any]]


class TranscribeResponse(BaseModel):
    text: str
    provider: str
