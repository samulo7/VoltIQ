from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.db.enums import LeadStatus
from app.db.models import Deal, Lead, Opportunity

ASIA_SHANGHAI = ZoneInfo("Asia/Shanghai")
EFFECTIVE_LEAD_STATUSES: frozenset[LeadStatus] = frozenset(
    {
        LeadStatus.CONTACTED,
        LeadStatus.CONVERTED,
    }
)


@dataclass(frozen=True)
class MetricsFilters:
    start_date: dt.date
    end_date: dt.date
    owner_user_id: uuid.UUID | None = None


@dataclass(frozen=True)
class LeadDailyCounts:
    lead_count: int = 0
    effective_lead_count: int = 0


class MetricsRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def collect_lead_counts_by_day(self, filters: MetricsFilters) -> dict[dt.date, LeadDailyCounts]:
        window_start_utc, window_end_utc = _lead_date_window_to_utc(
            start_date=filters.start_date,
            end_date=filters.end_date,
        )

        query = self._db.query(Lead.created_at, Lead.status).filter(
            Lead.created_at >= window_start_utc,
            Lead.created_at < window_end_utc,
        )
        if filters.owner_user_id is not None:
            query = query.filter(Lead.owner_user_id == filters.owner_user_id)

        counters: dict[dt.date, list[int]] = {}
        for created_at, status in query.all():
            created_date = _to_shanghai_date(created_at)
            if created_date < filters.start_date or created_date > filters.end_date:
                continue
            if created_date not in counters:
                counters[created_date] = [0, 0]
            counters[created_date][0] += 1
            if status in EFFECTIVE_LEAD_STATUSES:
                counters[created_date][1] += 1

        return {
            date_value: LeadDailyCounts(
                lead_count=totals[0],
                effective_lead_count=totals[1],
            )
            for date_value, totals in counters.items()
        }

    def collect_deal_counts_by_day(self, filters: MetricsFilters) -> dict[dt.date, int]:
        query = (
            self._db.query(Deal.deal_date)
            .join(Opportunity, Opportunity.id == Deal.opportunity_id)
            .filter(Deal.deal_date >= filters.start_date, Deal.deal_date <= filters.end_date)
        )
        if filters.owner_user_id is not None:
            query = query.filter(Opportunity.owner_user_id == filters.owner_user_id)

        counters: dict[dt.date, int] = {}
        for (deal_date,) in query.all():
            counters[deal_date] = counters.get(deal_date, 0) + 1
        return counters


def _lead_date_window_to_utc(
    *,
    start_date: dt.date,
    end_date: dt.date,
) -> tuple[dt.datetime, dt.datetime]:
    start_local = dt.datetime.combine(
        start_date,
        dt.time.min,
        tzinfo=ASIA_SHANGHAI,
    )
    end_local = dt.datetime.combine(
        end_date + dt.timedelta(days=1),
        dt.time.min,
        tzinfo=ASIA_SHANGHAI,
    )
    return start_local.astimezone(dt.timezone.utc), end_local.astimezone(dt.timezone.utc)


def _to_shanghai_date(value: dt.datetime) -> dt.date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(ASIA_SHANGHAI).date()
