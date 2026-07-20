from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_teacher_id
from app.db.session import get_db
from app.models.lesson import ClassroomSession, Lesson, LessonFile
from app.schemas.lesson import InitLessonResponse, LessonStatusResponse
from app.services.defaults import DEFAULT_TEACHER_QUESTIONS
from app.services.lesson_processing import (
    analyze_lesson_in_background,
    enrich_lesson_from_payload,
)
from app.services.student_state import initialize_session_students
from app.services.lesson_runtime import build_min_lesson_payload, guess_subject_icon
from app.services.ppt_preview import convert_office_to_pdf
from app.services.storage import resolve_upload_path, save_lesson_file

router = APIRouter(tags=["lesson"])
_LEGACY_TEACHER_ID = "legacy_teacher"

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


def _find_preview_source_file(lesson: Lesson) -> LessonFile | None:
    files = sorted(lesson.files or [], key=lambda f: f.created_at, reverse=True)
    for f in files:
        ext = (f.original_filename or "").lower()
        if ext.endswith(".pdf") or ext.endswith(".ppt") or ext.endswith(".pptx"):
            return f
    return None


def _ppt_page_count(lesson: Lesson) -> int:
    payload = lesson.ppt_payload or {}
    deck = payload.get("deck_info") if isinstance(payload, dict) else {}
    if isinstance(deck, dict):
        for key in ("slide_count", "total_slides", "page_count"):
            raw = deck.get(key)
            try:
                n = int(raw)
                if n > 0:
                    return n
            except (TypeError, ValueError):
                continue
    slides = payload.get("slides") if isinstance(payload, dict) else None
    if isinstance(slides, list) and slides:
        return len(slides)
    source = _find_preview_source_file(lesson)
    if source is not None:
        try:
            src_abs = resolve_upload_path(source.storage_path)
            pdf_abs = (
                src_abs
                if src_abs.suffix.lower() == ".pdf"
                else src_abs.with_suffix(".pdf")
            )
            if pdf_abs.exists():
                from pypdf import PdfReader

                reader = PdfReader(str(pdf_abs))
                if len(reader.pages) > 0:
                    return len(reader.pages)
        except Exception:
            pass
    return 1


def _prepare_preview_pdf_background(storage_path: str) -> None:
    try:
        src_abs = resolve_upload_path(storage_path)
    except ValueError:
        return
    if not src_abs.exists():
        return
    # 课前预转换：课堂仅做读取，不在预览接口现场转换
    convert_office_to_pdf(src_abs)


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
    teacher_id: str = Depends(get_current_teacher_id),
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
    uploaded_storage_path: str | None = None

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
        uploaded_storage_path = storage_path

    session = ClassroomSession(
        lesson_id=lesson.id,
        teacher_id=teacher_id,
        status="pending" if lesson.embedding_status != "done" else "ready",
        frontend_session_id=frontend_session_id.strip()
        if frontend_session_id and frontend_session_id.strip()
        else None,
    )
    db.add(session)
    db.commit()

    # 初始化学生状态库
    initialize_session_students(session.id, class_level, db=db)
    db.commit()

    if uploaded_storage_path:
        suffix = Path(uploaded_storage_path).suffix.lower()
        if suffix in {".ppt", ".pptx"}:
            background_tasks.add_task(
                _prepare_preview_pdf_background,
                uploaded_storage_path,
            )

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


@router.get("/lesson/{lesson_id}/ppt-preview")
def get_lesson_ppt_preview(
    lesson_id: str,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_teacher_id),
):
    lesson = db.get(Lesson, _parse_uuid(lesson_id, "lesson_id"))
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson 不存在")

    has_access = any(
        s.teacher_id in {teacher_id, _LEGACY_TEACHER_ID}
        for s in (lesson.sessions or [])
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="无权访问该课堂")

    source = _find_preview_source_file(lesson)
    if source is None:
        return {
            "ready": False,
            "message": "未找到可预览课件文件",
            "preview_path": None,
            "page_count": _ppt_page_count(lesson),
        }

    src_abs = resolve_upload_path(source.storage_path)
    if not src_abs.exists():
        return {
            "ready": False,
            "message": "课件文件不存在或已被清理",
            "preview_path": None,
            "page_count": _ppt_page_count(lesson),
        }

    pdf_abs = src_abs if src_abs.suffix.lower() == ".pdf" else src_abs.with_suffix(".pdf")
    if pdf_abs is None or not pdf_abs.exists():
        return {
            "ready": False,
            "message": "课件预览尚在准备中（或转换能力未配置）",
            "preview_path": None,
            "page_count": _ppt_page_count(lesson),
        }

    return {
        "ready": True,
        "message": "ok",
        "preview_path": f"/api/lesson/{lesson.id}/ppt-preview/file",
        "page_count": _ppt_page_count(lesson),
    }


@router.get("/lesson/{lesson_id}/ppt-preview/file")
def stream_lesson_ppt_preview_file(
    lesson_id: str,
    db: Session = Depends(get_db),
    teacher_id_q: str | None = Query(default=None, alias="teacher_id"),
    x_teacher_id: str | None = Header(default=None, alias="X-Teacher-Id"),
):
    teacher_id = str(teacher_id_q or x_teacher_id or "").strip()
    if not teacher_id:
        raise HTTPException(status_code=401, detail="缺少教师身份，请重新登录")

    lesson = db.get(Lesson, _parse_uuid(lesson_id, "lesson_id"))
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson 不存在")

    has_access = any(
        s.teacher_id in {teacher_id, _LEGACY_TEACHER_ID}
        for s in (lesson.sessions or [])
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="无权访问该课堂")

    source = _find_preview_source_file(lesson)
    if source is None:
        raise HTTPException(status_code=404, detail="未找到可预览课件文件")
    src_abs = resolve_upload_path(source.storage_path)
    if not src_abs.exists():
        raise HTTPException(status_code=404, detail="课件文件不存在")

    pdf_abs = src_abs if src_abs.suffix.lower() == ".pdf" else src_abs.with_suffix(".pdf")
    if pdf_abs is None or not pdf_abs.exists():
        raise HTTPException(status_code=409, detail="预览文件尚未就绪")
    return FileResponse(
        path=pdf_abs,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{pdf_abs.stem}.pdf"'
        },
    )


@router.post("/session/{session_id}/restart", response_model=InitLessonResponse)
def restart_classroom_session(
    session_id: str,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_teacher_id),
) -> InitLessonResponse:
    old_session = db.get(ClassroomSession, _parse_uuid(session_id, "session_id"))
    if old_session is None:
        raise HTTPException(status_code=404, detail="session 不存在")
    if old_session.teacher_id not in {teacher_id, _LEGACY_TEACHER_ID}:
        raise HTTPException(status_code=403, detail="无权访问该课堂")

    lesson = old_session.lesson
    new_session = ClassroomSession(
        lesson_id=lesson.id,
        teacher_id=teacher_id,
        status="pending" if lesson.embedding_status != "done" else "ready",
        frontend_session_id=old_session.frontend_session_id,
    )
    db.add(new_session)
    db.commit()

    initialize_session_students(new_session.id, lesson.class_level, db=db)
    db.commit()

    return InitLessonResponse(
        lesson_id=str(lesson.id),
        session_id=str(new_session.id),
        status="ready" if lesson.embedding_status == "done" else "processing",
        message="已基于当前课前配置创建新课堂",
    )
