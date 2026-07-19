"""课前 PPT 解析：VLM 读图 + LLM 结构化，输出完整 ppt JSON。"""
import base64
import json
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage

from setting.llm import llm, vlm


def _chat(model_wrapper: Any):
    return model_wrapper.model if hasattr(model_wrapper, "model") else model_wrapper


VLM_PROMPT = """你是教学课件分析助手。请根据本页附带的幻灯片截图/配图，用中文识别可见的教学相关视觉内容。

要求：
1. 只输出一个 JSON 对象，不要 Markdown 代码块，不要其他说明文字。
2. 格式严格为：{"visual_elements":["条目1","条目2",...]}
3. 每条 4～24 字，描述图表、几何图、示意图、照片、图标等；若无可用图像则返回 {"visual_elements":[]}。
"""


SLIDE_LLM_PROMPT = """你是一位资深教研员。请根据下列「页面文字」与「图像识别得到的视觉元素」，整理本页结构化信息。

【页面编号】第 {slide_no} 页

【页面文字】
{raw_text}

【视觉元素（来自图像识别，可能为空）】
{visual_note}

请只输出一个 JSON 对象（不要 Markdown），字段如下：
{{
  "title": "本页标题，12 字以内；若文字中无标题则概括主题",
  "text_blocks": ["将正文拆成若干条要点或保留关键句，字符串数组"],
  "summary": "用 25～60 字概括本页教学要点",
  "visual_elements": ["与教学相关的视觉关键词，可与上方列表合并去重，无则 []"]
}}
"""


DECK_LLM_PROMPT = """根据下列课件文件名与各页摘要，输出整份课件的总体信息。

【文件名】{filename}

【各页摘要（按页序）】
{page_summaries}

请只输出一个 JSON 对象：
{{
  "title": "课件主标题（概括主题）",
  "topic": "学科或单元主题关键词，如 初中数学-勾股定理"
}}
"""


def _extract_json_object(text: str) -> Dict[str, Any]:
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


def _mime_from_blob(blob: bytes) -> str:
    if not blob:
        return "image/png"
    if blob[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if blob[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def _vlm_visual_list(vlm_chat: Any, image_blobs: List[bytes]) -> List[str]:
    if not image_blobs:
        return []
    parts: List[Dict[str, Any]] = [{"type": "text", "text": VLM_PROMPT}]
    for blob in image_blobs[:3]:
        b64 = base64.b64encode(blob).decode("ascii")
        mime = _mime_from_blob(blob)
        parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    msg = HumanMessage(content=parts)
    try:
        resp = vlm_chat.invoke([msg])
        raw = resp.content if hasattr(resp, "content") else str(resp)
        data = _extract_json_object(raw)
        els = data.get("visual_elements")
        if isinstance(els, list):
            return [str(x).strip() for x in els if str(x).strip()]
    except Exception:
        pass
    return []


def _llm_slide_json(chat: Any, slide_no: int, raw_text: str, visual_elements: List[str]) -> Dict[str, Any]:
    visual_note = json.dumps(visual_elements, ensure_ascii=False) if visual_elements else "[]"
    prompt = SLIDE_LLM_PROMPT.format(
        slide_no=slide_no,
        raw_text=raw_text or "（无文字）",
        visual_note=visual_note,
    )
    try:
        resp = chat.invoke([HumanMessage(content=prompt)])
        raw = resp.content if hasattr(resp, "content") else str(resp)
        return _extract_json_object(raw)
    except Exception:
        return {}


def _llm_deck_json(chat: Any, filename: str, summaries: List[str]) -> Dict[str, Any]:
    body = "\n".join(f"- 第{i + 1}页：{s}" for i, s in enumerate(summaries))
    prompt = DECK_LLM_PROMPT.format(filename=filename, page_summaries=body or "（无摘要）")
    try:
        resp = chat.invoke([HumanMessage(content=prompt)])
        raw = resp.content if hasattr(resp, "content") else str(resp)
        return _extract_json_object(raw)
    except Exception:
        return {}


def _fallback_slide(slide_no: int, raw_text: str, visual_elements: List[str]) -> Dict[str, Any]:
    lines = [line.strip() for line in (raw_text or "").splitlines() if line.strip()]
    return {
        "title": (lines[0][:120] if lines else "") or f"第{slide_no}页",
        "text_blocks": lines,
        "summary": lines[0][:80] if lines else "",
        "visual_elements": visual_elements,
    }


class PreclassPptLLM:
    """使用 VLM 解析配图 + LLM 生成结构化 JSON。"""

    def run(self, *, filename: str, slides_text: List[Dict[str, Any]]) -> Dict[str, Any]:
        chat = _chat(llm)
        vlm_chat = _chat(vlm)

        slides_out: List[Dict[str, Any]] = []
        summaries: List[str] = []

        for slide in slides_text:
            slide_no = int(slide.get("slide_no", 0))
            raw_text = str(slide.get("raw_text", "")).strip()
            image_blobs = slide.get("image_blobs") or []
            if not isinstance(image_blobs, list):
                image_blobs = []

            vlm_vis = _vlm_visual_list(vlm_chat, image_blobs) if image_blobs else []

            llm_obj = _llm_slide_json(chat, slide_no, raw_text, vlm_vis)
            title = str(llm_obj.get("title") or "").strip()
            text_blocks = llm_obj.get("text_blocks")
            if not isinstance(text_blocks, list):
                text_blocks = []
            text_blocks = [str(x).strip() for x in text_blocks if str(x).strip()]
            summary = str(llm_obj.get("summary") or "").strip()
            merged_vis = llm_obj.get("visual_elements")
            if isinstance(merged_vis, list) and merged_vis:
                merged = [str(x).strip() for x in merged_vis if str(x).strip()]
            else:
                merged = list(vlm_vis)

            if not title and not text_blocks and not summary:
                fb = _fallback_slide(slide_no, raw_text, vlm_vis)
                title = fb["title"]
                text_blocks = fb["text_blocks"]
                summary = fb["summary"]
                merged = merged or fb["visual_elements"]

            slides_out.append(
                {
                    "slide_no": slide_no,
                    "title": title,
                    "text_blocks": text_blocks,
                    "visual_elements": merged,
                    "summary": summary or (text_blocks[0][:80] if text_blocks else ""),
                }
            )
            summaries.append(summary or (text_blocks[0][:80] if text_blocks else raw_text[:80]))

        deck = _llm_deck_json(chat, filename, summaries)
        deck_title = str(deck.get("title") or "").strip()
        deck_topic = str(deck.get("topic") or "").strip()
        if not deck_title and slides_out:
            deck_title = slides_out[0].get("title") or ""
        if not deck_topic:
            deck_topic = "未标注"

        return {
            "deck_info": {
                "title": deck_title or filename,
                "topic": deck_topic,
                "total_slides": len(slides_out),
                "source_file": filename,
            },
            "slides": slides_out,
        }
