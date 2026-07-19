"""各 Agent 共用的 LLM 调用与 JSON 解析。"""
import json
import re
from typing import Any, Dict

from langchain_core.messages import HumanMessage

from setting.llm import llm


def get_chat() -> Any:
    return llm.model if hasattr(llm, "model") else llm


def extract_json_object(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return {}


def invoke_json(system_prompt: str) -> Dict[str, Any]:
    """调用主 LLM，期望返回一个 JSON 对象。"""
    chat = get_chat()
    resp = chat.invoke([HumanMessage(content=system_prompt)])
    raw = resp.content if hasattr(resp, "content") else str(resp)
    return extract_json_object(raw)
