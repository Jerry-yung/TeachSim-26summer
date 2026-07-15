from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    grade: Mapped[str] = mapped_column(String(128))
    subject: Mapped[str] = mapped_column(String(128))
    class_level: Mapped[str] = mapped_column(String(64))
    atmosphere: Mapped[str] = mapped_column(String(64))
    custom_goal: Mapped[str] = mapped_column(Text, default="")
    teacher_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding_status: Mapped[str] = mapped_column(String(32), default="pending")
    lesson_topic: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    subject_icon: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    lesson_payload: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    ppt_payload: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    teaching_preferences: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    analysis_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    files: Mapped[List["LessonFile"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["ClassroomSession"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )


class LessonFile(Base):
    __tablename__ = "lesson_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    original_filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_path: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    lesson: Mapped[Lesson] = relationship(back_populates="files")


class ClassroomSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="pending")
    frontend_session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    report_payload: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    lesson: Mapped[Lesson] = relationship(back_populates="sessions")
    transcripts: Mapped[List["Transcript"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    turns: Mapped[List["SessionTurn"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    segments: Mapped[List["SessionSegment"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lesson_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(32), default="debug_upload")
    text: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32))
    raw_payload: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped[Optional["ClassroomSession"]] = relationship(
        back_populates="transcripts"
    )


class SessionTurn(Base):
    __tablename__ = "session_turns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    role_type: Mapped[str] = mapped_column(String(32))
    role_label: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text)
    event_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    called_student_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped[ClassroomSession] = relationship(back_populates="turns")


class SessionSegment(Base):
    __tablename__ = "session_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    segment_id: Mapped[str] = mapped_column(String(128), index=True)
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    slide_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    segment_payload: Mapped[Dict] = mapped_column(JSONB)
    eval_payload: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped[ClassroomSession] = relationship(back_populates="segments")
