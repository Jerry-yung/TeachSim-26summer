from __future__ import annotations

import asyncio
from pathlib import Path
import uuid

from app.db.session import session_scope
from app.models.lesson import Lesson, LessonFile
from app.services.ai_client import AIClient
from app.services.defaults import DEFAULT_TEACHER_QUESTIONS
from app.services.lesson_runtime import build_min_lesson_payload, guess_subject_icon
from app.services.storage import ensure_upload_root

_PPT_EXTENSIONS = {".pptx"}


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


def _should_parse_ppt(filename: str, content_type: str | None) -> bool:
    suffix = Path(filename or "").suffix.lower()
    if suffix in _PPT_EXTENSIONS:
        return True
    ctype = (content_type or "").lower()
    return "presentationml.presentation" in ctype


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
    content = file_path.read_bytes()
    need_ppt_parse = _should_parse_ppt(filename, content_type)

    lesson_task = ai_client.parse_lesson_file(
        filename=filename,
        content=content,
        grade=grade,
        subject=subject,
        content_type=content_type,
    )
    ppt_task = (
        ai_client.parse_ppt_file(
            filename=filename,
            content=content,
            content_type=content_type,
        )
        if need_ppt_parse
        else None
    )

    if ppt_task is None:
        lesson_result = await asyncio.gather(lesson_task, return_exceptions=True)
        lesson_payload = lesson_result[0]
        ppt_payload = None
    else:
        lesson_payload, ppt_payload = await asyncio.gather(
            lesson_task,
            ppt_task,
            return_exceptions=True,
        )

    lesson_error = lesson_payload if isinstance(lesson_payload, Exception) else None
    ppt_error = ppt_payload if isinstance(ppt_payload, Exception) else None
    lesson_payload_ok = None if lesson_error else lesson_payload
    ppt_payload_ok = None if ppt_error else ppt_payload

    with session_scope() as db:
        lesson = db.get(Lesson, lesson_uuid)
        if lesson is None:
            return

        errors: list[str] = []
        if lesson_error is not None:
            errors.append(f"教案解析失败(extractor): {lesson_error}")
        if need_ppt_parse and ppt_error is not None:
            errors.append(f"PPT解析失败(preclass_ppt_llm): {ppt_error}")

        if lesson_payload_ok is not None:
            lesson.lesson_payload = lesson_payload_ok
            enrich_lesson_from_payload(lesson, lesson_payload_ok)

        if ppt_payload_ok is not None:
            lesson.ppt_payload = ppt_payload_ok

        if lesson_payload_ok is None:
            lesson.embedding_status = "error"
            lesson.analysis_error = " | ".join(errors) if errors else "课前解析失败"
            return

        lesson.embedding_status = "done"
        lesson.analysis_error = " | ".join(errors) if errors else None
