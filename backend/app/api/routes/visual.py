"""课中视觉观察路由。

POST /api/inclass/visual-observation
  接收前端上传的 2-3s WebM clip + 缩略图帧 + 元数据
  写库后异步调用 AI VLM 分析，202 立即返回

GET  /api/report/{session_id}/visual-clip/{observation_id}
  鉴权后流式返回 WebM clip（供报告时间轴点击回放）
"""
from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.auth import User
from app.models.lesson import ClassroomSession, Lesson, SessionTurn, SessionVisualObservation
from app.schemas.visual import VisualObservationResponse
from app.services.ai_client import AIClient, AIServiceError
from app.services.storage import ensure_upload_root, resolve_upload_path

router = APIRouter(tags=["visual"])
logger = logging.getLogger(__name__)

_VISUAL_RETENTION_DAYS = 30
_CLIP_MAX_BYTES = 5 * 1024 * 1024   # 5MB 单窗口上限
_THUMB_MAX_BYTES = 500 * 1024        # 500KB


def _get_session_or_404(db: Session, session_id: str, user: User) -> ClassroomSession:
    try:
        sid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="session_id 不是合法 UUID") from exc
    row = (
        db.query(ClassroomSession)
        .join(Lesson, Lesson.id == ClassroomSession.lesson_id)
        .filter(
            ClassroomSession.id == sid,
            Lesson.owner_user_id == user.id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="session 不存在")
    return row


def _visual_dir(session_id: str) -> Path:
    root = ensure_upload_root()
    d = root / "visual" / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _save_file_bytes(dest: Path, upload: UploadFile, max_bytes: int) -> int:
    size = 0
    with dest.open("wb") as f:
        while True:
            chunk = await upload.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="文件超过大小限制")
            f.write(chunk)
    return size


def _load_frames_for_obs(
    obs: SessionVisualObservation,
    frames_b64: list[str],
) -> list[str]:
    if frames_b64:
        return frames_b64
    rel = obs.thumbnail_path or obs.clip_path
    if not rel:
        return []
    try:
        file_path = resolve_upload_path(rel)
        if not file_path.exists():
            return []
        raw = file_path.read_bytes()
        if rel.lower().endswith(".webm"):
            return []
        return [base64.b64encode(raw).decode()]
    except Exception:
        return []


async def _run_vlm_analysis(
    session_id_str: str,
    obs_id_str: str,
    frames_b64: list[str],
    chat_history: list[dict],
    window_start_sec: int,
    window_end_sec: int,
    segment_id: Optional[str],
    slide_no: Optional[int],
) -> None:
    """后台任务：调用 AI VLM，把结果写回数据库。"""
    from app.db.session import get_session_factory

    db: Session = get_session_factory()()
    try:
        obs = (
            db.query(SessionVisualObservation)
            .filter(SessionVisualObservation.observation_id == obs_id_str)
            .first()
        )
        if obs is None:
            return

        payload_frames = _load_frames_for_obs(obs, frames_b64)
        ai = AIClient()
        try:
            result = await ai.visual_analyze({
                "observation_id": obs_id_str,
                "session_id": session_id_str,
                "segment_id": segment_id or "",
                "window_start_sec": window_start_sec,
                "window_end_sec": window_end_sec,
                "slide_no": slide_no,
                "frames_b64": payload_frames,
                "chat_history": chat_history,
            })
            obs.vlm_payload = result
            obs.vlm_status = "done"
        except AIServiceError as exc:
            obs.vlm_status = "failed"
            obs.vlm_payload = {"error": str(exc)}
            logger.warning("VLM failed for %s: %s", obs_id_str, exc)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("VLM task crashed for %s: %s", obs_id_str, exc)
        try:
            obs = (
                db.query(SessionVisualObservation)
                .filter(SessionVisualObservation.observation_id == obs_id_str)
                .first()
            )
            if obs is not None:
                obs.vlm_status = "failed"
                obs.vlm_payload = {"error": str(exc)}
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def _schedule_vlm_analysis(**kwargs: Any) -> None:
    """FastAPI BackgroundTasks 对 async 任务不可靠；改用 create_task。"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("No running event loop; cannot schedule VLM for %s", kwargs.get("obs_id_str"))
        return
    loop.create_task(_run_vlm_analysis(**kwargs))


@router.post(
    "/inclass/visual-observation",
    response_model=VisualObservationResponse,
    status_code=202,
)
async def post_visual_observation(
    session_id: str = Form(...),
    observation_id: str = Form(...),
    segment_id: Optional[str] = Form(None),
    window_start_sec: int = Form(0),
    window_end_sec: int = Form(15),
    slide_no: Optional[int] = Form(None),
    precheck_passed: bool = Form(True),
    # 最近 20 条师生对话 JSON 字符串
    chat_history_json: str = Form("[]"),
    # 缩略图（第一帧 JPEG，可选）
    thumbnail: Optional[UploadFile] = File(None),
    # 2-3 秒 WebM clip（可选）
    clip: Optional[UploadFile] = File(None),
    # frames_b64：前端也可直接把帧编码后放 form-data（备用）
    frames_b64_json: str = Form("[]"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """接收单个 15s 视觉窗口数据，异步触发 VLM 分析，立即返回 202。"""
    import json as _json

    session = _get_session_or_404(db, session_id, current_user)
    settings = get_settings()

    try:
        chat_history: list[dict] = _json.loads(chat_history_json) or []
    except Exception:
        chat_history = []
    try:
        frames_b64: list[str] = _json.loads(frames_b64_json) or []
    except Exception:
        frames_b64 = []

    if not precheck_passed:
        return VisualObservationResponse(
            observation_id=observation_id,
            status="skipped",
            message="precheck_not_passed",
        )

    vdir = _visual_dir(session_id)
    expires = datetime.now(timezone.utc) + timedelta(days=_VISUAL_RETENTION_DAYS)

    clip_rel: Optional[str] = None
    thumb_rel: Optional[str] = None

    if clip is not None:
        clip_name = f"{observation_id}.webm"
        clip_path = vdir / clip_name
        await _save_file_bytes(clip_path, clip, _CLIP_MAX_BYTES)
        root = ensure_upload_root()
        clip_rel = str(clip_path.relative_to(root)).replace("\\", "/")

        # 若前端没有单独传缩略图，尝试从 frames_b64 获取第一帧写文件
        if thumbnail is None and frames_b64:
            try:
                thumb_path = vdir / f"{observation_id}_thumb.jpg"
                thumb_path.write_bytes(base64.b64decode(frames_b64[0]))
                thumb_rel = str(thumb_path.relative_to(root)).replace("\\", "/")
            except Exception:
                pass

    if thumbnail is not None:
        thumb_name = f"{observation_id}_thumb.jpg"
        thumb_path_f = vdir / thumb_name
        await _save_file_bytes(thumb_path_f, thumbnail, _THUMB_MAX_BYTES)
        root = ensure_upload_root()
        thumb_rel = str(thumb_path_f.relative_to(root)).replace("\\", "/")
        if not frames_b64:
            frames_b64 = [base64.b64encode(thumb_path_f.read_bytes()).decode()]

    if frames_b64 and not thumb_rel:
        try:
            thumb_path = vdir / f"{observation_id}_thumb.jpg"
            thumb_path.write_bytes(base64.b64decode(frames_b64[0]))
            root = ensure_upload_root()
            thumb_rel = str(thumb_path.relative_to(root)).replace("\\", "/")
        except Exception:
            pass

    if not frames_b64 and clip_rel is None:
        return VisualObservationResponse(
            observation_id=observation_id,
            status="skipped",
            message="no_visual_payload",
        )

    obs = SessionVisualObservation(
        id=uuid.uuid4(),
        session_id=session.id,
        observation_id=observation_id,
        segment_id=segment_id,
        window_start_sec=window_start_sec,
        window_end_sec=window_end_sec,
        slide_no=slide_no,
        clip_path=clip_rel,
        thumbnail_path=thumb_rel,
        vlm_status="pending",
        precheck_passed=precheck_passed,
        expires_at=expires,
    )
    db.add(obs)
    db.commit()

    # 取最近 20 条 SessionTurn 补充 chat_history（若前端未传）
    if not chat_history:
        turns = (
            db.query(SessionTurn)
            .filter(SessionTurn.session_id == session.id)
            .order_by(SessionTurn.event_ts.desc())
            .limit(20)
            .all()
        )
        chat_history = [
            {
                "role": t.role_type,
                "text": t.content,
                "class_elapsed_sec": t.class_elapsed_sec,
            }
            for t in reversed(turns)
        ]

    _schedule_vlm_analysis(
        session_id_str=session_id,
        obs_id_str=observation_id,
        frames_b64=frames_b64,
        chat_history=chat_history,
        window_start_sec=window_start_sec,
        window_end_sec=window_end_sec,
        segment_id=segment_id,
        slide_no=slide_no,
    )

    return VisualObservationResponse(
        observation_id=observation_id,
        status="accepted",
    )


@router.get("/report/{session_id}/visual-clip/{observation_id}")
def get_visual_clip(
    session_id: str,
    observation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """鉴权后返回 WebM clip 文件（报告时间轴点击回放）。"""
    _get_session_or_404(db, session_id, current_user)

    obs = (
        db.query(SessionVisualObservation)
        .filter(SessionVisualObservation.observation_id == observation_id)
        .first()
    )
    if obs is None or not obs.clip_path:
        raise HTTPException(status_code=404, detail="clip 不存在")

    file_path = (ensure_upload_root() / obs.clip_path).resolve()
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="clip 文件已过期或被删除")

    return FileResponse(
        path=str(file_path),
        media_type="video/webm",
        filename=f"{observation_id}.webm",
    )


@router.get("/report/{session_id}/visual-thumb/{observation_id}")
def get_visual_thumb(
    session_id: str,
    observation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """鉴权后返回缩略图 JPEG。"""
    _get_session_or_404(db, session_id, current_user)

    obs = (
        db.query(SessionVisualObservation)
        .filter(SessionVisualObservation.observation_id == observation_id)
        .first()
    )
    if obs is None or not obs.thumbnail_path:
        raise HTTPException(status_code=404, detail="缩略图不存在")

    file_path = (ensure_upload_root() / obs.thumbnail_path).resolve()
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="缩略图文件已过期或被删除")

    return FileResponse(
        path=str(file_path),
        media_type="image/jpeg",
        filename=f"{observation_id}_thumb.jpg",
    )
