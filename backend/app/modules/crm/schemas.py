from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, Field


class FollowUpCreateRequest(BaseModel):
    lead_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    content: str = Field(min_length=1)
    next_action_at: dt.datetime | None = None


class FollowUpUpdateRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    next_action_at: dt.datetime | None = None


class FollowUpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_id: uuid.UUID
    customer_id: uuid.UUID | None
    content: str
    next_action_at: dt.datetime | None
    created_by: uuid.UUID
    created_at: dt.datetime


class FollowUpListResult(BaseModel):
    total: int
    items: list[FollowUpResponse]
