from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx"}
MAX_BYTES = 20 * 1024 * 1024


def ensure_upload_root() -> Path:
    root = Path(get_settings().upload_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_upload_path(rel_storage_path: str) -> Path:
    root = ensure_upload_root()
    rel = Path(rel_storage_path or "")
    abs_path = (root / rel).resolve()
    if root != abs_path and root not in abs_path.parents:
        raise ValueError("非法文件路径")
    return abs_path


async def save_lesson_file(lesson_id: uuid.UUID, upload: UploadFile) -> tuple[str, int]:
    name = upload.filename or "upload"
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型，允许: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    root = ensure_upload_root()
    dest_dir = root / str(lesson_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4()
    dest_path = dest_dir / f"{file_id}{suffix}"

    size = 0
    chunk_size = 1024 * 1024
    with dest_path.open("wb") as f:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                dest_path.unlink(missing_ok=True)
                raise ValueError("文件超过 20MB 限制")
            f.write(chunk)

    rel = dest_path.relative_to(root)
    return str(rel).replace("\\", "/"), size
