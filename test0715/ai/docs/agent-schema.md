# JSON Schema 文档

> 本文档定义 AI 模块返回的 JSON 数据结构，供前后端开发者参考。

---

## 1. 教案解析 Schema（RAG）

**接口：** `POST /ai/parse_lesson` 或 `POST /ai/parse_lessons`

### 1.1 JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LessonAnalysisResult",
  "type": "object",
  "required": ["basic_info", "teaching_objectives", "knowledge_points", "preset_questions", "_file_info"],
  "properties": {
    "basic_info": {
      "type": "object",
      "required": ["lesson_topic", "subject", "lesson_type"],
      "properties": {
        "lesson_topic": {
          "type": "string",
          "description": "课程主题/课题名称"
        },
        "subject": {
          "type": "string",
          "description": "学科，如：初中数学、高中语文"
        },
        "lesson_type": {
          "type": "string",
          "description": "课型",
          "enum": ["新授课", "复习课", "实验课", "阅读课", "练习课"]
        }
      }
    },
    "teaching_objectives": {
      "type": "object",
      "required": ["knowledge", "ability", "emotion"],
      "properties": {
        "knowledge": {
          "type": "string",
          "description": "知识目标：学生要掌握的知识要点"
        },
        "ability": {
          "type": "string",
          "description": "能力目标：培养什么能力"
        },
        "emotion": {
          "type": "string",
          "description": "情感态度目标：价值观、兴趣培养"
        }
      }
    },
    "knowledge_points": {
      "type": "array",
      "description": "知识点列表",
      "items": {
        "type": "object",
        "required": ["id", "point", "difficulty", "category", "description", "tags", "prerequisite"],
        "properties": {
          "id": {
            "type": "string",
            "description": "知识点编号，如：kp1, kp2",
            "pattern": "^kp\\d+$"
          },
          "point": {
            "type": "string",
            "description": "知识点名称"
          },
          "difficulty": {
            "type": "string",
            "description": "难度",
            "enum": ["低", "中", "高"]
          },
          "category": {
            "type": "string",
            "description": "分类",
            "enum": ["概念", "技能", "应用", "拓展"]
          },
          "description": {
            "type": "string",
            "description": "详细描述"
          },
          "tags": {
            "type": "array",
            "description": "标签列表",
            "items": {
              "type": "string"
            }
          },
          "prerequisite": {
            "type": "string",
            "description": "前置知识"
          }
        }
      }
    },
    "preset_questions": {
      "type": "array",
      "description": "预设学生问题列表",
      "items": {
        "type": "object",
        "required": ["id", "question", "type", "difficulty", "trigger_timing", "related_kp", "expected_answer", "possible_followup"],
        "properties": {
          "id": {
            "type": "string",
            "description": "问题编号，如：q1, q2",
            "pattern": "^q\\d+$"
          },
          "question": {
            "type": "string",
            "description": "问题内容（学生口吻）"
          },
          "type": {
            "type": "string",
            "description": "问题类型",
            "enum": ["质疑型", "困惑型", "拓展型", "应用型", "细节型"]
          },
          "difficulty": {
            "type": "string",
            "description": "问题难度",
            "enum": ["低", "中", "高"]
          },
          "trigger_timing": {
            "type": "string",
            "description": "触发时机（对应知识点或环节）"
          },
          "related_kp": {
            "type": "string",
            "description": "关联的知识点id",
            "pattern": "^kp\\d+$"
          },
          "expected_answer": {
            "type": "string",
            "description": "期望的老师回答要点"
          },
          "possible_followup": {
            "type": "string",
            "description": "学生可能的追问"
          }
        }
      }
    },
    "_file_info": {
      "type": "object",
      "required": ["filename", "size"],
      "properties": {
        "filename": {
          "type": "array",
          "description": "文件名列表（单文件也是列表）",
          "items": {
            "type": "string"
          }
        },
        "size": {
          "type": "integer",
          "description": "文件总大小（字节）"
        }
      }
    }
  }
}
```

### 1.2 示例数据

```json
{
  "basic_info": {
    "lesson_topic": "勾股定理",
    "subject": "初中数学",
    "lesson_type": "新授课"
  },
  "teaching_objectives": {
    "knowledge": "理解勾股定理的几何意义和代数表达，掌握直角三角形已知两边求第三边的方法",
    "ability": "通过观察特殊直角三角形归纳数学规律，培养数形结合思想",
    "emotion": "感受中国古代数学成就，激发学习兴趣"
  },
  "knowledge_points": [
    {
      "id": "kp1",
      "point": "勾股定理的概念与公式",
      "difficulty": "中",
      "category": "概念",
      "description": "直角三角形两条直角边的平方和等于斜边的平方，数学表达式为a²+b²=c²",
      "tags": ["核心概念", "公式记忆", "几何定理"],
      "prerequisite": "直角三角形的基本性质，平方运算"
    },
    {
      "id": "kp2",
      "point": "勾股定理的直接应用计算",
      "difficulty": "低",
      "category": "应用",
      "description": "在直角三角形中已知任意两边长度，利用公式求第三边",
      "tags": ["计算技能", "公式应用"],
      "prerequisite": "一元二次方程求解，平方根运算"
    }
  ],
  "preset_questions": [
    {
      "id": "q1",
      "question": "老师，为什么这个定理叫勾股定理啊？勾和股分别指什么？",
      "type": "细节型",
      "difficulty": "低",
      "trigger_timing": "情境导入环节，展示弦图时",
      "related_kp": "kp1",
      "expected_answer": "在我国古代，直角三角形中较短的直角边叫勾，较长的直角边叫股，斜边叫弦",
      "possible_followup": "那国外叫什么定理？毕达哥拉斯和勾股定理有什么关系？"
    },
    {
      "id": "q2",
      "question": "为什么一定是直角三角形？如果是锐角三角形或钝角三角形，三边还有这个关系吗？",
      "type": "拓展型",
      "difficulty": "高",
      "trigger_timing": "探索新知环节，发现规律后",
      "related_kp": "kp1",
      "expected_answer": "勾股定理只适用于直角三角形。锐角三角形两边平方和大于第三边平方，钝角三角形则小于",
      "possible_followup": "那能不能用三边长度来判断一个三角形是不是直角三角形？"
    }
  ],
  "_file_info": {
    "filename": ["勾股定理教案.docx"],
    "size": 15411
  }
}
```

### 1.3 多文件上传示例

```json
{
  "basic_info": {
    "lesson_topic": "勾股定理（2课时）",
    "subject": "初中数学",
    "lesson_type": "新授课"
  },
  "teaching_objectives": {...},
  "knowledge_points": [...],
  "preset_questions": [...],
  "_file_info": {
    "filename": ["课时1-导入与探索.docx", "课时2-应用与拓展.docx"],
    "size": 31250
  }
}
```

---

## 2. 学生 Agent Schema

**接口：** `POST /ai/agent/reply`

### 2.1 JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentReply",
  "type": "object",
  "required": ["agent_type", "reply_text", "emotion"],
  "properties": {
    "agent_type": {
      "type": "string",
      "description": "虚拟学生类型",
      "enum": ["gangjing", "xuekun", "sleepy", "whisper"]
    },
    "reply_text": {
      "type": "string",
      "description": "学生的回复内容"
    },
    "emotion": {
      "type": "string",
      "description": "情绪状态",
      "enum": ["curious", "confused", "sleepy", "active", "whispering", "hesitant", "idle"]
    }
  }
}
```

### 2.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `agent_type` | string | ✅ | 虚拟学生类型标识 |
| `reply_text` | string | ✅ | 学生回复的文本内容 |
| `emotion` | string | ✅ | 学生当前的情绪状态 |

### 2.3 Agent 类型

| agent_type | 中文名 | 角色描述 | 典型回复特点 |
|------------|--------|----------|--------------|
| `gangjing` | 学优生/杠精 | 聪明好学，敢于质疑 | 有深度的问题、逻辑清晰 |
| `xuekun` | 学困生 | 基础薄弱，经常听不懂 | 简单问题、犹豫怯懦 |
| `sleepy` | 打瞌睡学生 | 注意力不集中 | 打哈欠、迷糊应和 |
| `whisper` | 交头接耳学生 | 上课小声聊天 | 悄悄话、问同桌 |

### 2.4 Emotion 情绪值

| emotion | 说明 | 适用 Agent |
|---------|------|------------|
| `curious` | 好奇/质疑 | gangjing |
| `confused` | 听不懂/困惑 | xuekun |
| `sleepy` | 困倦 | sleepy |
| `active` | 积极回应 | gangjing |
| `whispering` | 交头接耳 | whisper |
| `hesitant` | 犹豫/怯懦 | xuekun |
| `idle` | 无反应 | 所有（默认） |

### 2.5 示例数据

#### gangjing（学优生）

```json
{
  "agent_type": "gangjing",
  "reply_text": "老师，那如果是锐角三角形呢？",
  "emotion": "curious"
}
```

```json
{
  "agent_type": "gangjing",
  "reply_text": "老师，反过来也对吗？满足a²+b²=c²的一定是直角三角形？",
  "emotion": "curious"
}
```

#### xuekun（学困生）

```json
{
  "agent_type": "xuekun",
  "reply_text": "老师，我...为什么不是a+b=c啊？",
  "emotion": "confused"
}
```

```json
{
  "agent_type": "xuekun",
  "reply_text": "老师，我没听懂，可以再讲一遍吗？",
  "emotion": "hesitant"
}
```

#### sleepy（打瞌睡）

```json
{
  "agent_type": "sleepy",
  "reply_text": "（打哈欠）",
  "emotion": "sleepy"
}
```

#### whisper（交头接耳）

```json
{
  "agent_type": "whisper",
  "reply_text": "（小声）老师在讲什么？",
  "emotion": "whispering"
}
```

---

## 3. 前端渲染建议

### 3.1 教案解析结果展示

- **basic_info**：展示在课程标题区域
- **knowledge_points**：以列表或思维导图形式展示，标注难度
- **preset_questions**：按触发时机分组，作为课堂预设问题库

### 3.2 学生动画映射

| emotion | 建议动画 |
|---------|----------|
| `curious` | 举手、歪头思考 |
| `confused` | 挠头、皱眉 |
| `sleepy` | 打哈欠、趴在桌上 |
| `active` | 积极举手、点头 |
| `whispering` | 转头、捂嘴 |
| `hesitant` | 低头、小声 |

### 3.3 语音语调建议

| emotion | TTS 语速 | TTS 音调 |
|---------|----------|----------|
| `curious` | 正常 | 稍高 |
| `confused` | 稍慢 | 正常 |
| `sleepy` | 慢 | 低 |
| `active` | 稍快 | 高 |
| `whispering` | 快 | 低 |
| `hesitant` | 慢，有停顿 | 低 |

---

## 4. 关联文档

- [AI 模块与后端对接](./ai-backend-integration.md) - 后端集成指南
- [API 接口文档](../../docs/api.md) - 完整的 API 接口定义
