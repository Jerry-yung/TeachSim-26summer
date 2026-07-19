"""backend alignment for classroom/report

Revision ID: 20260715_0002
Revises: 20260714_0001
Create Date: 2026-07-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260417_0002"
down_revision: Union[str, None] = "20260411_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column(
            "lesson_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "lessons",
        sa.Column(
            "ppt_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "lessons",
        sa.Column(
            "teaching_preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column("lessons", sa.Column("analysis_error", sa.Text(), nullable=True))

    op.add_column(
        "sessions",
        sa.Column("frontend_session_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "report_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.create_table(
        "session_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_type", sa.String(length=32), nullable=False),
        sa.Column("role_label", sa.String(length=128), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("event_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("called_student_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_session_turns_session_id"), "session_turns", ["session_id"], unique=False
    )
    op.create_index(
        op.f("ix_session_turns_event_ts"), "session_turns", ["event_ts"], unique=False
    )

    op.create_table(
        "session_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_id", sa.String(length=128), nullable=False),
        sa.Column("start_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("slide_no", sa.Integer(), nullable=True),
        sa.Column(
            "segment_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "eval_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_session_segments_session_id"),
        "session_segments",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_segments_segment_id"),
        "session_segments",
        ["segment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_session_segments_segment_id"), table_name="session_segments")
    op.drop_index(op.f("ix_session_segments_session_id"), table_name="session_segments")
    op.drop_table("session_segments")

    op.drop_index(op.f("ix_session_turns_event_ts"), table_name="session_turns")
    op.drop_index(op.f("ix_session_turns_session_id"), table_name="session_turns")
    op.drop_table("session_turns")

    op.drop_column("sessions", "report_payload")
    op.drop_column("sessions", "frontend_session_id")

    op.drop_column("lessons", "analysis_error")
    op.drop_column("lessons", "teaching_preferences")
    op.drop_column("lessons", "ppt_payload")
    op.drop_column("lessons", "lesson_payload")
