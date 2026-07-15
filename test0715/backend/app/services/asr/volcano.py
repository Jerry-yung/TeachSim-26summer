"""
火山引擎（豆包语音）大模型录音文件极速版识别。
文档: https://www.volcengine.com/docs/6561/1631584

鉴权：旧版控制台 —— X-Api-App-Key（APP ID）+ X-Api-Access-Key（Access Token）
"""
from __future__ import annotations

import base64
import uuid

import httpx

FLASH_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"


def _build_headers(
    *,
    app_id: str,
    access_token: str,
    resource_id: str,
    request_id: str,
) -> dict[str, str]:
    return {
        "X-Api-App-Key": app_id,
        "X-Api-Access-Key": access_token,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
        "X-Api-Sequence": "-1",
        "Content-Type": "application/json",
    }


async def transcribe_flash(
    *,
    app_id: str | None,
    access_token: str | None,
    resource_id: str,
    audio_bytes: bytes,
    trust_env: bool = False,
) -> tuple[str, dict]:
    if not (app_id and app_id.strip()):
        raise RuntimeError("请配置 VOLC_ASR_APP_ID（控制台 APP ID，对应 X-Api-App-Key）")
    if not (access_token and access_token.strip()):
        raise RuntimeError(
            "请配置 VOLC_ASR_ACCESS_TOKEN（控制台 Access Token，对应 X-Api-Access-Key）"
        )

    app_id = app_id.strip()
    access_token = access_token.strip()
    req_id = str(uuid.uuid4())
    headers = _build_headers(
        app_id=app_id,
        access_token=access_token,
        resource_id=resource_id,
        request_id=req_id,
    )
    body = {
        "user": {"uid": app_id},
        "audio": {"data": base64.b64encode(audio_bytes).decode("ascii")},
        "request": {"model_name": "bigmodel"},
    }

    try:
        async with httpx.AsyncClient(
            timeout=120.0,
            trust_env=trust_env,
        ) as client:
            r = await client.post(FLASH_URL, json=body, headers=headers)
    except httpx.RequestError as exc:
        hint = (
            "若需使用系统/环境代理访问外网，可在 .env 设置 VOLC_HTTP_TRUST_ENV=true"
            if not trust_env
            else "请检查代理是否可用，或尝试 VOLC_HTTP_TRUST_ENV=false 直连"
        )
        raise RuntimeError(
            f"无法连接火山语音接口（网络/代理/TLS）: {exc!s}。{hint}"
        ) from exc

    status = r.headers.get("X-Api-Status-Code", "")
    msg = r.headers.get("X-Api-Message", "")
    logid = r.headers.get("X-Tt-Logid", "")

    try:
        payload = r.json()
    except Exception:
        payload = {"_raw": r.text[:2000]}

    raw_out = {
        "headers": {
            "X-Api-Status-Code": status,
            "X-Api-Message": msg,
            "X-Tt-Logid": logid,
        },
        "body": payload,
    }

    if status == "20000000":
        result = payload.get("result") or {}
        text = (result.get("text") or "").strip()
        return text, raw_out

    if status == "20000003":
        # 静音
        return "", raw_out

    if r.status_code >= 400:
        raise RuntimeError(
            f"火山 ASR HTTP {r.status_code} status={status} msg={msg} logid={logid}"
        )

    raise RuntimeError(
        f"火山 ASR 失败 status={status} msg={msg} logid={logid} body={payload}"
    )
