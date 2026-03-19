from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import OpportunityStage


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


class OpportunityCreateRequest(BaseModel):
    lead_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    amount_estimate: float | None = Field(default=None, ge=0)


class OpportunityStageUpdateRequest(BaseModel):
    stage: OpportunityStage
    lost_reason: str | None = Field(default=None, min_length=1)


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_id: uuid.UUID
    customer_id: uuid.UUID | None
    stage: OpportunityStage
    amount_estimate: float | None
    owner_user_id: uuid.UUID
    created_at: dt.datetime
    updated_at: dt.datetime


class OpportunityListResult(BaseModel):
    total: int
    items: list[OpportunityResponse]


class DealCreateRequest(BaseModel):
    opportunity_id: uuid.UUID
    deal_amount: float = Field(gt=0)
    deal_date: dt.date


class DealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opportunity_id: uuid.UUID
    deal_amount: float
    deal_date: dt.date
    created_by: uuid.UUID
    created_at: dt.datetime


class DealListResult(BaseModel):
    total: int
    items: list[DealResponse]


class OpportunityStatsResponse(BaseModel):
    opportunity_total: int
    stage_counts: dict[OpportunityStage, int]
    deal_count: int
    deal_amount_sum: float
