# 开发规范与协作指南（修订建议稿）

---

## 仓库结构

```text
TeachSim-26summer/
├── frontend/       ← 刘至晗 负责（Vue 3 + Vite + Pinia）
├── backend/        ← 唐一嘉 负责（FastAPI + SQLAlchemy + PostgreSQL）
├── ai/             ← 杨云天 负责（FastAPI + LangChain + Prompt）
└── docs/           ← 周光轩主要负责，三人共同监督

```

**原则：只在自己负责的文件夹里提交代码。** 修改别人负责目录的内容前先说明原因；接口变更必须同时通知调用方和文档负责人。

---

## 环境要求

- Node.js：建议使用当前 Vite 5 支持的 LTS 版本
- Python：3.11+
- PostgreSQL：可使用 Supabase 托管实例
- 前端端口：5173
- AI 服务端口：8001
- 业务后端端口：必须在 8000 和 8010 中统一，见下文

---

## 首次安装

### 前端（A）

```bash
cd frontend
npm install
```

### 业务后端（C）

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### AI 模块（B）

```bash
cd ai
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 环境变量

### 仓库根目录 `.env`

`ai/setting/llm.py` 明确从仓库根目录 `.env` 读取模型供应商密钥，例如：

```dotenv
DEEPSEEK_API_KEY=your_key_here
ECNU_API_KEY=your_key_here
SILICONFLOW_API_KEY=your_key_here
MOONSHOT_API_KEY=your_key_here
```

当前默认文本模型和报告模型使用 DeepSeek，多模态 PPT 图像分析使用 Moonshot 配置。实际启用的模型以 `ai/setting/llm.py` 中的统一入口为准。

### `backend/.env`

业务后端读取数据库、上传目录、AI 服务地址、CORS 和火山 ASR 调试配置。可从 `backend/.env.example` 复制后填写。

**安全要求：** `.env.example` 只能包含占位符。当前仓库示例文件中存在看起来可用的凭据，应立即轮换并清理 Git 历史；任何文档、Issue、聊天记录和截图中都不要再次复制这些值。

### 前端代理与浏览器能力

前端配置从仓库根目录读取 Vite 环境变量：

```dotenv
VITE_BACKEND_PROXY_TARGET=http://127.0.0.1:8000
VITE_AI_PROXY_TARGET=http://127.0.0.1:8001
```

当前 `vite.config.js` 的业务后端默认值是 8010，而业务后端文档默认用 8000。推荐显式设置 `VITE_BACKEND_PROXY_TARGET`，避免依赖不一致的默认值。

讯飞 ASR 当前前端通过业务后端 `/api/asr/xfyun/sign` 获取签名；MiniMax TTS 通过 `/api/tts/minimax/synthesize`。这两个路由当前未出现在 `backend/app`，联调前需合并或实现。

---

## 数据库迁移

```bash
cd backend
alembic upgrade head
```

当前两次迁移创建或扩展以下 6 张主要表：

- `lessons`
- `lesson_files`
- `sessions`
- `transcripts`
- `session_turns`
- `session_segments`

迁移文件中的 `revision` 标识与文件名日期不同，排查迁移链时应以文件内 `revision/down_revision` 为准。

---

## 本地启动

推荐顺序：数据库迁移 → AI 服务 → 业务后端 → 前端。

### 1. AI 服务（8001）

```bash
cd ai
python main.py
```

健康检查：`GET http://localhost:8001/health`

### 2. 业务后端

若前端显式代理到 8000：

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

若保持前端当前默认代理，则把端口改为 8010。不要使用 `uvicorn main:app`，因为应用入口位于 `backend/app/main.py`。

健康检查：`GET http://localhost:8000/health`（端口按实际配置）
Swagger：`http://localhost:8000/docs`

### 3. 前端（5173）

```bash
cd frontend
npm run dev
```

访问：`http://localhost:5173`

---

## 当前联调边界

业务后端当前已有：课程初始化、课程状态、课堂发言、学生静态状态、课堂片段评价、课后报告、调试 ASR。

当前前端还依赖但业务后端缺失：

- Cookie 登录注册和密码重置；
- PPT 预览和 PDF 下载；
- 会话重启；
- 学生实时回复转发；
- 历史课堂、最近五次对比、最新预设、能力画像；
- 讯飞 ASR 签名；
- MiniMax TTS。

在这些路由补齐前，不能把“登录到历史画像的完整主链路”标记为仓库现状。若相关代码位于其他分支，应先合并再更新文档。

---

## 接口变更流程

1. 在 `docs/api.md` 提议并确认前端可见合同。
2. 若涉及 AI，先更新 `ai/docs/ai-backend-contract-v2.md`。
3. 同步修改业务后端路由/Pydantic 模型、前端 `src/api/` 和调用页面。
4. 至少完成一次成功请求、一次参数错误和一次下游服务失败测试。
5. 更新接口状态和代码基线日期。

Supervisor 联调尤其要同时核对：

- 前端提交到业务后端的字段；
- 业务后端转发到 AI 的字段；
- `ai/main.py` 中 `SupervisorV2Request` 实际读取的字段；
- `ai/docs/ai-backend-contract-v2.md` 的字段说明。

当前已知差异是业务后端发送 `current_timestamp`、`called_student_id`，AI v2 读取 `class_elapsed_sec`、`called_student_status_digest`。

---

## 提交与里程碑

- 后续功能只提交到根目录的 `frontend/`、`backend/`、`ai/`、`docs/`。
- 不再新增 `testxxxx/` 目录。
- 里程碑使用 Git tag，例如 `week-0715`、`week-0719`、`week-0719-ai`。
- 提交前检查 `git status`，不要提交 `.env`、上传文件、构建产物或真实凭据。

---
