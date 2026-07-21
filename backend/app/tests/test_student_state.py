"""学生状态库单元测试"""

import uuid
from unittest.mock import MagicMock

from app.services.student_state import (
    CLASS_LEVEL_WEIGHTS,
    STUDENT_ROSTER,
    initialize_session_students,
    pick_random_students_by_type,
)


class TestInitializeSessionStudents:
    """测试学生类型分配初始化"""

    def test_reproducibility(self):
        """相同 session_id 应产生相同的分配结果"""
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
        """固定4人名单"""
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
        """统计分配比例是否接近预期"""
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
            # 允许 ±10% 误差（200次试验应足够收敛）
            assert abs(actual - w) < 0.10, f"{t} 比例偏差过大: {actual} vs {w}"


class TestPickRandomStudentsByType:
    """测试按类型随机挑选学生"""

    def test_empty_candidates(self):
        """无匹配学生时返回空列表"""
        db = MagicMock()
        # 正确 mock SQLAlchemy 链式调用
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
        """需求数量大于候选数量时返回全部"""
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
        """排除指定学生"""
        s1 = MagicMock(student_id="student_xm")
        s2 = MagicMock(student_id="student_xw")

        db = MagicMock()
        all_mock = MagicMock(return_value=[s2])  # 排除后只剩 s2
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
    """测试响应 Schema"""

    def test_inclass_utterance_response(self):
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
        from app.schemas.inclass import StudentReplyRequest

        req = StudentReplyRequest(
            session_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            student_id="student_xm",
            current_timestamp="2026-04-22T10:00:00+08:00",
            current_ppt=[{"slide_no": 1, "title": "测试页"}],
        )
        assert req.session_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert req.student_id == "student_xm"
        assert req.current_ppt[0]["slide_no"] == 1
