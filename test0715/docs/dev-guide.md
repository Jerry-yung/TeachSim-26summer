# 开发规范与协作指南


---

## 仓库结构

```
TeachSim/
└── test0715/
    ├── frontend/          ← 刘至晗 负责（Vue3 + Vite）
    ├── backend/           ← 唐一嘉 负责（FastAPI + PostgreSQL） 
    ├── ai/                ← 杨云天 负责（LangChain + Prompt）
    └── docs/              ← 周光轩主要负责，三人共同监督
        ├── api.md         ← 接口契约（改动需通知所有人）
        ├── design-principles.md ← 产品设计原则
        └── dev-guide.md   ← 开发规范与协作指南
```

**原则：只在自己负责的文件夹里提交代码。** 修改别人文件夹的内容前先在群里说明原因。

---



## 本地开发环境启动

### 前端（A）
```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

### 后端（C）
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# 访问 http://localhost:8000
```

### AI 模块（B）
```bash
cd ai
pip install -r requirements.txt
# 配置 .env 文件中的 API Key
python main.py
```

## 环境变量位置

- `backend/.env`：数据库、业务后端、火山 ASR 调试配置
- `test0715/.env`：AI 模型供应商 API Key，例如 `SILICONFLOW_API_KEY`
- `frontend/.env`：讯飞实时 ASR 配置
VITE_XFYUN_APP_ID=
VITE_XFYUN_API_KEY=
VITE_XFYUN_API_SECRET=
执行 `alembic upgrade head` 后会创建或更新以下主要表：

- lessons
- lesson_files
- sessions
- transcripts
- session_turns
- session_segments

`.env.example` 只能填写占位符，禁止写入真实数据库密码、Access Token 或 API Key。若密钥曾提交到 Git，应立即轮换并检查 Git 历史。

## 推荐启动顺序

1. 配置数据库和各模块 `.env`
2. 在 `backend/` 执行 `alembic upgrade head`
3. 启动 AI 服务（8001）
4. 启动业务后端（8000）
5. 启动前端（5173）

