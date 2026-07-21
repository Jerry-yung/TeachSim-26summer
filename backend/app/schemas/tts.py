from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MinimaxTTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    student_id: Optional[str] = None
