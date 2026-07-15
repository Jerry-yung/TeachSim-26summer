# 开发规范与协作指南


---

## 仓库结构

```
TeachSim/
├── frontend/          ← 刘至晗 负责（Vue3 + Vite）
├── backend/           ← 王宏伟 负责（FastAPI + PostgreSQL）
├── ai/                ← 杨云天 负责（LangChain + Prompt）
└── docs/              ← 三人共同维护
    ├── api.md         ← 接口契约（改动需通知所有人）
    ├── architecture.md← 架构约束
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


