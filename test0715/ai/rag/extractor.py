"""知识点与问题提取器"""
import json
import re
from typing import Dict, List, Any

from langchain_core.prompts import ChatPromptTemplate

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from setting.llm import llm


EXTRACTION_PROMPT = """你是一位资深教育专家，擅长深度分析教学教案并提取结构化信息。

请分析以下教案内容，提取教学信息并以 JSON 格式返回。

## 输出结构

{{
  "basic_info": {{
    "lesson_topic": "课程主题/课题名称",
    "subject": "学科（如：高中语文、初中数学）",
    "lesson_type": "课型（新授课/复习课/实验课/阅读课）"
  }},
  "teaching_objectives": {{
    "knowledge": "知识目标：学生要掌握的知识要点",
    "ability": "能力目标：培养什么能力",
    "emotion": "情感态度目标：价值观、兴趣培养"
  }},
  "knowledge_points": [
    {{
      "id": "kp1",
      "point": "知识点名称",
      "difficulty": "难度：低/中/高",
      "category": "分类：概念/技能/应用/拓展",
      "description": "详细描述",
      "tags": ["标签1", "标签2"],
      "prerequisite": "前置知识"
    }}
  ],
  "preset_questions": [
    {{
      "id": "q1",
      "question": "学生可能提出的问题（口语化）",
      "type": "问题类型：质疑型/困惑型/拓展型/应用型/细节型",
      "difficulty": "难度：低/中/高",
      "trigger_timing": "触发时机（对应哪个知识点或环节）",
      "related_kp": "关联的知识点id",
      "expected_answer": "期望的老师回答要点",
      "possible_followup": "学生可能的追问"
    }}
  ]
}}

## 教案内容

{content}

## 提取要求

1. basic_info: 从教案标题、标注信息中提取，如未明确则合理推测
2. teaching_objectives: 分别提取知识、能力、情感三维目标
3. knowledge_points: 提取4-8个核心知识点，包含id、难度、分类、描述、标签、前置知识
4. preset_questions: 生成5-8个学生可能提出的问题，要贴近真实课堂场景，包含追问

所有内容要具体、实用，preset_questions要体现不同学生的思维特点。

只返回JSON，不要其他文字。
"""


class LessonExtractor:
    """教案知识提取器"""
    
    def __init__(self):
        self.llm = llm.model if hasattr(llm, 'model') else llm
        self.prompt = ChatPromptTemplate.from_template(EXTRACTION_PROMPT)
        self.chain = self.prompt | self.llm
    
    def extract(self, content: str) -> Dict[str, Any]:
        """从教案文本中提取知识点和预设问题"""
        # 截断过长的内容
        max_length = 12000
        if len(content) > max_length:
            content = content[:max_length] + "\n\n[内容已截断]"
        
        try:
            response = self.chain.invoke({"content": content})
            result_text = response.content if hasattr(response, 'content') else str(response)
            result = self._extract_json(result_text)
            result = self._validate_result(result)
            return result
        except Exception as e:
            return self._fallback_result(content, str(e))
    
    def _extract_json(self, text: str) -> Dict:
        """从文本中提取 JSON"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        patterns = [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```']
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
        
        try:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
        
        raise ValueError("无法从响应中解析 JSON")
    
    def _validate_result(self, result: Dict) -> Dict:
        """验证并补充默认值"""
        defaults = {
            "basic_info": {
                "lesson_topic": "未识别课题",
                "subject": "未识别学科",
                "lesson_type": "新授课"
            },
            "teaching_objectives": {
                "knowledge": "理解本节课的核心知识",
                "ability": "培养基础学习能力",
                "emotion": "激发学习兴趣"
            },
            "knowledge_points": [
                {
                    "id": "kp1",
                    "point": "课程主要内容",
                    "difficulty": "中",
                    "category": "概念",
                    "description": "本节课的核心教学内容",
                    "tags": ["核心"],
                    "prerequisite": "基础知识"
                }
            ],
            "preset_questions": [
                {
                    "id": "q1",
                    "question": "老师，这部分内容我没听懂",
                    "type": "困惑型",
                    "difficulty": "中",
                    "trigger_timing": "讲解过程中",
                    "related_kp": "kp1",
                    "expected_answer": "需要进一步解释",
                    "possible_followup": "能再举个例子吗？"
                }
            ]
        }
        
        for key, default_value in defaults.items():
            if key not in result or not result[key]:
                result[key] = default_value
        
        return result
    
    def _fallback_result(self, content: str, error_msg: str) -> Dict[str, Any]:
        """提取失败时的默认结果"""
        lines = content.strip().split('\n')
        title = lines[0][:30] if lines else "未命名课程"
        
        return {
            "basic_info": {
                "lesson_topic": title,
                "subject": "未识别学科",
                "lesson_type": "新授课"
            },
            "teaching_objectives": {
                "knowledge": "理解本节课的核心知识",
                "ability": "培养基础学习能力",
                "emotion": "激发学习兴趣"
            },
            "knowledge_points": [
                {
                    "id": "kp1",
                    "point": "课程主要内容",
                    "difficulty": "中",
                    "category": "概念",
                    "description": "本节课的核心教学内容",
                    "tags": ["核心"],
                    "prerequisite": "基础知识"
                }
            ],
            "preset_questions": [
                {
                    "id": "q1",
                    "question": "老师，这个概念我不太理解",
                    "type": "困惑型",
                    "difficulty": "中",
                    "trigger_timing": "讲解过程中",
                    "related_kp": "kp1",
                    "expected_answer": "需要进一步解释说明",
                    "possible_followup": "可以举个例子吗？"
                }
            ],
            "_extraction_error": error_msg
        }
