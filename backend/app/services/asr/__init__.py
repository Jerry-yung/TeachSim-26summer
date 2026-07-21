from __future__ import annotations

from app.core.config import Settings

from app.services.asr.volcano import transcribe_flash


async def transcribe_audio(
    settings: Settings,
    audio_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> tuple[str, str, dict]:
    _ = (filename, content_type)  # 与调用方 UploadFile 元数据对齐；火山 flash 由服务端识别格式

    raw_label = (settings.asr_provider or "volcengine").strip()
    provider = raw_label.lower()
    if provider in ("volcengine", "volc", "huoshan") or raw_label in ("火山", "火山引擎"):
        text, payload = await transcribe_flash(
            app_id=settings.volc_asr_app_id or None,
            access_token=settings.volc_asr_access_token or None,
            resource_id=settings.volc_asr_resource_id,
            audio_bytes=audio_bytes,
            trust_env=settings.volc_http_trust_env,
        )
        return text, "volcengine", payload
    if provider == "aliyun":
        raise NotImplementedError("阿里云 ASR 尚未实现")
    raise RuntimeError(f"未知 ASR_PROVIDER: {provider}（当前仅支持 volcengine）")
