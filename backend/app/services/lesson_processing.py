from __future__ import annotations

from pathlib import Path
import uuid

from app.db.session import session_scope
from app.models.lesson import Lesson, LessonFile
from app.services.ai_client import AIClient
from app.services.defaults import DEFAULT_TEACHER_QUESTIONS
from app.services.lesson_runtime import build_min_lesson_payload, guess_subject_icon
from app.services.storage import ensure_upload_root


def enrich_lesson_from_payload(lesson: Lesson, payload: dict | None) -> None:
    if not payload:
        return
    basic = payload.get("basic_info") or {}
    subject = str(basic.get("subject") or lesson.subject or "").strip()
    lesson_topic = str(basic.get("lesson_topic") or lesson.lesson_topic or "").strip()
    if subject:
        lesson.subject = subject
        lesson.subject_icon = guess_subject_icon(subject)
    if lesson_topic:
        lesson.lesson_topic = lesson_topic
    if "teacher_questions" not in payload:
        payload["teacher_questions"] = DEFAULT_TEACHER_QUESTIONS


async def analyze_lesson_in_background(lesson_id: str) -> None:
    lesson_uuid = uuid.UUID(lesson_id)
    with session_scope() as db:
        lesson = db.get(Lesson, lesson_uuid)
        if lesson is None:
            return
        file_row = (
            db.query(LessonFile)
            .filter(LessonFile.lesson_id == lesson.id)
            .order_by(LessonFile.created_at.asc())
            .first()
        )
        if file_row is None:
            lesson.lesson_payload = build_min_lesson_payload(
                grade=lesson.grade,
                subject=lesson.subject,
                custom_goal=lesson.custom_goal,
                teacher_context=lesson.teacher_context,
            )
            lesson.embedding_status = "done"
            enrich_lesson_from_payload(lesson, lesson.lesson_payload)
            return

        root = ensure_upload_root()
        file_path = root / Path(file_row.storage_path)
        if not file_path.exists():
            lesson.embedding_status = "error"
            lesson.analysis_error = f"找不到上传文件: {file_row.storage_path}"
            return

        lesson.embedding_status = "processing"
        grade = lesson.grade
        subject = lesson.subject
        filename = file_row.original_filename
        content_type = file_row.content_type

    ai_client = AIClient()
    try:
        content = file_path.read_bytes()
        payload = await ai_client.parse_lesson_file(
            filename=filename,
            content=content,
            grade=grade,
            subject=subject,
            content_type=content_type,
        )
    except Exception as exc:
        with session_scope() as db:
            lesson = db.get(Lesson, lesson_uuid)
            if lesson is None:
                return
            lesson.embedding_status = "error"
            lesson.analysis_error = str(exc)
        return

    with session_scope() as db:
        lesson = db.get(Lesson, lesson_uuid)
        if lesson is None:
            return
        lesson.lesson_payload = payload
        lesson.analysis_error = None
        lesson.embedding_status = "done"
        enrich_lesson_from_payload(lesson, payload)
