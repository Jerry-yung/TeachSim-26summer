# backend

TeachSim 后端：FastAPI + SQLAlchemy + Alembic + PostgreSQL（Supabase）。

## 环境

- Python 3.11+（推荐）
- PostgreSQL（Supabase 托管即可）

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

复制 [`.env.example`](.env.example) 为 `.env`，填入数据库与 ASR 密钥。**不要将 `.env` 提交到 Git。**

数据库支持两种方式（二选一）：

1. **完整 URL**：`DATABASE_URL=postgresql+psycopg://user:URL编码密码@host:5432/postgres?sslmode=require`  
   - 密码含 `,` `.` `/` 等字符时必须做 URL 编码。
2. **分项变量**：`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_HOST`、`POSTGRES_PORT`、`POSTGRES_DB`、`POSTGRES_SSLMODE`（应用内会对密码做 `quote_plus`）。

## 数据库迁移

```bash
cd backend
alembic upgrade head
```

会在库里创建以下表：`lessons`、`lesson_files`、`sessions`、`transcripts`、`session_students`。

其中 `session_students` 为**学生状态库**，与 `sessions` 强绑定，记录课中4名虚拟学生的类型（学优/杠精/学困）及动态状态（举手/睡觉/交头接耳）。

## 启动 API

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- 健康检查：`GET http://localhost:8000/health`
- 文档：`http://localhost:8000/docs`

## 接口

### `GET /api/inclass/student-states/{session_id}`

查询某 session 下全班4名学生的当前状态（类型、举手、睡觉、交头接耳）。

```bash
curl -s http://localhost:8000/api/inclass/student-states/$(echo $SESSION_ID)
```

响应示例：
```json
[
  {"student_id":"student_xm","student_name":"小明","student_type":"xueyou","is_hand_raised":true,"is_sleeping":false,"is_whispering":false},
  {"student_id":"student_xw","student_name":"小闻","student_type":"gangjing","is_hand_raised":true,"is_sleeping":false,"is_whispering":false},
  {"student_id":"student_xw2","student_name":"小王","student_type":"xuekun","is_hand_raised":false,"is_sleeping":false,"is_whispering":false},
  {"student_id":"student_xl","student_name":"小乐","student_type":"xuekun","is_hand_raised":false,"is_sleeping":false,"is_whispering":false}
]
```

### `POST /api/inclass/utterance`

课堂实时交互核心接口。教师每轮发言调用一次，后端根据 AI Supervisor 决策返回学生动作。

**请求字段变更**：
- 新增 `discipline_action`（可选）：前端直接触发纪律事件，不经过 AI Supervisor。取值 `"start_whisper" | "start_sleep" | "cancel_whisper" | "cancel_sleep"`。
- `called_student_id`（可选）：被点名学生 ID。

**响应格式变更**（现为 `InclassUtteranceResponse`）：

| 字段 | 说明 |
|------|------|
| `dialog_state` | 课堂状态：`normal` / `questioning` / `ambiguous` / `misstatement` / `relay_answer` / `discipline_whisper` / `discipline_sleep` |
| `interaction_round_id` | 本回合唯一 UUID，防串台 |
| `play_mode` | `"immediate"`（收到即播）或 `"on_call_name"`（只举手/缓存，老师点名后再播） |
| `raised_hand_student_ids` | 本回合应显示举手动画的学生 ID 列表 |
| `preset_for_student_id` | 单预设场景下 AI 回复对应的学生 ID（ambiguous/misstatement/relay_answer/discipline 等） |
| `student_states_digest` | 全班当前状态快照，减少前端多次拉取 |
| `preset_consumed` | 本次响应是否为「点名消费预设」结果 |
| `student_event` | AI 生成的学生回复/候选列表 |

**curl 示例**：

教师正常发言（无点名）：
```bash
curl -s -X POST http://localhost:8000/api/inclass/utterance -H "Content-Type: application/json" -d '{"session_id":"'"$SESSION_ID"'","role":"teacher","content":"同学们，谁来回答这个问题？","current_timestamp":"2026-07-15T15:00:00+08:00"}' | python3 -m json.tool
```

教师点名并触发纪律解除（前端随机触发 discipline）：
```bash
curl -s -X POST http://localhost:8000/api/inclass/utterance -H "Content-Type: application/json" -d '{"session_id":"'"$SESSION_ID"'","role":"teacher","content":"小乐，别睡觉了","current_timestamp":"2026-07-15T15:01:00+08:00","called_student_id":"student_xl","discipline_action":"cancel_sleep"}' | python3 -m json.tool
```

**各 `dialog_state` 行为对照**：

| `dialog_state` | 举手行为 | `play_mode` | `preset_for_student_id` |
|---|---|---|---|
| `questioning` | 后端随机挑 **2 人**举手 | `on_call_name` | `null` |
| `ambiguous` | 后端随机指定 **1 学困生**举手 | `on_call_name` | 该学困生 ID |
| `misstatement` | 后端随机指定 **1 杠精**举手 | `on_call_name` | 该杠精 ID |
| `relay_answer` | 不举手，直接站立 | `immediate` | `called_student_id` |
| `discipline_whisper` | 不举手，直接站立 | `immediate` | `called_student_id` |
| `discipline_sleep` | 不举手，直接站立 | `immediate` | `called_student_id` |
| `normal` | 无 | `immediate` | `null` |

### `POST /api/init_lesson`

`multipart/form-data`：

| 字段 | 必填 | 说明 |
|------|------|------|
| `grade` | 是 | 年级 |
| `subject` | 是 | 学科 |
| `class_level` | 是 | `重点班` 或 `普通班` |
| `atmosphere` | 是 | `活跃` 或 `沉闷` |
| `custom_goal` | 否 | 练习目标，默认空 |
| `teacher_context` | 否 | 教师背景描述（与前端对接用） |
| `file` | 否 | 教案：pdf/doc/docx/ppt/pptx，最大 20MB |

成功：`{"lesson_id":"...","status":"processing","message":"..."}`  
错误：`{"code":400,"message":"..."}`（或其它 HTTP 状态码）。

### `POST /api/debug/transcribe`

默认联调 **火山引擎豆包语音 — 大模型录音文件极速版**（`ASR_PROVIDER=volcengine`）。一次请求返回全文，支持 **WAV / MP3 / OGG**。参见[官方文档](https://www.volcengine.com/docs/6561/1631584)。

`multipart/form-data`：

- `audio`：音频文件（必填，建议小于 20MB）
- `lesson_id`：可选，**标准 UUID**（与 `lessons.id` 一致）时写入 `transcripts.lesson_id`；非 UUID 会忽略，不返回 400

环境变量（火山 **旧版控制台**）：

- `VOLC_ASR_APP_ID`：控制台 **APP ID** → 请求头 `X-Api-App-Key`
- `VOLC_ASR_ACCESS_TOKEN`：控制台 **Access Token** → 请求头 `X-Api-Access-Key`
- `VOLC_ASR_RESOURCE_ID`：默认 `volc.bigasr.auc_turbo`（需在控制台开通对应资源）
- `VOLC_HTTP_TRUST_ENV`：默认 `false`，**不走**系统代理与环境变量里的 `HTTP(S)_PROXY`（避免本机错误代理导致无法连接）；仅当你必须用代理访问外网时设为 `true`
- `ASR_DEBUG_PERSIST`：`true`（默认）时在 `transcripts` 表落一条调试记录（`session_id` 为空；`provider` 为 `volcengine`）

阿里云：`ASR_PROVIDER=aliyun` 时暂返回 501（未实现）。

### curl 示例

初始化课程（无文件）：

```bash
curl -s -X POST http://localhost:8000/api/init_lesson \
  -F "grade=初二" -F "subject=数学" \
  -F "class_level=普通班" -F "atmosphere=活跃" \
  -F "custom_goal=练习衔接"
```

调试 ASR：

```bash
curl -s -X POST http://localhost:8000/api/debug/transcribe \
  -F "audio=@sample.wav;type=audio/wav"
```

## 上传文件存储

默认目录为项目内 `backend/uploads/`（已在仓库 `.gitignore` 中忽略）。可通过 `UPLOAD_DIR` 修改。

## CORS

默认允许 `http://localhost:5173`。修改环境变量 `CORS_ORIGINS`（逗号分隔多个源）。

## 测试

### 单元测试

```bash
cd backend
python -m app.tests.test_student_state
```

或直接运行：

```bash
cd backend
python -c "
import sys
sys.path.insert(0, '.')
from app.tests.test_student_state import (
    TestInitializeSessionStudents,
    TestPickRandomStudentsByType,
    TestResponseSchema,
)
TestInitializeSessionStudents().test_reproducibility()
TestInitializeSessionStudents().test_roster_fixed()
TestInitializeSessionStudents().test_distribution_approximate()
TestPickRandomStudentsByType().test_empty_candidates()
TestPickRandomStudentsByType().test_count_larger_than_candidates()
TestPickRandomStudentsByType().test_exclude_ids()
TestResponseSchema().test_inclass_utterance_response()
print('All tests passed!')
"
```

覆盖内容：
- 学生类型分配的可复现性（相同 `session_id` 产生相同结果）
- 固定4人名单验证
- 班级类型比例统计（重点班/普通班/平行班的学优/杠精/学困占比）
- 按类型随机挑选学生的边界条件（空候选、超量、排除指定 ID）
- 新响应 Schema 序列化正确性

### 接口联调（curl）

**1. 初始化课程并观察学生状态库自动创建**

```bash
# 1) 创建课程
RESP=$(curl -s -X POST http://localhost:8000/api/init_lesson \
  -F "grade=初二" -F "subject=数学" \
  -F "class_level=重点班" -F "atmosphere=活跃")
echo $RESP

# 提取 session_id
SESSION_ID=$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

# 2) 查询全班学生状态（应返回4人，student_type 按重点班比例分配）
curl -s http://localhost:8000/api/inclass/student-states/$SESSION_ID | python3 -m json.tool
```

**2. 模拟教师提问，观察举手状态**

```bash
# 教师提问 → 应返回 questioning + 2人举手 + on_call_mode
curl -s -X POST http://localhost:8000/api/inclass/utterance -H "Content-Type: application/json" -d '{"session_id":"'"$SESSION_ID"'","role":"teacher","content":"谁来回答一下这个问题？","current_timestamp":"2026-07-15T15:00:00+08:00"}' | python3 -m json.tool

# 验证举手状态已写入数据库
curl -s http://localhost:8000/api/inclass/student-states/$SESSION_ID | python3 -m json.tool
```

**3. 模拟 relay_answer（点名接力）**

```bash
# 教师点名某学生 → 应返回 relay_answer + immediate + preset_for_student_id 为该学生
curl -s -X POST http://localhost:8000/api/inclass/utterance -H "Content-Type: application/json" -d '{"session_id":"'"$SESSION_ID"'","role":"teacher","content":"小明，你来补充一下。","current_timestamp":"2026-07-15T15:01:00+08:00","called_student_id":"student_xm"}' | python3 -m json.tool
```

**4. 模拟 discipline 事件（前端随机触发）**

```bash
# 前端让学生开始睡觉 → 应返回 discipline_sleep + immediate
curl -s -X POST http://localhost:8000/api/inclass/utterance -H "Content-Type: application/json" -d '{"session_id":"'"$SESSION_ID"'","role":"teacher","content":"(系统事件)","current_timestamp":"2026-07-15T15:02:00+08:00","called_student_id":"student_xl","discipline_action":"start_sleep"}' | python3 -m json.tool

# 查询状态：student_xl 的 is_sleeping 应为 true
curl -s http://localhost:8000/api/inclass/student-states/$SESSION_ID | python3 -m json.tool

# 老师点名该学生解除睡觉状态 → 应返回 discipline_sleep + immediate + is_sleeping 重置为 false
curl -s -X POST http://localhost:8000/api/inclass/utterance -H "Content-Type: application/json" -d '{"session_id":"'"$SESSION_ID"'","role":"teacher","content":"小乐，醒醒。","current_timestamp":"2026-07-15T15:03:00+08:00","called_student_id":"student_xl","discipline_action":"cancel_sleep"}' | python3 -m json.tool
```

**5. 验证新一轮 utterance 重置举手状态**

```bash
# 第一轮：questioning 产生举手
curl -s -X POST http://localhost:8000/api/inclass/utterance -H "Content-Type: application/json" -d '{"session_id":"'"$SESSION_ID"'","role":"teacher","content":"谁来回答一下这个问题？","current_timestamp":"2026-07-15T15:00:00+08:00"}' | python3 -m json.tool

# 第二轮：普通发言（normal），查询 student-states，确认上一轮举手已被重置为 false
curl -s -X POST http://localhost:8000/api/inclass/utterance -H "Content-Type: application/json" -d '{"session_id":"'"$SESSION_ID"'","role":"teacher","content":"我们继续讲课。","current_timestamp":"2026-07-15T15:04:00+08:00"}' | python3 -m json.tool

curl -s http://localhost:8000/api/inclass/student-states/$SESSION_ID | python3 -m json.tool
```
