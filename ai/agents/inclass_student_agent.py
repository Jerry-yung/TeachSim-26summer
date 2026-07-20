"""课中学生 Agent（由 LLM 生成话术）."""
import json
import random
import re
from typing import Any, Dict, Tuple

from langchain_core.messages import HumanMessage

from .llm_utils import extract_json_object, get_chat


ROLE_NAMES = {
    "xueyou": "学优生（爱质疑、思维快）",
    "gangjing": "杠精（爱质疑、抓漏洞）",
    "xuekun": "学困生（基础弱、胆怯）",
    "sleepy": "打瞌睡学生",
    "whisper": "交头接耳学生",
}

_HAND_RAISE_PHRASES = (
    "我举手回答",
    "我举手",
    "举手回答",
    "老师我举手",
)

_REPLY_PREFIX_PHRASES = (
    "我试着想一下",
    "我试着想一下，",
    "我试着想一下。",
    "我试着说",
    "我试着说，",
    "我试着说。",
    "我试着说一下",
    "我试着说一下，",
    "我试着回答",
    "我试着回答：",
    "我来回答",
    "我来回答：",
)

_ANSWER_MODES = ("correct", "partial", "wrong", "off_topic")

# teacher_question 基础分布（simple / medium 难度、未做举手调节前）
_QUESTION_BASE_PROBS: Dict[str, Dict[str, float]] = {
    "xueyou": {"correct": 0.75, "partial": 0.18, "wrong": 0.06, "off_topic": 0.01},
    "gangjing": {"correct": 0.65, "partial": 0.20, "wrong": 0.12, "off_topic": 0.03},
    "xuekun": {"correct": 0.25, "partial": 0.35, "wrong": 0.35, "off_topic": 0.05},
}

# relay_answer 基础分布
_RELAY_BASE_PROBS: Dict[str, Dict[str, float]] = {
    "xueyou": {"correct": 0.70, "partial": 0.22, "wrong": 0.08, "off_topic": 0.00},
    "gangjing": {"correct": 0.60, "partial": 0.25, "wrong": 0.15, "off_topic": 0.00},
    "xuekun": {"correct": 0.30, "partial": 0.40, "wrong": 0.28, "off_topic": 0.02},
}

_ERROR_TYPES_BY_ROLE: Dict[str, Tuple[str, ...]] = {
    "xueyou": ("calculation_error", "over_extension"),
    "gangjing": ("contrarian_misjudgment", "overgeneralization"),
    "xuekun": (
        "concept_confusion",
        "formula_misapplication",
        "overgeneralization",
        "conclusion_without_conditions",
    ),
}

_ERROR_TYPE_LABELS: Dict[str, str] = {
    "concept_confusion": "概念混淆（把相近概念混为一谈）",
    "formula_misapplication": "公式误用（方法看着对但套错条件或符号）",
    "overgeneralization": "以偏概全（把特殊情况当成普遍结论）",
    "conclusion_without_conditions": "记结论忘条件（只背结论、漏掉适用前提）",
    "calculation_error": "计算小错（推理大体对、最后一步数或符号错）",
    "over_extension": "过度延伸（推理链过长、某一步跳错）",
    "contrarian_misjudgment": "抬杠式误判（抓住边角反例但结论站不住）",
}

STUDENT_REPLY_PROMPT = """你正在参与课堂模拟。角色：{role_name}。
触发原因：{trigger_reason}
学科背景：{subject}
本轮触发教师句（若有）：{trigger_teacher_text}
幻灯片/环节信息（若有）：{slide_hint}
最近关键上下文（辅助，勿喧宾夺主）：{recency_hint}
是否主动发言：{is_proactive_speaking}
{answer_quality_hint}

生成要求：
1) 先结合给定的上下文与 PPT 信息再作答，尽量围绕当前页要点。
2) 当触发原因是 teacher_question（教师提问）时，必须根据是否主动发言来决定语气：
   - is_proactive_speaking=true：语气可更自信、直接，但禁止出现任何"举手"相关措辞。
   - is_proactive_speaking=false：视为"未举手但被点名"，可在句中用"好像""可能""我不太确定"等表达迟疑，但仍需给出具体观点，不能只说不会或纯求助。
   - 禁止在 reply_text 开头使用固定套话，例如"我试着想一下""我试着说""我试着说一下""我来回答"等。
3) 无论任何场景，都不要在 reply_text 中出现"举手"、"我举手回答"等字样，发言积极性仅通过语气与情绪体现。
4) teacher_question 场景下的角色差异：
   - 学优生（xueyou）：回答更完整，逻辑更清楚；可在末尾带简短延伸；难题上也可能出错，但通常是"接近正确"的错误。
   - 杠精（gangjing）：更偏"质疑式回答"，会抓边界条件或反例，语气更尖锐但仍围绕题目；答错时常是抬杠方向错了。
   - 学困生（xuekun）：必须给出与题目相关的具体观点，不能只会"嗯…""不太会"；常见表现包括概念混淆、公式套错、结论错误、表述碎片化；未举手被点名时更迟疑，但仍要尝试作答。
   - 若上方「本轮答题质量要求」已指定 correct/partial/wrong/off_topic，必须严格按该要求组织内容，不得擅自改成另一种质量。
5) 当触发原因是 relay_answer（接力回答/补充指正）时，必须结合 background 中的上下文（含上一轮学生发言 student_utterances_on_slide）：
   - 学优生（xueyou）：先简要肯定上一位同学，再补充遗漏或纠正偏差，语气专业。
   - 杠精（gangjing）：直接指出上一位发言的逻辑漏洞或边界问题，语气尖锐但聚焦问题。
   - 学困生（xuekun）：先表示认同或指出困惑点，再尝试补充（可补偏），语气犹豫但具体。
   - 接力回答的关键：必须体现"听了上一位的发言后"的回应（补充、指正或纠错），不能脱离上下文独立回答。
   - 如果 student_utterances_on_slide 中有内容，请据此进行针对性回应；如果没有，则围绕当前 PPT 内容进行一般性补充。
6) 当 trigger_reason 为 teacher_misstatement（教师知识性错误）时：
   - **必须只针对「本轮触发教师句」指出错误或澄清**，不要回答更早对话里的其他话题。
   - 杠精（gangjing）：直接抓该句中的错误点；学困生（xuekun）：可犹豫但需点出哪里不对。
7) 当 trigger_reason 为 semantic_ambiguity（教师表述含糊/跳步）时：
   - **必须只针对「本轮触发教师句」表达困惑或请老师讲清楚**，不要展开无关内容。
8) 有「本轮触发教师句」时，它以第一优先级为准；最近关键上下文仅作辅助，不要被早期话题带偏。
9) 非上述场景按原角色设定生成（困惑、澄清、违纪解释等）。
10) 当是否主动发言=false 时，优先使用 hesitant/confused/embarrassed 情绪，通过措辞体现不确定，而非固定前缀；当=true 时，优先使用 curious 或自信语气。
11) 若 background.question_bundle.count > 1（老师连续多问）：
   - 你的回答需要覆盖这些连续问题的核心点，不能只回答最后一个问题。
   - 若 question_bundle.items 存在，优先按这些子问题顺序组织回答；若只有 question_bundle.text，则围绕其中的多个问点作答。

请用该角色口吻写一句课堂上的话（不超过 50 字），并给出情绪标签。
只输出 JSON：{{"reply_text":"...","emotion":"curious|confused|hesitant|sleepy|whispering|panicked|embarrassed|idle"}}

不要输出其他文字。"""


def _question_count(background: Dict[str, Any]) -> int:
    qb = background.get("question_bundle") or {}
    try:
        count = int(qb.get("count") or 0)
    except (TypeError, ValueError):
        count = 0
    items = qb.get("items") or []
    if count <= 0:
        count = max(len(items), 1)
    return max(count, 1)


def _estimate_difficulty(background: Dict[str, Any]) -> str:
    """simple | medium | complex"""
    count = _question_count(background)
    if count > 1:
        return "complex"
    return "simple"


def _copy_probs(source: Dict[str, float]) -> Dict[str, float]:
    return {mode: float(source.get(mode, 0.0)) for mode in _ANSWER_MODES}


def _normalize_probs(probs: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(v, 0.0) for v in probs.values())
    if total <= 0:
        return {"correct": 1.0, "partial": 0.0, "wrong": 0.0, "off_topic": 0.0}
    return {mode: max(probs.get(mode, 0.0), 0.0) / total for mode in _ANSWER_MODES}


def _shift_prob(
    probs: Dict[str, float],
    *,
    from_mode: str,
    to_mode: str,
    amount: float,
) -> None:
    if amount <= 0:
        return
    moved = min(amount, probs.get(from_mode, 0.0))
    probs[from_mode] = probs.get(from_mode, 0.0) - moved
    probs[to_mode] = probs.get(to_mode, 0.0) + moved


def _build_answer_probs(
    *,
    student_type: str,
    trigger_reason: str,
    background: Dict[str, Any],
    is_proactive_speaking: bool,
) -> Dict[str, float]:
    base_map = _QUESTION_BASE_PROBS if trigger_reason == "teacher_question" else _RELAY_BASE_PROBS
    fallback = base_map.get("xuekun", _QUESTION_BASE_PROBS["xuekun"])
    probs = _copy_probs(base_map.get(student_type, fallback))

    difficulty = _estimate_difficulty(background)
    if difficulty == "simple":
        _shift_prob(probs, from_mode="wrong", to_mode="correct", amount=0.04)
        if student_type == "xuekun":
            _shift_prob(probs, from_mode="wrong", to_mode="partial", amount=0.08)
        elif student_type == "xueyou":
            _shift_prob(probs, from_mode="wrong", to_mode="correct", amount=0.02)
    elif difficulty == "complex":
        if student_type == "xueyou":
            _shift_prob(probs, from_mode="correct", to_mode="wrong", amount=0.09)
            _shift_prob(probs, from_mode="correct", to_mode="partial", amount=0.03)
        elif student_type == "gangjing":
            _shift_prob(probs, from_mode="correct", to_mode="wrong", amount=0.06)
            _shift_prob(probs, from_mode="correct", to_mode="partial", amount=0.04)
        elif student_type == "xuekun":
            _shift_prob(probs, from_mode="correct", to_mode="wrong", amount=0.12)
            _shift_prob(probs, from_mode="partial", to_mode="wrong", amount=0.08)

    if is_proactive_speaking:
        if student_type == "xueyou":
            _shift_prob(probs, from_mode="wrong", to_mode="correct", amount=0.05)
            _shift_prob(probs, from_mode="partial", to_mode="correct", amount=0.03)
        elif student_type == "xuekun":
            _shift_prob(probs, from_mode="wrong", to_mode="partial", amount=0.06)
            _shift_prob(probs, from_mode="correct", to_mode="partial", amount=0.04)
    else:
        if student_type == "xuekun":
            _shift_prob(probs, from_mode="correct", to_mode="wrong", amount=0.08)
            _shift_prob(probs, from_mode="partial", to_mode="wrong", amount=0.04)
        elif student_type == "xueyou":
            _shift_prob(probs, from_mode="correct", to_mode="partial", amount=0.05)

    return _normalize_probs(probs)


def _sample_answer_mode(probs: Dict[str, float]) -> str:
    modes = list(_ANSWER_MODES)
    weights = [probs.get(mode, 0.0) for mode in modes]
    return random.choices(modes, weights=weights, k=1)[0]


def _sample_error_type(student_type: str, answer_mode: str) -> str:
    if answer_mode not in ("partial", "wrong", "off_topic"):
        return ""
    pool = _ERROR_TYPES_BY_ROLE.get(student_type, _ERROR_TYPES_BY_ROLE["xuekun"])
    if answer_mode == "off_topic":
        return "concept_confusion"
    if answer_mode == "partial" and student_type == "xueyou":
        return random.choice(("calculation_error", "over_extension"))
    return random.choice(pool)


def _build_answer_quality_hint(
    *,
    student_type: str,
    trigger_reason: str,
    answer_mode: str,
    error_type: str,
) -> str:
    if trigger_reason not in ("teacher_question", "relay_answer"):
        return "本轮答题质量要求：（未预设，按角色自然作答即可。）"

    mode_labels = {
        "correct": "回答基本正确，紧扣当前页要点与教师问题",
        "partial": "回答方向大体对，但缺关键一步、细节有误或表述不完整",
        "wrong": "回答与正确答案明显不符，但必须是与题目相关的具体错误观点，禁止只说「不会」",
        "off_topic": "回答偏题或答非所问，但仍要有一句像学生会说的话",
    }
    lines = [
        "本轮答题质量要求（系统预设，必须严格执行，不要偏离）：",
        f"- 质量档位：{answer_mode}（{mode_labels[answer_mode]}）",
    ]
    if error_type:
        label = _ERROR_TYPE_LABELS.get(error_type, error_type)
        lines.append(f"- 错误形态：{label}")
    if trigger_reason == "relay_answer":
        lines.append("- 接力场景：必须体现听了上一位同学发言后的回应，partial/wrong 时可跟风补偏或错误纠正。")
    if student_type == "xuekun" and answer_mode == "wrong":
        lines.append("- 学困生答错时也要给出具体错误结论，可搭配「好像」「可能」等迟疑语气。")
    if student_type == "xueyou" and answer_mode == "wrong":
        lines.append("- 学优生答错时仍应像认真思考过的错误，避免无厘头。")
    return "\n".join(lines)


def _sample_answer_profile(
    *,
    student_type: str,
    trigger_reason: str,
    background: Dict[str, Any],
    is_proactive_speaking: bool,
) -> Tuple[str, str]:
    if trigger_reason not in ("teacher_question", "relay_answer"):
        return "", ""
    if student_type not in ("xueyou", "gangjing", "xuekun"):
        return "", ""

    probs = _build_answer_probs(
        student_type=student_type,
        trigger_reason=trigger_reason,
        background=background,
        is_proactive_speaking=is_proactive_speaking,
    )
    answer_mode = _sample_answer_mode(probs)
    error_type = _sample_error_type(student_type, answer_mode)
    return answer_mode, error_type


def _build_recency_hint(background: Dict[str, Any]) -> str:
    teacher_items = background.get("teacher_utterances_on_slide") or []
    student_items = background.get("student_utterances_on_slide") or []
    teacher_last = [str(x.get("text", "")).strip() for x in teacher_items[-4:]]
    student_last = [str(x.get("text", "")).strip() for x in student_items[-2:]]
    teacher_last = [x for x in teacher_last if x]
    student_last = [x for x in student_last if x]
    chunks = []
    trigger_line = str(background.get("trigger_teacher_text") or "").strip()
    if trigger_line:
        chunks.append("本轮触发教师句: " + trigger_line)
    if teacher_last:
        chunks.append("最近教师发言: " + " | ".join(teacher_last))
    if student_last:
        chunks.append("最近学生发言: " + " | ".join(student_last))
    qb = background.get("question_bundle") or {}
    try:
        q_count = int(qb.get("count") or 0)
    except (TypeError, ValueError):
        q_count = 0
    q_text = str(qb.get("text") or "").strip()
    if q_count > 1 and q_text:
        chunks.append(f"老师连续提问({q_count}问): {q_text}")
    return "；".join(chunks) if chunks else "无"


def _strip_reply_prefixes(text: str) -> str:
    cleaned = str(text or "").strip()
    for phrase in _REPLY_PREFIX_PHRASES:
        if cleaned.startswith(phrase):
            cleaned = cleaned[len(phrase):].lstrip("，。；： …")
    cleaned = re.sub(
        r"^(老师[，,]?)?(我试着(想一下|说(一下)?|回答)|我来回答)[：:，,。…\s]*",
        "",
        cleaned,
    )
    return cleaned.strip()


def _sanitize_reply_text(text: str, *, is_proactive_speaking: bool) -> str:
    del is_proactive_speaking
    cleaned = _strip_reply_prefixes(text)
    for phrase in _HAND_RAISE_PHRASES:
        cleaned = cleaned.replace(phrase, "")
    # 避免生成“我觉得小X说的”这类串台式表述，直接聚焦老师问题
    cleaned = re.sub(r"我觉得小[\u4e00-\u9fa5]{1,2}说的[，,]?", "我觉得", cleaned)
    cleaned = re.sub(r"小[\u4e00-\u9fa5]{1,2}说(得)?[，,]?", "", cleaned)
    cleaned = cleaned.replace("，，", "，").replace("。。", "。").lstrip("，。；： ")
    if not cleaned:
        return "根据题目，我先说一个初步想法。"
    return cleaned


class InclassStudentAgent:
    """由主 LLM 生成学生交互话术。"""

    def reply(
        self,
        *,
        student_type: str,
        trigger_reason: str,
        background: Dict[str, Any],
        is_triggered: bool = False,
        is_proactive_speaking: bool = True,
    ) -> Dict[str, Any]:
        subject = str(background.get("subject", "本课"))
        recency_hint = _build_recency_hint(background)
        trigger_teacher_text = str(background.get("trigger_teacher_text") or "").strip() or "（无）"
        slide_hint = json.dumps(
            {
                k: v
                for k, v in background.items()
                if k not in ("subject", "trigger_teacher_text")
            },
            ensure_ascii=False,
        )
        role_name = ROLE_NAMES.get(student_type, student_type)
        answer_mode, error_type = _sample_answer_profile(
            student_type=student_type,
            trigger_reason=trigger_reason,
            background=background,
            is_proactive_speaking=bool(is_proactive_speaking),
        )
        answer_quality_hint = _build_answer_quality_hint(
            student_type=student_type,
            trigger_reason=trigger_reason,
            answer_mode=answer_mode,
            error_type=error_type,
        ) if answer_mode else "本轮答题质量要求：（未预设，按角色自然作答即可。）"
        prompt = STUDENT_REPLY_PROMPT.format(
            role_name=role_name,
            trigger_reason=trigger_reason,
            subject=subject,
            trigger_teacher_text=trigger_teacher_text,
            slide_hint=slide_hint,
            recency_hint=recency_hint,
            is_proactive_speaking=str(bool(is_proactive_speaking)).lower(),
            answer_quality_hint=answer_quality_hint,
        )
        chat = get_chat()
        resp = chat.invoke([HumanMessage(content=prompt)])
        raw = resp.content if hasattr(resp, "content") else str(resp)
        data = extract_json_object(raw)
        reply_text = _sanitize_reply_text(
            str(data.get("reply_text", "")).strip(),
            is_proactive_speaking=bool(is_proactive_speaking),
        )
        emotion = str(data.get("emotion", "idle")).strip()
        return {
            "student_type": student_type,
            "emotion": emotion or "idle",
            "reply_text": reply_text or "（无回复）",
            "is_triggered": bool(is_triggered),
            "is_proactive_speaking": bool(is_proactive_speaking),
        }