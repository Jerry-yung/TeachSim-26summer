# AI 模块与后端对接文档

> 本文档面向后端开发者，说明如何与 AI 模块进行集成。

---

## 1. 服务配置

### 1.1 AI 服务地址

在 backend 的配置文件（如 `.env` 或 `config.py`）中添加：

```python
AI_SERVICE_URL = "http://localhost:8001"  # AI 模块服务地址
```

### 1.2 环境变量

AI 模块支持以下环境变量：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `AI_SERVICE_URL` | `http://localhost:8001` | AI 服务对外地址 |
| `AI_PORT` | `8001` | AI 服务监听端口 |
| `AI_HOST` | `0.0.0.0` | AI 服务监听主机 |

---

## 2. 数据流向

```
前端 (A) <-> 后端 (C) <-> AI 模块 (B)
```

**重要原则：**
- 前端**不直接**调用 AI 模块
- 后端作为中转层，调用 AI 模块并存储结果到数据库
- 后端将处理后的数据返回给前端

---

## 3. 完整业务流程

### 3.1 课前配置流程

```
1. 用户在前端上传教案文件
2. 用户填写教学背景配置（年级、班级类型、教学背景描述等）
3. 后端调用 AI 模块解析教案
4. 后端将 AI 返回的数据 + 用户配置 合并存储
5. 返回给前端展示知识点和预设问题
```

### 3.2 用户配置字段（前端收集）

| 字段名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| `grade` | string | 是 | 年级 | "初二"、"高一" |
| `class_type` | string | 否 | 班级类型 | "重点班"、"普通班" |
| `duration` | string | 否 | 上课时长 | "45分钟"、"2课时" |
| `teaching_background` | string | 否 | 教学背景描述 | "学生基础较弱，需要多举例子" |
| `atmosphere` | string | 否 | 课堂氛围 | "活跃"、"沉闷" |

---

## 4. API 调用示例

### 4.1 解析教案

**接口：** `POST /ai/parse_lesson`

**Python 示例：**

```python
import requests

AI_SERVICE_URL = "http://localhost:8001"

def parse_lesson(file_path):
    """解析教案文件"""
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{AI_SERVICE_URL}/ai/parse_lesson",
            files={"file": f},
            timeout=180  # LLM 处理较慢，建议设置 180 秒超时
        )
    
    if response.status_code == 200:
        return response.json()
    else:
        # 处理错误
        error_data = response.json()
        raise Exception(f"解析失败: {error_data.get('error_message', '未知错误')}")
```

**AI 返回数据示例：**

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
  "knowledge_points": [...],
  "preset_questions": [...],
  "_file_info": {
    "filename": ["教案.docx"],
    "size": 15411
  }
}
```

**后端处理：合并用户配置**

```python
def create_lesson(file_path, user_config):
    """
    创建课程：解析教案 + 合并用户配置
    
    user_config 示例：
    {
        "grade": "初二",
        "class_type": "普通班",
        "duration": "45分钟",
        "teaching_background": "学生基础较弱，需要多举例子"
    }
    """
    # 1. 调用 AI 解析教案
    ai_result = parse_lesson(file_path)
    
    # 2. 合并用户配置到 basic_info
    lesson_data = {
        "lesson_id": generate_uuid(),
        "basic_info": {
            **ai_result["basic_info"],  # AI 解析的基础信息
            "grade": user_config.get("grade"),  # 用户选择的年级
            "class_type": user_config.get("class_type"),  # 班级类型
            "duration": user_config.get("duration"),  # 上课时长
        },
        "user_config": {
            "teaching_background": user_config.get("teaching_background"),
            "atmosphere": user_config.get("atmosphere")
        },
        "teaching_objectives": ai_result["teaching_objectives"],
        "knowledge_points": ai_result["knowledge_points"],
        "preset_questions": ai_result["preset_questions"],
        "_file_info": ai_result["_file_info"],
        "status": "ready"
    }
    
    # 3. 存储到数据库
    db.lessons.insert(lesson_data)
    
    return lesson_data
```

**最终返回给前端的完整数据：**

```json
{
  "lesson_id": "uuid-xxxx",
  "basic_info": {
    "lesson_topic": "勾股定理",
    "subject": "初中数学",
    "lesson_type": "新授课",
    "grade": "初二",
    "class_type": "普通班",
    "duration": "45分钟"
  },
  "user_config": {
    "teaching_background": "学生基础较弱，需要多举例子",
    "atmosphere": "活跃"
  },
  "teaching_objectives": {...},
  "knowledge_points": [...],
  "preset_questions": [...]
}
```

---

### 4.2 Supervisor 主控决策

**接口：** `POST /ai/supervisor/decide`

**Python 示例：**

```python
def supervisor_decide(teacher_text, lesson_topic, subject, session_id):
    """主控决策：分析教师发言，决定下一步动作"""
    response = requests.post(
        f"{AI_SERVICE_URL}/ai/supervisor/decide",
        json={
            "teacher_text": teacher_text,
            "lesson_topic": lesson_topic,
            "subject": subject,
            "session_id": session_id
        },
        timeout=30
    )
    return response.json()
```

**返回数据示例：**

```json
{
  "session_id": "session-001",
  "timestamp_ms": 1699123456789,
  "evaluation_note": "教态自然，引出勾股定理",
  "is_questioning": false,
  "error_detected": false,
  "trigger_agent": "gangjing",
  "agent_prompt": "老师刚讲完勾股定理，请用初二学生口吻质疑..."
}
```

**业务处理逻辑：**

```python
result = supervisor_decide(
    teacher_text="同学们，今天讲勾股定理",
    lesson_topic="勾股定理",
    subject="初中数学",
    session_id="session-001"
)

# 1. 记录评估
log_evaluation(result["session_id"], result["evaluation_note"])

# 2. 检测错误
if result["error_detected"]:
    # 记录错误，触发纠错流程
    log_error(result["session_id"], result["evaluation_note"])

# 3. 判断是否触发学生
if result["trigger_agent"]:
    # 调用 Agent 生成回复
    agent_reply = get_agent_reply(
        result["trigger_agent"],
        result["agent_prompt"]
    )
    # 通过 WebSocket 推送给前端
    websocket.send({
        "event": "student_action",
        "student_id": result["trigger_agent"],
        "reply_text": agent_reply["reply_text"]
    })
```

---

### 4.3 Agent 学生回复

**接口：** `POST /ai/agent/reply`

**Python 示例：**

```python
def agent_reply(agent_type, context, subject="数学"):
    """生成学生 Agent 的回复"""
    response = requests.post(
        f"{AI_SERVICE_URL}/ai/agent/reply",
        json={
            "agent_type": agent_type,
            "context": context,
            "subject": subject
        },
        timeout=30
    )
    return response.json()
```

**返回数据示例：**

```json
{
  "agent_type": "gangjing",
  "reply_text": "老师，那如果是锐角三角形呢？",
  "emotion": "curious"
}
```

**Agent 类型说明：**

| agent_type | 角色 | 典型回复风格 |
|------------|------|-------------|
| `gangjing` | 学优生/杠精 | 质疑、追问、有深度 |
| `xuekun` | 学困生 | 困惑、基础问题、犹豫 |
| `sleepy` | 打瞌睡 | 打哈欠、迷糊 |
| `whisper` | 交头接耳 | 小声说话、问同桌 |

---

## 5. 接口清单

| 接口 | 方法 | 用途 | 超时建议 |
|------|------|------|----------|
| `/ai/parse_lesson` | POST | 解析教案文件 | 180s |
| `/ai/parse_lessons` | POST | 解析多个教案文件 | 180s |
| `/ai/supervisor/decide` | POST | 主控决策 | 30s |
| `/ai/agent/reply` | POST | 学生 Agent 回复 | 30s |

---

## 6. 错误处理

### 6.1 错误码规范

AI 模块返回的错误码格式：

```json
{
  "error_code": "AI4001",
  "error_message": "不支持的文件格式",
  "error_detail": "详细的错误信息",
  "timestamp_ms": 1699123456789
}
```

常见错误码：

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|-------------|
| AI4000 | 文件解析失败 | 400 |
| AI4001 | 不支持的文件格式 | 400 |
| AI4002 | 文件过大 | 400 |
| AI5000 | AI 服务调用失败 | 500 |
| AI5001 | AI 服务响应超时 | 500 |
| AI5002 | AI 响应格式错误 | 500 |
| AI6000 | 无效的 Agent 类型 | 400 |
| AI6001 | 决策过程出错 | 500 |
| AI9999 | 未知错误 | 500 |

查看完整错误码规范：

curl -s http://localhost:8001/error-codes

### 6.2 获取错误码列表

```bash
curl -s http://localhost:8001/error-codes
```

---

## 7. 数据库设计建议

### 7.1 教案表（lessons）

```sql
CREATE TABLE lessons (
    lesson_id VARCHAR(36) PRIMARY KEY,
    -- basic_info（AI 解析 + 用户配置合并）
    topic VARCHAR(255),
    subject VARCHAR(50),
    lesson_type VARCHAR(20),
    grade VARCHAR(20),           -- 用户配置
    class_type VARCHAR(20),      -- 用户配置
    duration VARCHAR(20),        -- 用户配置
    -- user_config
    teaching_background TEXT,    -- 用户配置：教学背景描述
    atmosphere VARCHAR(20),      -- 用户配置：课堂氛围
    -- AI 解析内容
    teaching_objectives JSON,
    knowledge_points JSON,
    preset_questions JSON,
    file_info JSON,
    status VARCHAR(20),  -- parsing, ready, error
    created_at TIMESTAMP
);
```

### 7.2 课堂会话表（sessions）

```sql
CREATE TABLE sessions (
    session_id VARCHAR(36) PRIMARY KEY,
    lesson_id VARCHAR(36),
    teacher_id VARCHAR(36),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20),  -- ongoing, ended
    FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id)
);
```

### 7.3 课堂事件表（events）

```sql
CREATE TABLE events (
    event_id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36),
    timestamp_ms BIGINT,
    teacher_text TEXT,
    evaluation_note TEXT,
    trigger_agent VARCHAR(20),
    agent_reply TEXT,
    emotion VARCHAR(20),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

---

## 8. 注意事项

1. **超时设置**：教案解析接口较慢，建议设置 180 秒超时
2. **文件格式**：旧版 .doc 和 .ppt 不支持，需转换为 .docx/.pptx
3. **用户配置合并**：AI 返回的 `basic_info` 不包含年级、时长等信息，需要后端从用户配置中补充
4. **并发处理**：建议后端使用异步或队列处理 AI 请求
5. **错误重试**：AI 服务偶发超时，建议实现重试机制
