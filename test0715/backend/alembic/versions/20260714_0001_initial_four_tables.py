"""initial four tables

Revision ID: 20260714_0001
Revises:
Create Date: 2026-07-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260411_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lessons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grade", sa.String(length=128), nullable=False),
        sa.Column("subject", sa.String(length=128), nullable=False),
        sa.Column("class_level", sa.String(length=64), nullable=False),
        sa.Column("atmosphere", sa.String(length=64), nullable=False),
        sa.Column(
            "custom_goal",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column("teacher_context", sa.Text(), nullable=True),
        sa.Column(
            "embedding_status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("lesson_topic", sa.String(length=512), nullable=True),
        sa.Column("subject_icon", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lesson_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_lesson_files_lesson_id"), "lesson_files", ["lesson_id"], unique=False
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sessions_lesson_id"), "sessions", ["lesson_id"], unique=False
    )

    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="debug_upload",
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_transcripts_lesson_id"), "transcripts", ["lesson_id"], unique=False
    )
    op.create_index(
        op.f("ix_transcripts_session_id"), "transcripts", ["session_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transcripts_session_id"), table_name="transcripts")
    op.drop_index(op.f("ix_transcripts_lesson_id"), table_name="transcripts")
    op.drop_table("transcripts")
    op.drop_index(op.f("ix_sessions_lesson_id"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index(op.f("ix_lesson_files_lesson_id"), table_name="lesson_files")
    op.drop_table("lesson_files")
    op.drop_table("lessons")
