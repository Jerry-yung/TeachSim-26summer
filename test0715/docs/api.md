# TeachSim API 接口文档

> **这是三人协作的"合同文件"**，所有接口的 URL、请求体、响应体在开发前必须在此确认。
> 如需修改接口，请提 PR 更新本文档，并通知相关成员。

---

## 目录

- [通用约定](#通用约定)
- [一、课前配置模块](#一课前配置模块)
- [二、课堂实时模块（WebSocket）](#二课堂实时模块websocket)
- [三、报告模块](#三报告模块)
- [四、智能体内部数据格式（B ↔ C）](#四智能体内部数据格式b--c)

---

## 通用约定

- Base URL（本地开发）：`http://localhost:8000`
- 所有 HTTP 接口请求/响应均使用 `application/json`
- 文件上传使用 `multipart/form-data`
- 认证方式：暂定 Bearer Token（Header: `Authorization: Bearer <token>`）
- 错误响应统一格式：
  ```json
  { "code": 400, "message": "错误原因描述" }
  ```

---

## 一、课前配置模块

### 1.1 上传教案并初始化课程

**前端 (A) → 后端 (C)**

```
POST /api/init_lesson
Content-Type: multipart/form-data
```

**请求体：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | 教案文件（Word / PDF / PPT） |
| `grade` | string | 年级，如 `"初二"` |
| `subject` | string | 学科，如 `"数学"` |
| `class_level` | string | `"重点班"` \| `"普通班"` |
| `atmosphere` | string | `"活跃"` \| `"沉闷"` |
| `custom_goal` | string | 教师自定义练习目标，如 `"我想解决衔接生硬的问题"` |

**响应体：**

```json
{
  "lesson_id": "uuid-xxxx",
  "status": "processing",
  "message": "教案上传成功，正在后台提取知识点"
}
```

---

### 1.2 查询教案预处理状态

**前端 (A) → 后端 (C)**

```
GET /api/lesson/{lesson_id}/status
```

**响应体：**

```json
{
  "lesson_id": "uuid-xxxx",
  "embedding_status": "done",
  "lesson_topic": "《勾股定理》",
  "subject": "初中数学",
  "subject_icon": "📐",
  "knowledge_points_preview": [
    { "point": "勾股定理定义", "difficulty": "中" },
    { "point": "勾股数", "difficulty": "高" }
  ],
  "preset_questions": [
    "如果不是直角三角形，勾股定理还成立吗？",
    "勾股定理的逆定理是什么？"
  ],
  "teacher_questions": [
    {
      "id": "grade",
      "type": "radio",
      "label": "学生年级",
      "required": true,
      "options": ["初一", "初二", "初三"]
    },
    {
      "id": "prior_knowledge",
      "type": "checkbox",
      "label": "AI 识别到本课依赖以下前置知识，请确认学生掌握情况",
      "hint": "可多选，AI 将据此校准虚拟学生的知识起点",
      "required": false,
      "options": ["直角三角形基础", "平方运算", "面积法"]
    }
  ]
}
```

> **说明**：`teacher_questions` 由杨云天（成员 B）的 AI 模块根据教案内容动态生成，问题数量和选项内容因课程而异。前端只负责渲染，不参与生成逻辑。
```

---

## 二、课堂实时模块（WebSocket）

WebSocket 地址：`ws://localhost:8000/ws/classroom/{session_id}`

### 2.1 前端 → 后端：发送音频片段

```json
{
  "event": "audio_chunk",
  "audio_base64": "<base64编码的音频数据>",
  "duration_ms": 1500
}
```

### 2.2 后端 → 前端：ASR 转写结果（实时字幕）

```json
{
  "event": "transcript_update",
  "text": "直角三角形的斜边平方等于两直角边的平方和",
  "is_final": true,
  "timestamp_ms": 5200
}
```

### 2.3 后端 → 前端：触发学生动作

这是前端最核心的事件，收到后需要：① 让对应小人产生动画 ② 播放 TTS 音频

```json
{
  "event": "student_action",
  "student_id": "gangjing",
  "action": "raise_hand",
  "audio_url": "/static/tts/reply_xxxx.mp3",
  "reply_text": "老师，那如果是锐角三角形呢？"
}
```

| `student_id` 可选值 | 说明 |
|---------------------|------|
| `gangjing` | 杠精/学优生 |
| `xuekun` | 学困生 |
| `sleepy` | 打瞌睡的学生 |
| `whisper` | 交头接耳的学生 |

| `action` 可选值 | 说明 |
|----------------|------|
| `raise_hand` | 举手发言 |
| `sleep` | 打瞌睡 |
| `whisper` | 交头接耳 |
| `confused` | 发呆/迷惑 |
| `idle` | 恢复普通状态 |

### 2.4 前端 → 后端：教师开始上课

```json
{ "event": "class_start", "lesson_id": "uuid-xxxx" }
```

### 2.5 前端 → 后端：教师下课

```json
{ "event": "class_end" }
```

### 2.6 后端 → 前端：报告生成完毕通知

```json
{
  "event": "report_ready",
  "session_id": "uuid-xxxx",
  "redirect_url": "/report/uuid-xxxx"
}
```

---

## 三、报告模块

### 3.1 获取课后报告

**前端 (A) → 后端 (C)**

```
GET /api/report/{session_id}
```

**响应体：**

```json
{
  "session_id": "uuid-xxxx",
  "scores": {
    "content_accuracy": 85,
    "syllabus_alignment": 90,
    "interaction_quality": 70,
    "pacing": 75,
    "language_appropriateness": 80
  },
  "radar_chart_data": {
    "indicators": ["内容准确度", "教案贴合度", "互动质量", "课堂节奏", "语言表达"],
    "values": [85, 90, 70, 75, 80]
  },
  "hard_stats": {
    "total_duration_min": 42,
    "total_words": 6800,
    "avg_speed_wpm": 162,
    "avg_wait_time_sec": 1.2,
    "filler_words": { "对不对": 12, "就是": 8, "呃": 5 }
  },
  "improvement_suggestions": "本节课教案贴合度较高，但互动环节偏少...",
  "is_improved": true,
  "history_comparison": "对比上节课，互动质量提升了 15 分"
}
```

---

## 四、智能体内部数据格式（B ↔ C）

> 这部分是成员 B 和 C 之间的内部约定，前端无需关心。

### 4.1 主控 Supervisor 决策输出（B → C）

```json
{
  "session_id": "uuid-xxxx",
  "timestamp_ms": 5200,
  "evaluation_note": "教态良好，准确讲出勾股定理定义",
  "is_questioning": false,
  "error_detected": false,
  "trigger_agent": "gangjing",
  "agent_prompt": "老师刚讲完勾股定理，请用初二学生口吻质疑：如果不是直角三角形还成立吗？"
}
```

### 4.2 Worker Agent（学生）回复输出（B → C）

```json
{
  "agent_type": "gangjing",
  "reply_text": "老师，那如果是锐角三角形呢？",
  "emotion": "curious"
}
```

| `emotion` 可选值 | 说明 |
|-----------------|------|
| `curious` | 好奇/质疑 |
| `confused` | 听不懂 |
| `sleepy` | 困倦 |
| `active` | 积极回应 |

---

*文档版本：v0.1 | 最后更新：2026-04-08 | 如有变更请同步通知 A/B/C 三位成员*
