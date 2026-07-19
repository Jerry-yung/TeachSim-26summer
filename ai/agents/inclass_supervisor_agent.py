"""课中主控 Agent（supervisor_agent）：自行推断 dialog_state，再决定是否调用 student agent。"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage

from .inclass_student_agent import InclassStudentAgent
from .llm_utils import extract_json_object, get_chat

# 与课中契约一致；由本模块推断，不由请求体传入
DIALOG_STATES = frozenset(
    {
        "normal",
        "questioning",
        "relay_answer",  # 接力回答：老师让另一位学生补充/指正上一位的回答
        "ambiguous",
        "misstatement",
        "discipline_whisper",
        "discipline_sleep",
    }
)

STATE_INFER_PROMPT = """你是课堂主控 AI，需要根据【教师本轮发言】与【课堂背景】判断当前对话状态 dialog_state。

【教师本轮发言 teacher_text】
{teacher_text}

【本轮发言发生时间 current_timestamp】（ISO8601，与 teacher_text 对应；未传则标为未提供）
{teacher_text_ts_line}

【课堂背景 background】
（建议含：subject、当前页 slide_no；**slides** 仅含**当前页一条**（与 `slide_no` 一致），结构与课前 `POST /ai/v2/preclass/ppt/parse` 的 **slides[]** 单条一致：`slide_no`、`title`、`text_blocks[]`、`visual_elements[]`、`summary`；
**teacher_utterances_on_slide** 为本页教师已发言，建议每项为 `{{"ts":"ISO8601","text":"..."}}` 便于后端按时间戳落库；
**student_utterances_on_slide** 为本页学生已发言，用于接力回答场景；
**called_student_status_digest** 为被点名学生状态摘要（可含 `student_id` 等）：JSON null 表示无摘要，非 null 表示有摘要（服务端据此在「提问类」下区分 relay_answer / questioning，你无需在语义上区分二者））
{background_json}

请只输出一个 JSON 对象，不要 Markdown，格式：
{{"dialog_state":"取值之一"}}

dialog_state 取值只能是：
- normal：常规讲授、小结或过渡，不需要虚拟学生插话。
- questioning：教师向全班提问、追问、请学生回答或讨论。**凡属此类一律输出 questioning**（不要输出 relay_answer）；系统会根据 background.called_student_status_digest 是否为 JSON null 自动映射为 relay_answer（非 null）或 questioning（null）。
- relay_answer：与 questioning 的判定依据完全相同，**仅由服务端根据 called_student_status_digest 非 null 映射得到**，你推断时不要输出 relay_answer。
- ambiguous：教师表述含糊、节奏跳跃或「默认大家都懂」，学生整体容易困惑。
- misstatement：教师表述存在明显知识性错误风险，适合由学生温和澄清。
- discipline_whisper：提醒不要说话、保持安静等与交头接耳纪律相关。
- discipline_sleep：提醒不要打瞌睡、集中注意力等与睡觉纪律相关。

判断时请结合 background 中的上下文（尤其是本页教师历史发言），以本轮 teacher_text 为主。"""


def _normalize_dialog_state(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s in DIALOG_STATES:
        return s
    aliases = {
        "question": "questioning",
        "ask": "questioning",
        "discipline": "discipline_whisper",
    }
    return aliases.get(s)


def _is_teacher_class_questioning_like(teacher_text: str) -> bool:
    """教师向全班提问、追问、请学生回答或讨论（questioning 与 relay_answer 的共同语义依据）。"""
    t = teacher_text.strip()
    if re.search(r"[?？]", t):
        return True
    if any(
        k in t
        for k in (
            "你来补充",
            "你补充一下",
            "你来指正",
            "你指正一下",
            "你来纠错",
            "你纠正一下",
            "刚才说得不够",
            "刚才不够完整",
            "谁来补充",
            "谁补充一下",
            "谁来指正",
            "谁纠正一下",
            "谁能",
            "哪位",
            "为什么",
            "怎么理解",
            "请回答",
            "说一说",
            "解释一下",
        )
    ):
        return True
    return False


def _split_questioning_vs_relay(dialog_state: str, background: Dict[str, Any]) -> str:
    """questioning 与 relay_answer 语义相同，唯一区别：called_student_status_digest 非 null → relay_answer。"""
    if dialog_state not in ("questioning", "relay_answer"):
        return dialog_state
    digest = (background or {}).get("called_student_status_digest")
    if digest is not None:
        return "relay_answer"
    return "questioning"


_VALID_INCLASS_STUDENT_TYPES = frozenset({"xueyou", "gangjing", "xuekun"})


def _student_type_from_relay_digest(background: Dict[str, Any]) -> str:
    """接力回答仅生成一条候选：角色取自 called_student_status_digest.student_type。"""
    digest = (background or {}).get("called_student_status_digest")
    if isinstance(digest, dict):
        raw = str(digest.get("student_type", "")).strip().lower()
        if raw in _VALID_INCLASS_STUDENT_TYPES:
            return raw
    return "xueyou"


def _infer_dialog_state_rules(teacher_text: str, background: Dict[str, Any]) -> str:
    """LLM 不可用时的规则推断。"""
    t = teacher_text.strip()
    blob = t + "\n" + json.dumps(background or {}, ensure_ascii=False)

    if "别说话" in t or "安静" in t or "不要讲话" in t:
        return "discipline_whisper"
    if "打瞌睡" in t or "瞌睡" in t or "抬头" in t:
        return "discipline_sleep"

    if _is_teacher_class_questioning_like(t):
        return _split_questioning_vs_relay("questioning", background or {})

    if any(
        k in t
        for k in ("不懂也", "先往下", "应该都懂了吧", "不用深究", "先记住", "以后再讲")
    ):
        return "ambiguous"

    if ("勾股" in blob and "任意三角形" in blob) or (
        "勾股" in t and "任意" in t and "三角形" in t
    ):
        return "misstatement"

    return "normal"


def _map_state_to_trigger(dialog_state: str) -> Tuple[bool, str, Optional[str]]:
    """由 dialog_state 确定性映射是否触发学生及原因。"""
    if dialog_state == "normal":
        return False, "none", None
    if dialog_state == "questioning":
        return True, "teacher_question", "all"
    if dialog_state == "relay_answer":
        return True, "relay_answer", "xueyou"  # 占位；实际 student_type 见 digest，在 decide 中覆盖
    if dialog_state == "ambiguous":
        return True, "semantic_ambiguity", "xuekun"
    if dialog_state == "misstatement":
        return True, "teacher_misstatement", "gangjing"
    if dialog_state == "discipline_whisper":
        return True, "discipline_whisper_violation", "whisper"
    if dialog_state == "discipline_sleep":
        return True, "discipline_sleep_violation", "sleepy"
    return False, "none", None


class InclassSupervisorAgent:
    """自行推断 dialog_state，再决定是否由 InclassStudentAgent 生成话术。"""

    def __init__(self, student_agent: InclassStudentAgent | None = None) -> None:
        self.student_agent = student_agent or InclassStudentAgent()

    def decide(
        self,
        *,
        teacher_text: str,
        background: Dict[str, Any] | None = None,
        teacher_text_ts: str | None = None,
    ) -> Dict[str, Any]:
        bg = background or {}
        dialog_state = self._infer_dialog_state(teacher_text, bg, teacher_text_ts)
        should, reason, target = _map_state_to_trigger(dialog_state)
        if dialog_state == "relay_answer":
            target = _student_type_from_relay_digest(bg)

        decision: Dict[str, Any] = {
            "dialog_state": dialog_state,
            "should_trigger_student": should,
            "trigger_reason": reason,
            "target_student_type": target,
            "student_event": None,
        }

        if should and target:
            bg_reply = dict(bg)
            if teacher_text_ts:
                bg_reply["teacher_text_ts"] = teacher_text_ts

            if dialog_state == "questioning":
                decision["student_event"] = self._questioning_dual_events(
                    trigger_reason=reason,
                    background=bg_reply,
                )
            elif dialog_state == "relay_answer":
                # 仅一条：digest 中的 student_type，主动发言
                decision["student_event"] = [
                    self.student_agent.reply(
                        student_type=target,
                        trigger_reason=reason,
                        background=bg_reply,
                        is_triggered=False,
                        is_proactive_speaking=True,
                    )
                ]
            else:
                decision["student_event"] = self.student_agent.reply(
                    student_type=target,
                    trigger_reason=reason,
                    background=bg_reply,
                    is_triggered=dialog_state in ("ambiguous", "misstatement"),
                    is_proactive_speaking=dialog_state in ("ambiguous", "misstatement"),
                )
        else:
            decision["should_trigger_student"] = False
            decision["trigger_reason"] = "none"
            decision["target_student_type"] = None
            decision["student_event"] = None

        return decision

    def _questioning_dual_events(
        self,
        *,
        trigger_reason: str,
        background: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return [
            self.student_agent.reply(
                student_type="xueyou",
                trigger_reason=trigger_reason,
                background=background,
                is_triggered=False,
                is_proactive_speaking=True,
            ),
            self.student_agent.reply(
                student_type="xueyou",
                trigger_reason=trigger_reason,
                background=background,
                is_triggered=False,
                is_proactive_speaking=False,
            ),
            self.student_agent.reply(
                student_type="gangjing",
                trigger_reason=trigger_reason,
                background=background,
                is_triggered=False,
                is_proactive_speaking=True,
            ),
            self.student_agent.reply(
                student_type="gangjing",
                trigger_reason=trigger_reason,
                background=background,
                is_triggered=False,
                is_proactive_speaking=False,
            ),
            self.student_agent.reply(
                student_type="xuekun",
                trigger_reason=trigger_reason,
                background=background,
                is_triggered=False,
                is_proactive_speaking=True,
            ),
            self.student_agent.reply(
                student_type="xuekun",
                trigger_reason=trigger_reason,
                background=background,
                is_triggered=False,
                is_proactive_speaking=False,
            ),
        ]

    def _infer_dialog_state(
        self,
        teacher_text: str,
        background: Dict[str, Any],
        teacher_text_ts: str | None = None,
    ) -> str:
        ts_line = (teacher_text_ts or "").strip() or "未提供"
        try:
            chat = get_chat()
            prompt = STATE_INFER_PROMPT.format(
                teacher_text=teacher_text.strip(),
                teacher_text_ts_line=ts_line,
                background_json=json.dumps(background, ensure_ascii=False, indent=2),
            )
            resp = chat.invoke([HumanMessage(content=prompt)])
            raw = resp.content if hasattr(resp, "content") else str(resp)
            data = extract_json_object(raw)
            state = _normalize_dialog_state(data.get("dialog_state"))
            if state is not None:
                return _split_questioning_vs_relay(state, background)
        except Exception:
            pass
        return _infer_dialog_state_rules(teacher_text, background)
