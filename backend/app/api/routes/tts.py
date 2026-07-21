"""
MiniMax T2A 代理（短连接 WebSocket → 聚合 MP3 二进制流）

密钥仅在后端 .env；前端 POST 本接口获取音频并播放，失败时降级浏览器 speechSynthesis。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.deps.auth import get_current_user
from app.models.auth import User
from app.schemas.tts import MinimaxTTSRequest
from app.services.minimax_t2a import MinimaxT2AError, synthesize_speech_ws

router = APIRouter(tags=["tts"])


@router.post("/tts/minimax/synthesize")
async def minimax_synthesize(
    body: MinimaxTTSRequest,
    _current_user: User = Depends(get_current_user),
) -> Response:
    try:
        audio_bytes = await synthesize_speech_ws(
            body.text,
            student_id=body.student_id,
        )
    except MinimaxT2AError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store"},
    )
