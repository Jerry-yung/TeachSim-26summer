"""add session_visual_observations table

Revision ID: 20260723_0004
Revises: 20260721_0003
Create Date: 2026-07-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260720_0004"
down_revision: Union[str, None] = "20260720_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("role", sa.String(64), server_default="实习教师", nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"])

    # 2. auth_sessions
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_addr", sa.String(128), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_token_hash"),
    )
    op.create_index(op.f("ix_auth_sessions_user_id"), "auth_sessions", ["user_id"])
    op.create_index(op.f("ix_auth_sessions_session_token_hash"), "auth_sessions", ["session_token_hash"])
    op.create_index(op.f("ix_auth_sessions_expires_at"), "auth_sessions", ["expires_at"])

    # 3. auth_email_challenges
    op.create_table(
        "auth_email_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=True),
        sa.Column("verified_token_hash", sa.String(128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("send_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_email_challenges_email"), "auth_email_challenges", ["email"])
    op.create_index(op.f("ix_auth_email_challenges_expires_at"), "auth_email_challenges", ["expires_at"])
    op.create_index(op.f("ix_auth_email_challenges_purpose"), "auth_email_challenges", ["purpose"])
    op.create_index(op.f("ix_auth_email_challenges_purpose_email"), "auth_email_challenges", ["purpose", "email"])

    # 4. lessons.owner_user_id
    op.add_column(
        "lessons",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(op.f("ix_lessons_owner_user_id"), "lessons", ["owner_user_id"])
    op.create_foreign_key(
        op.f("fk_lessons_owner_user_id_users"),
        "lessons",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 5. session_visual_observations
    op.create_table(
        "session_visual_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_id", sa.String(128), nullable=False),
        sa.Column("segment_id", sa.String(128), nullable=True),
        sa.Column("window_start_sec", sa.Integer(), nullable=False),
        sa.Column("window_end_sec", sa.Integer(), nullable=False),
        sa.Column("slide_no", sa.Integer(), nullable=True),
        sa.Column("clip_path", sa.String(1024), nullable=True),
        sa.Column("thumbnail_path", sa.String(1024), nullable=True),
        sa.Column("vlm_status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("vlm_payload", postgresql.JSONB(), nullable=True),
        sa.Column("precheck_passed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_session_visual_observations_session_id"), "session_visual_observations", ["session_id"])
    op.create_index(op.f("ix_session_visual_observations_observation_id"), "session_visual_observations", ["observation_id"])
    op.create_index(op.f("ix_session_visual_observations_segment_id"), "session_visual_observations", ["segment_id"])
    op.create_index(op.f("ix_session_visual_observations_vlm_status"), "session_visual_observations", ["vlm_status"])


def downgrade() -> None:
    op.drop_table("session_visual_observations")
    op.drop_constraint(op.f("fk_lessons_owner_user_id_users"), "lessons", type_="foreignkey")
    op.drop_index(op.f("ix_lessons_owner_user_id"), table_name="lessons")
    op.drop_column("lessons", "owner_user_id")
    op.drop_table("auth_email_challenges")
    op.drop_table("auth_sessions")
    op.drop_table("users")
