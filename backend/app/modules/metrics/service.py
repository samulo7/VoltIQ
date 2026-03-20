from __future__ import annotations

import datetime as dt
import uuid
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.modules.metrics.repository import LeadDailyCounts, MetricsFilters, MetricsRepository
from app.modules.metrics.schemas import MetricsDailyItem, MetricsOverviewResponse, MetricsSummary

ASIA_SHANGHAI = ZoneInfo("Asia/Shanghai")
TIMEZONE_NAME = "Asia/Shanghai"


class MetricsService:
    def __init__(self, repo: MetricsRepository) -> None:
        self._repo = repo

    def get_overview(
        self,
        *,
        start_date: dt.date | None,
        end_date: dt.date | None,
        owner_user_id: uuid.UUID | None,
    ) -> MetricsOverviewResponse:
        resolved_start_date, resolved_end_date = _resolve_date_range(
            start_date=start_date,
            end_date=end_date,
        )
        if resolved_start_date > resolved_end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be less than or equal to end_date.",
            )

        filters = MetricsFilters(
            start_date=resolved_start_date,
            end_date=resolved_end_date,
            owner_user_id=owner_user_id,
        )

        lead_daily_counts = self._repo.collect_lead_counts_by_day(filters)
        deal_daily_counts = self._repo.collect_deal_counts_by_day(filters)

        daily_items: list[MetricsDailyItem] = []
        summary_lead_count = 0
        summary_deal_count = 0
        summary_effective_lead_count = 0

        for date_value in _iter_dates(resolved_start_date, resolved_end_date):
            lead_counts = lead_daily_counts.get(date_value, LeadDailyCounts())
            deal_count = deal_daily_counts.get(date_value, 0)
            conversion_rate = _calculate_conversion_rate(
                deal_count=deal_count,
                effective_lead_count=lead_counts.effective_lead_count,
            )
            daily_items.append(
                MetricsDailyItem(
                    date=date_value,
                    lead_count=lead_counts.lead_count,
                    deal_count=deal_count,
                    effective_lead_count=lead_counts.effective_lead_count,
                    conversion_rate=conversion_rate,
                )
            )
            summary_lead_count += lead_counts.lead_count
            summary_deal_count += deal_count
            summary_effective_lead_count += lead_counts.effective_lead_count

        summary_conversion_rate = _calculate_conversion_rate(
            deal_count=summary_deal_count,
            effective_lead_count=summary_effective_lead_count,
        )

        return MetricsOverviewResponse(
            timezone=TIMEZONE_NAME,
            start_date=resolved_start_date,
            end_date=resolved_end_date,
            summary=MetricsSummary(
                lead_count=summary_lead_count,
                deal_count=summary_deal_count,
                effective_lead_count=summary_effective_lead_count,
                conversion_rate=summary_conversion_rate,
            ),
            daily=daily_items,
        )


def _resolve_date_range(
    *,
    start_date: dt.date | None,
    end_date: dt.date | None,
) -> tuple[dt.date, dt.date]:
    if start_date is None and end_date is None:
        today = _today_in_shanghai()
        return today, today
    if start_date is None:
        assert end_date is not None
        return end_date, end_date
    if end_date is None:
        return start_date, start_date
    return start_date, end_date


def _today_in_shanghai() -> dt.date:
    return dt.datetime.now(tz=ASIA_SHANGHAI).date()


def _iter_dates(start_date: dt.date, end_date: dt.date) -> list[dt.date]:
    day_count = (end_date - start_date).days + 1
    return [start_date + dt.timedelta(days=index) for index in range(day_count)]


def _calculate_conversion_rate(*, deal_count: int, effective_lead_count: int) -> float:
    if effective_lead_count <= 0:
        return 0.0
    return deal_count / effective_lead_count
