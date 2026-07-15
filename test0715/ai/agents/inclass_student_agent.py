"""课中学生 Agent（由 LLM 生成话术）."""
import json
from typing import Any, Dict

from langchain_core.messages import HumanMessage

from .llm_utils import extract_json_object, get_chat


ROLE_NAMES = {
    "xueyou": "学优生（爱质疑、思维快）",
    "gangjing": "杠精（爱质疑、抓漏洞）",
    "xuekun": "学困生（基础弱、胆怯）",
    "sleepy": "打瞌睡学生",
    "whisper": "交头接耳学生",
}

STUDENT_REPLY_PROMPT = """你正在参与课堂模拟。角色：{role_name}。
触发原因：{trigger_reason}
学科背景：{subject}
幻灯片/环节信息（若有）：{slide_hint}
是否主动发言：{is_proactive_speaking}

生成要求：
1) 先结合给定的上下文与 PPT 信息再作答，尽量围绕当前页要点。
2) 当触发原因是 teacher_question（教师提问）时，必须生成"主动举手回答"的一句话，不能生成"我没听懂/请再讲一遍/我不会"这类求助句。
3) teacher_question 场景下的角色差异：
   - 学优生（xueyou）：回答更完整，逻辑更清楚；可在末尾带简短延伸。
   - 杠精（gangjing）：更偏"质疑式回答"，会抓边界条件或反例，语气更尖锐但仍围绕题目。
   - 学困生（xuekun）：也要尝试作答，可出现条理不清、细节缺失或结论错误，但语气应是"我来回答/我觉得..."，而不是求助。
4) 当触发原因是 relay_answer（接力回答/补充指正）时，必须结合 background 中的上下文（含上一轮学生发言 student_utterances_on_slide）：
   - 学优生（xueyou）：先简要肯定上一位同学，再补充遗漏或纠正偏差，语气专业。
   - 杠精（gangjing）：直接指出上一位发言的逻辑漏洞或边界问题，语气尖锐但聚焦问题。
   - 学困生（xuekun）：先表示认同或指出困惑点，再尝试补充（可补偏），语气犹豫但具体。
   - 接力回答的关键：必须体现"听了上一位的发言后"的回应（补充、指正或纠错），不能脱离上下文独立回答。
   - 如果 student_utterances_on_slide 中有内容，请据此进行针对性回应；如果没有，则围绕当前 PPT 内容进行一般性补充。
5) 非上述场景按原角色设定生成（困惑、澄清、违纪解释等）。
6) 当是否主动发言=false 时，语气应更被动（如"我试着回答…""我觉得可能是…"），但仍需给出具体观点，不能只说不会。

请用该角色口吻写一句课堂上的话（不超过 50 字），并给出情绪标签。
只输出 JSON：{{"reply_text":"...","emotion":"curious|confused|hesitant|sleepy|whispering|panicked|embarrassed|idle"}}

不要输出其他文字。"""


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
        slide_hint = json.dumps(
            {k: v for k, v in background.items() if k != "subject"},
            ensure_ascii=False,
        )
        role_name = ROLE_NAMES.get(student_type, student_type)
        prompt = STUDENT_REPLY_PROMPT.format(
            role_name=role_name,
            trigger_reason=trigger_reason,
            subject=subject,
            slide_hint=slide_hint,
            is_proactive_speaking=str(bool(is_proactive_speaking)).lower(),
        )
        chat = get_chat()
        resp = chat.invoke([HumanMessage(content=prompt)])
        raw = resp.content if hasattr(resp, "content") else str(resp)
        data = extract_json_object(raw)
        reply_text = str(data.get("reply_text", "")).strip()
        emotion = str(data.get("emotion", "idle")).strip()
        return {
            "student_type": student_type,
            "emotion": emotion or "idle",
            "reply_text": reply_text or "（无回复）",
            "is_triggered": bool(is_triggered),
            "is_proactive_speaking": bool(is_proactive_speaking),
        }
