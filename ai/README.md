# ai 负责人：杨云天

## 主要内容

- 课前解析：教案结构化提取（`rag/extractor.py`）与 PPT 解析（`agents/preclass_ppt_llm.py`）。
- 课中评估：单段课堂评价（`agents/inclass_segment_eval_llm.py`）与主控决策（`agents/inclass_supervisor_agent.py`）。
- 课中互动：按主控决策触发学生话术生成（`agents/inclass_student_agent.py`）。
- 课后总结：汇总多段评价生成课后报告（`agents/postclass_report_llm.py`）。
- 服务入口：FastAPI 路由与请求模型统一在 `main.py`。

## 相关文档（包含测试）

- [测试手册（curl 命令）](./测试.md)
- [后端字段契约](./docs/ai-backend-contract-v2.md)

## 架构总览

- 课前
  - 教案解析链路：上传文件 -> `DocumentParser` 转纯文本 -> `LessonExtractor` 组装提示词并调用 `llm` 做结构化提取 -> 输出教案 JSON。
  - PPT 解析链路：上传 pptx -> `rag/parser.py` 提取每页文本/图片上下文 -> `PreclassPptLLM` 生成 PPT 解析 json。
- 课中
  - `InclassSegmentEvalLLM`：输入单个课堂片段（时间戳、师生发言、当前 PPT 页内容、当前页上下文），输出该片段的评分、优点、问题、改进建议。
  - `InclassSupervisorAgent`：输入 `teacher_text`、`teacher_text_ts`、`background`，先推断 `dialog_state`（正常、提问、模糊、讲错），再决定是否调用学生角色。
  - `InclassStudentAgent`：由 `InclassSupervisorAgent` 内部调用并生成学生事件。`questioning` 返回六条（学优主动/非主动、杠精主动/非主动、学困主动/非主动）；`relay_answer` 返回一条（`called_student_status_digest.student_type`，主动）；`ambiguous/misstatement` 返回一条（主动）；事件中包含 `is_triggered` 与 `is_proactive_speaking` 字段。
- 课后
  - `PostclassReportLLM`：汇总课前结构化结果 + 多段课堂评价，输出课后总评、维度分数与优先改进项。

## 快速开始

1. 安装依赖（与后端共用仓库根目录 `.venv`，见主 `README.md`）

```bash
# 已在仓库根目录激活 .venv 后：
pip install -r ai/requirements.txt
```

2. 配置密钥（在项目根目录 `cp .env.example .env`，填写各供应商 API Key；勿提交 `.env`）

3. 启动服务

```bash
cd ai
python main.py
```

4. 按测试手册联调

直接使用 [测试.md](./测试.md) 中的 curl 命令，不使用 Python 测试脚本。

## 目录结构

```text
ai/
├── main.py                            # FastAPI 入口，定义 v2 路由与请求模型
├── requirements.txt                   # Python 依赖
├── README.md                          # 本说明文档
├── 测试.md                             # curl 联调手册（推荐从这里执行）
│
├── setting/
│   └── llm.py                         # 模型与供应商配置（llm/vlm 统一入口）
│
├── rag/
│   ├── __init__.py                    # rag 模块导出
│   ├── parser.py                      # 多格式文件解析（pdf/docx/pptx 等）
│   └── extractor.py                   # 教案结构化提取提示词与解析逻辑
│
├── agents/
│   ├── __init__.py                    # agents 模块导出
│   ├── llm_utils.py                   # 通用 LLM 调用/JSON 提取工具
│   ├── preclass_ppt_llm.py            # PPT 页级结构生成
│   ├── inclass_segment_eval_llm.py    # 课堂片段评价
│   ├── inclass_supervisor_agent.py    # 主控状态推断与触发决策
│   ├── inclass_student_agent.py       # 学生角色话术生成
│   ├── postclass_report_llm.py        # 课后报告生成
│   └── student_agents.py              # 兼容的学生 Agent 实现
│
├── tests/
│   └── samples/                       # curl 请求体样例 JSON
│       ├── segment_eval_body.json
│       ├── supervisor_v2_decide_misstatement_body.json
│       └── report_generate_body.json
│
├── docs/
│   └── ai-backend-contract-v2.md      # 当前后端契约（推荐）
│
└── 教案/                               # 本地联调用样例教案文件
```

