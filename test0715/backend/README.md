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

会在库里创建四张表：`lessons`、`lesson_files`、`sessions`、`transcripts`。

## 启动 API

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- 健康检查：`GET http://localhost:8000/health`
- 文档：`http://localhost:8000/docs`

## 接口

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
