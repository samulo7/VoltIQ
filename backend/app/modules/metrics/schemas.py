from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class MetricsSummary(BaseModel):
    lead_count: int
    deal_count: int
    effective_lead_count: int
    conversion_rate: float


class MetricsDailyItem(BaseModel):
    date: dt.date
    lead_count: int
    deal_count: int
    effective_lead_count: int
    conversion_rate: float


class MetricsOverviewResponse(BaseModel):
    timezone: str
    start_date: dt.date
    end_date: dt.date
    summary: MetricsSummary
    daily: list[MetricsDailyItem]
