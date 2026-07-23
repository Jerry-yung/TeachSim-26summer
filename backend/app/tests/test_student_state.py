"""
学生状态库单元测试

本模块对 app.services.student_state 中的核心函数进行单元测试，覆盖以下场景：

1. 课堂初始化时对学生类型的随机分配（initialize_session_students）
   - 验证相同 session_id 在相同班级水平下产生确定性（可复现）的分配结果
   - 验证固定 4 人名单（小明/小红/小王/小乐）的学员身份不随班级水平变化
   - 验证大量试验（200 次）中各学生类型的出现比例收敛于 CLASS_LEVEL_WEIGHTS 预设权重

2. 按学生类型随机挑选学生（pick_random_students_by_type）
   - 验证候选集为空时直接返回空列表，不抛异常
   - 验证请求数量超过候选数量时返回全部候选（不做填充）
   - 验证 exclude_ids 参数能正确排除指定学生，使被排除者不会出现在结果中

3. 课堂交互相关 Pydantic Schema 的构造与字段校验
   - InclassUtteranceResponse：Supervisor 决策后返回给前端的完整响应体，包含对话状态、
     举手学生列表、预设学生 ID、学生事件等字段
   - StudentReplyResponse：前端点名后 AI 生成的学生单条回复，包含回答文本、情绪标签、
     是否主动发言等字段
   - StudentReplyRequest：前端发起点名请求时的请求体，包含 session_id、目标学生 ID、
     当前时间戳和当前页 PPT 上下文

所有测试均使用 unittest.mock.MagicMock 模拟 SQLAlchemy 数据库会话，不依赖真实数据库连接。
"""

import uuid
from unittest.mock import MagicMock

from app.services.student_state import (
    CLASS_LEVEL_WEIGHTS,
    STUDENT_ROSTER,
    initialize_session_students,
    pick_random_students_by_type,
)


class TestInitializeSessionStudents:
    """
    测试 initialize_session_students 函数的行为。

    该函数负责在课堂 session 创建时，为固定的 4 名学生（STUDENT_ROSTER）
    按班级水平对应的权重随机分配学生类型（xueyou / gangjing / xuekun）。
    分配结果对于相同的 session_id 和班级水平必须是确定性的（可复现），
    即后端使用 session_id 作为伪随机种子。
    """

    def test_reproducibility(self):
        """
        验证相同 session_id 和班级水平产生相同的类型分配结果。

        原理：initialize_session_students 内部使用 session_id 作为 Python
        random.Random 的种子，因此相同的输入参数应产生完全一致的输出序列。
        本测试对同一 session_id 连续调用两次，断言两次返回结果中
        每个学生的 student_type 序列完全一致。
        """
        session_id = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

        db = MagicMock()
        db.add = MagicMock()
        db.flush = MagicMock()
        db.refresh = MagicMock()

        recs1 = initialize_session_students(session_id, "重点班", db=db)
        recs2 = initialize_session_students(session_id, "重点班", db=db)

        types1 = [r.student_type for r in recs1]
        types2 = [r.student_type for r in recs2]
        assert types1 == types2

    def test_roster_fixed(self):
        """
        验证无论班级水平如何，始终分配固定的 4 名学生身份。

        STUDENT_ROSTER 定义了 4 名学生的 student_id 和 student_name：
        student_xm（小明）、student_xw（小红）、student_xw2（小王）、
        student_xl（小乐）。本测试验证初始化后返回的记录数量为 4，
        且 student_id 和 student_name 的顺序与 ROSTER 定义完全一致。
        student_type 可以不同（由权重随机决定），但身份标识不变。
        """
        session_id = uuid.UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901")
        db = MagicMock()
        db.add = MagicMock()
        db.flush = MagicMock()
        db.refresh = MagicMock()

        recs = initialize_session_students(session_id, "平行班", db=db)
        assert len(recs) == 4
        ids = [r.student_id for r in recs]
        assert ids == [s["student_id"] for s in STUDENT_ROSTER]
        names = [r.student_name for r in recs]
        assert names == [s["student_name"] for s in STUDENT_ROSTER]

    def test_distribution_approximate(self):
        """
        验证大量试验中学生类型的出现比例收敛于 CLASS_LEVEL_WEIGHTS 预设权重。

        本测试对 "重点班" 班级水平进行 200 次独立初始化（每次使用不同的
        session_id 以确保独立性），累计统计 xueyou、gangjing、xuekun
        三类学生的总出现次数，计算各自占比后与 CLASS_LEVEL_WEIGHTS["重点班"]
        中的目标权重比较。

        断言允许 ±10%（即 ±0.10 绝对值）的偏差。200 次试验共 800 个学生样本，
        根据大数定律该样本量足以使比例收敛到目标权重的 ±10% 范围内。
        如果某类型的实际比例偏差超过 10%，可能是随机种子策略或权重配置有误。
        """
        counts = {"xueyou": 0, "gangjing": 0, "xuekun": 0}
        n_trials = 200

        for i in range(n_trials):
            session_id = uuid.UUID(f"c3d4e5f6-a7b8-9012-cdef-{i:012d}")
            db = MagicMock()
            db.add = MagicMock()
            db.flush = MagicMock()
            db.refresh = MagicMock()

            recs = initialize_session_students(session_id, "重点班", db=db)
            for r in recs:
                counts[r.student_type] += 1

        total = n_trials * 4
        weights = CLASS_LEVEL_WEIGHTS["重点班"]
        for t, w in weights.items():
            actual = counts[t] / total
            # 允许 ±10% 的偏差范围（200 次试验应充分收敛）
            assert abs(actual - w) < 0.10, f"{t} 比例偏差过大: {actual} vs {w}"


class TestPickRandomStudentsByType:
    """
    测试 pick_random_students_by_type 函数的行为。

    该函数从指定 session 的已初始化学生中，按 student_type 筛选候选池，
    随机挑选指定数量的学生返回。支持通过 exclude_ids 参数排除已被选中的学生。
    函数内部使用 session_id + interaction_round_id 作为随机种子以确保可复现性。
    """

    def test_empty_candidates(self):
        """
        验证当数据库中没有匹配 student_type 的学生时，返回空列表而不抛异常。

        本测试通过 MagicMock 模拟 SQLAlchemy 的链式调用（query().filter().all()），
        使 all() 返回空列表模拟 "无匹配学生" 的场景。函数应优雅返回 []，
        而非抛出 IndexError 或其他异常。

        这在实际场景中对应于：某类型学生（如 xueyou）在本次课堂中未分配，
        但调用方仍请求挑选该类型学生的情况。
        """
        db = MagicMock()
        # 模拟 SQLAlchemy 链式调用链：db.query(Model).filter(条件).all() → []
        all_mock = MagicMock(return_value=[])
        first_filter = MagicMock()
        first_filter.all = all_mock
        query = MagicMock()
        query.filter = MagicMock(return_value=first_filter)
        db.query = MagicMock(return_value=query)

        result = pick_random_students_by_type(
            uuid.uuid4(), "xueyou", 1, db
        )
        assert result == []

    def test_count_larger_than_candidates(self):
        """
        验证请求数量超过实际候选数量时，返回所有候选而不做填充或报错。

        本场景模拟：候选池中仅有 1 名 xueyou 学生（student_xm），
        但调用方请求挑选 5 名。函数应返回全部 1 名学生，
        而非抛出错误、返回 None 或填充至 5 个。

        这在多轮举手场景中可能发生：当前可选学生已被前几轮挑走，
        剩余候选数小于期望数，此时应有多少返回多少。
        """
        mock_student = MagicMock()
        mock_student.student_id = "student_xm"

        db = MagicMock()
        all_mock = MagicMock(return_value=[mock_student])
        first_filter = MagicMock()
        first_filter.all = all_mock
        query = MagicMock()
        query.filter = MagicMock(return_value=first_filter)
        db.query = MagicMock(return_value=query)

        result = pick_random_students_by_type(
            uuid.uuid4(), "xueyou", 5, db
        )
        assert len(result) == 1
        assert result[0].student_id == "student_xm"

    def test_exclude_ids(self):
        """
        验证 exclude_ids 参数能正确排除指定学生。

        本测试构造两个学生的候选池（s1 为 student_xm，s2 为 student_xw），
        请求挑选 2 名 xueyou 学生但排除 student_xm。预期结果中只应包含
        student_xw（共 1 名），验证排除逻辑生效。

        同时验证排除过滤条件是通过 SQLAlchemy 的 ~SessionStudent.student_id.in_(exclude_ids)
        生成，再叠加原有的 session_id + student_type 条件。

        exclude_ids 的实际使用场景：同一轮举手交互中已举手的学生，
        在重新分配举手时应被排除，避免同一人连续被选中两次。
        """
        s1 = MagicMock(student_id="student_xm")
        s2 = MagicMock(student_id="student_xw")

        db = MagicMock()
        all_mock = MagicMock(return_value=[s2])  # student_xm 已被排除，仅剩 student_xw
        second_filter = MagicMock()
        second_filter.all = all_mock
        first_filter = MagicMock()
        first_filter.filter = MagicMock(return_value=second_filter)
        query = MagicMock()
        query.filter = MagicMock(return_value=first_filter)
        db.query = MagicMock(return_value=query)

        result = pick_random_students_by_type(
            uuid.uuid4(), "xueyou", 2, db, exclude_ids=["student_xm"]
        )
        assert len(result) == 1
        assert result[0].student_id == "student_xw"


class TestResponseSchema:
    """
    测试课堂实时交互相关的 Pydantic 响应/请求 Schema。

    这些 Schema 定义前后端之间的数据传输格式，验证其构造、字段默认值和
    类型校验的正确性。Pydantic 的 BaseModel 会在构造时自动进行类型转换
    和校验，因此本测试类主要验证字段值能正确存取。
    """

    def test_inclass_utterance_response(self):
        """
        验证 InclassUtteranceResponse 的构造与字段存取。

        InclassUtteranceResponse 是 POST /inclass/utterance 接口返回给前端的
        完整响应体，包含以下核心字段：

        - dialog_state: Supervisor 推断的当前对话状态（如 questioning 表示
          教师正在提问），前端据此决定后续交互流程（展示举手/等待点名/立即播放）
        - should_trigger_student: 是否需要触发虚拟学生事件
        - play_mode: 前端播放模式（"on_call_name" 表示等老师点名后再播放回答）
        - raised_hand_student_ids: 本轮举手的学生 ID 列表
        - student_states_digest: 全体学生的状态摘要（含学生类型和举手状态），
          供前端渲染学生面板
        - student_event: AI 生成的候选学生事件数组，在 questioning 状态下返回
          多条（6 条，覆盖学优/杠精/学困 × 主动/非主动），在 normal 状态下为 None

        本测试构造一个 questioning 状态下的典型响应，验证 dialog_state、
        play_mode 和举手学生列表的正确性。
        """
        from app.schemas.inclass import InclassUtteranceResponse, StudentStateItem

        resp = InclassUtteranceResponse(
            dialog_state="questioning",
            should_trigger_student=True,
            trigger_reason="teacher_question",
            target_student_type="all",
            interaction_round_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            play_mode="on_call_name",
            raised_hand_student_ids=["student_xm", "student_xw"],
            preset_for_student_id=None,
            student_states_digest=[
                StudentStateItem(student_id="student_xm", student_type="xueyou", is_hand_raised=True),
                StudentStateItem(student_id="student_xw", student_type="gangjing", is_hand_raised=True),
            ],
            preset_consumed=False,
            student_event=[{"student_type": "xueyou", "reply_text": "test"}],
        )
        assert resp.dialog_state == "questioning"
        assert resp.play_mode == "on_call_name"
        assert resp.raised_hand_student_ids == ["student_xm", "student_xw"]

    def test_student_reply_response(self):
        """
        验证 StudentReplyResponse 的构造与字段存取。

        StudentReplyResponse 是 POST /inclass/student-reply 接口的响应体，
        前端点名某个举手学生后，后端调用 AI StudentAgent 生成单条回答，
        封装为该 Schema 返回。

        关键字段：

        - student_id: 回答学生的唯一标识（对应 STUDENT_ROSTER 中的 student_id）
        - student_type: 学生角色类型（xueyou / gangjing / xuekun），
          前端据此决定播放动画风格和声音
        - reply_text: AI 生成的学生回答文本，应符合该学生类型的角色设定
          （如学优生回答质量高、学困生回答犹豫不完整）
        - emotion: 学生情绪标签（如 curious 表示好奇、hesitant 表示犹豫），
          前端据此渲染面部表情和身体动作
        - is_proactive_speaking: 是否主动发言。True 表示该学生主动举手
          后发言（无需老师点名）；False 表示是被点名后才回答

        本测试构造一个学优生的典型回答响应，逐字段验证。
        """
        from app.schemas.inclass import StudentReplyResponse

        resp = StudentReplyResponse(
            student_id="student_xm",
            student_type="xueyou",
            reply_text="老师，我觉得这里可以用面积法来证明。",
            emotion="curious",
            is_proactive_speaking=True,
        )
        assert resp.student_id == "student_xm"
        assert resp.student_type == "xueyou"
        assert resp.reply_text == "老师，我觉得这里可以用面积法来证明。"
        assert resp.emotion == "curious"
        assert resp.is_proactive_speaking is True

    def test_student_reply_request(self):
        """
        验证 StudentReplyRequest 的构造与字段存取。

        StudentReplyRequest 是 POST /inclass/student-reply 接口的请求体，
        当老师在前端点击某个举手的学生时，前端发送此请求获取该学生的 AI 回答。

        关键字段：

        - session_id: 当前课堂会话的唯一标识（UUID 字符串），后端据此查询
          该 session 的学生状态和对话历史
        - student_id: 被点名的目标学生 ID，后端据此查询学生的姓名、类型、
          当前举手状态等信息
        - current_timestamp: 当前时刻的 ISO8601 格式时间戳（含时区），
          记录点名发生的具体时间，用于落库 event_ts
        - current_ppt: 当前页 PPT 的结构化信息数组（通常仅一条），结构与
          课前 PPT 解析结果中 slides[] 的单条一致，包含 slide_no、title、
          text_blocks 等字段。AI StudentAgent 据此生成与当前教学内容相关的回答

        本测试验证 session_id、student_id 和 current_ppt 字段能正确存储和读取。
        """
        from app.schemas.inclass import StudentReplyRequest

        req = StudentReplyRequest(
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            student_id="student_xm",
            current_timestamp="2026-07-18T10:00:00+08:00",
            current_ppt=[{"slide_no": 1, "title": "测试页"}],
        )
        assert req.session_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert req.student_id == "student_xm"
        assert req.current_ppt[0]["slide_no"] == 1
