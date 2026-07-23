# TeachSim API 接口文档

> **这是一人主操刀，三人监督的“合同文件”**，所有接口的 URL、请求体、响应体在开发前必须在此确认。  
> 如需修改接口，请提 PR 更新本文档，并通知相关成员。

---

## 目录

- [通用约定](#通用约定)
- [一、认证模块](#一认证模块)
- [二、课前配置模块](#二课前配置模块)
- [三、课堂交互模块](#三课堂交互模块)
- [四、视觉教态模块](#四视觉教态模块)
- [五、报告与历史模块](#五报告与历史模块)
- [六、语音模块](#六语音模块)
- [七、AI 服务接口](#七ai-服务接口)

---

## 通用约定

- 前端地址：`http://localhost:5173`
- 业务后端 Base URL：`http://localhost:8010`
- AI 服务 Base URL：`http://localhost:8001`
- 前端通过 `/backend-api` 代理业务后端，通过 `/ai-api` 代理 AI 服务。
- JSON 接口使用 `application/json`，文件上传使用 `multipart/form-data`。
- 业务认证使用 HttpOnly Cookie，前端请求携带 `credentials: include`。
- 课程、课堂、报告和历史数据均与当前登录用户关联。

统一错误响应：

```json
{
  "code": 400,
  "message": "错误原因描述"
}
```

---

## 一、认证模块

路由前缀：`/api/auth`

### 1.1 邮箱注册

发送验证码：

```http
POST /api/auth/register/send-code
```

```json
{
  "email": "teacher@example.com"
}
```

校验验证码：

```http
POST /api/auth/register/verify-code
```

```json
{
  "email": "teacher@example.com",
  "code": "123456"
}
```

完成注册：

```http
POST /api/auth/register/complete
```

```json
{
  "email": "teacher@example.com",
  "display_name": "教师姓名",
  "password": "password",
  "verification_token": "token"
}
```

注册成功后自动建立登录会话。

### 1.2 登录与退出

登录：

```http
POST /api/auth/login
```

```json
{
  "email": "teacher@example.com",
  "password": "password"
}
```

退出：

```http
POST /api/auth/logout
```

获取当前用户：

```http
GET /api/auth/me
```

用户响应：

```json
{
  "user": {
    "id": "uuid",
    "email": "teacher@example.com",
    "display_name": "教师姓名",
    "role": "实习教师"
  }
}
```

### 1.3 密码重置

- `POST /api/auth/password-reset/send-code`
- `POST /api/auth/password-reset/verify-code`
- `POST /api/auth/password-reset/complete`

完成密码重置：

```json
{
  "email": "teacher@example.com",
  "new_password": "new-password",
  "verification_token": "token"
}
```

---

## 二、课前配置模块

### 2.1 初始化课程

```http
POST /api/init_lesson
Content-Type: multipart/form-data
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `grade` | string | 是 | 学生年级 |
| `subject` | string | 是 | 授课学科 |
| `class_level` | string | 是 | `重点班`、`普通班`、`平行班` |
| `atmosphere` | string | 是 | 课堂氛围 |
| `custom_goal` | string | 否 | 本次训练目标 |
| `teacher_context` | string | 否 | 教师补充的课堂背景 |
| `lesson_json` | JSON 字符串 | 否 | 结构化教案 |
| `ppt_json` | JSON 字符串 | 否 | 结构化课件 |
| `teaching_preferences_json` | JSON 字符串 | 否 | 开课前问卷结果 |
| `frontend_session_id` | string | 否 | 前端会话标识 |
| `file` | File | 否 | PDF、DOC、DOCX、PPT、PPTX，最大 20MB |

响应：

```json
{
  "lesson_id": "uuid",
  "session_id": "uuid",
  "status": "ready",
  "message": "课堂初始化成功"
}
```

课程初始化同时完成：

- 课程和课堂会话入库；
- 教案、课件和教学偏好保存；
- 4 名虚拟学生的课堂状态初始化；
- PPT/PPTX 课件预览准备；
- 课程内容结构化分析。

### 2.2 查询课程分析状态

```http
GET /api/lesson/{lesson_id}/status
```

```json
{
  "lesson_id": "uuid",
  "embedding_status": "done",
  "lesson_topic": "勾股定理",
  "subject": "初中数学",
  "subject_icon": "🔢",
  "knowledge_points_preview": [
    {
      "point": "勾股定理定义",
      "difficulty": "中"
    }
  ],
  "teacher_questions": []
}
```

### 2.3 PPT 预览

- `GET /api/lesson/{lesson_id}/ppt-preview`
- `GET /api/lesson/{lesson_id}/ppt-preview/file`

预览状态：

```json
{
  "ready": true,
  "message": "ok",
  "preview_path": "/api/lesson/{lesson_id}/ppt-preview/file",
  "page_count": 12
}
```

### 2.4 重新创建课堂

```http
POST /api/session/{session_id}/restart
```

该接口复用原课程和课前配置，创建全新的课堂会话和学生状态。

---

## 三、课堂交互模块

路由前缀：`/api/inclass`

### 3.1 保存课堂发言并执行决策

```http
POST /api/inclass/utterance
Content-Type: application/json
```

```json
{
  "session_id": "uuid",
  "role": "teacher",
  "content": "谁能回答这个问题？",
  "current_timestamp": "2026-07-23T10:00:00+08:00",
  "class_elapsed_sec": 125,
  "called_student_id": null,
  "discipline_student_id": null,
  "slide_no": 2,
  "current_ppt": [],
  "skip_supervisor": false,
  "discipline_action": null
}
```

| 字段 | 说明 |
|---|---|
| `session_id` | 当前课堂 UUID |
| `role` | `teacher` 或学生角色 |
| `content` | 本轮发言 |
| `current_timestamp` | ISO8601 时间 |
| `class_elapsed_sec` | 课内计时秒数 |
| `called_student_id` | 被点名学生 ID |
| `discipline_student_id` | 纪律事件目标学生 |
| `slide_no` | 当前 PPT 页 |
| `current_ppt` | 当前页结构化内容 |
| `skip_supervisor` | 是否只保存发言 |
| `discipline_action` | 睡觉、交头接耳状态的开始或取消操作 |

决策响应：

```json
{
  "dialog_state": "questioning",
  "should_trigger_student": true,
  "trigger_reason": "teacher_question",
  "target_student_type": "all",
  "interaction_round_id": "uuid",
  "play_mode": "on_call_name",
  "raised_hand_student_ids": [
    "student_xm",
    "student_xw"
  ],
  "preset_for_student_id": null,
  "student_states_digest": [],
  "preset_consumed": false,
  "student_event": null
}
```

课堂状态：

| `dialog_state` | 课堂行为 |
|---|---|
| `normal` | 正常讲课 |
| `questioning` | 根据课堂氛围、问题难度和学生状态选择学生举手 |
| `ambiguous` | 学困生针对表述提出疑问 |
| `misstatement` | 杠精学生针对知识点提出质疑 |
| `relay_answer` | 被点名学生补充或接力回答 |
| `discipline_whisper` | 处理交头接耳场景 |
| `discipline_sleep` | 处理睡觉场景 |

`play_mode` 取值：

- `immediate`：收到回复后立即播放；
- `on_call_name`：学生先举手，教师点名后播放。

普通发言可返回 `204 No Content`，前端据此继续课堂流程。

### 3.2 点名学生回复

```http
POST /api/inclass/student-reply
```

```json
{
  "session_id": "uuid",
  "student_id": "student_xm",
  "current_timestamp": "2026-07-23T10:01:00+08:00",
  "class_elapsed_sec": 180,
  "slide_no": 2,
  "current_ppt": [],
  "question_bundle_text": "为什么勾股定理只适用于直角三角形？",
  "question_count": 1,
  "question_items": []
}
```

```json
{
  "student_id": "student_xm",
  "student_type": "xueyou",
  "reply_text": "学生回复内容",
  "emotion": "curious",
  "is_proactive_speaking": true
}
```

### 3.3 查询虚拟学生状态

- `GET /api/inclass/student-state/{student_id}?session_id={session_id}`
- `GET /api/inclass/student-states/{session_id}`

```json
{
  "student_id": "student_xm",
  "student_name": "小明",
  "student_type": "xueyou",
  "is_hand_raised": true,
  "is_sleeping": false,
  "is_whispering": false
}
```

课堂学生：

| `student_id` | 显示名称 |
|---|---|
| `student_xm` | 小明 |
| `student_xw` | 小闻（原文）；系统界面显示小红 |
| `student_xw2` | 小王 |
| `student_xl` | 小乐 |

学生类型与动态状态按课堂会话保存。

### 3.4 保存并评价课堂片段

```http
POST /api/inclass/segment
```

主要字段：

- `session_id`、`segment_id`
- `start_ts`、`end_ts`
- `start_elapsed_sec`、`end_elapsed_sec`
- `slide_no`
- `teacher_utterances`
- `student_utterances`
- `ppt_context`、`current_ppt`、`ppt_text`

评价响应：

```json
{
  "scores": {
    "instructional_clarity": 85,
    "student_engagement": 78,
    "pace_control": 80
  },
  "strengths": [
    "表现亮点"
  ],
  "issues": [
    "需要关注的课堂表现"
  ],
  "improvement_actions": [
    "下一次可执行的改进动作"
  ]
}
```

---

## 四、视觉教态模块

### 4.1 上传视觉观察窗口

```http
POST /api/inclass/visual-observation
Content-Type: multipart/form-data
```

成功状态码：202。

| 字段 | 说明 |
|---|---|
| `session_id` | 当前课堂 |
| `observation_id` | 视觉窗口标识 |
| `segment_id` | 对应课堂片段 |
| `window_start_sec` / `window_end_sec` | 课堂时间窗口 |
| `slide_no` | 当前 PPT 页 |
| `precheck_passed` | 前端画面预检结果 |
| `chat_history_json` | 最近师生对话 |
| `frames_b64_json` | JPEG 抽样帧 |
| `thumbnail` | JPEG 缩略图 |
| `clip` | WebM 短片 |

```json
{
  "observation_id": "uuid_w1",
  "status": "accepted",
  "message": ""
}
```

系统以 15 秒为观察窗口，结合抽样图像、短片、课堂发言和 PPT 页码完成教姿教态分析。

### 4.2 获取视觉素材

- `GET /api/report/{session_id}/visual-clip/{observation_id}`
- `GET /api/report/{session_id}/visual-thumb/{observation_id}`

接口分别返回 WebM 课堂短片和 JPEG 缩略图。

---

## 五、报告与历史模块

### 5.1 获取课后报告

```http
GET /api/report/{session_id}
```

查询参数：

- `force=true`：重新生成报告；
- `wait_visual=true`：等待视觉分析结果。

报告包括：

- 课程主题、学科、班级和课堂时长；
- 内容准确、教案贴合、互动质量、课堂节奏和语言表达；
- 总字数、平均语速、等待时间和口头禅；
- 课堂时间分布和问题类型；
- 自定义训练目标反馈；
- 课堂高光和师生互动事件；
- 教姿教态综合得分、维度分数和时间轴；
- 改进建议。

### 5.2 最近五节课堂比较

```http
GET /api/report/{session_id}/recent5-comparison
```

比较指标：

- 平均语速；
- 平均等待时长；
- 互动质量；
- 讲述模糊与错误数。

### 5.3 历史课堂

路由前缀：`/api/history`

- `GET /sessions`
- `GET /session-dates`
- `GET /sessions/{session_id}`
- `DELETE /sessions/{session_id}`
- `GET /latest-preset`
- `GET /ability-profile`

历史课堂支持：

- 课程主题搜索；
- 日期范围筛选；
- 报告回看；
- 课堂记录删除；
- 上一节课配置复用；
- 能力画像与趋势分析。

能力画像包括课堂节奏、互动组织、讲解清晰度和课堂管理。

---

## 六、语音模块

### 6.1 讯飞实时 ASR 签名

```http
POST /api/asr/xfyun/sign
```

```json
{
  "ws_url": "wss://...",
  "app_id": "app-id",
  "expires_in_seconds": 300
}
```

前端使用签名 URL 建立讯飞实时听写连接。

### 6.2 MiniMax 学生语音

```http
POST /api/tts/minimax/synthesize
```

```json
{
  "text": "学生需要朗读的内容",
  "student_id": "student_xm"
}
```

成功响应类型为 `audio/mpeg`。学生 ID 用于选择对应音色。

### 6.3 调试音频转写

```http
POST /api/debug/transcribe
Content-Type: multipart/form-data
```

- `audio`：WAV、MP3 或 OGG，最大 20MB；
- `lesson_id`：可关联当前用户的课程。

---

## 七、AI 服务接口

AI 服务主要接口：

- `POST /ai/parse_lesson`
- `POST /ai/parse_lessons`
- `POST /ai/v2/preclass/lesson/parse`
- `POST /ai/v2/preclass/ppt/parse`
- `POST /ai/v2/inclass/segment/eval`
- `POST /ai/v2/inclass/supervisor/decide`
- `POST /ai/v2/inclass/student/reply`
- `POST /ai/v2/inclass/visual/analyze`
- `POST /ai/v2/postclass/report/generate`

AI 服务完成教案解析、PPT 结构化、课堂状态判断、虚拟学生回复、课堂片段评价、教姿教态分析和课后报告生成。

---

*文档版本：v1.0 | 最后更新：2026-07-23 | 如有变更请同步通知 A/B/C 三位成员*

