"""讯飞 ASR 签名接口 schemas（响应只回必要字段，不回 secret）。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class XfyunSignResponse(BaseModel):
    """前端建立 WebSocket 所需的最小信息。"""

    ws_url: str = Field(
        ...,
        description="已签名的讯飞 ASR WebSocket URL；URL 自带的 date 头约 5 分钟内有效",
    )
    app_id: str = Field(
        ...,
        description="讯飞应用 ID — 前端发首帧 common.app_id 用",
    )
    expires_in_seconds: int = Field(
        300,
        description="URL 大致有效期（秒）。讯飞官方按 date 头 ±5min 校验。",
    )
