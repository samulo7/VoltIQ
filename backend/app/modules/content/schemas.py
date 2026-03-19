from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import ContentTaskStatus, ContentTaskType


class ContentTaskCreateRequest(BaseModel):
    task_type: ContentTaskType
    prompt: str = Field(min_length=1)


class ContentTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_type: ContentTaskType
    prompt: str
    status: ContentTaskStatus
    result_text: str | None
    result_meta: dict[str, Any] | None
    created_by: uuid.UUID
    created_at: dt.datetime
    updated_at: dt.datetime


class ContentTaskListResult(BaseModel):
    total: int
    items: list[ContentTaskResponse]
