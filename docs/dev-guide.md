# 开发规范与协作指南

---

## 仓库结构

```text
TeachSim-26summer/
├── frontend/       ← 刘至晗 负责（Vue 3 + Vite + Pinia）
├── backend/        ← 唐一嘉 负责（FastAPI + SQLAlchemy + PostgreSQL）
├── ai/             ← 杨云天 负责（FastAPI + LangChain + Prompt）
└── docs/           ← 周光轩主要负责，三人共同监督
```

**原则：只在自己负责的文件夹里提交代码。** 修改别人负责目录的内容前先说明原因；接口变更同时通知调用方和文档负责人。

---

## 技术栈

### 前端

- Vue 3
- Vite 5
- Pinia
- Vue Router
- ECharts
- PDF.js
- 浏览器 WebSocket、MediaRecorder、Web Audio 和 SpeechSynthesis

### 业务后端

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- HttpOnly Cookie 会话

### AI 服务

- FastAPI
- LangChain
- 大语言模型
- 多模态视觉模型
- 教案、课件、课堂片段和报告智能体

---

## 服务端口

| 服务 | 地址 |
|---|---|
| 前端 | `http://localhost:5173` |
| 业务后端 | `http://localhost:8010` |
| AI 服务 | `http://localhost:8001` |

前端代理：

```dotenv
VITE_BACKEND_PROXY_TARGET=http://127.0.0.1:8010
VITE_AI_PROXY_TARGET=http://127.0.0.1:8001
```

---

## 安装依赖

### 前端（A）

```bash
cd frontend
npm install
```

### 业务后端（C）

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### AI 模块（B）

```bash
cd ai
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 环境变量

在仓库根目录创建 `.env`，统一保存业务后端和 AI 服务配置。`.env` 不提交到 Git。

### 数据库

```dotenv
DATABASE_URL=postgresql://user:encoded_password@host:5432/postgres
UPLOAD_DIR=uploads
```

也可以使用：

```dotenv
POSTGRES_USER=placeholder
POSTGRES_PASSWORD=placeholder
POSTGRES_HOST=placeholder
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_SSLMODE=require
```

### 业务后端

```dotenv
AI_SERVICE_URL=http://localhost:8001
AI_TIMEOUT_S=30
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
JWT_SECRET=请填写至少32字符的随机字符串
AUTH_SESSION_COOKIE_NAME=teachsim_session
AUTH_SESSION_TTL_HOURS=168
AUTH_SESSION_COOKIE_SECURE=false
```

### 邮箱验证码

```dotenv
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USERNAME=placeholder
SMTP_PASSWORD=placeholder
SMTP_FROM=placeholder
SMTP_USE_SSL=true
AUTH_CODE_TTL_MINUTES=10
AUTH_CODE_RESEND_SECONDS=60
AUTH_CODE_MAX_ATTEMPTS=5
AUTH_PASSWORD_MIN_LENGTH=8
```

### 语音服务

```dotenv
ASR_PROVIDER=volcengine
VOLC_ASR_APP_ID=placeholder
VOLC_ASR_ACCESS_TOKEN=placeholder
VOLC_ASR_RESOURCE_ID=volc.bigasr.auc_turbo
VOLC_HTTP_TRUST_ENV=false
ASR_DEBUG_PERSIST=true

XFYUN_APP_ID=placeholder
XFYUN_API_KEY=placeholder
XFYUN_API_SECRET=placeholder

MINIMAX_API_KEY=placeholder
MINIMAX_T2A_MODEL=speech-2.6-turbo
MINIMAX_T2A_TIMEOUT_S=45
```

### AI 模型

```dotenv
DEEPSEEK_API_KEY=placeholder
ECNU_API_KEY=placeholder
SILICONFLOW_API_KEY=placeholder
MOONSHOT_API_KEY=placeholder
QWEN_API_KEY=placeholder
```

实际启用模型以 `ai/setting/llm.py` 为准。

---

## 数据库

执行迁移：

```bash
cd backend
alembic upgrade head
```

项目数据表：

| 表名 | 用途 |
|---|---|
| `users` | 邮箱用户 |
| `auth_sessions` | 登录会话 |
| `auth_email_challenges` | 注册和重置验证码 |
| `teachers` | 教师信息 |
| `lessons` | 课程和结构化教案 |
| `lesson_files` | 上传文件 |
| `sessions` | 课堂会话 |
| `transcripts` | 音频转写 |
| `session_turns` | 师生发言 |
| `session_segments` | 课堂片段和评价 |
| `session_students` | 虚拟学生类型和动态状态 |
| `session_visual_observations` | 教姿教态视觉窗口 |

---

## 启动项目

推荐启动顺序：数据库 → AI 服务 → 业务后端 → 前端。

### 1. 启动 AI 服务

```bash
cd ai
python main.py
```

健康检查：

```text
GET http://localhost:8001/health
```

### 2. 启动业务后端

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

- 健康检查：`http://localhost:8010/health`
- Swagger：`http://localhost:8010/docs`

### 3. 启动前端

```bash
cd frontend
npm run dev
```

访问：`http://localhost:5173`

---

## 系统主流程

### 1. 用户认证

前端调用 `/api/auth/*` 完成注册、登录、退出和密码重置。业务后端设置 HttpOnly Cookie，并将用户会话保存到数据库。

### 2. 课前配置

教师上传教案和 PPT，或进入自由模式。前端调用 AI 服务获得结构化课程内容，再通过 `/api/init_lesson` 创建课程和课堂会话。

### 3. 虚拟课堂

1. 前端调用讯飞签名接口并建立实时 ASR。
2. 完整教师发言发送到 `/api/inclass/utterance`。
3. 业务后端保存发言并调用 AI Supervisor。
4. 学生根据问题难度和课堂氛围举手。
5. 教师点名后调用 `/api/inclass/student-reply`。
6. 学生回复通过 MiniMax TTS 或浏览器语音播放。
7. PPT 翻页、时间窗口结束或停止录音时提交课堂片段。
8. 用户开启视觉功能后，前端按 15 秒窗口上传教姿观察数据。

### 4. 课后报告

报告接口汇总：

- 教案和教学偏好；
- 师生发言；
- 课堂片段评价；
- Supervisor 决策；
- 虚拟学生互动；
- 视觉教态结果。

### 5. 历史与能力画像

历史模块提供课堂筛选、报告查看、最近五节比较、配置复用和教师能力画像。

---

## 测试

### 业务后端

```bash
cd backend
python -m pytest app/tests
```

测试覆盖：

- 学生状态初始化；
- 举手策略；
- JWT 密钥校验；
- 数据查询性能回归；
- 讯飞签名安全。

### 前端

```bash
cd frontend
npm run build
```

### AI 服务

按照 `ai/测试.md` 中的 curl 命令测试：

- 教案解析；
- PPT 解析；
- 课堂片段评价；
- Supervisor 决策；
- 学生回复；
- 视觉分析；
- 课后报告。

---

## 接口变更流程

1. 在 `docs/api.md` 中确认前端可见合同。
2. AI 字段同步更新 `ai/docs/ai-backend-contract-v2.md`。
3. 同步修改业务后端路由、Schema、前端 API 和调用页面。
4. 完成接口测试。
5. 更新文档版本和里程碑。

Supervisor 相关改动同步检查：

- `frontend/src/views/ClassroomView.vue`
- `backend/app/schemas/inclass.py`
- `backend/app/api/routes/inclass.py`
- `backend/app/services/ai_client.py`
- `ai/main.py`
- `ai/agents/inclass_supervisor_agent.py`

视觉分析相关改动同步检查：

- `frontend/src/api/visual.js`
- `frontend/src/views/ClassroomView.vue`
- `backend/app/api/routes/visual.py`
- `backend/app/services/reporting.py`
- `ai/agents/inclass_visual_obs_llm.py`
- `frontend/src/views/ReportView.vue`

---

## 提交规范

- 功能代码提交到根目录的 `frontend/`、`backend/`、`ai/`。
- 项目文档提交到 `docs/`。
- 里程碑使用 Git tag 标记。
- 提交前检查 `git status`。
- `.env`、真实密钥、上传文件和构建产物不提交到 Git。
- 接口变更在提交信息中注明影响模块。

