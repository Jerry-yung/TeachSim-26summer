"""Questioning 举手策略：课前氛围 × Supervisor 题目难度。"""

from __future__ import annotations

import logging
import math
import random
from typing import Any, Literal, Sequence

from app.models.session_student import SessionStudent

_logger = logging.getLogger(__name__)

AtmosphereTier = Literal["active", "balanced", "immersive"]
DifficultyBand = Literal["simple", "medium", "hard"]

# P(0), P(1), P(2) — 举手人数目标（随后受 50% 上限与 eligible 人数约束）
_COUNT_DISTRIBUTIONS: dict[AtmosphereTier, dict[DifficultyBand, tuple[float, float, float]]] = {
    "active": {
        "simple": (0.05, 0.35, 0.60),
        "medium": (0.10, 0.45, 0.45),
        "hard": (0.15, 0.55, 0.30),
    },
    "balanced": {
        "simple": (0.20, 0.45, 0.35),
        "medium": (0.25, 0.55, 0.20),
        "hard": (0.35, 0.50, 0.15),
    },
    "immersive": {
        "simple": (0.45, 0.45, 0.10),
        "medium": (0.50, 0.45, 0.05),
        "hard": (0.60, 0.40, 0.00),
    },
}

_TYPE_WEIGHTS: dict[AtmosphereTier, dict[DifficultyBand, dict[str, float]]] = {
    "active": {
        "simple": {"xueyou": 0.45, "xuekun": 0.45, "gangjing": 0.10},
        "medium": {"xueyou": 0.50, "xuekun": 0.35, "gangjing": 0.15},
        "hard": {"xueyou": 0.75, "xuekun": 0.15, "gangjing": 0.10},
    },
    "balanced": {
        "simple": {"xueyou": 0.40, "xuekun": 0.40, "gangjing": 0.20},
        "medium": {"xueyou": 0.45, "xuekun": 0.35, "gangjing": 0.20},
        "hard": {"xueyou": 0.60, "xuekun": 0.25, "gangjing": 0.15},
    },
    "immersive": {
        "simple": {"xueyou": 0.35, "xuekun": 0.50, "gangjing": 0.15},
        "medium": {"xueyou": 0.40, "xuekun": 0.45, "gangjing": 0.15},
        "hard": {"xueyou": 0.55, "xuekun": 0.35, "gangjing": 0.10},
    },
}

_ACTIVE_ALIASES = frozenset(
    {
        "活跃",
        "active",
        "活跃互动型",
        "严谨讨论型",
        "练习主导型",
    }
)
_BALANCED_ALIASES = frozenset({"均衡", "balanced", "均衡参与型"})
_IMMERSIVE_ALIASES = frozenset(
    {
        "沉闷",
        "immersive",
        "沉浸讲解型",
        "沉浸讲授型",
    }
)


def normalize_atmosphere(raw: Any) -> AtmosphereTier:
    text = str(raw or "").strip()
    if text in _ACTIVE_ALIASES:
        return "active"
    if text in _BALANCED_ALIASES:
        return "balanced"
    if text in _IMMERSIVE_ALIASES:
        return "immersive"
    return "active"


def normalize_question_difficulty(raw: Any) -> DifficultyBand:
    if raw is None:
        return "medium"
    try:
        score = int(raw)
    except (TypeError, ValueError):
        _logger.warning("question_difficulty 无法解析: %r，使用 medium", raw)
        return "medium"
    if score <= 2:
        return "simple"
    if score == 3:
        return "medium"
    if score >= 4:
        return "hard"
    return "medium"


def _max_raise_count(eligible_count: int) -> int:
    if eligible_count <= 0:
        return 0
    return max(0, math.floor(eligible_count * 0.5))


def _sample_target_count(
    dist: tuple[float, float, float],
    rng: random.Random,
) -> int:
    p0, p1, p2 = dist
    r = rng.random()
    if r < p0:
        return 0
    if r < p0 + p1:
        return 1
    return 2


def _pick_weighted_without_replacement(
    pool: list[SessionStudent],
    count: int,
    type_weights: dict[str, float],
    rng: random.Random,
) -> list[str]:
    picked: list[str] = []
    remaining = list(pool)
    for _ in range(count):
        if not remaining:
            break
        weights = [max(type_weights.get(s.student_type, 0.1), 0.01) for s in remaining]
        total = sum(weights)
        roll = rng.random() * total
        acc = 0.0
        chosen_idx = 0
        for i, w in enumerate(weights):
            acc += w
            if roll <= acc:
                chosen_idx = i
                break
        chosen = remaining.pop(chosen_idx)
        picked.append(chosen.student_id)
    return picked


def select_questioning_hand_raises(
    *,
    session_id: Any,
    interaction_round_id: str,
    students: Sequence[SessionStudent],
    atmosphere: AtmosphereTier,
    difficulty_band: DifficultyBand,
) -> list[str]:
    """按氛围与难度选出举手学生 ID（不写入 DB）。"""
    eligible = [
        s
        for s in students
        if not s.is_sleeping and not s.is_whispering
    ]
    if not eligible:
        return []

    max_raise = _max_raise_count(len(eligible))
    if max_raise <= 0:
        return []

    dist = _COUNT_DISTRIBUTIONS[atmosphere][difficulty_band]
    type_weights = _TYPE_WEIGHTS[atmosphere][difficulty_band]
    rng = random.Random(f"{session_id}:{interaction_round_id}")

    target = _sample_target_count(dist, rng)
    target = min(target, max_raise, len(eligible))
    if target <= 0:
        return []

    return _pick_weighted_without_replacement(
        eligible,
        target,
        type_weights,
        rng,
    )
