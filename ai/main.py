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
from typing import Optional, List, Dict, Any

# 确保能导入本地模块
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 导入模块
from rag import LessonExtractor
from rag.parser import DocumentParser
from agents import (
    PreclassPptLLM,
    InclassSegmentEvalLLM,
    InclassSupervisorAgent,
    InclassStudentAgent,
    PostclassReportLLM,
)

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
student_agent = InclassStudentAgent()
preclass_ppt_llm = PreclassPptLLM()
segment_eval_llm = InclassSegmentEvalLLM()
inclass_supervisor_v2 = InclassSupervisorAgent()
postclass_report_llm = PostclassReportLLM()


# ============ 数据模型 ============


class ChatMessage(BaseModel):
    """对话历史消息"""
    role: str  # "teacher" | "student" | "system" 等
    content: str


class AgentRequest(BaseModel):
    """Agent 回复请求"""
    agent_type: str  # gangjing, xuekun, sleepy, whisper
    context: str
    subject: Optional[str] = "数学"
    chat_history: Optional[List[ChatMessage]] = None  # 可选：提供对话上下文


class SupervisorV2Request(BaseModel):
    """v2 主控：师生交互请求体；dialog_state 由 Supervisor 内部推断并随响应返回。

    字段说明：
    - teacher_text: 教师本轮发言内容（必填）
    - current_timestamp: 当前时间戳（ISO8601，可选但建议必传）
    - subject: 学科（如"初中数学"，可选）
    - chat_history: 对话历史（可选），包含教师和学生发言
    - current_ppt: 当前 PPT 页内容（可选），结构与 PPT 结构化输出的 slides[] 单条一致
    - called_student_status_digest: 被点名学生状态摘要（可选）；JSON null 表示无（空），与「提问类」
      组合为 questioning；非 null 时为 relay_answer（与 questioning 语义依据相同，仅由此字段区分）
    """
    teacher_text: str
    current_timestamp: Optional[str] = None  # ISO8601，表示当前时刻
    subject: Optional[str] = None  # 学科
    chat_history: Optional[List[ChatMessage]] = None  # 对话历史
    current_ppt: Optional[List[Dict[str, Any]]] = None  # 当前 PPT 页（仅一条）
    called_student_status_digest: Optional[Any] = None  # null → questioning；非 null → relay_answer


class ReportGenerateRequest(BaseModel):
    lesson_json: Dict[str, Any]
    segment_evals: List[Dict[str, Any]]


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


# ============ v2 联调接口（与 `测试.md` 中 curl 一致） ============


@app.post("/ai/v2/preclass/lesson/parse")
async def v2_preclass_lesson_parse(
    file: UploadFile = File(...),
    grade: Optional[str] = Form(""),
    subject: Optional[str] = Form(""),
):
    """教案上传解析，等价于 `/ai/parse_lesson`，供联调手册固定路径使用。"""
    try:
        return await _parse_single_file(file, grade, subject)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=make_error_response("AI_UNSUPPORTED_FORMAT", str(e)),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_response("AI_PARSE_ERROR", str(e)),
        )


@app.post("/ai/v2/preclass/ppt/parse")
async def v2_preclass_ppt_parse(file: UploadFile = File(...)):
    """上传 pptx，返回 deck_info + slides（每页内容）。"""
    try:
        content = await file.read()
        slides_text = DocumentParser.parse_pptx_slides(content)
        name = file.filename or "upload.pptx"
        return preclass_ppt_llm.run(filename=name, slides_text=slides_text)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=make_error_response("AI_UNSUPPORTED_FORMAT", str(e)),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_response("AI_PARSE_ERROR", str(e)),
        )


@app.post("/ai/v2/inclass/segment/eval")
def v2_inclass_segment_eval(body: Dict[str, Any] = Body(...)):
    """段落评价（LLM2）。"""
    try:
        return segment_eval_llm.run(body)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_response("AI_LLM_ERROR", str(e)),
        )


@app.post("/ai/v2/inclass/supervisor/decide")
def v2_inclass_supervisor_decide(req: SupervisorV2Request):
    """主控 + 直连 student agent（v2）。

    支持两种调用方式：
    1. 新格式：teacher_text + current_timestamp + subject + chat_history + current_ppt
       + called_student_status_digest
    2. 旧格式兼容：通过 background 字段（已废弃，向后兼容）
    """
    try:
        # 将新格式转换为内部 background 格式
        background = {}

        # 学科
        if req.subject:
            background["subject"] = req.subject

        # 当前 PPT 页（取第一条，如果有的话）
        if req.current_ppt and len(req.current_ppt) > 0:
            ppt_slide = req.current_ppt[0]
            background["slide_no"] = ppt_slide.get("slide_no")
            background["slides"] = [ppt_slide]

        # 对话历史：转换为 teacher_utterances_on_slide 格式（仅取 teacher 角色）
        # 同时保留 student_utterances_on_slide（取 student 角色）用于接力回答
        teacher_utterances = []
        student_utterances = []
        if req.chat_history:
            for msg in req.chat_history:
                if msg.role == "teacher":
                    teacher_utterances.append({"ts": req.current_timestamp or "", "text": msg.content})
                elif msg.role == "student":
                    student_utterances.append({"ts": req.current_timestamp or "", "text": msg.content, "student_id": ""})

        if teacher_utterances:
            background["teacher_utterances_on_slide"] = teacher_utterances
        if student_utterances:
            background["student_utterances_on_slide"] = student_utterances

        # questioning / relay_answer 的唯一区分：digest 是否为 null（见 Supervisor 内逻辑）
        background["called_student_status_digest"] = req.called_student_status_digest

        return inclass_supervisor_v2.decide(
            teacher_text=req.teacher_text,
            teacher_text_ts=req.current_timestamp,
            background=background,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_response("AI_DECISION_ERROR", str(e)),
        )


@app.post("/ai/v2/postclass/report/generate")
def v2_postclass_report_generate(body: ReportGenerateRequest):
    """课后报告（LLM3）。"""
    try:
        return postclass_report_llm.run(
            lesson_json=body.lesson_json,
            segment_evals=body.segment_evals,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=make_error_response("AI_LLM_ERROR", str(e)),
        )


# ============ Agent 模块接口 ============

@app.post("/ai/agent/reply")
def agent_reply(request: AgentRequest):
    """
    生成学生 Agent 的回复
    
    支持多轮对话场景：
    - 正常回答：被老师点名后正常作答
    - 未准备被点名：懵逼、答不上来
    - 被发现违纪：慌张解释
    - 接力回答：第二个被点名时接上前面的讨论
    
    返回格式（符合 api.md 4.2）：
    {
        "agent_type": "gangjing",
        "reply_text": "老师，那如果是锐角三角形呢？",
        "emotion": "curious"
    }
    
    emotion 可选值：
    - curious(好奇/质疑): 学优生主动提问
    - confused(听不懂): 学困生困惑
    - sleepy(困倦): 打瞌睡状态
    - active(积极): 积极回应
    - whispering(交头接耳): 私下讨论
    - hesitant(犹豫/怯懦): 学困生紧张
    - panicked(慌张): 被发现违纪
    - embarrassed(尴尬/羞愧): 违纪后被批评
    - idle(无反应): 不触发
    """
    if request.agent_type not in ["gangjing", "xuekun", "sleepy", "whisper"]:
        raise HTTPException(
            status_code=400,
            detail=make_error_response("AI_INVALID_AGENT_TYPE", f"无效的 agent_type: {request.agent_type}")
        )
    
    try:
        # 构建带对话历史的 context
        context = request.context
        if request.chat_history:
            history_str = "\n".join([
                f"{msg.role}: {msg.content}"
                for msg in request.chat_history[-5:]  # 取最近5轮
            ])
            context = f"对话历史：\n{history_str}\n\n当前情境：{context}"
        
        # 使用新的 InclassStudentAgent 接口
        result = student_agent.reply(
            student_type=request.agent_type,
            trigger_reason="test",
            background={
                "subject": request.subject,
                "context": context,
            },
            is_triggered=False,
            is_proactive_speaking=True,
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
    context: str = "老师刚讲完勾股定理的定义",
    subject: str = "数学"
):
    r"""
    测试 Agent 功能

    用法：
        curl http://localhost:8001/test/agent/gangjing?context=老师刚讲完勾股定理\&subject=数学
    """
    if agent_type not in ["gangjing", "xuekun", "sleepy", "whisper"]:
        raise HTTPException(
            status_code=400,
            detail=make_error_response("AI_INVALID_AGENT_TYPE", f"无效的 agent_type: {agent_type}")
        )

    try:
        # 使用新的 InclassStudentAgent 接口
        result = student_agent.reply(
            student_type=agent_type,
            trigger_reason="test",
            background={
                "subject": subject,
                "context": context,
            },
            is_triggered=False,
            is_proactive_speaking=True,
        )
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
        
        # v2 Supervisor 决策（内部推断 dialog_state）
        supervisor_result = inclass_supervisor_v2.decide(
            teacher_text=teacher_text,
            teacher_text_ts=None,
            background={
                "subject": lesson_info.get("basic_info", {}).get("subject", "未识别学科"),
                "slide_no": None,
                "slides": [],
                "teacher_utterances_on_slide": [],
            },
        )
        
        # 如果需要 Agent 回复
        agent_result = None
        if supervisor_result.get("student_event"):
            agent_result = supervisor_result.get("student_event")
        
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
║  - GET  /test/agent/{{type}} 测试学生 Agent                   ║
╠══════════════════════════════════════════════════════════════╣
║  错误码规范: GET /error-codes                                ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(app, host=AI_HOST, port=AI_PORT)
