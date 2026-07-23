from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(256), nullable=False)
    password_hash = Column(String(512), nullable=False)
    role = Column(String(64), nullable=False, server_default="实习教师")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
