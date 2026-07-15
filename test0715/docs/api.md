# TeachSim API 接口文档

> **这是一人主操刀，三人监督的"合同文件"**，所有接口的 URL、请求体、响应体在开发前必须在此确认。
> 如需修改接口，请提 PR 更新本文档，并通知相关成员。

---

## 目录

- [通用约定](#通用约定)
- [一、课前配置模块](#一课前配置模块)
- [二、课堂实时模块（HTTP + 浏览器 ASR）](#二课堂实时模块http--浏览器-asr)
- [三、报告模块](#三报告模块)
- [四、智能体内部数据格式（B ↔ C）](#四智能体内部数据格式b--c)

---

## 通用约定

- 前端地址：`http://localhost:5173`
- 业务后端 Base URL：`http://localhost:8000`
- AI 服务 Base URL：`http://localhost:8001`
- 前端通过 `/backend-api` 代理业务后端，通过 `/ai-api` 代理 AI 服务
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
| `file` | File，可选 | 教案或课件文件，上传接口接受 PDF、DOC、DOCX、PPT、PPTX，最大 20MB。当前自动内容解析主要支持 PDF、DOCX、PPTX；旧版 DOC、PPT 建议先转换为 DOCX、PPTX；不上传文件时进入自由模式 |
| `grade` | string | 年级，如 `"初二"` |
| `subject` | string | 学科，如 `"数学"` |
| `class_level` | string | `"重点班"` \| `"普通班"` \| `"平行班"` |
| `atmosphere` | string | `"活跃"` \| `"沉闷"` \| `"活跃互动型"` \| `"沉浸讲解型"` \| `"严谨讨论型"` \| `"练习主导型"` |
| `custom_goal` | string | 教师自定义练习目标，如 `"我想解决衔接生硬的问题"` |

**响应体：**

```json
{
  "lesson_id": "uuid-xxxx",
  "session_id": "uuid-xxxx",
  "status": "processing",
  "message": "教案上传成功，正在后台提取知识点"
}
```
- `processing`：上传的文件正在解析。
- `ready`：课堂已经初始化完成，可以开始上课。

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


---

## 二、课堂实时模块（HTTP + 浏览器 ASR）

当前业务后端没有课堂 WebSocket 接口。浏览器直接连接讯飞 WebSocket 完成实时语音识别，识别后的完整句子通过 HTTP 发送给业务后端。

### 2.1 保存课堂发言并执行 Supervisor 决策

```http
POST /api/inclass/utterance
Content-Type: application/json
```

**请求体：**

```json
{
  "session_id": "uuid-xxxx",
  "role": "teacher",
  "content": "谁能回答这个问题？",
  "current_timestamp": "2026-07-16T10:00:00+08:00",
  "called_student_id": null,
  "current_ppt": [],
  "skip_supervisor": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | 是 | 课堂会话 UUID，由 `/api/init_lesson` 返回 |
| `role` | string | 是 | 发言角色；`teacher` 表示教师，其他值按学生发言处理 |
| `content` | string | 是 | 本轮发言内容，不能为空 |
| `current_timestamp` | string | 是 | 发言时间，使用包含时区的 ISO8601 格式 |
| `called_student_id` | string \| null | 否 | 本轮点名的具体学生 ID |
| `current_ppt` | array \| null | 否 | 当前 PPT 页面内容，通常只传一页 |
| `skip_supervisor` | boolean | 否 | 是否跳过 AI Supervisor，默认 `false` |

当发言角色不是教师，或者 `skip_supervisor` 为 `true` 时，只保存发言，不执行 AI 决策。

**无须触发虚拟学生时的响应：**

```json
{
  "dialog_state": "normal",
  "should_trigger_student": false,
  "trigger_reason": "none",
  "target_student_type": null,
  "student_event": null
}
```

**触发虚拟学生时的响应示例：**

```json
{
  "dialog_state": "misstatement",
  "should_trigger_student": true,
  "trigger_reason": "检测到可能的知识性错误",
  "target_student_type": "gangjing",
  "student_event": {
    "student_type": "gangjing",
    "emotion": "curious",
    "reply_text": "老师，这里是不是还需要满足直角三角形这个条件？",
    "is_triggered": true,
    "is_proactive_speaking": true
  }
}
```

> `student_event` 可能是单个对象、候选对象数组或 `null`。完整决策格式以 `ai/docs/ai-backend-contract-v2.md` 为准。

---

### 2.2 查询虚拟学生状态

```http
GET /api/inclass/student-state/{student_id}
```

**路径参数：**

| 参数 | 类型 | 说明 |
|---|---|---|
| `student_id` | string | 具体虚拟学生 ID |

当前支持的学生：

| `student_id` | 显示名称 | `student_type` |
|---|---|---|
| `student_xm` | 小明 | `xueyou` |
| `student_xw` | 小闻 | `gangjing` |
| `student_xw2` | 小王 | `xuekun` |
| `student_xl` | 小乐 | `xuekun` |

**响应体：**

```json
{
  "student_id": "student_xw",
  "student_type": "gangjing",
  "is_hand_raised": true
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `student_id` | string | 具体学生 ID |
| `student_type` | string | AI 学生人设类型 |
| `is_hand_raised` | boolean | 当前是否处于举手状态 |

如果 `student_id` 不存在，返回：

```json
{
  "code": 404,
  "message": "student 不存在"
}
```

---

### 2.3 保存并评价课堂片段

```http
POST /api/inclass/segment
Content-Type: application/json
```

该接口保存一个课堂片段，并将片段发送给 AI 服务进行评价。前端通常在 PPT 翻页、无 PPT 时累计约三分钟，或者教师停止录音时调用该接口。

**请求体：**

```json
{
  "session_id": "uuid-xxxx",
  "segment_id": "seg-1721095200000-1",
  "start_ts": "2026-07-16T10:00:00+08:00",
  "end_ts": "2026-07-16T10:03:00+08:00",
  "slide_no": 2,
  "teacher_utterances": [
    {
      "speaker": "teacher",
      "ts": "2026-07-16T10:00:10+08:00",
      "text": "勾股定理适用于什么样的三角形？"
    }
  ],
  "student_utterances": [
    {
      "speaker": "小闻",
      "ts": "2026-07-16T10:00:15+08:00",
      "text": "应该是直角三角形。"
    }
  ],
  "current_ppt": [
    {
      "slide_no": 2,
      "title": "勾股定理",
      "text_blocks": [
        "在直角三角形中，两条直角边的平方和等于斜边的平方。"
      ],
      "visual_elements": [],
      "summary": "介绍勾股定理的基本定义"
    }
  ],
  "ppt_text": "在直角三角形中，两条直角边的平方和等于斜边的平方。"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | 是 | 课堂会话 UUID |
| `segment_id` | string | 是 | 当前课堂片段的唯一标识 |
| `start_ts` | string | 是 | 片段开始时间，使用 ISO8601 格式 |
| `end_ts` | string | 是 | 片段结束时间，不得早于 `start_ts` |
| `slide_no` | integer \| null | 否 | 当前 PPT 页码 |
| `teacher_utterances` | array | 否 | 当前片段中的教师发言，默认空数组 |
| `student_utterances` | array | 否 | 当前片段中的学生发言，默认空数组 |
| `ppt_context` | object \| null | 否 | 已整理的当前 PPT 页面上下文 |
| `current_ppt` | array \| null | 否 | 当前 PPT 页面内容，通常只传一页 |
| `ppt_text` | string \| null | 否 | 当前 PPT 页面提取出的纯文本 |

每条发言包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `speaker` | string | 发言者名称或角色 |
| `ts` | string | 发言时间 |
| `text` | string | 发言内容 |

**响应体：**

```json
{
  "scores": {
    "instructional_clarity": 85,
    "student_engagement": 78,
    "pace_control": 80
  },
  "strengths": [
    "能够通过提问检查学生是否理解勾股定理的适用条件"
  ],
  "issues": [
    "学生回答后缺少进一步追问"
  ],
  "improvement_actions": [
    "学生回答后继续追问为什么必须是直角三角形"
  ]
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `scores.instructional_clarity` | integer | 讲解清晰度，范围 0～100 |
| `scores.student_engagement` | integer | 学生参与度，范围 0～100 |
| `scores.pace_control` | integer | 课堂节奏控制，范围 0～100 |
| `strengths` | array | 当前片段表现较好的地方 |
| `issues` | array | 当前片段存在的问题 |
| `improvement_actions` | array | 可执行的改进建议 |

如果同一课堂中再次提交相同的 `segment_id`，后端会更新原有片段记录，而不是重复创建记录。

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
    "filler_words": [
      { "word": "然后", "count": 5 },
      { "word": "就是", "count": 8 },
      { "word": "对不对", "count": 12 },
      { "word": "呃", "count": 5 }
    ]
  },
  "improvement_suggestions": "本节课教案贴合度较高，但互动环节偏少...",
  "is_improved": false,
  "history_comparison": ""
}
```
历史课堂对比目前尚未实现，这两个字段为后续功能预留。

---

## 四、智能体内部数据格式（B ↔ C）

> AI 与业务后端之间使用 v2 接口。完整字段定义以
`ai/docs/ai-backend-contract-v2.md` 为准，本文件只记录前端可见的业务接口，避免维护两份重复契约。

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

*文档版本：v0.1 | 最后更新：2026-07-15 | 如有变更请同步通知 A/B/C 三位成员*
