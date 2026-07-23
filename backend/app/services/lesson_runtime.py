from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

# 课堂展示时间统一按中国时区（与前端 toLocaleString 默认行为一致）
DISPLAY_TZ = ZoneInfo("Asia/Shanghai")


def parse_iso_datetime(value: str) -> datetime:
    text = (value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def format_display_datetime(
    dt: datetime | None,
    fmt: str = "%Y-%m-%d %H:%M",
) -> str:
    """将库内 UTC（或带时区）时间格式化为本地展示字符串。"""
    if dt is None:
        return ""
    aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    return aware.astimezone(DISPLAY_TZ).strftime(fmt)


def guess_subject_icon(subject: str) -> str:
    text = subject or ""
    if "数学" in text:
        return "🔢"
    if "语文" in text or "文学" in text:
        return "📖"
    if "英语" in text or "外语" in text:
        return "🌍"
    if "物理" in text:
        return "⚛️"
    if "化学" in text:
        return "🧪"
    if "生物" in text:
        return "🧬"
    if "历史" in text:
        return "🏛️"
    if "地理" in text:
        return "🗺️"
    if "政治" in text or "道德" in text:
        return "⚖️"
    if "音乐" in text:
        return "🎵"
    if "美术" in text or "艺术" in text:
        return "🎨"
    if "体育" in text:
        return "⚽"
    return "📚"


def build_min_lesson_payload(
    *,
    grade: str,
    subject: str,
    custom_goal: str,
    teacher_context: str | None,
) -> dict[str, Any]:
    objective = custom_goal.strip() or "理解本节课核心内容"
    return {
        "basic_info": {
            "lesson_topic": "未上传教案",
            "subject": subject or "通用",
            "lesson_type": "模拟课堂",
            "grade": grade,
        },
        "teaching_objectives": {
            "knowledge": objective,
            "ability": "提升课堂表达与组织能力",
            "emotion": teacher_context or "建立自然的课堂互动节奏",
        },
        "knowledge_points": [
            {
                "id": "kp1",
                "point": objective,
                "difficulty": "中",
                "category": "概念",
                "description": teacher_context or "未提供教案，按通用课堂训练处理",
                "tags": ["课堂模拟"],
                "prerequisite": "基础知识",
            }
        ],
    }


def copy_slide_without_none(slide: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in slide.items():
        if value is None:
            continue
        if isinstance(value, list):
            out[key] = [x for x in value if x is not None]
        else:
            out[key] = value
    return out
