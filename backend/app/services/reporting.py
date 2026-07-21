from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models.lesson import ClassroomSession, SessionSegment, SessionTurn

FILLER_LEXICON = [
    "然后",
    "就是",
    "对不对",
    "呃",
    "嗯",
    "那个",
    "这个",
    "其实",
    "就是说",
    "那么",
    "好吧",
    "大家看",
]
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
INTERACTION_STATES = {
    "questioning",
    "ambiguous",
    "misstatement",
    "relay_answer",
    "discipline_whisper",
    "discipline_sleep",
}
_DECISION_LOG_PATH = (
    Path(__file__).resolve().parents[2] / "logs" / "inclass_decisions.jsonl"
)


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
    has_class_data = bool(turns or segments)
    elapsed_duration_min = _duration_minutes_from_elapsed(segments)
    if not has_class_data:
        duration_min = 0
    else:
        duration_min = elapsed_duration_min or _duration_minutes(started_at, ended_at)
    hard_stats = _build_hard_stats(turns, started_at, ended_at, duration_min=duration_min)
    target_duration_min = _extract_target_duration_min(lesson_json)
    duration_overtime = (
        bool(target_duration_min and duration_min > target_duration_min)
        if has_class_data
        else False
    )
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
    highlights = _build_highlight_events(
        segments, turns, started_at, session_id=str(session.id)
    )
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
    if not has_class_data:
        suggestions = "本次课堂未开始授课，暂无可分析的讲课与互动数据。请开启“开始授课”后再生成报告。"

    return {
        "session_id": str(session.id),
        "lesson_topic": lesson_topic,
        "subject": subject,
        "class_info": class_info,
        "created_at": started_at.strftime("%Y-%m-%d %H:%M"),
        "duration_min": duration_min,
        "target_duration_min": target_duration_min,
        "duration_overtime": duration_overtime,
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


def _extract_target_duration_min(lesson_json: dict[str, Any]) -> int | None:
    prefs = lesson_json.get("teaching_preferences") or {}
    candidates = [
        prefs.get("duration"),
        lesson_json.get("duration"),
    ]
    for raw in candidates:
        text = str(raw or "").strip()
        if not text:
            continue
        matched = re.search(r"(\d+(?:\.\d+)?)", text)
        if not matched:
            continue
        minutes = float(matched.group(1))
        if minutes > 0:
            return int(round(minutes))
    return None


def _build_hard_stats(
    turns: list[SessionTurn],
    started_at: datetime,
    ended_at: datetime,
    duration_min: int | None = None,
) -> dict[str, Any]:
    teacher_turns = [turn for turn in turns if turn.role_type == "teacher"]
    student_turns = [turn for turn in turns if turn.role_type == "student"]
    total_words = sum(len((turn.content or "").strip()) for turn in teacher_turns)
    if duration_min is None:
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

    teacher_blob = "\n".join(turn.content for turn in teacher_turns)
    filler_counts = _top_filler_words(teacher_blob)

    return {
        "total_duration_min": duration_min,
        "talk_duration_min": duration_min,
        "total_words": total_words,
        "avg_speed_wpm": avg_speed,
        "avg_wait_time_sec": avg_wait,
        "filler_words": filler_counts,
    }


def _top_filler_words(text: str, top_n: int = 4) -> list[dict[str, Any]]:
    blob = str(text or "")
    rows = []
    palette = ["#2563EB", "#10B981", "#F59E0B", "#A855F7"]
    for word in FILLER_LEXICON:
        count = len(re.findall(re.escape(word), blob))
        rows.append({"word": word, "count": count})
    rows.sort(key=lambda x: (-x["count"], -len(x["word"]), x["word"]))
    top = rows[:top_n]
    total = sum(item["count"] for item in top)
    out = []
    for idx, item in enumerate(top):
        pct = (item["count"] / total * 100) if total > 0 else 0
        out.append(
            {
                **item,
                "pct": round(pct, 1),
                "color": palette[idx % len(palette)],
            }
        )
    return out


def _duration_minutes_from_elapsed(segments: list[SessionSegment]) -> int | None:
    max_elapsed_sec = 0
    for seg in segments:
        payload = seg.segment_payload or {}
        raw = payload.get("end_elapsed_sec")
        if raw is None:
            # backward compatibility for old historical rows
            raw = payload.get("timer_elapsed_sec")
        try:
            sec = int(raw)
        except (TypeError, ValueError):
            continue
        if sec > max_elapsed_sec:
            max_elapsed_sec = sec
    if max_elapsed_sec <= 0:
        return None
    return max(1, int(round(max_elapsed_sec / 60)))


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
        seg_minutes = _segment_minutes(segment)
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
    session_id: str,
) -> list[dict[str, Any]]:
    events = []
    # 优先采用 supervisor 决策日志中的真实判定，缺失时再回退文本推断。
    interaction_events = _build_interaction_events_from_decision_logs(
        session_id=session_id,
        turns=turns,
        started_at=started_at,
    )
    if not interaction_events:
        interaction_events = _build_interaction_events(turns, started_at)
    events.extend(interaction_events)
    ordered = sorted(segments, key=lambda item: item.start_ts)
    for segment in ordered:
        eval_payload = segment.eval_payload or {}
        strengths = eval_payload.get("strengths") or []
        issues = eval_payload.get("issues") or []
        time_label = _segment_time_label(segment, started_at)
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
    # 保序去重：优先保留互动类节点，再补充评估节点
    dedup: list[dict[str, Any]] = []
    seen = set()
    for ev in events:
        key = (ev.get("time"), ev.get("text"))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(ev)
    dedup.sort(key=lambda item: _time_label_to_seconds(str(item.get("time") or "")))
    return dedup


def _build_interaction_events(
    turns: list[SessionTurn],
    started_at: datetime,
) -> list[dict[str, Any]]:
    ordered = sorted(turns, key=lambda item: (item.event_ts, item.created_at))
    out: list[dict[str, Any]] = []
    for idx, turn in enumerate(ordered):
        if turn.role_type != "teacher":
            continue
        text = str(turn.content or "").strip()
        if not text:
            continue
        state = _infer_interaction_state_from_text(text)
        if not state:
            continue
        out.append(
            {
                "time": _relative_time(started_at, turn.event_ts),
                "type": "warning"
                if state
                in {"ambiguous", "misstatement", "discipline_whisper", "discipline_sleep"}
                else "good",
                "text": _interaction_title(state, text),
                "teacher_turns": [text[:120]] if state == "questioning" else [f"老师：{text[:120]}"],
                "student_turns": _nearest_student_turns(ordered, idx),
            }
        )
    return out


def _build_interaction_events_from_decision_logs(
    *,
    session_id: str,
    turns: list[SessionTurn],
    started_at: datetime,
) -> list[dict[str, Any]]:
    rows = _load_session_decision_rows(
        session_id,
        stages={
            "questioning_bundle_resolved",
            "ambiguous_resolved",
            "misstatement_resolved",
            "relay_answer_resolved",
            "discipline_sleep_resolved",
            "discipline_whisper_resolved",
            "supervisor_decision",
            "supervisor_decision_normal_204",
        },
    )
    if not rows:
        return []
    ordered_turns = sorted(turns, key=lambda item: (item.event_ts, item.created_at))
    out: list[dict[str, Any]] = []

    # 1) questioning 由 questioning_bundle_resolved 生成（匿名学生）
    for row in rows:
        if str(row.get("stage") or "") != "questioning_bundle_resolved":
            continue
        request = row.get("request") or {}
        bundle = row.get("bundle") or {}
        resolved = row.get("resolved_student_reply") or {}
        question_count = _to_int(bundle.get("question_count")) or 1
        question_items = bundle.get("question_items") or []
        merged = str(bundle.get("question_bundle_text") or "").strip()
        teacher_turns: list[str] = [merged[:120]] if merged else []
        if not teacher_turns and isinstance(question_items, list):
            for item in question_items[:1]:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or "").strip()
                if text:
                    teacher_turns = [text[:120]]
                    break
        reply_text = str(resolved.get("reply_text") or "").strip()
        if not teacher_turns or not reply_text:
            continue
        node_text = str(bundle.get("bundle_title") or "").strip()
        if not node_text:
            node_text = merged or (
                f"问题共{question_count}问"
                if question_count > 1
                else "课堂提问"
            )
        label = str(bundle.get("bundle_title") or "").strip()
        if not label:
            label = node_text
        if not label.startswith("提问：") and not label.startswith("连续提问："):
            label = f"提问：{label}"
        out.append(
            {
                "time": _decision_time_label(request, started_at),
                "type": "good",
                "text": label,
                "teacher_turns": teacher_turns,
                "student_turns": [f"学生：{reply_text[:120]}"],
            }
        )

    # 2) 其他五类交互优先从 *_resolved 生成（避免 turn 窗口串行）
    resolved_stage_to_state = {
        "ambiguous_resolved": "ambiguous",
        "misstatement_resolved": "misstatement",
        "relay_answer_resolved": "relay_answer",
        "discipline_sleep_resolved": "discipline_sleep",
        "discipline_whisper_resolved": "discipline_whisper",
    }
    has_resolved_interactions = False
    for row in rows:
        stage = str(row.get("stage") or "").strip()
        state = resolved_stage_to_state.get(stage)
        if not state:
            continue
        request = row.get("request") or {}
        resolved_student = row.get("resolved_student") or {}
        teacher_text = str(request.get("content") or "").strip()
        if not teacher_text:
            continue
        reply_text = str(resolved_student.get("reply_text") or "").strip()
        student_name = str(resolved_student.get("student_name") or "").strip()
        if state in {"relay_answer", "discipline_sleep", "discipline_whisper"} and student_name:
            student_prefix = student_name
        else:
            student_prefix = "学生"
        student_turns = [f"{student_prefix}：{reply_text[:120]}"] if reply_text else []
        out.append(
            {
                "time": _decision_time_label(request, started_at),
                "type": "warning" if state in {"ambiguous", "misstatement"} else "good",
                "text": _interaction_title(state, teacher_text, truncate=False),
                "teacher_turns": [f"老师：{teacher_text}"],
                "student_turns": student_turns,
            }
        )
        has_resolved_interactions = True

    # 3) 兼容历史数据：若无 *_resolved，再退回旧 supervisor_decision 拼接逻辑
    if has_resolved_interactions:
        out.sort(key=lambda item: _time_label_to_seconds(str(item.get("time") or "")))
        return out

    anchors: list[dict[str, Any]] = []
    last_teacher_idx = -1
    for row in rows:
        stage = str(row.get("stage") or "").strip()
        if stage not in {"supervisor_decision", "supervisor_decision_normal_204"}:
            continue
        supervisor_raw = row.get("supervisor_raw") or {}
        response = row.get("response") or {}
        request = row.get("request") or {}
        state = str(
            (response.get("dialog_state") if isinstance(response, dict) else "")
            or (supervisor_raw.get("dialog_state") if isinstance(supervisor_raw, dict) else "")
            or ""
        ).strip()
        if state not in {
            "ambiguous",
            "misstatement",
            "relay_answer",
            "discipline_whisper",
            "discipline_sleep",
        }:
            continue
        text = str(request.get("content") or "").strip()
        if not text and isinstance(supervisor_raw, dict):
            text = str(supervisor_raw.get("teacher_text") or "").strip()
        if not text:
            continue
        request_turn_id = str(row.get("request_turn_id") or "").strip()
        teacher_idx = _find_teacher_turn_index_by_turn_id(
            ordered_turns,
            request_turn_id=request_turn_id,
        )
        if teacher_idx is None:
            teacher_idx = _find_teacher_turn_index(
                ordered_turns,
                teacher_text=text,
                start_after_idx=last_teacher_idx,
            )
        if isinstance(teacher_idx, int):
            last_teacher_idx = teacher_idx
        anchors.append(
            {
                "state": state,
                "text": text,
                "request": request,
                "teacher_idx": teacher_idx,
            }
        )

    for idx, anchor in enumerate(anchors):
        state = str(anchor.get("state") or "")
        text = str(anchor.get("text") or "")
        request = anchor.get("request") or {}
        teacher_idx = anchor.get("teacher_idx")
        next_teacher_idx: int | None = None
        for j in range(idx + 1, len(anchors)):
            nxt = anchors[j].get("teacher_idx")
            if isinstance(nxt, int) and isinstance(teacher_idx, int) and nxt > teacher_idx:
                next_teacher_idx = nxt
                break

        teacher_lines: list[str] = [f"老师：{text[:120]}"]
        student_lines: list[str] = []
        if isinstance(teacher_idx, int):
            teacher_lines, student_lines = _collect_dialogue_block_from_anchor(
                turns=ordered_turns,
                teacher_idx=teacher_idx,
                state=state,
                next_teacher_idx=next_teacher_idx,
            )

        out.append(
            {
                "time": _decision_time_label(request, started_at),
                "type": "warning"
                if state
                in {"ambiguous", "misstatement", "discipline_whisper", "discipline_sleep"}
                else "good",
                "text": _interaction_title(state, text),
                "teacher_turns": teacher_lines,
                "student_turns": student_lines,
            }
        )
    out.sort(key=lambda item: _time_label_to_seconds(str(item.get("time") or "")))
    return out


def _interaction_title(state: str, text: str, *, truncate: bool = True) -> str:
    raw = str(text or "").strip()
    body = raw[:56] if truncate else raw
    mapping = {
        "questioning": "提问",
        "relay_answer": "追问",
        "ambiguous": "知识点讲述模糊",
        "misstatement": "知识点讲述错误",
        "discipline_whisper": "课堂纪律提醒",
        "discipline_sleep": "课堂纪律提醒",
    }
    prefix = mapping.get(str(state or "").strip(), "课堂互动")
    return f"{prefix}：{body}" if body else prefix


def _time_label_to_seconds(label: str) -> int:
    text = str(label or "").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", text)
    if not m:
        return 0
    return int(m.group(1)) * 60 + int(m.group(2))


def _find_teacher_turn_index_by_turn_id(
    turns: list[SessionTurn],
    *,
    request_turn_id: str,
) -> int | None:
    target = str(request_turn_id or "").strip()
    if not target:
        return None
    for idx, turn in enumerate(turns):
        if turn.role_type != "teacher":
            continue
        if str(turn.id) == target:
            return idx
    return None


def _load_session_decision_rows(
    session_id: str,
    *,
    stages: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not _DECISION_LOG_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with _DECISION_LOG_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(row.get("session_id") or "") != str(session_id):
                    continue
                stage = str(row.get("stage") or "").strip()
                if stages is not None and stage not in stages:
                    continue
                rows.append(row)
    except OSError:
        return []
    rows.sort(key=lambda item: str(item.get("ts") or ""))
    return rows


def _decision_time_label(request: dict[str, Any], started_at: datetime) -> str:
    elapsed = _to_int(request.get("class_elapsed_sec"))
    if elapsed is not None and elapsed >= 0:
        return _relative_time_from_elapsed(elapsed)
    raw_ts = str(request.get("current_timestamp") or "").strip()
    if raw_ts:
        dt = _try_parse_iso_datetime(raw_ts)
        if dt is not None:
            return _relative_time(started_at, dt)
    return "00:00"


def _try_parse_iso_datetime(raw: str) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _find_teacher_turn_index(
    turns: list[SessionTurn],
    *,
    teacher_text: str,
    start_after_idx: int = -1,
) -> int | None:
    target = str(teacher_text or "").strip()
    if not target:
        return None
    # 优先在“上一锚点之后”按同文本匹配，避免重复文本错配到旧轮次。
    for idx in range(max(start_after_idx + 1, 0), len(turns)):
        turn = turns[idx]
        if turn.role_type != "teacher":
            continue
        text = str(turn.content or "").strip()
        if text == target:
            return idx

    # 若后半段找不到，再全局精确匹配一次（处理极端乱序情况）。
    for idx, turn in enumerate(turns):
        if turn.role_type != "teacher":
            continue
        text = str(turn.content or "").strip()
        if text == target:
            return idx
    return None


def _collect_dialogue_block_from_anchor(
    *,
    turns: list[SessionTurn],
    teacher_idx: int,
    state: str,
    next_teacher_idx: int | None = None,
) -> tuple[list[str], list[str]]:
    teacher_turns: list[str] = []
    student_turns: list[str] = []
    if teacher_idx < 0 or teacher_idx >= len(turns):
        return teacher_turns, student_turns

    teacher_limit = 3 if state in {"questioning", "relay_answer"} else 2
    student_limit = 2

    # 教师问题块：从锚点起，连续收集教师句，直到遇到学生句或下一交互锚点
    i = teacher_idx
    while i < len(turns) and len(teacher_turns) < teacher_limit:
        if next_teacher_idx is not None and i >= next_teacher_idx:
            break
        t = turns[i]
        if t.role_type == "teacher":
            text = str(t.content or "").strip()
            if text:
                teacher_turns.append(f"老师：{text[:120]}")
            i += 1
            continue
        break

    # 学生回答块：紧随其后连续学生句，遇到教师句或下一交互锚点即停止
    while i < len(turns) and len(student_turns) < student_limit:
        if next_teacher_idx is not None and i >= next_teacher_idx:
            break
        t = turns[i]
        if t.role_type == "student":
            text = str(t.content or "").strip()
            if text:
                student_turns.append(f"学生：{text[:120]}")
            i += 1
            continue
        break

    return teacher_turns, student_turns


def _infer_interaction_state_from_text(text: str) -> str | None:
    t = str(text or "")
    if any(k in t for k in ("别说话", "安静", "不要讲话")):
        return "discipline_whisper"
    if any(k in t for k in ("别睡", "打瞌睡", "抬头听讲", "别打瞌睡")):
        return "discipline_sleep"
    if any(k in t for k in ("不必深究", "先往下听", "大概知道", "先记住这个结论")):
        return "ambiguous"
    if any(
        k in t
        for k in (
            "任意三角形两边就能直接套勾股",
            "忠比孝更重要",
            "反对孝道",
        )
    ):
        return "misstatement"
    if any(k in t for k in ("补充一下", "你来补充", "你来指正", "纠错")):
        return "relay_answer"
    if _looks_like_question(t):
        return "questioning"
    return None


def _nearest_student_turns(turns: list[SessionTurn], teacher_idx: int) -> list[str]:
    out: list[str] = []
    for turn in turns[teacher_idx + 1 :]:
        if turn.role_type != "student":
            continue
        text = str(turn.content or "").strip()
        if not text:
            continue
        out.append(f"学生：{text[:120]}")
        if len(out) >= 2:
            break
    return out


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


def _segment_minutes(segment: SessionSegment) -> float:
    payload = segment.segment_payload or {}
    start_elapsed = _to_int(payload.get("start_elapsed_sec"))
    end_elapsed = _to_int(payload.get("end_elapsed_sec"))
    if (
        start_elapsed is not None
        and end_elapsed is not None
        and end_elapsed >= start_elapsed
    ):
        return max((end_elapsed - start_elapsed) / 60, 0.5)
    return max((segment.end_ts - segment.start_ts).total_seconds() / 60, 0.5)


def _segment_time_label(segment: SessionSegment, started_at: datetime) -> str:
    payload = segment.segment_payload or {}
    start_elapsed = _to_int(payload.get("start_elapsed_sec"))
    if start_elapsed is not None and start_elapsed >= 0:
        return _relative_time_from_elapsed(start_elapsed)
    return _relative_time(started_at, segment.start_ts)


def _relative_time_from_elapsed(elapsed_sec: int) -> str:
    seconds = max(int(elapsed_sec), 0)
    minutes = seconds // 60
    remain = seconds % 60
    return f"{minutes:02d}:{remain:02d}"


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
