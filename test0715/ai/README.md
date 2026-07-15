# ai

AI 算法目录 —— 负责人：杨云天

## 主要内容

1. **RAG 模块**：教案解析与知识点提取，支持 PDF、Word、PPT、Excel、Markdown 等多种格式，支持单文件和多文件上传
2. **Supervisor 主控决策**：实时分析教师授课内容，判断提问/错误状态，决策触发虚拟学生类型
3. **学生 Agent**：学优生（gangjing）、学困生（xuekun）、打瞌睡（sleepy）、交头接耳（whisper）四种角色回复生成
4. **错误码规范**：定义文件解析、LLM 调用、业务逻辑等 8 类标准错误码
5. **LLM 配置**：统一入口，支持 ECNU、Moonshot、SiliconFlow 多供应商切换
6. **FastAPI 服务**：提供标准 RESTful 接口，符合 api.md 约定格式

## 技术栈

- Python + LangChain
- FastAPI（测试服务）

## 包含模块


| 模块         | 路径               | 功能                    |
| ---------- | ---------------- | --------------------- |
| LLM 配置     | `setting/llm.py` | 统一大模型入口，支持多供应商切换      |
| RAG        | `rag/`           | 教案解析、知识点提取、预设问题生成     |
| Supervisor | `supervisor/`    | 主控决策：判断教师状态、触发学生反应    |
| Agents     | `agents/`        | 学生角色：学优生、学困生、打瞌睡、交头接耳 |


## 相关文档


| 文档                                          | 路径                                  | 说明                     |
| ------------------------------------------- | ----------------------------------- | ---------------------- |
| [与后端对接指南](./docs/ai-backend-integration.md) | `ai/docs/ai-backend-integration.md` | 后端开发者集成指南              |
| [JSON Schema 定义](./docs/agent-schema.md)    | `ai/docs/agent-schema.md`           | 教案解析 & Agent 回复 Schema |


## 快速开始

### 1. 安装依赖

```bash
cd ai
pip install -r requirements.txt
```

### 2. 配置 API Key

在项目根目录修改 `.env.example` 文件中的 api key，然后执行：

```bash
cp .env.example .env
```

### 3. 启动服务

```bash
cd ai
python main.py
# 服务运行在 http://localhost:8001
```

---

## 测试指南（新建终端运行）

### 接口 1：教案解析（RAG）（约 20～60s 响应完成，受文件大小影响）

**接口地址：** `POST /ai/parse_lesson`

**请求示例：**

```bash
cd ai
```

```bash
# 单文件
curl -s -X POST http://localhost:8001/ai/parse_lesson \
  -F "file=@教案/简短教案-高中三角函数.docx"

# 多文件
curl -s -X POST http://localhost:8001/ai/parse_lessons \
  -F "files=@教案/文件1.pdf" \
  -F "files=@教案/文件2.pptx"
```

**成功响应（JSON）：**

```json
{
  "basic_info": {
    "lesson_topic": "勾股定理",
    "subject": "初中数学",
    "lesson_type": "新授课"
  },
  "teaching_objectives": {
    "knowledge": "理解勾股定理的几何意义...",
    "ability": "培养数形结合思想...",
    "emotion": "感受中国古代数学成就..."
  },
  "knowledge_points": [
    {
      "id": "kp1",
      "point": "勾股定理的概念与公式",
      "difficulty": "中",
      "category": "概念",
      "description": "直角三角形两条直角边的平方和等于斜边的平方...",
      "tags": ["核心概念", "公式记忆"],
      "prerequisite": "直角三角形的基本性质"
    }
  ],
  "preset_questions": [
    {
      "id": "q1",
      "question": "老师，为什么这个定理叫勾股定理啊？",
      "type": "细节型",
      "difficulty": "低",
      "trigger_timing": "情境导入环节",
      "related_kp": "kp1",
      "expected_answer": "在我国古代，直角三角形中较短的直角边叫勾...",
      "possible_followup": "那国外叫什么定理？"
    }
  ],
  "_file_info": {
    "filename": ["测试教案.docx"],
    "size": 15411
  }
}
```

---

### 接口 2：主控 Supervisor 决策（约 6s 响应完成）

**接口地址：** `POST /ai/supervisor/decide`

**请求示例：**

```bash
curl -s -X POST http://localhost:8001/ai/supervisor/decide \
  -H "Content-Type: application/json" \
  -d '{
    "teacher_text": "同学们，今天我们来学习勾股定理",
    "lesson_topic": "勾股定理",
    "subject": "初中数学",
    "session_id": "session-001"
  }'
```

**成功响应（JSON，符合 api.md 4.1 格式）：**

```json
{
  "session_id": "session-001",
  "timestamp_ms": 1699123456789,
  "evaluation_note": "教态自然，准确引出勾股定理定义",
  "is_questioning": false,
  "error_detected": false,
  "trigger_agent": null,
  "agent_prompt": null
}
```

---

### 接口 3：学生 Agent 回复（约 8s 响应完成）

**接口地址：** `POST /ai/agent/reply`

**请求示例：**

```bash
curl -s -X POST http://localhost:8001/ai/agent/reply \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "gangjing",
    "context": "老师刚讲完勾股定理的定义",
    "subject": "数学"
  }'
```

**成功响应（JSON，符合 docs/agent-schema.md）：**

```json
{
  "agent_type": "gangjing",
  "reply_text": "老师，那如果是锐角三角形呢？",
  "emotion": "curious"
}
```

**emotion 可选值说明：**


| emotion    | 说明    |
| ---------- | ----- |
| curious    | 好奇/质疑 |
| confused   | 听不懂   |
| sleepy     | 困倦    |
| active     | 积极回应  |
| whispering | 交头接耳  |
| hesitant   | 犹豫/怯懦 |
| idle       | 无反应   |


更多示例请参考 [Agent JSON Schema](docs/agent-schema.md)

---

## 切换大模型

编辑 `ai/setting/llm.py`，修改最后一行：

```python
# 当前
llm = LLM_siliconflow_deepseek()
# 或
llm = LLM_siliconflow_minimax()
...
```

---

## 目录结构

```
ai/
├── setting/
│   └── llm.py              # LLM 配置
├── rag/
│   ├── __init__.py
│   ├── parser.py           # 多格式文档解析
│   └── extractor.py        # 知识点提取
├── supervisor/
│   ├── __init__.py
│   └── prompt.py           # 主控决策
├── agents/
│   ├── __init__.py
│   └── student_agents.py   # 学生角色
├── docs/                   # AI 模块文档
│   ├── ai-backend-integration.md  # 后端对接指南
│   └── agent-schema.md            # JSON Schema 定义
├── 教案/                    # 测试用教案文件夹
├── main.py                 # FastAPI 服务
├── requirements.txt
└── README.md
```

---

