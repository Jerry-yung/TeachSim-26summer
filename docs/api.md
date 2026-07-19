# TeachSim API 接口文档（修订建议稿）

> **这是一人主操刀，三人监督的“合同文件”**，所有接口的 URL、请求体、响应体在开发前必须在此确认。
> 如需修改接口，请提 PR 更新本文档，并通知相关成员。

> 代码审阅基线：2026-07-19。本文按当前仓库实际代码区分“已实现”和“待补齐”，不把前端调用或 UI mock 当作后端已实现能力。

---

## 目录

- [通用约定](#通用约定)
- [一、当前业务后端已实现接口](#一当前业务后端已实现接口)

- [二、AI 服务接口](#二ai-服务接口)
- [三、联调阻塞项](#三联调阻塞项)

---

## 通用约定

- 前端地址：`http://localhost:5173`
- AI 服务 Base URL：`http://localhost:8001`
- 业务后端代码文档使用端口 8000；当前前端代理默认指向 8010。联调前必须二选一统一：
  - 后端以 `--port 8010` 启动；或
  - 设置 `VITE_BACKEND_PROXY_TARGET=http://127.0.0.1:8000`。
- 前端通过 `/backend-api` 代理业务后端，通过 `/ai-api` 代理 AI 服务。
- JSON 接口使用 `application/json`；文件上传使用 `multipart/form-data`。
- 业务后端 `HTTPException` 和参数校验错误统一转换为：

  ```json
  { "code": 400, "message": "错误原因描述" }
  ```

- 当前前端按 Cookie 会话方式发送 `credentials: include`
---

## 一、当前业务后端已实现接口

### 1.1 健康检查

`GET /health`

```json
{ "status": "ok" }
```

### 1.2 上传教案并初始化课程

`POST /api/init_lesson`，`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `grade` | string | 是 | 年级 |
| `subject` | string | 是 | 学科 |
| `class_level` | string | 是 | `重点班`、`普通班`、`平行班` |
| `atmosphere` | string | 是 | `活跃`、`沉闷`、`活跃互动型`、`沉浸讲解型`、`严谨讨论型`、`练习主导型` |
| `custom_goal` | string | 否 | 自定义训练目标，默认空字符串 |
| `teacher_context` | string | 否 | 教师输入的课堂背景 |
| `lesson_json` | JSON 字符串 | 否 | 已结构化教案对象 |
| `ppt_json` | JSON 字符串 | 否 | 已结构化 PPT 对象 |
| `teaching_preferences_json` | JSON 字符串 | 否 | 开课前问卷结果 |
| `frontend_session_id` | string | 否 | 前端临时会话标识 |
| `file` | File | 否 | PDF、DOC、DOCX、PPT、PPTX，最大 20MB |

响应：

```json
{
  "lesson_id": "uuid-xxxx",
  "session_id": "uuid-xxxx",
  "status": "processing",
  "message": "教案上传成功，正在后台提取知识点"
}
```

- 有可解析文件且未提供 `lesson_json`：`processing`，后端后台调用 AI 解析。
- 已提供 `lesson_json`，或未上传文件进入自由模式：`ready`。
- 当前接口只接收一个 `file`。前端若同时有教案和 PPT，会先直接调用 AI 合并解析，再把结构化结果和一个原始文件交给业务后端。

### 1.3 查询课程预处理状态

`GET /api/lesson/{lesson_id}/status`

```json
{
  "lesson_id": "uuid-xxxx",
  "embedding_status": "done",
  "lesson_topic": "勾股定理",
  "subject": "初中数学",
  "subject_icon": "🔢",
  "knowledge_points_preview": [
    { "point": "勾股定理定义", "difficulty": "中" }
  ],
  "teacher_questions": []
}
```

`teacher_questions` 优先读取 AI 教案结构化结果；为空时使用业务后端内置问卷。内置问卷包括时长、年级、班级类型、学生基础、教学目标、突破方向和课堂氛围。

### 1.4 保存课堂发言并执行 Supervisor 决策

`POST /api/inclass/utterance`，`application/json`

```json
{
  "session_id": "uuid-xxxx",
  "role": "teacher",
  "content": "谁能回答这个问题？",
  "current_timestamp": "2026-07-19T10:00:00+08:00",
  "called_student_id": null,
  "current_ppt": [],
  "skip_supervisor": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `session_id` | string | 是 | 标准 UUID |
| `role` | string | 是 | 精确为 `teacher` 时按教师处理，其他值按学生处理 |
| `content` | string | 是 | 非空发言内容 |
| `current_timestamp` | string | 是 | ISO8601；代码可解析 `Z` |
| `called_student_id` | string/null | 否 | 被点名学生 ID |
| `current_ppt` | array/null | 否 | 当前 PPT 页，通常一项 |
| `skip_supervisor` | boolean | 否 | 默认 `false` |

非教师发言或 `skip_supervisor=true` 时只落库，返回固定 `normal`。教师发言会携带最近 20 条历史调用 AI Supervisor。

> 当前阻塞：业务后端发送给 AI 的字段是 `current_timestamp`、`called_student_id`；AI v2 实际读取 `class_elapsed_sec`、`called_student_status_digest`。修复前，接力回答等依赖 digest 的能力不能视为已打通。

### 1.5 查询虚拟学生静态状态

`GET /api/inclass/student-state/{student_id}`

| `student_id` | 文档/前端显示名 | `student_type` | 默认举手 |
|---|---|---|---:|
| `student_xm` | 小明 | `xueyou` | 否 |
| `student_xw` | 小闻（原文）；前端当前显示“小红”，待团队统一 | `gangjing` | 是 |
| `student_xw2` | 小王 | `xuekun` | 否 |
| `student_xl` | 小乐 | `xuekun` | 是 |

该接口返回的是进程内常量，不按 `session_id` 存储动态状态。前端传入的 `session_id` 查询参数当前会被忽略。

### 1.6 保存并评价课堂片段

`POST /api/inclass/segment`，`application/json`

必填字段：`session_id`、`segment_id`、`start_ts`、`end_ts`。可选字段：`slide_no`、`teacher_utterances`、`student_utterances`、`ppt_context`、`current_ppt`、`ppt_text`。

`teacher_utterances` 和 `student_utterances` 中每项均为：

```json
{ "speaker": "teacher", "ts": "2026-07-19T10:00:10+08:00", "text": "讲解内容" }
```

响应：

```json
{
  "scores": {
    "instructional_clarity": 85,
    "student_engagement": 78,
    "pace_control": 80
  },
  "strengths": ["表现亮点"],
  "issues": ["存在问题"],
  "improvement_actions": ["可执行建议"]
}
```

同一课堂重复提交相同 `segment_id` 时更新原记录。数据库当前没有 `(session_id, segment_id)` 唯一约束，幂等性由应用查询保证，并发重复请求仍需额外防护。

### 1.7 获取课后报告

`GET /api/report/{session_id}`

首次请求会把会话标为 `completed`，调用 AI 报告接口；AI 调用失败时使用本地降级报告。结果写入 `sessions.report_payload`，后续请求直接返回缓存。

主要响应字段：

- 课程信息：`session_id`、`lesson_topic`、`subject`、`class_info`、`created_at`、`duration_min`
- 总体结论：`overall_level`、`overall_desc`
- 五维结果：`dimensions`、`scores`、`radar_chart_data`
- 硬指标：`hard_stats`
- 教学结构：`time_distribution`、`question_types`
- 定向反馈：`custom_goal_feedback`、`improvement_suggestions`
- 课堂证据：`highlight_events`
- 历史预留：`is_improved=false`、`history_comparison=""`

注意：当前 `total_words` 实际按教师发言字符串长度计算，中文场景更接近“字符数”，并非严格分词后的词数；`avg_speed_wpm` 也基于该值。

### 1.8 调试音频转写

`POST /api/debug/transcribe`，`multipart/form-data`

- `audio`：必填，WAV/MP3/OGG，最大 20MB。
- `lesson_id`：可选；合法 UUID 时可关联教案，非法值直接忽略。
- 当前实现支持火山引擎；`ASR_PROVIDER=aliyun` 尚未实现。



---

## 二、AI 服务接口

AI 服务监听 8001。完整内部契约只在 `ai/docs/ai-backend-contract-v2.md` 维护，本文不重复定义字段。

当前主要接口：

- `POST /ai/parse_lesson`
- `POST /ai/parse_lessons`
- `POST /ai/v2/preclass/lesson/parse`
- `POST /ai/v2/preclass/ppt/parse`
- `POST /ai/v2/inclass/segment/eval`
- `POST /ai/v2/inclass/supervisor/decide`
- `POST /ai/v2/inclass/student/reply`
- `POST /ai/v2/postclass/report/generate`

---

## 三、联调阻塞项

1. 统一业务后端端口 8000/8010。
2. 决定并实现 Cookie 会话认证，或临时放开前端路由守卫。
3. 统一 Supervisor 字段：优先采用 AI v2 的 `class_elapsed_sec`、`called_student_status_digest`。
4. 在业务后端实现 `/api/inclass/student-reply` 转发，或明确让前端直连 AI v2。
5. 合并或实现 PPT 预览、会话重启、历史课堂、能力画像、ASR 签名和 TTS 接口。
6. 统一 `student_xw` 的显示名；在团队决定前保留原文人名，不擅自替换。

---

*文档版本：v0.2 | 代码基线：2026-07-19 | 如有变更请同步通知 A/B/C 三位成员*

