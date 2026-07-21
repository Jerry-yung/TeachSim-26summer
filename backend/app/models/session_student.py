from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SessionStudent(Base):
    __tablename__ = "session_students"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[str] = mapped_column(String(64), nullable=False)
    student_name: Mapped[str] = mapped_column(String(128), nullable=False)
    student_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_hand_raised: Mapped[bool] = mapped_column(default=False)
    is_sleeping: Mapped[bool] = mapped_column(default=False)
    is_whispering: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session: Mapped["ClassroomSession"] = relationship(back_populates="students")
