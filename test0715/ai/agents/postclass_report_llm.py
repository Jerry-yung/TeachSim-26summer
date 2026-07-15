"""课后报告 LLM（LLM3）."""
import json
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage

from .llm_utils import extract_json_object, get_chat


REPORT_PROMPT = """你是一位资深教研员，需要根据「教案概要」与「多个课堂片段评价结果」撰写课后综合报告。

【教案 JSON】
{lesson_json}

【各片段评价（LLM2 输出列表）】
{segment_evals_json}

【生成要求（必须遵守）】
1) 若教案 JSON 中包含 `teaching_preferences`，你必须结合其中字段进行定向分析：
   - grade：学生年级
   - class_type：重点班，普通班，平行班
   - primary_goal：知识理解与记忆，技能掌握与方法运用，思维拓展与探究讨论，情感体验与价值建构
   - breakthrough_focus：课堂节奏把控，知识点衔接流畅度，提问质量与互动引导，语言表达与亲和力，时间分配合理性
2) summary 与 priority_improvements 必须明显体现上述偏好，不可只做通用评价。
3) priority_improvements 里至少 1-2 条要直接对应 breakthrough_focus。
4) overall_score 与 dimension_scores 仍需和片段数据整体一致、可解释。

请只输出一个 JSON 对象，不要 Markdown，格式：
{{
  "lesson_topic": "与教案一致的课题名",
  "overall_score": 0,
  "dimension_scores": {{
    "instructional_clarity": 0,
    "student_engagement": 0,
    "pace_control": 0
  }},
  "summary": "200 字内总评",
  "priority_improvements": ["3～5 条可执行改进项"]
}}"""


class PostclassReportLLM:
    """汇总 LLM2 段落评价 + 教案 JSON，由主 LLM 输出报告。"""

    def run(self, *, lesson_json: Dict[str, Any], segment_evals: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            chat = get_chat()
            prompt = REPORT_PROMPT.format(
                lesson_json=json.dumps(lesson_json, ensure_ascii=False, indent=2),
                segment_evals_json=json.dumps(segment_evals, ensure_ascii=False, indent=2),
            )
            resp = chat.invoke([HumanMessage(content=prompt)])
            raw = resp.content if hasattr(resp, "content") else str(resp)
            data = extract_json_object(raw)
            dim = data.get("dimension_scores") or {}
            if not isinstance(dim, dict):
                dim = {}
            topic = str(data.get("lesson_topic") or "").strip() or lesson_json.get("basic_info", {}).get(
                "lesson_topic", "未命名课程"
            )
            overall = int(data.get("overall_score", 0) or 0)
            dims_out = {
                "instructional_clarity": int(dim.get("instructional_clarity", 0) or 0),
                "student_engagement": int(dim.get("student_engagement", 0) or 0),
                "pace_control": int(dim.get("pace_control", 0) or 0),
            }
            if segment_evals and (
                overall == 0 or all(v == 0 for v in dims_out.values())
            ):
                fb = self._fallback(lesson_json, segment_evals)
                if overall == 0:
                    overall = int(fb["overall_score"])
                if all(v == 0 for v in dims_out.values()):
                    dims_out = dict(fb["dimension_scores"])
            return {
                "lesson_topic": topic,
                "overall_score": overall,
                "dimension_scores": dims_out,
                "summary": str(data.get("summary") or "").strip() or "（无摘要）",
                "priority_improvements": _list_or_default(data.get("priority_improvements")),
            }
        except Exception:
            return self._fallback(lesson_json, segment_evals)

    def _fallback(self, lesson_json: Dict[str, Any], segment_evals: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not segment_evals:
            avg_clarity = avg_engagement = avg_pace = 0
        else:
            avg_clarity = int(
                sum(x["scores"]["instructional_clarity"] for x in segment_evals) / len(segment_evals)
            )
            avg_engagement = int(
                sum(x["scores"]["student_engagement"] for x in segment_evals) / len(segment_evals)
            )
            avg_pace = int(sum(x["scores"]["pace_control"] for x in segment_evals) / len(segment_evals))

        topic = lesson_json.get("basic_info", {}).get("lesson_topic", "未命名课程")
        prefs = lesson_json.get("teaching_preferences") or {}
        focus_text = str(prefs.get("breakthrough_focus", "")).strip()
        focus_items = _focus_default_items(focus_text)
        default_items = ["增加高质量追问链", "每页PPT结束前增加形成性评价"]
        merged_items = (focus_items + default_items)[:5]

        goal_text = str(prefs.get("primary_goal", "")).strip()
        focus_hint = f"，并围绕「{goal_text}」目标做了定向分析" if goal_text else ""
        return {
            "lesson_topic": topic,
            "overall_score": int((avg_clarity + avg_engagement + avg_pace) / 3) if segment_evals else 0,
            "dimension_scores": {
                "instructional_clarity": avg_clarity,
                "student_engagement": avg_engagement,
                "pace_control": avg_pace,
            },
            "summary": f"{topic}课堂整体节奏稳定，建议进一步提升互动密度{focus_hint}。",
            "priority_improvements": merged_items,
        }


def _list_or_default(val: Any) -> List[str]:
    if isinstance(val, list) and val:
        return [str(x).strip() for x in val if str(x).strip()][:8]
    return ["增加高质量追问链", "每页PPT结束前增加形成性评价"]


def _focus_default_items(focus_text: str) -> List[str]:
    """根据 breakthrough_focus 文字内容返回对应的改进建议。"""
    mapping = {
        "课堂节奏把控": ["按「导入-讲解-练习-小结」切分时间片，设置每 8-10 分钟节奏检查点"],
        "知识点衔接流畅度": ["每个新知识点前先做前置回顾，讲解后立即用一题完成衔接验证"],
        "提问质量与互动引导": ["每页至少设置 1 个高质量追问，并追问到「理由+反例」层级"],
        "语言表达与亲和力": ["关键定义用更短句复述一次，并增加鼓励性反馈语提升亲和力"],
        "时间分配合理性": ["将板演、讲解、练习时间预分配并在课堂中按节点校正"],
    }
    return mapping.get(focus_text, [])
