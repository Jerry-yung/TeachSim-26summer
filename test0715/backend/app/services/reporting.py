from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from app.models.lesson import ClassroomSession, SessionSegment, SessionTurn

FILLER_WORDS = ["然后", "就是", "对不对", "呃"]
QUESTION_TYPE_COLORS = {
    "封闭式": "#E5E7EB",
    "引导式": "#BFDBFE",
    "开放式": "#2563EB",
}
TIME_COLORS = {
    "课堂导入": "#6366F1",
    "新知讲授": "#2563EB",
    "互动问答": "#10B981",
    "总结巩固": "#F59E0B",
}


def build_ai_report_fallback(
    lesson_json: dict[str, Any],
    segment_evals: list[dict[str, Any]],
) -> dict[str, Any]:
    lesson_topic = (
        lesson_json.get("basic_info", {}).get("lesson_topic")
        or lesson_json.get("lesson_topic")
        or "未命名课程"
    )
    if not segment_evals:
        dimension_scores = {
            "instructional_clarity": 72,
            "student_engagement": 68,
            "pace_control": 70,
        }
    else:
        dimension_scores = {
            "instructional_clarity": int(
                sum(x["scores"]["instructional_clarity"] for x in segment_evals)
                / len(segment_evals)
            ),
            "student_engagement": int(
                sum(x["scores"]["student_engagement"] for x in segment_evals)
                / len(segment_evals)
            ),
            "pace_control": int(
                sum(x["scores"]["pace_control"] for x in segment_evals)
                / len(segment_evals)
            ),
        }
    overall_score = int(sum(dimension_scores.values()) / len(dimension_scores))
    improvement_pool = []
    for item in segment_evals:
        improvement_pool.extend(item.get("improvement_actions") or [])
    if not improvement_pool:
        improvement_pool = ["增加高质量追问链", "每页 PPT 结束前增加一次快速检测"]
    return {
        "lesson_topic": lesson_topic,
        "overall_score": overall_score,
        "dimension_scores": dimension_scores,
        "summary": f"{lesson_topic}课堂整体基础较稳，建议继续增强互动密度与节奏控制。",
        "priority_improvements": improvement_pool[:4],
    }


def build_report_response(
    session: ClassroomSession,
    turns: list[SessionTurn],
    segments: list[SessionSegment],
    lesson_json: dict[str, Any],
    ai_report: dict[str, Any],
) -> dict[str, Any]:
    started_at = session.started_at or session.created_at
    ended_at = session.ended_at or started_at
    duration_min = _duration_minutes(started_at, ended_at)
    hard_stats = _build_hard_stats(turns, started_at, ended_at)
    question_types = _build_question_types(turns)
    time_distribution = _build_time_distribution(segments, duration_min)
    dimensions, scores = _build_dimensions(ai_report)
    overall_level, overall_desc = _overall_level_and_desc(
        int(ai_report.get("overall_score") or 0),
        _normalize_report_wording(str(ai_report.get("summary") or "").strip()),
    )
    custom_goal_feedback = _build_custom_goal_feedback(
        lesson_json=lesson_json,
        ai_report=ai_report,
        scores=scores,
    )
    highlights = _build_highlight_events(segments, turns, started_at)
    lesson_topic = (
        ai_report.get("lesson_topic")
        or lesson_json.get("basic_info", {}).get("lesson_topic")
        or session.lesson.lesson_topic
        or "未命名课程"
    )
    subject = (
        lesson_json.get("basic_info", {}).get("subject")
        or session.lesson.subject
        or "通用"
    )
    class_info = " · ".join(
        x for x in [session.lesson.grade, session.lesson.class_level] if x
    )
    suggestions = _format_suggestions(ai_report)

    return {
        "session_id": str(session.id),
        "lesson_topic": lesson_topic,
        "subject": subject,
        "class_info": class_info,
        "created_at": started_at.strftime("%Y-%m-%d %H:%M"),
        "duration_min": duration_min,
        "overall_level": overall_level,
        "overall_desc": overall_desc,
        "dimensions": dimensions,
        "hard_stats": hard_stats,
        "time_distribution": time_distribution,
        "question_types": question_types,
        "custom_goal_feedback": custom_goal_feedback,
        "improvement_suggestions": suggestions,
        "is_improved": False,
        "history_comparison": "",
        "highlight_events": highlights,
        "scores": scores,
        "radar_chart_data": {
            "indicators": [item["label"] for item in dimensions],
            "values": [item["_val"] for item in dimensions],
        },
    }


def _duration_minutes(started_at: datetime, ended_at: datetime) -> int:
    seconds = max((ended_at - started_at).total_seconds(), 1)
    return max(1, int(round(seconds / 60)))


def _build_hard_stats(
    turns: list[SessionTurn],
    started_at: datetime,
    ended_at: datetime,
) -> dict[str, Any]:
    teacher_turns = [turn for turn in turns if turn.role_type == "teacher"]
    student_turns = [turn for turn in turns if turn.role_type == "student"]
    total_words = sum(len((turn.content or "").strip()) for turn in teacher_turns)
    duration_min = _duration_minutes(started_at, ended_at)
    avg_speed = int(round(total_words / duration_min)) if duration_min else 0

    wait_samples = []
    for turn in teacher_turns:
        if not _looks_like_question(turn.content):
            continue
        next_student = next(
            (
                candidate
                for candidate in student_turns
                if candidate.event_ts >= turn.event_ts
            ),
            None,
        )
        if next_student is None:
            continue
        wait_samples.append((next_student.event_ts - turn.event_ts).total_seconds())
    avg_wait = round(sum(wait_samples) / len(wait_samples), 1) if wait_samples else 0

    filler_counts = []
    teacher_blob = "\n".join(turn.content for turn in teacher_turns)
    for word in FILLER_WORDS:
        filler_counts.append({"word": word, "count": teacher_blob.count(word)})

    return {
        "total_duration_min": duration_min,
        "talk_duration_min": duration_min,
        "total_words": total_words,
        "avg_speed_wpm": avg_speed,
        "avg_wait_time_sec": avg_wait,
        "filler_words": filler_counts,
    }


def _build_question_types(turns: list[SessionTurn]) -> list[dict[str, Any]]:
    counts = Counter({"封闭式": 0, "引导式": 0, "开放式": 0})
    for turn in turns:
        if turn.role_type != "teacher":
            continue
        if not _looks_like_question(turn.content):
            continue
        counts[_classify_question(turn.content)] += 1
    return [
        {
            "type": q_type,
            "count": counts[q_type],
            "color": QUESTION_TYPE_COLORS[q_type],
        }
        for q_type in ["封闭式", "引导式", "开放式"]
    ]


def _build_time_distribution(
    segments: list[SessionSegment],
    duration_min: int,
) -> list[dict[str, Any]]:
    if not segments:
        return [
            {
                "segment": "新知讲授",
                "duration": duration_min,
                "color": TIME_COLORS["新知讲授"],
            }
        ]

    buckets: dict[str, float] = defaultdict(float)
    ordered = sorted(segments, key=lambda item: item.start_ts)
    for idx, segment in enumerate(ordered):
        seg_minutes = max((segment.end_ts - segment.start_ts).total_seconds() / 60, 0.5)
        payload = segment.segment_payload or {}
        student_utterances = payload.get("student_utterances") or []
        if idx == 0:
            label = "课堂导入"
        elif idx == len(ordered) - 1:
            label = "总结巩固"
        elif student_utterances:
            label = "互动问答"
        else:
            label = "新知讲授"
        buckets[label] += seg_minutes

    return [
        {
            "segment": label,
            "duration": max(1, int(round(minutes))),
            "color": TIME_COLORS[label],
        }
        for label, minutes in buckets.items()
    ]


def _build_dimensions(
    ai_report: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    dim = ai_report.get("dimension_scores") or {}
    clarity = int(dim.get("instructional_clarity") or 0)
    engagement = int(dim.get("student_engagement") or 0)
    pace = int(dim.get("pace_control") or 0)
    scores = {
        "content_accuracy": clarity,
        "syllabus_alignment": int(round((clarity + pace) / 2)),
        "interaction_quality": engagement,
        "pacing": pace,
        "language_appropriateness": int(round((clarity + pace) / 2)),
    }
    labels = {
        "content_accuracy": "内容准确",
        "syllabus_alignment": "教案贴合",
        "interaction_quality": "互动质量",
        "pacing": "课堂节奏",
        "language_appropriateness": "语言表达",
    }
    dimensions = []
    for key, value in scores.items():
        dimensions.append(
            {
                "key": key,
                "label": labels[key],
                "_val": value,
                "level": _level_badge(value),
            }
        )
    return dimensions, scores


def _overall_level_and_desc(overall_score: int, summary: str) -> tuple[str, str]:
    if overall_score >= 85:
        level = "整体优秀"
    elif overall_score >= 70:
        level = "整体良好"
    elif overall_score >= 60:
        level = "整体待提升"
    else:
        level = "整体需关注"
    if summary:
        return level, summary.strip()
    return level, "课堂表现已生成，可查看各维度详情"


def _build_custom_goal_feedback(
    *,
    lesson_json: dict[str, Any],
    ai_report: dict[str, Any],
    scores: dict[str, int],
) -> dict[str, Any] | None:
    prefs = lesson_json.get("teaching_preferences") or {}
    goal = (
        prefs.get("breakthrough_focus")
        or lesson_json.get("custom_goal")
        or lesson_json.get("teacher_context")
    )
    if not goal:
        return None
    if "互动" in goal or "提问" in goal:
        score = scores["interaction_quality"]
    elif "节奏" in goal or "时间" in goal:
        score = scores["pacing"]
    else:
        score = scores["language_appropriateness"]
    improvements = ai_report.get("priority_improvements") or []
    feedback = _normalize_report_wording(str(ai_report.get("summary") or "").strip())
    if improvements:
        feedback = f"{feedback}\n\n建议优先行动：{improvements[0]}"
    return {
        "goal": goal,
        "level": _level_badge(score),
        "feedback": feedback or "已根据本次训练重点生成定向分析。",
    }


def _build_highlight_events(
    segments: list[SessionSegment],
    turns: list[SessionTurn],
    started_at: datetime,
) -> list[dict[str, Any]]:
    events = []
    ordered = sorted(segments, key=lambda item: item.start_ts)
    for segment in ordered:
        eval_payload = segment.eval_payload or {}
        strengths = eval_payload.get("strengths") or []
        issues = eval_payload.get("issues") or []
        time_label = _relative_time(started_at, segment.start_ts)
        teacher_turns, student_turns = _collect_context_turns(
            segment_payload=segment.segment_payload or {},
            turns=turns,
            start_ts=segment.start_ts,
            end_ts=segment.end_ts,
        )
        if strengths:
            events.append(
                {
                    "time": time_label,
                    "type": "good",
                    "text": str(strengths[0]),
                    "teacher_turns": teacher_turns,
                    "student_turns": student_turns,
                }
            )
        if issues:
            events.append(
                {
                    "time": time_label,
                    "type": "warning",
                    "text": str(issues[0]),
                    "teacher_turns": teacher_turns,
                    "student_turns": student_turns,
                }
            )
        if len(events) >= 4:
            break
    return events[:4]


def _collect_context_turns(
    *,
    segment_payload: dict[str, Any],
    turns: list[SessionTurn],
    start_ts: datetime,
    end_ts: datetime,
) -> tuple[list[str], list[str]]:
    teacher_from_segment, student_from_segment = _collect_from_segment_payload(
        segment_payload
    )
    if teacher_from_segment or student_from_segment:
        return teacher_from_segment, student_from_segment

    teacher_turns: list[str] = []
    student_turns: list[str] = []
    for turn in turns:
        if turn.event_ts < start_ts or turn.event_ts > end_ts:
            continue
        text = str(turn.content or "").strip()
        if not text:
            continue
        speaker = str(turn.role_label or ("老师" if turn.role_type == "teacher" else "学生")).strip()
        line = f"{speaker}：{text[:120]}"
        if turn.role_type == "teacher" and len(teacher_turns) < 2:
            teacher_turns.append(line)
        elif turn.role_type == "student" and len(student_turns) < 2:
            student_turns.append(line)
        if len(teacher_turns) >= 2 and len(student_turns) >= 2:
            break

    # Fallback: if segment window is sparse, sample around segment start.
    if teacher_turns and student_turns:
        return teacher_turns, student_turns

    around_start = sorted(
        turns,
        key=lambda t: abs((t.event_ts - start_ts).total_seconds()),
    )
    for turn in around_start:
        text = str(turn.content or "").strip()
        if not text:
            continue
        speaker = str(turn.role_label or ("老师" if turn.role_type == "teacher" else "学生")).strip()
        line = f"{speaker}：{text[:120]}"
        if turn.role_type == "teacher" and len(teacher_turns) < 2:
            teacher_turns.append(line)
        elif turn.role_type == "student" and len(student_turns) < 2:
            student_turns.append(line)
        if len(teacher_turns) >= 2 and len(student_turns) >= 2:
            break

    return teacher_turns, student_turns


def _collect_from_segment_payload(
    payload: dict[str, Any],
) -> tuple[list[str], list[str]]:
    teacher_turns: list[str] = []
    student_turns: list[str] = []

    raw_teacher = payload.get("teacher_utterances") or []
    raw_student = payload.get("student_utterances") or []
    if not isinstance(raw_teacher, list) and not isinstance(raw_student, list):
        return teacher_turns, student_turns

    for item in raw_teacher[:2]:
        if not isinstance(item, dict):
            continue
        speaker = _normalize_speaker_label(str(item.get("speaker") or "老师").strip())
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        teacher_turns.append(f"{speaker}：{text[:120]}")

    for item in raw_student[:2]:
        if not isinstance(item, dict):
            continue
        speaker = _normalize_speaker_label(str(item.get("speaker") or "学生").strip())
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        student_turns.append(f"{speaker}：{text[:120]}")

    return teacher_turns, student_turns


def _normalize_speaker_label(label: str) -> str:
    raw = (label or "").strip().lower()
    if raw in {"teacher", "老师", "teacher_agent"}:
        return "老师"
    if raw in {"student", "学生"}:
        return "学生"
    return label or "学生"


def _format_suggestions(ai_report: dict[str, Any]) -> str:
    summary = _normalize_report_wording(str(ai_report.get("summary") or "").strip())
    improvements = ai_report.get("priority_improvements") or []
    parts = [summary] if summary else []
    for idx, item in enumerate(improvements[:4], start=1):
        parts.append(f"{idx}. {_normalize_report_wording(str(item))}")
    return "\n\n".join(parts).strip() or "本次课堂已生成改进建议。"


def _normalize_report_wording(text: str) -> str:
    out = str(text or "")
    replacements = {
        "breakthrough_focus": "训练重点",
        "PPT内容普遍缺失": "本节课未使用PPT辅助讲解",
        "必须": "建议",
    }
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out


def _looks_like_question(text: str) -> bool:
    raw = (text or "").strip()
    return bool(raw and (re.search(r"[?？]", raw) or any(k in raw for k in ["谁", "什么", "为什么", "怎么", "请回答"])))


def _classify_question(text: str) -> str:
    raw = text or ""
    if any(k in raw for k in ["为什么", "怎么理解", "请说明理由", "你怎么看"]):
        return "开放式"
    if any(k in raw for k in ["是不是", "是否", "对不对", "什么", "哪个"]):
        return "封闭式"
    return "引导式"


def _level_badge(score: int) -> dict[str, str]:
    if score >= 85:
        return {"label": "优秀", "cls": "green"}
    if score >= 70:
        return {"label": "良好", "cls": "blue"}
    if score >= 60:
        return {"label": "待提升", "cls": "amber"}
    return {"label": "需关注", "cls": "red"}


def _relative_time(started_at: datetime, current: datetime) -> str:
    seconds = max(int((current - started_at).total_seconds()), 0)
    minutes = seconds // 60
    remain = seconds % 60
    return f"{minutes:02d}:{remain:02d}"
