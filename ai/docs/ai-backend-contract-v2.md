# AI 与后端对接规范（v2）

本文档定义 TeachSim `ai` 模块 v2 的数据契约。v2 为破坏性版本，不保证兼容 v1。

## 1. 通用约定

- 编码：UTF-8
- 时间戳：统一使用 ISO8601（含时区），示例 `2026-04-16T08:05:10+08:00`
- 请求追踪：后端应传 `trace_id`；AI 原样回传
- 幂等键：涉及文件解析任务时，后端应传 `idempotency_key`

## 2. 课前契约

## 2.1 教案结构化

- 输入（后端 -> AI）：
  - `lesson_text`（string, required）
  - `metadata`（object, optional）
- 输出（AI -> 后端）：
  - `basic_info`（required）
  - `teaching_objectives`（required）
  - `knowledge_points`（required）

### 2.1.1 后端入库前增强字段（必做）

`LessonExtractor` 输出写入后端数据库前，后端需在同一份教案 JSON 中追加前端开课前问卷结果（用于后续个性化分析与报告定向）。

- `teaching_preferences.duration`（number|string，required）：上课时长（分钟）
- `teaching_preferences.grade`（string，required）：学生年级
- `teaching_preferences.class_type`（string，required）：班级类型，取值 `重点班` | `普通班` | `平行班`
- `teaching_preferences.primary_goal`（string，required）：教学目标，取值 `知识理解与记忆` | `技能掌握与方法运用` | `思维拓展与探究讨论` | `情感体验与价值建构`
- `teaching_preferences.breakthrough_focus`（string，required）：突破方向，取值 `课堂节奏把控` | `知识点衔接流畅度` | `提问质量与互动引导` | `语言表达与亲和力` | `时间分配合理性`

说明：
- 上述字段直接传自然语言字符串值（如 `"普通班"`、`"提问质量与互动引导"`），无需编码映射。
- 该增强字段由后端维护，AI 不负责回填问卷答案。

## 2.2 PPT 结构化（PPT_LLM）

- 输入（后端 -> AI）：
  - `filename`（string, required）
  - `slides_text`（array, required）
- 输出（AI -> 后端）：
  - `deck_info`（required）
  - `slides[]`（required）
    - `slide_no`（int）
    - `title`（string）
    - `text_blocks[]`（string）
    - `visual_elements[]`（string）
    - `summary`（string）

## 3. 课中契约

## 3.1 段落评价

- 输入（后端 -> AI）：
  - `segment_id`（string, required）
  - `start_ts` / `end_ts`（string, required）
  - `slide_no`（int, required）
  - `teacher_utterances[]`（required）
  - `student_utterances[]`（required）
  - `ppt_context`（object, optional）
- 输出（AI -> 后端）：
  - `scores`（required）
    - `instructional_clarity`（0-100）
    - `student_engagement`（0-100）
    - `pace_control`（0-100）
  - `strengths[]`（required）
  - `issues[]`（required）
  - `improvement_actions[]`（required）

## 3.2 主控触发（SupervisorAgent）

- 输入（后端 -> AI）：
  - `teacher_text`（string, required）：教师**本轮**发言。
  - `current_timestamp`（string, optional 但**强烈建议必传**）：ISO8601（含时区），表示教师说出**本轮** `teacher_text` 的时刻，便于落库。
  - `subject`（string, optional）：学科（如"初中数学"、"高中物理"）。
  - `chat_history`（array, optional）：对话历史，包含教师和学生发言，用于推断上下文。每项结构：
    - `role`（string）：`"teacher"` | `"student"`
    - `content`（string）：发言内容
  - `current_ppt`（array, optional）：**仅传当前页一条**；结构与 **2.2 PPT 结构化** 输出中 `slides[]` **单条**一致。字段：`slide_no`（int）、`title`（string）、`text_blocks`（string[]）、`visual_elements`（string[]）、`summary`（string）。
  - `called_student_status_digest`（object | string | null, optional）：被点名学生状态摘要；无摘要时传 JSON `null`。与「提问类」组合时：`null` → `questioning`，非 `null` → `relay_answer`（二者语义依据相同，仅由此字段区分）。
  - **不要**传入 `dialog_state`：由 `SupervisorAgent` 内部用 LLM 推断（失败时规则回退），再据此决定是否调用 `StudentAgent`。

- 输出（AI -> 后端）：
  - `dialog_state`（string）：推断结果，取值 `normal` | `questioning` | `relay_answer` | `ambiguous` | `misstatement` | `discipline_whisper` | `discipline_sleep`
  - `should_trigger_student`（bool）
  - `trigger_reason`（string）
  - `target_student_type`（string|null）
  - `student_event`（object | object[] | null）
    - 当 `dialog_state = questioning` 时，返回长度为 6 的数组，顺序为：学优主动、学优非主动、杠精主动、杠精非主动、学困主动、学困非主动。
    - 当 `dialog_state = relay_answer` 时，返回长度为 1 的数组：仅包含 `called_student_status_digest.student_type` 对应角色的一条候选，`is_triggered=false`，`is_proactive_speaking=true`（单条对象字段结构与 questioning 中每一项相同）。
    - 当 `dialog_state = ambiguous` 或 `misstatement` 时，返回单个对象。
    - 每个事件对象都包含：
      - `student_type`（string）
      - `emotion`（string）
      - `reply_text`（string）
      - `is_triggered`（bool）：`ambiguous/misstatement` 为 `true`（即让前端自动触发让学生说话）；`questioning/relay_answer` 为 `false`（只有当老师在前端点击相应的学生后，才变为`true`，学生开始回答问题）。
      - `is_proactive_speaking`（bool）：是否主动发言。`questioning` 同时覆盖 `true/false`；`relay_answer` 固定为 `true`；`ambiguous/misstatement` 固定为 `true`。

说明：`student_event` 由 `SupervisorAgent` 在需要时内部调用 `StudentAgent` 生成；`should_trigger_student` 等与 `dialog_state` 的映射由 AI 侧固定规则保证一致。

## 4. 课后契约

- 输入（后端 -> AI）：
  - `lesson_json`（object, required）
  - `segment_evals[]`（array, required）
- 输出（AI -> 后端）：
  - `lesson_topic`（string）
  - `overall_score`（int）
  - `dimension_scores`（object）
  - `summary`（string）
  - `priority_improvements[]`（array）

## 5. 错误响应规范

统一错误体：

```json
{
  "error_code": "AI5000",
  "error_message": "internal llm error",
  "error_detail": "optional detail",
  "trace_id": "from-backend-or-ai",
  "timestamp": "2026-04-16T08:10:00+08:00"
}
```

建议错误码：

- `AI4001`：参数缺失/格式错误
- `AI4002`：不支持的文件或字段
- `AI5000`：LLM 调用失败
- `AI5001`：LLM 超时
- `AI5002`：模型输出结构不合法

## 6. 超时与重试建议

- 教案/PPT 解析：后端超时建议 `180s`
- 课中决策与段落评价：后端超时建议 `30s`
- 重试策略：仅对 `AI5001` 做指数退避重试（最多 2 次）

## 7. 版本策略

- 响应中建议携带 `contract_version: "v2"`
- 任何字段删除或语义变化都应升级版本号（v3+）

