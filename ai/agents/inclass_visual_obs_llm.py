"""课中教姿教态视觉分析 VLM（每 15 秒窗口一次）。

主 VLM：Qwen2.5-VL-7B-Instruct（SiliconFlow）
疑难复核：GLM-4.6V（SiliconFlow）—— confidence < 0.45 时自动触发

场景：居家/在线模拟试讲（坐姿、半身、偏侧入镜均属正常）

输入：
    3 帧 base64 JPEG + 最近 20 条师生 chat_history + segment/slide 上下文

输出（结构化 JSON）：
    posture / gesture / expression 各维度分数与问题
    affect（nervousness / anxiety / naturalness 0-1）
    teaching_presence_score（综合 0-100）
    confidence（VLM 自评 0-1）
    highlights（时间轴事件列表）
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from setting.llm import visual_vlm, visual_vlm_fallback
from .llm_utils import extract_json_object

_CONFIDENCE_FALLBACK_THRESHOLD = 0.45
_HOME_TEACHING_MIN_CONFIDENCE = 0.55

VISUAL_PROMPT = """你是一位资深教学督导，正在对模拟授课视频截图进行教姿教态点评。
你的点评风格应像一位专业导师：以鼓励为主、具体建设，既肯定亮点，也**指出真实不足**。

【评分参考标准：教师资格证面试仪表仪态要求】
- 仪表仪态占比约 10%，核心看：举止自然大方、有亲和力；衣着/形象得体；肢体表达得当
- 站姿：端正、稳重、亲切、自然；挺胸抬头、目视前方、平肩收腹；避免长时间手撑桌面、身体不稳、侧身而站、双手交叉抱胸/背后
- 坐姿：正襟危坐即可；避免双腿开叉过大、抖腿、仰靠椅背、二郎腿
- 眼神：与"学生"/镜头有交流，可环视可注视；避免长时间低头、视线飘忽、视而不见
- 手势：自然得体、配合讲解；避免无意义小动作、手势过多过杂、手扶讲桌、频繁扶眼镜
- 表情：自然亲切、面带微笑；避免僵硬、紧绷、面无表情
- 整体气质：从容自信、积极开朗

【评分场景说明（仅供评分参考，禁止写入反馈文字）】
- 本次为模拟授课/在线试讲，教师可坐可站，摄像头视角不限
- 半身/头肩入镜即可评估，侧脸、偏位、轻微后仰、自然坐姿均不扣分
- 仅当**画面中完全看不到教师**或**严重模糊**时，才给 confidence < 0.35

【课堂上下文】
- 当前知识点/PPT 第 {slide_no} 页
- 窗口时间段：课堂第 {window_start_sec}-{window_end_sec} 秒
- 当前片段 ID：{segment_id}

【最近师生对话（最多20条）】
{chat_history_text}

【评估维度】
1. 身体姿态：是否端正稳重？是否含胸/驼背/明显后仰？肢体是否过于封闭（双臂交叉）？
2. 手势运用：是否自然配合讲解？是否有无意义小动作或过于频繁？
3. 面部表情：是否自然亲切？是否有微笑？是否僵硬/紧绷？
4. 眼神视线：是否注视镜头/学生？是否长时间低头看稿或视线游离？
5. 整体气场：是否从容自信、有亲和力？

【评分标准】
- 各维度 score：0-100（85+优秀，70-84良好，60-69合格/待提升，<60需关注）
- **基础分原则**：只要教师出镜并在正常讲授，姿态无明显崩塌、表情无明显僵硬，建议从 75 分左右起评，不要过低
- **容错原则**：模拟授课/居家环境下，轻微偏位、侧脸、自然坐姿、偶尔低头看稿、手势不多但自然，只作轻微扣分（一般不低于 70）
- **扣分项**：仅当出现明显且持续的问题时才明显降分，例如：双臂长时间交叉抱胸、严重驼背/后仰、长时间低头不看镜头、表情过度紧张僵硬、手势杂乱无章或过多干扰讲解
- confidence：教师头肩清晰可见时应 ≥ 0.55；只要疑似出镜且正常授课，不要给过低 confidence

【highlights 要求（重要）】
- type 只有两种：`good`（绿色亮点）或 `warning`（橙色待改进）
- **参考课中片段评价的思路：每个窗口尽量同时挖掘"做得好的地方"和"可改进的地方"，保持 green / orange 均衡，不要只挑问题**
- **以下情况为 good，例如：**
  - "身体端正，面向镜头/学生，姿态稳定自信"
  - "配合讲解使用手势，指向PPT关键内容，表达清晰有力"
  - "表情自然亲切，面带微笑，富有亲和力"
  - "注视镜头与学生保持眼神交流，互动感强"
  - "坐姿端正，上身挺拔，显得从容专业"
- **以下情况为 warning（真实问题示例）：**
  - "长时间低头看稿/看屏幕，与学生眼神交流不足"
  - "双臂交叉抱胸或背在身后，肢体显得封闭/防御"
  - "身体明显驼背、后仰或侧向一边，姿态松懈"
  - "面部表情僵硬、紧张或长时间无表情，缺乏亲和力"
  - "手势过多过杂、无意义小动作多，分散学生注意力"
  - "长时间注视别处或视线游离，未看向镜头/学生"
  - "频繁扶眼镜、摸头发、摸脸等习惯性小动作"
- warning 只写真实需要改进的问题，不要为写而写；没有明显问题时 warning 可为空
- 每条 text 须**具体描述行为**，既夸到点上也指出不足，例如："讲解时双臂交叉，肢体略显封闭" 或 "配合手势指向PPT，表达清晰有力"
- **禁止**写"居家"、"线上场景"、"模拟授课"等场景描述
- **禁止**写空话套话如"整体自然"、"继续保持"之类
- 若本窗口确实无实质内容（如完全无人），highlights 可为空 []

【输出格式】
请**仅根据本次截图与对话**独立评分，下方 JSON 仅展示结构，数值文字必须反映真实观察。
请只输出 JSON，不要 Markdown，不要代码块：
{{
  "posture": {{"score": <0-100>, "stance": "seated|upright|unknown", "issues": ["..."]}},
  "gesture": {{"score": <0-100>, "richness": "low|medium|high", "issues": ["..."]}},
  "expression": {{"score": <0-100>, "primary": "neutral|smile|serious|tense|unknown", "issues": ["..."]}},
  "gaze": {{"toward_students": true|false, "issue": "..."}},
  "affect": {{"nervousness": <0-1>, "anxiety": <0-1>, "naturalness": <0-1>}},
  "teaching_presence_score": <0-100>,
  "confidence": <0-1>,
  "highlights": [{{"type": "good|warning", "text": "具体行为描述"}}]
}}

注意：
- issues 为空 [] 表示该维度表现良好
- 仅当确实无人/完全看不清时 confidence < 0.35
- 结合对话判断教师是否在讲授重点时段
- 评分时以教师资格证面试"仪表仪态得体、举止自然大方、有亲和力"为合格线，合格即可给 70 分以上"""


def _format_chat_history(chat_history: List[Dict[str, Any]]) -> str:
    if not chat_history:
        return "（暂无对话记录）"
    lines = []
    for item in chat_history[-20:]:
        role = item.get("role", "")
        text = str(item.get("text") or item.get("content") or "").strip()
        elapsed = item.get("class_elapsed_sec")
        time_tag = f"[{elapsed//60:02d}:{elapsed%60:02d}]" if elapsed is not None else ""
        role_cn = "教师" if role == "teacher" else f"学生({role})"
        lines.append(f"{time_tag} {role_cn}：{text}")
    return "\n".join(lines)


def _build_image_content(frames_b64: List[str]) -> list:
    """构造 langchain 多模态 content 块（文本 + 图片列表）。"""
    content = []
    for b64 in frames_b64[:3]:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
    return content


def _run_vlm(model_wrapper: Any, prompt_text: str, frames_b64: List[str]) -> Dict[str, Any]:
    model = model_wrapper.model if hasattr(model_wrapper, "model") else model_wrapper
    content = _build_image_content(frames_b64)
    content.append({"type": "text", "text": prompt_text})
    resp = model.invoke([HumanMessage(content=content)])
    raw = resp.content if hasattr(resp, "content") else str(resp)
    return extract_json_object(raw)


def _calc_presence_score(data: Dict[str, Any]) -> int:
    posture = int((data.get("posture") or {}).get("score") or 75)
    gesture = int((data.get("gesture") or {}).get("score") or 75)
    expression = int((data.get("expression") or {}).get("score") or 75)
    return int(round(0.35 * posture + 0.30 * gesture + 0.35 * expression))


def _avg_dimension_score(data: Dict[str, Any]) -> float:
    scores = [
        int((data.get("posture") or {}).get("score") or 0),
        int((data.get("gesture") or {}).get("score") or 0),
        int((data.get("expression") or {}).get("score") or 0),
    ]
    nonzero = [s for s in scores if s > 0]
    return sum(nonzero) / len(nonzero) if nonzero else 0.0


def _teacher_likely_visible(data: Dict[str, Any]) -> bool:
    presence = int(data.get("teaching_presence_score") or 0)
    if presence >= 40:
        return True
    if _avg_dimension_score(data) >= 40:
        return True
    for key in ("posture", "gesture", "expression"):
        issues = (data.get(key) or {}).get("issues") or []
        if any(str(i).strip() for i in issues):
            return True
    if data.get("highlights"):
        return True
    return False


def _normalize_highlight_type(ev: Dict[str, str]) -> Dict[str, str]:
    """把 VLM 返回的 info 映射为 good，保留 warning，其余归为 good。"""
    t = str(ev.get("type") or "good").lower()
    if t == "warning":
        return {**ev, "type": "warning"}
    return {**ev, "type": "good"}


def _ensure_highlights(data: Dict[str, Any]) -> None:
    """规范化 highlights 类型；不再强制兜底每个窗口都生成一条。"""
    raw = data.get("highlights") or []
    if not isinstance(raw, list):
        raw = []

    normalized = [_normalize_highlight_type(ev) for ev in raw if str(ev.get("text") or "").strip()]

    # 若 VLM 没有给 highlights，从 issues 里摘取实质性问题作 warning
    if not normalized:
        for key, label in (("posture", "教姿"), ("gesture", "手势"), ("expression", "表情")):
            dim = data.get(key) or {}
            for issue in dim.get("issues") or []:
                text = str(issue).strip()
                if text:
                    normalized.append({"type": "warning", "text": f"{label}：{text}"})
        gaze_issue = str((data.get("gaze") or {}).get("issue") or "").strip()
        if gaze_issue:
            normalized.append({"type": "warning", "text": f"视线：{gaze_issue}"})

    data["highlights"] = normalized


def _apply_home_teaching_adjustments(data: Dict[str, Any]) -> Dict[str, Any]:
    if data.get("skip_reason"):
        return data

    presence = int(data.get("teaching_presence_score") or 0)
    if presence <= 0 and _avg_dimension_score(data) > 0:
        data["teaching_presence_score"] = _calc_presence_score(data)
        presence = int(data["teaching_presence_score"])

    if _teacher_likely_visible(data):
        conf = float(data.get("confidence") or 0.0)
        data["confidence"] = max(conf, _HOME_TEACHING_MIN_CONFIDENCE)

    _ensure_highlights(data)
    return data


def _normalize_output(data: Dict[str, Any], observation_id: str) -> Dict[str, Any]:
    posture = data.get("posture") or {}
    gesture = data.get("gesture") or {}
    expression = data.get("expression") or {}
    gaze = data.get("gaze") or {}
    affect = data.get("affect") or {}
    highlights = data.get("highlights") or []
    if not isinstance(highlights, list):
        highlights = []

    presence = data.get("teaching_presence_score")
    if not presence:
        presence = _calc_presence_score(data)

    raw_conf = data.get("confidence")
    confidence = 0.75 if raw_conf is None else float(raw_conf)
    confidence = max(0.0, min(1.0, confidence))

    return {
        "observation_id": observation_id,
        "posture": {
            "score": int(posture.get("score") or 75),
            "stance": str(posture.get("stance") or "unknown"),
            "issues": list(posture.get("issues") or []),
        },
        "gesture": {
            "score": int(gesture.get("score") or 75),
            "richness": str(gesture.get("richness") or "medium"),
            "issues": list(gesture.get("issues") or []),
        },
        "expression": {
            "score": int(expression.get("score") or 75),
            "primary": str(expression.get("primary") or "neutral"),
            "issues": list(expression.get("issues") or []),
        },
        "gaze": {
            "toward_students": bool(gaze.get("toward_students", True)),
            "issue": str(gaze.get("issue") or ""),
        },
        "affect": {
            "nervousness": float(affect.get("nervousness") or 0.2),
            "anxiety": float(affect.get("anxiety") or 0.2),
            "naturalness": float(affect.get("naturalness") or 0.75),
        },
        "teaching_presence_score": int(presence),
        "confidence": confidence,
        "highlights": highlights,
    }


class InclassVisualObsLLM:
    """课中每 15 秒窗口调用一次，分析教师教姿教态。"""

    def run(
        self,
        *,
        observation_id: str,
        frames_b64: List[str],
        chat_history: Optional[List[Dict[str, Any]]] = None,
        window_start_sec: int = 0,
        window_end_sec: int = 15,
        segment_id: str = "",
        slide_no: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not frames_b64:
            return self._empty_result(observation_id, reason="no_frames")

        chat_text = _format_chat_history(chat_history or [])
        prompt = VISUAL_PROMPT.format(
            slide_no=slide_no if slide_no is not None else "未知",
            window_start_sec=window_start_sec,
            window_end_sec=window_end_sec,
            segment_id=segment_id or "未知",
            chat_history_text=chat_text,
        )

        try:
            data = _run_vlm(visual_vlm, prompt, frames_b64)
        except Exception as e:
            return self._empty_result(observation_id, reason=f"vlm_error:{e}")

        confidence = float(data.get("confidence") or 0.0)
        if confidence < _CONFIDENCE_FALLBACK_THRESHOLD:
            try:
                data_fb = _run_vlm(visual_vlm_fallback, prompt, frames_b64)
                conf_fb = float(data_fb.get("confidence") or 0.0)
                if conf_fb > confidence:
                    data = data_fb
            except Exception:
                pass

        result = _normalize_output(data, observation_id)
        return _apply_home_teaching_adjustments(result)

    def _empty_result(self, observation_id: str, reason: str = "") -> Dict[str, Any]:
        return {
            "observation_id": observation_id,
            "posture": {"score": 0, "stance": "unknown", "issues": []},
            "gesture": {"score": 0, "richness": "unknown", "issues": []},
            "expression": {"score": 0, "primary": "unknown", "issues": []},
            "gaze": {"toward_students": False, "issue": ""},
            "affect": {"nervousness": 0.0, "anxiety": 0.0, "naturalness": 0.0},
            "teaching_presence_score": 0,
            "confidence": 0.0,
            "highlights": [],
            "skip_reason": reason,
        }
