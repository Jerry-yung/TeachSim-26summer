"""add teacher_id to sessions, class_elapsed_sec/slide_no to session_turns

Revision ID: 20260720_0002
Revises: 20260717_0001
Create Date: 2026-07-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260720_0002"
down_revision: Union[str, None] = "20260717_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # sessions.teacher_id — models require it, but existing rows may not have it
    op.add_column(
        "sessions",
        sa.Column("teacher_id", sa.String(128), nullable=True),
    )
    op.create_index(op.f("ix_sessions_teacher_id"), "sessions", ["teacher_id"])

    # session_turns.class_elapsed_sec / slide_no
    op.add_column(
        "session_turns",
        sa.Column("class_elapsed_sec", sa.Integer(), nullable=True),
    )
    op.add_column(
        "session_turns",
        sa.Column("slide_no", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_turns", "slide_no")
    op.drop_column("session_turns", "class_elapsed_sec")
    op.drop_index(op.f("ix_sessions_teacher_id"), table_name="sessions")
    op.drop_column("sessions", "teacher_id")
