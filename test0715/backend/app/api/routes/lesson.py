from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lesson import ClassroomSession, Lesson, LessonFile
from app.schemas.lesson import InitLessonResponse, LessonStatusResponse
from app.services.defaults import DEFAULT_TEACHER_QUESTIONS
from app.services.lesson_processing import (
    analyze_lesson_in_background,
    enrich_lesson_from_payload,
)
from app.services.lesson_runtime import build_min_lesson_payload, guess_subject_icon
from app.services.storage import save_lesson_file

router = APIRouter(tags=["lesson"])

CLASS_LEVELS = {"重点班", "普通班", "平行班"}
ATMOSPHERES = {"活跃", "沉闷", "活跃互动型", "沉浸讲解型", "严谨讨论型", "练习主导型"}


def _parse_json_field(name: str, raw: Optional[str]) -> Optional[dict]:
    if raw is None or not raw.strip():
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"{name} 不是合法 JSON") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=400, detail=f"{name} 必须是 JSON 对象")
    return value


def _parse_uuid(raw: str, name: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{name} 不是合法 UUID") from exc


@router.post("/init_lesson", response_model=InitLessonResponse)
async def init_lesson(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    grade: str = Form(...),
    subject: str = Form(...),
    class_level: str = Form(...),
    atmosphere: str = Form(...),
    custom_goal: str = Form(""),
    teacher_context: Optional[str] = Form(None),
    lesson_json: Optional[str] = Form(None),
    ppt_json: Optional[str] = Form(None),
    teaching_preferences_json: Optional[str] = Form(None),
    frontend_session_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
) -> InitLessonResponse:
    if class_level not in CLASS_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"class_level 必须是：{', '.join(sorted(CLASS_LEVELS))}",
        )
    if atmosphere not in ATMOSPHERES:
        raise HTTPException(
            status_code=400,
            detail=f"atmosphere 必须是：{', '.join(sorted(ATMOSPHERES))}",
        )

    lesson_payload = _parse_json_field("lesson_json", lesson_json)
    ppt_payload = _parse_json_field("ppt_json", ppt_json)
    teaching_preferences = _parse_json_field(
        "teaching_preferences_json", teaching_preferences_json
    )

    lesson = Lesson(
        grade=grade.strip(),
        subject=subject.strip(),
        class_level=class_level.strip(),
        atmosphere=atmosphere.strip(),
        custom_goal=custom_goal.strip(),
        teacher_context=teacher_context.strip() if teacher_context else None,
        embedding_status="pending",
        lesson_payload=lesson_payload,
        ppt_payload=ppt_payload,
        teaching_preferences=teaching_preferences,
        subject_icon=guess_subject_icon(subject.strip()),
    )

    if lesson_payload:
        if teaching_preferences:
            lesson_payload["teaching_preferences"] = teaching_preferences
        enrich_lesson_from_payload(lesson, lesson_payload)
        lesson.embedding_status = "done"
    elif file is None:
        lesson.lesson_payload = build_min_lesson_payload(
            grade=lesson.grade,
            subject=lesson.subject,
            custom_goal=lesson.custom_goal,
            teacher_context=lesson.teacher_context,
        )
        if teaching_preferences:
            lesson.lesson_payload["teaching_preferences"] = teaching_preferences
        enrich_lesson_from_payload(lesson, lesson.lesson_payload)
        lesson.embedding_status = "done"

    db.add(lesson)
    db.flush()

    if file is not None and (file.filename or "").strip():
        try:
            storage_path, size = await save_lesson_file(lesson.id, file)
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        db.add(
            LessonFile(
                lesson_id=lesson.id,
                original_filename=file.filename or "upload",
                content_type=file.content_type,
                size_bytes=size,
                storage_path=storage_path,
            )
        )

    session = ClassroomSession(
        lesson_id=lesson.id,
        status="pending" if lesson.embedding_status != "done" else "ready",
        frontend_session_id=frontend_session_id.strip()
        if frontend_session_id and frontend_session_id.strip()
        else None,
    )
    db.add(session)
    db.commit()

    if file is not None and lesson.embedding_status != "done":
        background_tasks.add_task(analyze_lesson_in_background, str(lesson.id))
        return InitLessonResponse(
            lesson_id=str(lesson.id),
            session_id=str(session.id),
            status="processing",
            message="教案上传成功，正在后台提取知识点",
        )

    return InitLessonResponse(
        lesson_id=str(lesson.id),
        session_id=str(session.id),
        status="ready",
        message="课堂初始化成功",
    )


@router.get("/lesson/{lesson_id}/status", response_model=LessonStatusResponse)
def get_lesson_status(
    lesson_id: str,
    db: Session = Depends(get_db),
) -> LessonStatusResponse:
    lesson = db.get(Lesson, _parse_uuid(lesson_id, "lesson_id"))
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson 不存在")

    payload = lesson.lesson_payload or {}
    basic = payload.get("basic_info") or {}
    knowledge_points = payload.get("knowledge_points") or []
    preview = []
    for item in knowledge_points[:3]:
        if not isinstance(item, dict):
            continue
        preview.append(
            {
                "point": str(item.get("point") or "未命名知识点"),
                "difficulty": str(item.get("difficulty") or "中"),
            }
        )

    teacher_questions = payload.get("teacher_questions")
    if not isinstance(teacher_questions, list) or not teacher_questions:
        teacher_questions = DEFAULT_TEACHER_QUESTIONS

    return LessonStatusResponse(
        lesson_id=str(lesson.id),
        embedding_status=lesson.embedding_status,
        lesson_topic=str(
            basic.get("lesson_topic") or lesson.lesson_topic or "未识别课题"
        ),
        subject=str(basic.get("subject") or lesson.subject or "通用"),
        subject_icon=lesson.subject_icon or guess_subject_icon(lesson.subject),
        knowledge_points_preview=preview,
        teacher_questions=teacher_questions,
    )
