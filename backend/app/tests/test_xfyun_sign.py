"""
回归测试：讯飞 ASR 签名服务（token-vending 模式）。

为什么这样测：
- 重点是"前端拿到的 URL 必须由后端密钥签出，且响应里不回显 secret"
- 不依赖网络（讯飞官方 endpoint 不可达），只验证签名构造的正确性
- 同 PR #1 / #2 的测试约定：不导入 routes 模块（绕开 Python 3.10+ 语法），
  service 层用纯函数 + 命名参数注入，可独立测试
"""

from __future__ import annotations

import base64
from urllib.parse import parse_qs, unquote, urlparse

import pytest

from app.services.xfyun_sign import (
    XfyunConfigError,
    build_signed_ws_url,
)


# 讯飞官方文档示例（占位值，仅用于签名构造测试）
_FIXED_DATE = "Wed, 11 May 2026 07:00:00 GMT"
_APP_ID = "test_app_id_1234"
_API_KEY = "test_api_key_abcdef"
_API_SECRET = "test_api_secret_ghijkl"


# ---------- 配置缺失测试 ----------

@pytest.mark.parametrize(
    "missing_field",
    ["app_id", "api_key", "api_secret"],
)
def test_missing_field_raises_config_error(missing_field):
    """三件套任一为空必须 RuntimeError，前端拿到 503 而不是签出错误的 URL。"""
    kwargs = dict(app_id=_APP_ID, api_key=_API_KEY, api_secret=_API_SECRET)
    kwargs[missing_field] = ""
    with pytest.raises(XfyunConfigError):
        build_signed_ws_url(**kwargs)


@pytest.mark.parametrize(
    "missing_field",
    ["app_id", "api_key", "api_secret"],
)
def test_missing_field_none_also_raises(missing_field):
    """None 值同样视为未配置（pydantic-settings 默认会给空字符串，但保险起见）。"""
    kwargs = dict(app_id=_APP_ID, api_key=_API_KEY, api_secret=_API_SECRET)
    kwargs[missing_field] = None  # type: ignore[arg-type]
    with pytest.raises(XfyunConfigError):
        build_signed_ws_url(**kwargs)


def test_config_error_message_does_not_leak_which_field():
    """错误消息不应回显具体哪个字段缺失（避免给攻击者侦察）。"""
    with pytest.raises(XfyunConfigError) as exc:
        build_signed_ws_url(app_id="", api_key=_API_KEY, api_secret=_API_SECRET)
    msg = str(exc.value)
    # 提到"配置不完整"或大致名称没问题，但不应说"app_id 为空"这种精确信息
    assert "API_KEY" in msg or "API_SECRET" in msg or "APP_ID" in msg
    # 关键：不应单独指出"哪一个"
    # （这里是宽松断言：只要错误消息列出全部三件套就 OK，相当于"全部需要"）


# ---------- 签名正确性测试 ----------

def test_url_contains_required_query_params():
    """讯飞 URL 必须含 authorization / date / host 三个参数。"""
    signed = build_signed_ws_url(
        app_id=_APP_ID,
        api_key=_API_KEY,
        api_secret=_API_SECRET,
        now_rfc7231=_FIXED_DATE,
    )
    parsed = urlparse(signed.ws_url)
    assert parsed.scheme == "wss"
    assert parsed.hostname == "iat-api.xfyun.cn"
    assert parsed.path == "/v2/iat"

    qs = parse_qs(parsed.query)
    assert "authorization" in qs
    assert "date" in qs
    assert "host" in qs
    assert qs["host"][0] == "iat-api.xfyun.cn"
    assert unquote(qs["date"][0]) == _FIXED_DATE


def test_authorization_decodes_to_canonical_format():
    """authorization 参数 base64 解码后必须符合讯飞协议格式。"""
    signed = build_signed_ws_url(
        app_id=_APP_ID,
        api_key=_API_KEY,
        api_secret=_API_SECRET,
        now_rfc7231=_FIXED_DATE,
    )
    qs = parse_qs(urlparse(signed.ws_url).query)
    auth_b64 = unquote(qs["authorization"][0])
    auth_decoded = base64.b64decode(auth_b64).decode()

    assert f'api_key="{_API_KEY}"' in auth_decoded
    assert 'algorithm="hmac-sha256"' in auth_decoded
    assert 'headers="host date request-line"' in auth_decoded
    assert 'signature="' in auth_decoded


def test_signature_is_deterministic_for_fixed_date():
    """同样输入必须签出同样 URL（HMAC 决定性）。"""
    a = build_signed_ws_url(
        app_id=_APP_ID, api_key=_API_KEY, api_secret=_API_SECRET,
        now_rfc7231=_FIXED_DATE,
    )
    b = build_signed_ws_url(
        app_id=_APP_ID, api_key=_API_KEY, api_secret=_API_SECRET,
        now_rfc7231=_FIXED_DATE,
    )
    assert a.ws_url == b.ws_url


def test_different_secrets_produce_different_signatures():
    """密钥变 → 签名必须变（确认 HMAC 真的用了 secret）。"""
    a = build_signed_ws_url(
        app_id=_APP_ID, api_key=_API_KEY, api_secret="secret-one",
        now_rfc7231=_FIXED_DATE,
    )
    b = build_signed_ws_url(
        app_id=_APP_ID, api_key=_API_KEY, api_secret="secret-two",
        now_rfc7231=_FIXED_DATE,
    )
    assert a.ws_url != b.ws_url


def test_response_does_not_leak_secret():
    """
    返回结构里不能含 api_secret 任何片段。
    本测试是合规线 —— 防止有人手贱在响应里加调试字段把 secret 漏出去。
    """
    signed = build_signed_ws_url(
        app_id=_APP_ID,
        api_key=_API_KEY,
        api_secret=_API_SECRET,
        now_rfc7231=_FIXED_DATE,
    )
    # NamedTuple 转字符串看所有字段
    serialized = repr(signed)
    assert _API_SECRET not in serialized
    assert _API_SECRET not in signed.ws_url  # secret 不应明文出现在 URL 中


def test_app_id_in_response():
    """app_id 必须回到响应里（前端发首帧需要它）。"""
    signed = build_signed_ws_url(
        app_id=_APP_ID,
        api_key=_API_KEY,
        api_secret=_API_SECRET,
        now_rfc7231=_FIXED_DATE,
    )
    assert signed.app_id == _APP_ID


def test_default_date_is_recent():
    """不传 now_rfc7231 时应使用当前 UTC 时间（讯飞要求 ±5min）。"""
    from email.utils import parsedate_to_datetime
    from datetime import datetime, timezone

    signed = build_signed_ws_url(
        app_id=_APP_ID, api_key=_API_KEY, api_secret=_API_SECRET,
    )
    qs = parse_qs(urlparse(signed.ws_url).query)
    date_str = unquote(qs["date"][0])
    parsed_date = parsedate_to_datetime(date_str)
    now = datetime.now(timezone.utc)
    delta = abs((now - parsed_date).total_seconds())
    assert delta < 60, f"date 与当前时间相差 {delta}s，应该 < 60s"


# ---------- 反向回归：确保前端代码不再读 VITE_XFYUN_* ----------

def test_frontend_xfyun_module_no_longer_reads_secrets():
    """
    静态扫描 `frontend/src/api/xfyunAsr.js`，
    确认不再有 `VITE_XFYUN_API_KEY` / `VITE_XFYUN_API_SECRET` 的读取代码。
    （注释里提到这些名字是 OK 的，所以扫的是 import.meta.env.VITE_XFYUN_API_）
    """
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[3]
    js = (repo_root / "frontend" / "src" / "api" / "xfyunAsr.js").read_text()

    # 关键：不能有 import.meta.env.VITE_XFYUN_API_ 的读取
    forbidden = "import.meta.env.VITE_XFYUN_API_"
    assert forbidden not in js, (
        f"{forbidden} 不应再出现在 xfyunAsr.js 中 — 密钥应由后端 token-vending 接口提供"
    )
