"""举手策略单元测试。"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.services.hand_raise_policy import (
    normalize_atmosphere,
    normalize_question_difficulty,
    select_questioning_hand_raises,
)


def _student(sid: str, stype: str, *, sleeping: bool = False, whispering: bool = False):
    return SimpleNamespace(
        student_id=sid,
        student_type=stype,
        is_sleeping=sleeping,
        is_whispering=whispering,
    )


class TestNormalizeAtmosphere:
    def test_three_tiers_and_legacy(self):
        assert normalize_atmosphere("活跃互动型") == "active"
        assert normalize_atmosphere("活跃") == "active"
        assert normalize_atmosphere("严谨讨论型") == "active"
        assert normalize_atmosphere("均衡参与型") == "balanced"
        assert normalize_atmosphere("均衡") == "balanced"
        assert normalize_atmosphere("沉浸讲解型") == "immersive"
        assert normalize_atmosphere("沉闷") == "immersive"


class TestNormalizeDifficulty:
    def test_bands(self):
        assert normalize_question_difficulty(1) == "simple"
        assert normalize_question_difficulty(2) == "simple"
        assert normalize_question_difficulty(3) == "medium"
        assert normalize_question_difficulty(5) == "hard"
        assert normalize_question_difficulty(None) == "medium"


class TestSelectQuestioningHandRaises:
    def _pool(self):
        return [
            _student("student_xm", "xueyou"),
            _student("student_xw", "gangjing"),
            _student("student_xw2", "xuekun"),
            _student("student_xl", "xuekun"),
        ]

    def test_max_half_class(self):
        ids = select_questioning_hand_raises(
            session_id=uuid.uuid4(),
            interaction_round_id="round-1",
            students=self._pool(),
            atmosphere="active",
            difficulty_band="simple",
        )
        assert len(ids) <= 2
        assert len(set(ids)) == len(ids)

    def test_excludes_sleeping_and_whispering(self):
        pool = self._pool()
        pool[0] = _student("student_xm", "xueyou", sleeping=True)
        ids = select_questioning_hand_raises(
            session_id=uuid.uuid4(),
            interaction_round_id="round-2",
            students=pool,
            atmosphere="active",
            difficulty_band="simple",
        )
        assert "student_xm" not in ids
        assert len(ids) <= 1

    def test_reproducible_with_same_seed_inputs(self):
        sid = uuid.UUID("00000000-0000-0000-0000-000000000001")
        students = self._pool()
        a = select_questioning_hand_raises(
            session_id=sid,
            interaction_round_id="same-round",
            students=students,
            atmosphere="balanced",
            difficulty_band="medium",
        )
        b = select_questioning_hand_raises(
            session_id=sid,
            interaction_round_id="same-round",
            students=students,
            atmosphere="balanced",
            difficulty_band="medium",
        )
        assert a == b

    def test_immersive_hard_never_two_in_distribution_cap(self):
        """沉浸+难题 P(2)=0；多次抽样不应出现 3+ 人（4 人班上限 2）。"""
        sid = uuid.uuid4()
        students = self._pool()
        for i in range(30):
            ids = select_questioning_hand_raises(
                session_id=sid,
                interaction_round_id=f"imm-hard-{i}",
                students=students,
                atmosphere="immersive",
                difficulty_band="hard",
            )
            assert len(ids) <= 1
