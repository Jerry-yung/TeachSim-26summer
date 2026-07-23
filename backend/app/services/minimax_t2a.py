from __future__ import annotations

import asyncio
import json
import ssl
from typing import Any, Optional

import websockets

from app.core.config import Settings, get_settings

# 仅按课堂人物 student_id 选音色（与 agent_type / 举手睡觉等状态无关）
STUDENT_ID_VOICE = {
    "student_xm": "male-qn-qingse",       # 小明 · 男 · 清涩青年
    "student_xw": "female-shaonv",        # 小红 · 女 · 少女
    "student_xw2": "male-qn-jingying",    # 小王 · 男 · 精英青年
    "student_xl": "female-chengshu",      # 小乐 · 女 · 成熟女性（官方无 female-daxuesheng）
}

DEFAULT_VOICE = "male-qn-qingse"


class MinimaxT2AError(RuntimeError):
    pass


def resolve_voice_id(*, student_id: Optional[str] = None) -> str:
    if student_id and student_id in STUDENT_ID_VOICE:
        return STUDENT_ID_VOICE[student_id]
    return DEFAULT_VOICE


def default_voice_setting(voice_id: str) -> dict[str, Any]:
    return {
        "voice_id": voice_id,
        "speed": 1.0,
        "vol": 1.0,
        "pitch": 0,
        "english_normalization": False,
    }


def _check_base_resp(message: dict[str, Any]) -> None:
    base = message.get("base_resp") or {}
    code = base.get("status_code", 0)
    if code and int(code) != 0:
        status_msg = base.get("status_msg") or f"MiniMax status_code={code}"
        raise MinimaxT2AError(str(status_msg))


async def _recv_json(ws: websockets.WebSocketClientProtocol, timeout: float) -> dict[str, Any]:
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise MinimaxT2AError("MiniMax 返回非 JSON 对象")
    return payload


async def synthesize_speech_ws(
    text: str,
    *,
    student_id: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> bytes:
    """
    Short-lived WebSocket T2A: connect → task_start → task_continue → collect audio → task_finish.
    Returns concatenated MP3 bytes.
    """
    cfg = settings or get_settings()
    api_key = (cfg.minimax_api_key or "").strip()
    if not api_key:
        raise MinimaxT2AError("MINIMAX_API_KEY 未配置")

    content = (text or "").strip()
    if not content:
        raise MinimaxT2AError("合成文本为空")
    if len(content) > 2000:
        content = content[:2000]

    voice_id = resolve_voice_id(student_id=student_id)
    voice_setting = default_voice_setting(voice_id)

    timeout = float(cfg.minimax_t2a_timeout_s)
    ws_url = (cfg.minimax_t2a_ws_url or "").strip()
    if not ws_url:
        raise MinimaxT2AError("MINIMAX_T2A_WS_URL 未配置")

    headers = {"Authorization": f"Bearer {api_key}"}
    ssl_context = ssl.create_default_context()

    audio_parts: list[bytes] = []

    async with websockets.connect(
        ws_url,
        additional_headers=headers,
        ssl=ssl_context,
        open_timeout=timeout,
        close_timeout=5,
    ) as ws:
        connected = await _recv_json(ws, timeout)
        if connected.get("event") != "connected_success":
            raise MinimaxT2AError(f"建连失败: {connected.get('event')}")
        _check_base_resp(connected)

        start_msg = {
            "event": "task_start",
            "model": cfg.minimax_t2a_model,
            "voice_setting": voice_setting,
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        }
        await ws.send(json.dumps(start_msg, ensure_ascii=False))
        started = await _recv_json(ws, timeout)
        event = started.get("event")
        if event == "task_failed":
            _check_base_resp(started)
            raise MinimaxT2AError("MiniMax task_start 失败")
        if event != "task_started":
            raise MinimaxT2AError(f"task_start 未确认: {event}")
        _check_base_resp(started)

        await ws.send(
            json.dumps({"event": "task_continue", "text": content}, ensure_ascii=False)
        )

        while True:
            message = await _recv_json(ws, timeout)
            event = message.get("event")
            if event == "task_failed":
                _check_base_resp(message)
                raise MinimaxT2AError("MiniMax 合成任务失败")

            _check_base_resp(message)

            data = message.get("data") or {}
            hex_audio = data.get("audio") if isinstance(data, dict) else None
            if hex_audio:
                try:
                    audio_parts.append(bytes.fromhex(hex_audio))
                except ValueError as exc:
                    raise MinimaxT2AError("MiniMax 音频 hex 解码失败") from exc

            if message.get("is_final"):
                break

        try:
            await ws.send(json.dumps({"event": "task_finish"}))
        except Exception:
            pass

    if not audio_parts:
        raise MinimaxT2AError("MiniMax 未返回音频数据")

    return b"".join(audio_parts)
