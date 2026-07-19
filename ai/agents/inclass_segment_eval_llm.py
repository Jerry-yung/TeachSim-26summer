"""课中段落评价 LLM（LLM2）."""
import json
from typing import Any, Dict, List

from .llm_utils import extract_json_object, get_chat
from langchain_core.messages import HumanMessage


SEGMENT_EVAL_PROMPT = """你是一位资深教研员，正在评价「模拟课堂」中某一页 PPT 停留时段的教学片段。

请根据下列 JSON 数据（含教师发言、学生发言、可选 ppt_context），从教学清晰度、学生活跃度、节奏把控三方面打分（0-100 整数），并给出优点、问题与可执行改进建议。

【片段数据】
{segment_json}

请只输出一个 JSON 对象，不要 Markdown，格式如下：
{{
  "scores": {{
    "instructional_clarity": 0,
    "student_engagement": 0,
    "pace_control": 0
  }},
  "strengths": ["2～4 条"],
  "issues": ["0～4 条，无则 []"],
  "improvement_actions": ["2～4 条具体建议"]
}}

字段名必须完全一致。"""


class InclassSegmentEvalLLM:
    """对某页 PPT 停留段落进行详细评价（主模型 LLM）。"""

    def run(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        segment_json = json.dumps(segment, ensure_ascii=False, indent=2)
        prompt = SEGMENT_EVAL_PROMPT.format(segment_json=segment_json)
        try:
            chat = get_chat()
            resp = chat.invoke([HumanMessage(content=prompt)])
            raw = resp.content if hasattr(resp, "content") else str(resp)
            data = extract_json_object(raw)
            scores = data.get("scores") or {}
            if not isinstance(scores, dict):
                scores = {}
            out = {
                "segment_id": segment.get("segment_id"),
                "start_ts": segment.get("start_ts"),
                "end_ts": segment.get("end_ts"),
                "slide_no": segment.get("slide_no"),
                "scores": {
                    "instructional_clarity": int(scores.get("instructional_clarity", 75)),
                    "student_engagement": int(scores.get("student_engagement", 75)),
                    "pace_control": int(scores.get("pace_control", 75)),
                },
                "strengths": _as_str_list(data.get("strengths"), 4),
                "issues": _as_str_list(data.get("issues"), 4),
                "improvement_actions": _as_str_list(data.get("improvement_actions"), 4),
            }
            return out
        except Exception:
            return self._fallback(segment)

    def _fallback(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        teacher_turns: List[Dict[str, Any]] = segment.get("teacher_utterances", [])
        student_turns: List[Dict[str, Any]] = segment.get("student_utterances", [])
        text_count = sum(len(x.get("text", "")) for x in teacher_turns)
        interaction_count = len(student_turns)
        score_delivery = 85 if text_count > 60 else 72
        score_interaction = 88 if interaction_count >= 2 else 70
        return {
            "segment_id": segment.get("segment_id"),
            "start_ts": segment.get("start_ts"),
            "end_ts": segment.get("end_ts"),
            "slide_no": segment.get("slide_no"),
            "scores": {
                "instructional_clarity": score_delivery,
                "student_engagement": score_interaction,
                "pace_control": 80,
            },
            "strengths": ["讲解逻辑完整", "能结合当前页内容组织表达"],
            "issues": ["互动次数偏少，建议加入追问"] if interaction_count < 2 else [],
            "improvement_actions": [
                "本页结束前增加一次检查性提问",
                "总结关键词并让学生复述",
            ],
        }


def _as_str_list(val: Any, max_n: int) -> List[str]:
    if not isinstance(val, list):
        return []
    out = [str(x).strip() for x in val if str(x).strip()]
    return out[:max_n]
