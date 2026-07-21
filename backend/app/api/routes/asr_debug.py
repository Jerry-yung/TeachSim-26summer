from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.lesson import Transcript
from app.schemas.lesson import TranscribeResponse
from app.services.asr import transcribe_audio

router = APIRouter(tags=["debug"])

# 火山极速版建议单请求约 20MB 内；调试接口略放宽
MAX_ASR_BYTES = 20 * 1024 * 1024


@router.post("/transcribe", response_model=TranscribeResponse)
async def debug_transcribe(
    db: Session = Depends(get_db),
    audio: UploadFile = File(
        ...,
        description="wav / mp3 / ogg（火山豆包极速版识别）",
    ),
    lesson_id: Optional[str] = Form(
        None,
        description="可选，关联 lessons.id（标准 UUID）。非 UUID 会忽略，不报错",
    ),
) -> TranscribeResponse:
    settings = get_settings()
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="空音频文件")
    if len(data) > MAX_ASR_BYTES:
        raise HTTPException(status_code=400, detail="音频超过 20MB，请截短后重试")

    try:
        text, provider, raw = await transcribe_audio(
            settings,
            data,
            filename=audio.filename,
            content_type=audio.content_type,
        )
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    lid: Optional[uuid.UUID] = None
    if lesson_id and lesson_id.strip():
        try:
            lid = uuid.UUID(lesson_id.strip())
        except ValueError:
            # 前端可能传路由里的 session-xxx、mock id 等，调试接口不强制 UUID
            lid = None

    if settings.asr_debug_persist:
        try:
            row = Transcript(
                session_id=None,
                lesson_id=lid,
                source="debug_upload",
                text=text,
                provider=provider,
                raw_payload=raw,
            )
            db.add(row)
            db.commit()
        except Exception:
            db.rollback()

    return TranscribeResponse(text=text, provider=provider)
