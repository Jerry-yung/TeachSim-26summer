from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, get_settings


class AIServiceError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        payload: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class AIClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.base_url = self.settings.ai_service_url.rstrip("/")
        self.timeout = httpx.Timeout(self.settings.ai_timeout_s)

    async def parse_lesson_file(
        self,
        *,
        filename: str,
        content: bytes,
        grade: str = "",
        subject: str = "",
        content_type: str | None = None,
    ) -> dict[str, Any]:
        files = {
            "file": (filename, content, content_type or "application/octet-stream"),
        }
        data = {"grade": grade, "subject": subject}
        return await self._post_multipart("/ai/parse_lesson", data=data, files=files)

    async def parse_lessons(
        self,
        *,
        files: list[tuple[str, bytes, str | None]],
        grade: str = "",
        subject: str = "",
    ) -> dict[str, Any]:
        req_files = [
            ("files", (name, content, content_type or "application/octet-stream"))
            for name, content, content_type in files
        ]
        data = {"grade": grade, "subject": subject}
        return await self._post_multipart("/ai/parse_lessons", data=data, files=req_files)

    async def supervisor_decide(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post_json("/ai/v2/inclass/supervisor/decide", payload)

    async def segment_eval(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post_json("/ai/v2/inclass/segment/eval", payload)

    async def generate_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post_json("/ai/v2/postclass/report/generate", payload)

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
            except httpx.HTTPError as exc:
                raise AIServiceError(f"AI 服务调用失败: {exc}") from exc
        return self._parse_response(response)

    async def _post_multipart(
        self,
        path: str,
        *,
        data: dict[str, Any],
        files: Any,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, data=data, files=files)
            except httpx.HTTPError as exc:
                raise AIServiceError(f"AI 服务调用失败: {exc}") from exc
        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text[:2000]}

        if response.status_code >= 400:
            message = payload.get("detail") if isinstance(payload, dict) else payload
            raise AIServiceError(
                f"AI 服务返回错误: {message}",
                status_code=502,
                payload=payload,
            )
        if not isinstance(payload, dict):
            raise AIServiceError(
                "AI 服务返回非 JSON 对象",
                status_code=502,
                payload=payload,
            )
        return payload
