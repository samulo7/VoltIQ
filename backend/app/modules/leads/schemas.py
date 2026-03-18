from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import LeadStatus


class LeadCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    phone: str = Field(min_length=1, max_length=32)
    company_name: str = Field(min_length=1, max_length=128)
    source_channel: str = Field(min_length=1, max_length=64)
    owner_user_id: uuid.UUID | None = None
    status: LeadStatus = LeadStatus.NEW


class LeadUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    company_name: str | None = Field(default=None, min_length=1, max_length=128)
    source_channel: str | None = Field(default=None, min_length=1, max_length=64)
    status: LeadStatus | None = None


class LeadAssignRequest(BaseModel):
    owner_user_id: uuid.UUID


class LeadMergeRequest(BaseModel):
    merged_payload: dict[str, Any]
    merge_reason: str = Field(default="manual_merge", min_length=1, max_length=64)


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    phone: str
    company_name: str
    source_channel: str
    status: LeadStatus
    owner_user_id: uuid.UUID
    latest_follow_up_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime


class LeadCreateResult(BaseModel):
    action: str
    lead: LeadResponse
    merge_reason: str | None = None


class LeadListResult(BaseModel):
    total: int
    items: list[LeadResponse]
