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

【本轮发言发生时间 current_timestamp】（课内计时器时间，格式可为 MM:SS；未传则标为未提供）
{teacher_text_ts_line}

【课堂背景 background】
（建议含：subject、当前页 slide_no；**slides** 仅含**当前页一条**（与 `slide_no` 一致），结构与课前 `POST /ai/v2/preclass/ppt/parse` 的 **slides[]** 单条一致：`slide_no`、`title`、`text_blocks[]`、`visual_elements[]`、`summary`；
**teacher_utterances_on_slide** 为本页教师已发言，建议每项为 `{{"ts":"MM:SS","text":"..."}}`；
**student_utterances_on_slide** 为本页学生已发言，用于接力回答场景；
**called_student_status_digest** 为被点名学生状态摘要（可含 `student_id` 等）：JSON null 表示无摘要，非 null 表示有摘要（服务端据此在「提问类」下区分 relay_answer / questioning，你无需在语义上区分二者））
{background_json}

请只输出一个 JSON 对象，不要 Markdown，格式：
{{"dialog_state":"取值之一","question_difficulty":整数或null}}

当且仅当 dialog_state 为 questioning 时，必须额外给出 question_difficulty（整数 1-5，5 表示最难）：
- 1：事实回忆、是非判断、直接读数/记定义，几乎无需推理。
- 2：简单理解或单步应用，依据刚讲内容即可回答。
- 3：需要一步推理、概念辨析或结合本页内容综合回答。
- 4：多步推理、证明思路、迁移应用或需联系前后文。
- 5：开放探究、综合证明、易错辨析或需较高学科素养才能答好。
非 questioning 时 question_difficulty 必须为 null。

dialog_state 取值只能是：
- normal：常规讲授、小结或过渡，不需要虚拟学生插话。
- questioning：教师**明确**向全班提问、追问、请学生回答或组织讨论（须能读出「需要学生开口回应」的意图）。**不是**提问：纯肯定/评价（如「说得很好」「说的没错」）、承接推进、小结过渡、陈述标准或结论而无请学生作答。
  凡属提问类一律输出 questioning（不要输出 relay_answer）；系统会根据 called_student_status_digest 是否为 JSON null 自动映射 relay_answer（非 null）或 questioning（null）。
- relay_answer：与 questioning 的判定依据完全相同，**仅由服务端根据 called_student_status_digest 非 null 映射得到**，你推断时不要输出 relay_answer。
- ambiguous：教师表述含糊、节奏跳跃或「默认大家都懂」，学生整体容易困惑。
- misstatement：教师表述存在明显知识性错误风险，适合由学生温和澄清。**不是** misstatement：教师承认/纠正刚才口误（如「我讲错了」「刚才说错了」「更正一下」）或补充正确说法。
- discipline_whisper：提醒不要说话、保持安静等与交头接耳纪律相关。
- discipline_sleep：提醒不要打瞌睡、集中注意力等与睡觉纪律相关。

判断时请结合 background 中的上下文（尤其是本页教师历史发言），以本轮 teacher_text 为主。"""

STATE_INFER_GUIDE = """
补充判定要求：
1) 不要只做关键词匹配；请结合“本轮 + 最近上下文”判断。
2) ambiguous：教师跳步、省略推理、默认学生已懂；即使无固定词，语义上“先记结论/后面再讲”也算 ambiguous。
3) questioning 与 normal 的区分（重要）：
   - questioning：有问句，或明确请全班/某人回答、解释、讨论、补充、指正（如「为什么」「谁来」「请回答」「你说说」）。
   - normal：短评价/肯定/承接（如「说的没错」「说得很好」「很好」「不错」）、陈述事实或标准、小结推进，**没有**请学生此刻开口的意图。
   - 不要因为句子里出现「说」字就判 questioning；「说得对」通常是评价上一位学生，不是向全班发问。
4) ambiguous 与 misstatement：前者偏含糊/跳步，后者偏知识性错误或结论不成立。
5) 若学生刚指出老师上一句有误，老师本轮在认错、更正或给出正确说法，判 normal，不要再次判 misstatement。
6) 明确提问、追问、点名回答时，才判 questioning（再由服务端映射 relay_answer）。
7) question_difficulty 仅在与 questioning 同时输出；请结合学科、PPT 与提问表述综合评估，不要机械套词。

示例（不要机械套词）：
- “这个先记住，证明过程先不展开，后面再看。” => ambiguous
- “大家应该都懂了，我们直接套这个结论往下推。” => ambiguous
- “说的没错”“说得很好”“很好，我们继续。” => normal
- “1%是很好的标准，可以据此判断误差。” => normal（陈述标准，非提问）
- “这一步为什么成立？谁来解释一下？” => questioning，question_difficulty 约 3-4
- “任意三角形都可直接用勾股定理。” => misstatement
- “是我讲错了，相似要两个角相等。” => normal（认错/更正，不是新错误）
- “小明别讲话，先安静听。” => discipline_whisper
"""


def _normalize_question_difficulty(raw: Any) -> Optional[int]:
    """解析 LLM 返回的 question_difficulty，不做规则打分。"""
    if raw is None:
        return None
    try:
        score = int(raw)
    except (TypeError, ValueError):
        return None
    if 1 <= score <= 5:
        return score
    return None


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
            "有没有问题",
            "有什么问题",
        )
    ):
        return True
    return False


def _should_downgrade_questioning_to_normal(teacher_text: str) -> bool:
    """规则兜底：无互动提问意图的短肯定/评价/陈述，不应判 questioning。"""
    t = teacher_text.strip()
    if not t or re.search(r"[?？]", t):
        return False
    if _is_teacher_class_questioning_like(t):
        return False
    if len(t) > 36:
        return False
    if re.search(
        r"(请|谁来|谁能|哪位|是否|怎么|为什么|吗|呢|对不对|对吗|请问|你来说说|大家来)",
        t,
    ):
        return False
    if re.fullmatch(
        r"(?:说的?|讲(?:得)?)?(?:没错|很好|挺好|对的?|正确|可以|行|不错|蛮好|没问题)[。.!！…]*",
        t,
    ):
        return True
    if re.fullmatch(r"(?:很好|不错|正确|可以|行|对的?|没问题)[。.!！…]*", t):
        return True
    if re.search(r"(说得?很好|说得?不错|说得?对|说的?没错|很好|不错)", t) and len(t) <= 16:
        return True
    return False


def _apply_questioning_guardrails(dialog_state: str, teacher_text: str) -> str:
    if dialog_state not in ("questioning", "relay_answer"):
        return dialog_state
    if _should_downgrade_questioning_to_normal(teacher_text):
        return "normal"
    return dialog_state


def _is_teacher_correction_or_clarification(
    teacher_text: str,
    background: Dict[str, Any] | None = None,
) -> bool:
    """教师认错、更正口误或补充正确说法，不应再触发 misstatement。"""
    t = teacher_text.strip()
    if not t:
        return False
    correction_cues = (
        "我讲错了",
        "讲错了",
        "说错了",
        "刚才错了",
        "说错了",
        "更正一下",
        "纠正一下",
        "补充说明",
        "准确地说",
        "准确一点",
        "刚才那句话",
        "不是这个意思",
        "刚才口误",
        "我刚才说的不对",
    )
    if any(cue in t for cue in correction_cues):
        return True
    if re.search(r"(刚才|之前).{0,12}(说错|讲错|不对|有误)", t):
        return True
    if re.search(r"(更正|纠正|补充).{0,8}(说法|理解|判断)", t):
        return True
    return False


def _apply_misstatement_guardrails(
    dialog_state: str,
    teacher_text: str,
    background: Dict[str, Any] | None = None,
) -> str:
    if dialog_state != "misstatement":
        return dialog_state
    if _is_teacher_correction_or_clarification(teacher_text, background):
        return "normal"
    return dialog_state


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

    if _is_teacher_class_questioning_like(t) and not _should_downgrade_questioning_to_normal(t):
        return _split_questioning_vs_relay("questioning", background or {})

    if any(
        k in t
        for k in (
            "不懂也",
            "先往下",
            "应该都懂了吧",
            "不用深究",
            "不必深究",
            "大概知道",
            "先记住",
            "以后再讲",
        )
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
        dialog_state, question_difficulty = self._infer_dialog_state(
            teacher_text, bg, teacher_text_ts
        )
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
            trigger_line = teacher_text.strip()
            if trigger_line and dialog_state != "questioning":
                bg_reply["trigger_teacher_text"] = trigger_line

            if dialog_state == "questioning":
                # 不再预生成 6 条候选回复；由前端点名后通过 /ai/v2/inclass/student/reply 实时生成
                decision["student_event"] = None
                if question_difficulty is not None:
                    decision["question_difficulty"] = question_difficulty
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
    ) -> Tuple[str, Optional[int]]:
        t = teacher_text.strip()

        # 状态库短路：called_student 在数据库中确实处于 sleep/whisper 状态时，
        # 跳过 LLM 直接返回对应纪律类型，避免误判且节省一次 LLM 调用。
        digest = (background or {}).get("called_student_status_digest")
        if isinstance(digest, dict):
            if digest.get("is_sleeping"):
                return "discipline_sleep", None
            if digest.get("is_whispering"):
                return "discipline_whisper", None

        ts_line = (teacher_text_ts or "").strip() or "未提供"
        try:
            chat = get_chat()
            prompt = STATE_INFER_PROMPT.format(
                teacher_text=t,
                teacher_text_ts_line=ts_line,
                background_json=json.dumps(background, ensure_ascii=False, indent=2),
            )
            prompt = f"{prompt}\n\n{STATE_INFER_GUIDE}"
            resp = chat.invoke([HumanMessage(content=prompt)])
            raw = resp.content if hasattr(resp, "content") else str(resp)
            data = extract_json_object(raw)
            state = _normalize_dialog_state(data.get("dialog_state"))
            difficulty = _normalize_question_difficulty(data.get("question_difficulty"))
            if state is not None:
                state = _apply_questioning_guardrails(state, t)
                state = _apply_misstatement_guardrails(state, t, background)
                state = _split_questioning_vs_relay(state, background)
                if state != "questioning":
                    difficulty = None
                return state, difficulty
        except Exception:
            pass
        ruled = _infer_dialog_state_rules(teacher_text, background)
        ruled = _apply_questioning_guardrails(ruled, t)
        ruled = _apply_misstatement_guardrails(ruled, t, background)
        return ruled, None
