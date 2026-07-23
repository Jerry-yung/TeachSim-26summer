"""
讯飞 ASR WebSocket 签名服务

将原本暴露在前端 bundle 里的 `API_KEY` / `API_SECRET` 收到后端，
前端只通过鉴权接口拿一次性签名 URL 就能直连讯飞 WebSocket。

讯飞 IAT v2 协议（已稳定多年，未变）：
    Authorization = base64(api_key="…", algorithm="hmac-sha256",
                           headers="host date request-line",
                           signature=hmac_sha256(secret, signOrigin))
    signOrigin   = "host: iat-api.xfyun.cn\\ndate: <RFC 7231 GMT>\\nGET /v2/iat HTTP/1.1"

`date` 头限制窗口（讯飞要求 ±5min），所以本服务签出的 URL 也只在
~5min 内有效，泄漏后影响面有限——这是 token-vending 模式的安全前提。

设计参考：
- 同样的 HMAC 签名前端代码原本在 `frontend/src/api/xfyunAsr.js::buildAuthUrl()`
- 把这一段挪到后端，并加上鉴权与配置完整性检查
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from email.utils import formatdate
from typing import NamedTuple
from urllib.parse import quote

# 讯飞官方 v2 端点（与前端原实现一致，避免协议偏移）
_XFYUN_HOST = "iat-api.xfyun.cn"
_XFYUN_PATH = "/v2/iat"
_XFYUN_URL_BASE = f"wss://{_XFYUN_HOST}{_XFYUN_PATH}"


class XfyunSignedUrl(NamedTuple):
    """签好名的 WebSocket URL + APP_ID（前端建立连接用 APP_ID 作 common.app_id）。"""

    ws_url: str
    app_id: str


class XfyunConfigError(RuntimeError):
    """讯飞配置缺失或不完整 — 后端没法签名，应当 503 而不是 500。"""


def build_signed_ws_url(
    app_id: str,
    api_key: str,
    api_secret: str,
    *,
    now_rfc7231: str | None = None,
) -> XfyunSignedUrl:
    """
    构造已签名的讯飞 ASR WebSocket URL。

    Args:
        app_id, api_key, api_secret: 讯飞控制台拿到的三件套（**仅后端持有**）
        now_rfc7231: 测试用注入点；生产环境不传，自动取 UTC now

    Raises:
        XfyunConfigError: 任何一个三件套为空字符串/None

    Returns:
        XfyunSignedUrl(ws_url, app_id) — 前端拿 ws_url 直接 `new WebSocket(url)`
    """
    if not (app_id and api_key and api_secret):
        # 不在错误里回显具体哪个字段为空，避免给攻击者侦察信息
        raise XfyunConfigError(
            "讯飞 ASR 配置未在后端 .env 中完整设置 "
            "(需要 XFYUN_APP_ID / XFYUN_API_KEY / XFYUN_API_SECRET)"
        )

    date = now_rfc7231 or formatdate(usegmt=True)  # RFC 7231 GMT
    sign_origin = (
        f"host: {_XFYUN_HOST}\n"
        f"date: {date}\n"
        f"GET {_XFYUN_PATH} HTTP/1.1"
    )

    signature_bytes = hmac.new(
        api_secret.encode("utf-8"),
        sign_origin.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_bytes).decode("ascii")

    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(
        authorization_origin.encode("utf-8")
    ).decode("ascii")

    ws_url = (
        f"{_XFYUN_URL_BASE}"
        f"?authorization={quote(authorization, safe='')}"
        f"&date={quote(date, safe='')}"
        f"&host={_XFYUN_HOST}"
    )
    return XfyunSignedUrl(ws_url=ws_url, app_id=app_id)
