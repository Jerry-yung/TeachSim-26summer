"""
讯飞 ASR 签名路由（前端 token-vending）

为什么需要：原本前端 `xfyunAsr.js` 直接读 `VITE_XFYUN_API_KEY/SECRET` 算 HMAC，
意味着密钥被打进客户端 bundle，F12 即可窃取（盗刷讯飞账户）。

修复模式：
1. 后端独占 `XFYUN_API_KEY/SECRET`（不带 VITE_ 前缀，绝不暴露给前端）
2. 前端登录后调 `POST /api/asr/xfyun/sign` 拿一次性签名 URL
3. URL 自带过期（讯飞 date 头 ±5min），泄漏后影响窗口很小

要求：调用方必须携带有效 JWT Bearer token，未登录直接 401。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps.auth import get_current_user
from app.models.auth import User
from app.core.config import get_settings
from app.schemas.asr import XfyunSignResponse
from app.services.xfyun_sign import (
    XfyunConfigError,
    build_signed_ws_url,
)

router = APIRouter(tags=["asr"])


@router.post("/asr/xfyun/sign", response_model=XfyunSignResponse)
def sign_xfyun_ws_url(
    _current_user: User = Depends(get_current_user),
) -> XfyunSignResponse:
    """
    返回一次性的讯飞 ASR WebSocket 签名 URL。

    - 鉴权：JWT Bearer token（未登录 401）
    - 配置缺失：503（让运维知道需要补 .env，而不是让前端误判为代码 bug）
    - 成功：返回 ws_url + app_id + 大致有效期
    """
    settings = get_settings()
    try:
        signed = build_signed_ws_url(
            app_id=settings.xfyun_app_id,
            api_key=settings.xfyun_api_key,
            api_secret=settings.xfyun_api_secret,
        )
    except XfyunConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return XfyunSignResponse(
        ws_url=signed.ws_url,
        app_id=signed.app_id,
        expires_in_seconds=300,
    )
