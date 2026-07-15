"""AI 模块 FastAPI 服务入口

提供测试接口，支持独立运行验证功能。
与后端的对接接口在 backend 实现，通过 HTTP 调用本模块的函数。

环境变量：
    AI_SERVICE_URL: AI 服务地址（默认：http://localhost:8001）
    AI_PORT: 服务端口（默认：8001）
    AI_HOST: 服务主机（默认：0.0.0.0）
"""
import os
import sys
import time
from pathlib import Path
from typing import Optional, List

# 确保能导入本地模块
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 导入模块
from rag import LessonExtractor
from rag.parser import DocumentParser
from supervisor import Supervisor
from agents import StudentAgent

# ============ 配置 ============

# AI 服务配置
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")
AI_PORT = int(os.getenv("AI_PORT", "8001"))
AI_HOST = os.getenv("AI_HOST", "0.0.0.0")

# ============ 错误码规范 ============

ERROR_CODES = {
    # 文件解析错误 (4000-4099)
    "AI_PARSE_ERROR": {"code": "AI4000", "message": "文件解析失败"},
    "AI_UNSUPPORTED_FORMAT": {"code": "AI4001", "message": "不支持的文件格式"},
    "AI_FILE_TOO_LARGE": {"code": "AI4002", "message": "文件过大"},
    
    # LLM 调用错误 (5000-5099)
    "AI_LLM_ERROR": {"code": "AI5000", "message": "AI 服务调用失败"},
    "AI_LLM_TIMEOUT": {"code": "AI5001", "message": "AI 服务响应超时"},
    "AI_JSON_PARSE_ERROR": {"code": "AI5002", "message": "AI 响应格式错误"},
    
    # 业务逻辑错误 (6000-6099)
    "AI_INVALID_AGENT_TYPE": {"code": "AI6000", "message": "无效的 Agent 类型"},
    "AI_DECISION_ERROR": {"code": "AI6001", "message": "决策过程出错"},
}

def make_error_response(error_key: str, detail: str = None) -> dict:
    """生成标准错误响应"""
    error_info = ERROR_CODES.get(error_key, {"code": "AI9999", "message": "未知错误"})
    result = {
        "error_code": error_info["code"],
        "error_message": error_info["message"],
        "timestamp_ms": int(time.time() * 1000)
    }
    if detail:
        result["error_detail"] = detail
    return result

# ============ FastAPI 应用 ============

app = FastAPI(
    title="TeachSim AI 模块",
    description="教案解析、主控决策、学生 Agent 服务",
    version="0.1.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
extractor = LessonExtractor()
supervisor = Supervisor()
student_agent = StudentAgent()


# ============ 数据模型 ============

class SupervisorRequest(BaseModel):
    """主控决策请求"""
    teacher_text: str
    lesson_topic: Optional[str] = "未指定"
    subject: Optional[str] = "未指定"
    current_topic: Optional[str] = ""
    session_id: Optional[str] = None


class AgentRequest(BaseModel):
    """Agent 回复请求"""
    agent_type: str  # gangjing, xuekun, sleepy, whisper
    context: str
    subject: Optional[str] = "数学"


# ============ 健康检查 ============

@app.get("/")
def root():
    """服务状态"""
    return {
        "service": "TeachSim AI",
        "status": "running",
        "version": "0.1.0",
        "service_url": AI_SERVICE_URL
    }


@app.get("/health")
def health():
    """健康检查"""
    return {
        "status": "ok",
        "service_url": AI_SERVICE_URL,
        "timestamp_ms": int(time.time() * 1000)
    }


@app.get("/supported-formats")
def supported_formats():
    """获取支持的文件格式列表"""
    from rag.parser import DocumentParser
    return {
        "supported_extensions": DocumentParser.get_supported_extensions(),
        "notes": [
            ".pdf - PDF 文档",
            ".docx - Word 文档（推荐）",
            ".pptx - PowerPoint 演示文稿",
            ".xlsx/.xls - Excel 表格",
            ".txt/.md/.csv - 文本文件",
            ".html/.htm - 网页文件",
            ".rtf - 富文本格式",
            "旧版 .doc 和 .ppt 请转换为新版格式"
        ]
    }


@app.get("/error-codes")
def get_error_codes():
    """获取错误码规范"""
    return {
        "error_codes": ERROR_CODES,
        "description": "AI 模块错误码规范，供后端和前端参考"
    }


# ============ 教案解析接口 ============

async def _parse_single_file(file: UploadFile, grade: str = "", subject: str = "") -> dict:
    """解析单个文件"""
    content = await file.read()
    text = DocumentParser.parse(content, file.filename)
    result = extractor.extract(text)
    result["_file_info"] = {
        "filename": [file.filename],  # 统一为列表格式
        "size": len(content),
        "grade": str(grade) if grade else None,
        "subject": str(subject) if subject else None
    }
    return result


@app.post("/ai/parse_lesson")
async def parse_lesson(
    file: UploadFile = File(...),
    grade: Optional[str] = Form(""),
    subject: Optional[str] = Form("")
):
    """
    解析教案文件（支持单文件），提取知识点和预设问题
    
    - 支持 PDF、Word（.docx）、PPT（.pptx）、Excel、Markdown 等格式
    - 返回 JSON 格式的知识点大纲和预设问题
    """
    try:
        return await _parse_single_file(file, grade, subject)
    except ValueError as e:
        raise HTTPException(
            status_code=400, 
            detail=make_error_response("AI_UNSUPPORTED_FORMAT", str(e))
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=make_error_response("AI_PARSE_ERROR", str(e))
        )


@app.post("/ai/parse_lessons")
async def parse_lessons(
    files: List[UploadFile] = File(...),
    grade: Optional[str] = Form(""),
    subject: Optional[str] = Form("")
):
    """
    解析多个教案文件，合并内容后统一提取知识点
    
    - 支持同时上传多个文件
    - 将所有文件内容合并后一起解析
    - 返回统一的解析结果，filename 为文件列表
    """
    try:
        # 读取所有文件并合并内容
        combined_text_parts = []
        filenames = []
        total_size = 0
        
        for file in files:
            content = await file.read()
            text = DocumentParser.parse(content, file.filename)
            combined_text_parts.append(f"=== {file.filename} ===\n{text}\n")
            filenames.append(file.filename)
            total_size += len(content)
        
        # 合并所有文本
        combined_text = "\n".join(combined_text_parts)
        
        # 提取知识点（一次性处理合并后的内容）
        result = extractor.extract(combined_text)
        
        # 添加文件信息（filename 为列表）
        result["_file_info"] = {
            "filename": filenames,  # 列表格式
            "size": total_size,
            "grade": str(grade) if grade else None,
            "subject": str(subject) if subject else None
        }
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=400, 
            detail=make_error_response("AI_UNSUPPORTED_FORMAT", str(e))
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=make_error_response("AI_PARSE_ERROR", str(e))
        )


@app.post("/test/rag")
async def test_rag(
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None)
):
    """
    测试 RAG 功能（支持单文件或多文件）
    
    单文件用法：
        curl -X POST http://localhost:8001/test/rag \
          -F "file=@教案.pdf"
    
    多文件用法：
        curl -X POST http://localhost:8001/test/rag \
          -F "files=@教案1.pdf" \
          -F "files=@教案2.docx" \
          -F "files=@补充材料.md"
    
    返回格式统一为：
    {
        "basic_info": {...},
        "teaching_objectives": {...},
        "knowledge_points": [...],
        "preset_questions": [...],
        "_file_info": {
            "filename": ["file1.pdf", "file2.docx"],  // 列表格式
            "size": 12345
        }
    }
    """
    # 检查是否上传了文件
    if not file and (not files or len(files) == 0):
        raise HTTPException(
            status_code=400, 
            detail=make_error_response("AI_PARSE_ERROR", "请上传至少一个文件（使用 file 或 files 参数）")
        )
    
    # 如果上传了多个文件或同时上传了 file 和 files
    if files and len(files) > 0:
        all_files = ([file] if file else []) + list(files)
        return await parse_lessons(all_files)
    
    # 单文件处理
    return await parse_lesson(file)


# ============ Supervisor 模块接口 ============

@app.post("/ai/supervisor/decide")
def supervisor_decide(request: SupervisorRequest):
    """
    主控决策：根据教师发言决定下一步动作
    
    返回格式（符合 api.md 4.1）：
    {
        "session_id": "uuid-xxxx",
        "timestamp_ms": 5200,
        "evaluation_note": "教态良好，准确讲出勾股定理定义",
        "is_questioning": false,
        "error_detected": false,
        "trigger_agent": "gangjing",
        "agent_prompt": "老师刚讲完勾股定理，请用初二学生口吻质疑：如果不是直角三角形还成立吗？"
    }
    """
    try:
        result = supervisor.decide(
            teacher_text=request.teacher_text,
            lesson_topic=request.lesson_topic,
            subject=request.subject,
            current_topic=request.current_topic,
            session_id=request.session_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_response("AI_DECISION_ERROR", str(e))
        )


class TeacherTextRequest(BaseModel):
    teacher_text: str

@app.post("/test/supervisor")
def test_supervisor(request: TeacherTextRequest):
    """
    测试 Supervisor 功能（简化版）
    
    用法：
        curl -X POST http://localhost:8001/test/supervisor \
          -H "Content-Type: application/json" \
          -d '{"teacher_text": "同学们好，今天讲勾股定理"}'
    """
    try:
        result = supervisor.decide(
            teacher_text=request.teacher_text,
            lesson_topic="勾股定理",
            subject="初中数学"
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_response("AI_DECISION_ERROR", str(e))
        )


# ============ Agent 模块接口 ============

@app.post("/ai/agent/reply")
def agent_reply(request: AgentRequest):
    """
    生成学生 Agent 的回复
    
    返回格式（符合 api.md 4.2）：
    {
        "agent_type": "gangjing",
        "reply_text": "老师，那如果是锐角三角形呢？",
        "emotion": "curious"
    }
    
    emotion 可选值：curious(好奇), confused(听不懂), sleepy(困倦), active(积极), whispering(交头接耳)
    """
    if request.agent_type not in ["gangjing", "xuekun", "sleepy", "whisper"]:
        raise HTTPException(
            status_code=400,
            detail=make_error_response("AI_INVALID_AGENT_TYPE", f"无效的 agent_type: {request.agent_type}")
        )
    
    try:
        result = student_agent.generate_reply(
            agent_type=request.agent_type,
            context=request.context,
            subject=request.subject
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_response("AI_LLM_ERROR", str(e))
        )


@app.get("/test/agent/{agent_type}")
def test_agent(
    agent_type: str,
    context: str = "老师刚讲完勾股定理的定义"
):
    """
    测试 Agent 功能
    
    用法：
        curl http://localhost:8001/test/agent/gangjing?context=老师刚讲完勾股定理
    """
    if agent_type not in ["gangjing", "xuekun", "sleepy", "whisper"]:
        raise HTTPException(
            status_code=400,
            detail=make_error_response("AI_INVALID_AGENT_TYPE", f"无效的 agent_type: {agent_type}")
        )
    
    try:
        result = student_agent.generate_reply(agent_type, context, "数学")
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_response("AI_LLM_ERROR", str(e))
        )


# ============ 批量测试接口 ============

@app.post("/test/full_pipeline")
async def test_full_pipeline(
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    teacher_text: Optional[str] = Form("同学们，今天我们来学习勾股定理")
):
    """
    完整流程测试：上传教案 → 提取知识点 → 模拟教师发言 → Supervisor 决策 → Agent 回复
    
    支持单文件或多文件上传
    
    单文件：
        curl -X POST http://localhost:8001/test/full_pipeline \
          -F "file=@教案.pdf" \
          -F "teacher_text=同学们好"
    
    多文件：
        curl -X POST http://localhost:8001/test/full_pipeline \
          -F "files=@教案1.pdf" \
          -F "files=@教案2.docx" \
          -F "teacher_text=同学们好"
    """
    try:
        # 解析教案（单文件或多文件，统一格式）
        if files and len(files) > 0:
            all_files = ([file] if file else []) + list(files)
            lesson_info = await parse_lessons(all_files)
        else:
            lesson_info = await parse_lesson(file)
        
        # Supervisor 决策
        supervisor_result = supervisor.decide(
            teacher_text=teacher_text,
            lesson_topic=lesson_info.get("basic_info", {}).get("lesson_topic", "未命名课程"),
            subject=lesson_info.get("basic_info", {}).get("subject", "未识别学科"),
            current_topic=lesson_info.get("knowledge_points", [{}])[0].get("point", "")
        )
        
        # 如果需要 Agent 回复
        agent_result = None
        if supervisor_result.get("trigger_agent"):
            agent_result = student_agent.generate_reply(
                agent_type=supervisor_result["trigger_agent"],
                context=supervisor_result.get("agent_prompt", "请回应老师"),
                subject=lesson_info.get("basic_info", {}).get("subject", "数学")
            )
        
        return {
            "lesson_info": lesson_info,
            "supervisor_decision": supervisor_result,
            "agent_reply": agent_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_response("AI_LLM_ERROR", str(e))
        )


# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                   TeachSim AI 模块已启动                      ║
╠══════════════════════════════════════════════════════════════╣
║  服务地址: {AI_SERVICE_URL:<48} ║
║  监听端口: {AI_HOST}:{AI_PORT:<37} ║
╠══════════════════════════════════════════════════════════════╣
║  测试接口:                                                    ║
║  - POST /test/rag          测试教案解析（支持多文件）        ║
║  - POST /test/supervisor   测试主控决策                      ║
║  - GET  /test/agent/{{type}} 测试学生 Agent                   ║
╠══════════════════════════════════════════════════════════════╣
║  错误码规范: GET /error-codes                                ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(app, host=AI_HOST, port=AI_PORT)
