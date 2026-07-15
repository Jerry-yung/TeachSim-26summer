"""学生角色 Agent"""
import json
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from setting.llm import llm


class StudentAgent:
    """虚拟学生 Agent"""
    
    # emotion 可选值说明
    EMOTION_TYPES = {
        "curious": "好奇/质疑",
        "confused": "听不懂",
        "sleepy": "困倦",
        "active": "积极回应",
        "whispering": "交头接耳",
        "hesitant": "犹豫/怯懦",
        "idle": "无反应"
    }
    
    AGENT_PROMPTS = {
        "gangjing": """你是一名初二学优生（"杠精"模式），正在上{subject}课。

性格特点：
- 聪明好学，喜欢深入思考问题
- 敢于质疑，不盲从权威
- 提问有深度，能触及知识本质
- 语气礼貌但有探究精神

当前情境：
{context}

请用初二学生的口吻，根据上述情境说一句话。
要求：
1. 内容要有思考深度，不是简单重复
2. 语气符合学生身份，不要太书面化
3. 可以是质疑、追问或拓展思考
4. 回答控制在30字以内

输出格式（JSON）：
{{"reply_text": "你的发言", "emotion": "curious|confused|active"}}""",

        "xuekun": """你是一名{subject}学困生，正在上课。

性格特点：
- 基础薄弱，经常听不懂
- 不敢直接说不懂，但会委婉表达困惑
- 需要老师耐心解释
- 语气怯懦、犹豫

当前情境：
{context}

请用学生的口吻，表达你的困惑或求助。
要求：
1. 内容体现基础薄弱，问题比较简单
2. 语气犹豫、不自信
3. 可以用"老师，我..."开头
4. 回答控制在25字以内

输出格式（JSON）：
{{"reply_text": "你的发言", "emotion": "confused|hesitant"}}""",

        "sleepy": """你是一名正在打瞌睡的学生。

状态：
- 老师讲课时间太长，你开始犯困
- 注意力不集中，半睡半醒

当前情境：
{context}

请描述你打瞌睡的状态。
要求：
1. 可能是小声打哈欠、趴在桌上、或者迷糊地应和
2. 内容简短（10字以内）
3. 不要说话，只是状态描述

输出格式（JSON）：
{{"reply_text": "你的状态", "emotion": "sleepy"}}""",

        "whisper": """你和同桌正在交头接耳。

状态：
- 老师在讲课，但你们在小声聊天
- 讨论与课堂内容无关或半相关的话题

当前情境：
{context}

请描述你们交头接耳的内容。
要求：
1. 小声、含糊、断断续续
2. 内容简短（15字以内）
3. 可能是在问同桌老师讲了什么

输出格式（JSON）：
{{"reply_text": "你的悄悄话", "emotion": "whispering"}}"""
    }
    
    def __init__(self):
        self.llm = llm.model if hasattr(llm, 'model') else llm
    
    def generate_reply(
        self,
        agent_type: str,
        context: str,
        subject: str = "数学"
    ) -> Dict[str, Any]:
        """
        生成学生回复
        
        Args:
            agent_type: 学生类型 (gangjing/xuekun/sleepy/whisper)
            context: 当前情境描述（来自 Supervisor 的 agent_prompt）
            subject: 学科
        
        Returns:
            {"agent_type": "gangjing", "reply_text": "...", "emotion": "..."}
            符合 api.md 中 4.2 Worker Agent 回复输出格式
        """
        if agent_type not in self.AGENT_PROMPTS:
            return {
                "agent_type": agent_type,
                "reply_text": "（沉默）",
                "emotion": "idle"
            }
        
        prompt_template = self.AGENT_PROMPTS[agent_type]
        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "context": context,
                "subject": subject
            })
            
            result_text = response.content if hasattr(response, 'content') else str(response)
            
            # 解析 JSON
            result = self._extract_json(result_text)
            
            # 添加 agent_type 字段（符合 api.md 格式）
            result["agent_type"] = agent_type
            
            # 确保必要字段
            if "reply_text" not in result:
                result["reply_text"] = "老师，我不太明白..."
            if "emotion" not in result:
                result["emotion"] = self._default_emotion(agent_type)
            
            return result
            
        except Exception as e:
            # 返回默认回复（包含 agent_type）
            return self._default_reply(agent_type)
    
    def _extract_json(self, text: str) -> Dict:
        """从文本中提取 JSON"""
        import re
        
        # 首先尝试直接解析
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # 尝试从 markdown 代码块中提取
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
        
        # 如果实在解析不了，把整个文本作为 reply_text
        return {"reply_text": text.strip(), "emotion": "unknown"}
    
    def _default_emotion(self, agent_type: str) -> str:
        """默认情绪"""
        emotions = {
            "gangjing": "curious",
            "xuekun": "confused",
            "sleepy": "sleepy",
            "whisper": "whispering"
        }
        return emotions.get(agent_type, "idle")
    
    def _default_reply(self, agent_type: str) -> Dict[str, Any]:
        """默认回复（符合 api.md 格式）"""
        defaults = {
            "gangjing": {
                "agent_type": "gangjing",
                "reply_text": "老师，我想问一下，这个公式是怎么推导出来的？",
                "emotion": "curious"
            },
            "xuekun": {
                "agent_type": "xuekun",
                "reply_text": "老师，我...我没听懂，可以再讲一遍吗？",
                "emotion": "confused"
            },
            "sleepy": {
                "agent_type": "sleepy",
                "reply_text": "（打哈欠）",
                "emotion": "sleepy"
            },
            "whisper": {
                "agent_type": "whisper",
                "reply_text": "（小声）老师在讲什么？",
                "emotion": "whispering"
            }
        }
        return defaults.get(agent_type, {"agent_type": agent_type, "reply_text": "...", "emotion": "idle"})


# 快捷函数
def quick_reply(agent_type: str, context: str, subject: str = "数学") -> Dict[str, Any]:
    """快速生成回复"""
    agent = StudentAgent()
    return agent.generate_reply(agent_type, context, subject)
