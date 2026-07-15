"""Supervisor 主控决策 Prompt"""
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from langchain_core.prompts import ChatPromptTemplate

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from setting.llm import llm


@dataclass
class SupervisorDecision:
    """Supervisor 决策结果"""
    session_id: str               # 会话ID
    timestamp_ms: int             # 时间戳（毫秒）
    evaluation_note: str          # 评估备注
    is_questioning: bool          # 老师是否在提问
    error_detected: bool          # 是否检测到错误
    trigger_agent: Optional[str]  # 触发哪个 agent（null 表示不触发）
    agent_prompt: Optional[str]   # 给 agent 的 prompt


SUPERVISOR_SYSTEM_PROMPT = """你是 TeachSim 课堂的主控 AI Supervisor，负责实时分析教师的授课内容，并决定是否需要虚拟学生做出反应。

## 你的职责

1. **判断教师当前状态**
   - 正在讲解知识点
   - 正在提问（is_questioning = true）
   - 正在组织课堂活动

2. **检测内容错误**（重要）
   - 学科知识性错误
   - 概念混淆或表述不准确
   - 数学公式、历史事实、科学原理等错误

3. **决定触发哪个虚拟学生**
   - gangjing: 学优生/杠精，喜欢质疑、提出有深度的问题、指出老师错误
   - xuekun: 学困生，表示听不懂、需要基础解释
   - sleepy: 打瞌睡的学生（在老师讲课平淡时触发）
   - whisper: 交头接耳的学生（在课堂纪律松散时触发）
   - null: 不触发任何学生

4. **生成 Agent Prompt**
   - 根据当前教学内容和触发场景，给 agent 清晰的指令
   - 包含：背景信息、学生角色设定、应该说什么、语气要求

## 输出格式

必须返回有效的 JSON，格式如下：

{{  
  "session_id": "uuid-xxxx",
  "timestamp_ms": 5200,
  "evaluation_note": "教态良好，准确讲出勾股定理定义",
  "is_questioning": false,
  "error_detected": false,
  "trigger_agent": "gangjing" | "xuekun" | "sleepy" | "whisper" | null,
  "agent_prompt": "老师刚讲完勾股定理，请用初二学生口吻质疑：如果不是直角三角形还成立吗？"
}}

注意：
- session_id: 保持传入的 session_id
- timestamp_ms: 当前时间戳（毫秒）
- trigger_agent 为 null 时，agent_prompt 也为 null
- evaluation_note: 简短评估，如"教态自然"或"⚠️ 发现错误：..."

## 决策规则

1. **老师在提问时**（is_questioning = true）
   - 通常不触发学生反应，等待老师点名
   - trigger_agent = null

2. **老师讲解出现错误时**（error_detected = true）
   - trigger_agent = "gangjing"
   - agent_prompt 要明确指出错误并给出纠正

3. **老师讲解完一个知识点后**
   - 30% 概率触发 gangjing 提出深度问题
   - 20% 概率触发 xuekun 表示困惑
   - 触发时需要生成合适的 agent_prompt

4. **讲课时间过长且平淡**
   - 可能触发 sleepy 或 whisper

5. **正常情况下**
   - trigger_agent = null
   - 只记录 evaluation_note

## 学科知识参考（用于错误检测）

- 数学：勾股定理只适用于直角三角形；负数没有实数平方根；0 不能作除数
- 物理：牛顿第一定律需要理想条件；作用力与反作用力作用在不同物体上
- 化学：催化剂不参与反应但最终不变；燃烧需要氧气

请根据上述规则，对教师的授课内容做出准确判断。
"""

SUPERVISOR_USER_PROMPT = """## 课堂上下文

课程主题: {lesson_topic}
学科: {subject}
当前知识点: {current_topic}
会话ID: {session_id}

## 对话历史（最近3轮）

{chat_history}

## 教师当前发言

"{teacher_text}"

## 请输出决策 JSON
"""


class Supervisor:
    """课堂主控决策器"""
    
    def __init__(self):
        self.llm = llm.model if hasattr(llm, 'model') else llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SUPERVISOR_SYSTEM_PROMPT),
            ("human", SUPERVISOR_USER_PROMPT)
        ])
        self.chain = self.prompt | self.llm
    
    def decide(
        self,
        teacher_text: str,
        lesson_topic: str = "未指定",
        subject: str = "未指定",
        current_topic: str = "",
        chat_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根据教师发言做出决策
        
        Args:
            teacher_text: 教师当前发言
            lesson_topic: 课程主题
            subject: 学科
            current_topic: 当前讲解的知识点
            chat_history: 对话历史
            session_id: 会话ID（不传则自动生成）
        
        Returns:
            决策结果字典（符合 api.md 格式）
        """
        # 生成 session_id 和时间戳
        session_id = session_id or str(uuid.uuid4())
        timestamp_ms = int(time.time() * 1000)
        
        # 格式化对话历史
        history_str = self._format_history(chat_history or [])
        
        try:
            response = self.chain.invoke({
                "teacher_text": teacher_text,
                "lesson_topic": lesson_topic,
                "subject": subject,
                "current_topic": current_topic,
                "chat_history": history_str,
                "session_id": session_id
            })
            
            result_text = response.content if hasattr(response, 'content') else str(response)
            
            # 解析 JSON
            result = self._extract_json(result_text)
            
            # 确保必要字段存在
            result["session_id"] = session_id
            result["timestamp_ms"] = timestamp_ms
            
            # 确保 trigger_agent 和 agent_prompt 同时为 null
            if result.get("trigger_agent") is None:
                result["agent_prompt"] = None
            
            return result
            
        except Exception as e:
            # 出错时返回安全默认值
            return {
                "session_id": session_id,
                "timestamp_ms": timestamp_ms,
                "evaluation_note": f"决策出错: {str(e)}",
                "is_questioning": self._detect_question(teacher_text),
                "error_detected": False,
                "trigger_agent": None,
                "agent_prompt": None
            }
    
    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """格式化对话历史"""
        if not history:
            return "（无历史记录）"
        
        lines = []
        for item in history[-3:]:  # 只取最近3轮
            role = item.get("role", "unknown")
            content = item.get("content", "")
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines) if lines else "（无历史记录）"
    
    def _extract_json(self, text: str) -> Dict:
        """从文本中提取 JSON"""
        # 首先尝试直接解析
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # 尝试从 markdown 代码块中提取
        import re
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
        
        # 尝试找到第一个 { 和最后一个 }
        try:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
        
        raise ValueError("无法从响应中解析 JSON")
    
    def _detect_question(self, text: str) -> bool:
        """简单启发式判断是否在提问"""
        question_patterns = [
            r'谁.*？', r'什么.*？', r'怎么.*？', r'为什么.*？',
            r'是不是', r'对不对', r'好不好', r'可以吗',
            r'哪位同学', r'谁来', r'请回答', r'谁知道',
        ]
        
        # 检测问号
        if '？' in text or '?' in text:
            return True
        
        # 检测疑问词
        import re
        for pattern in question_patterns:
            if re.search(pattern, text):
                return True
        
        return False


# 快捷函数
def quick_decide(teacher_text: str, **kwargs) -> Dict[str, Any]:
    """快速决策函数"""
    supervisor = Supervisor()
    return supervisor.decide(teacher_text, **kwargs)
