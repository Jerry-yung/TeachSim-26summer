# backend

后端项目目录 —— 负责人：唐一嘉

## 技术栈
- Python + FastAPI
- PostgreSQL + pgvector
- 阿里/百度 ASR & TTS API

## 包含模块
- 用户认证与管理
- 课程初始化接口（/api/init_lesson）
- 课堂实时 WebSocket 服务
- ASR 语音转文字 + TTS 文字转语音
- 报告生成与数据统计
- 弱点标签与历史记忆机制

## 启动方式
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
