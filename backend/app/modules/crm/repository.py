from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.enums import OpportunityStage
from app.db.models import AuditLog, Customer, Deal, FollowUp, Lead, Opportunity


@dataclass(frozen=True)
class FollowUpListFilters:
    lead_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    created_at_start: dt.datetime | None = None
    created_at_end: dt.datetime | None = None
    owner_user_id: uuid.UUID | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class OpportunityListFilters:
    lead_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    stage: OpportunityStage | None = None
    owner_user_id: uuid.UUID | None = None
    updated_at_start: dt.datetime | None = None
    updated_at_end: dt.datetime | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class DealListFilters:
    opportunity_id: uuid.UUID | None = None
    owner_user_id: uuid.UUID | None = None
    deal_date_start: dt.date | None = None
    deal_date_end: dt.date | None = None
    limit: int = 20
    offset: int = 0


class CrmRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_lead_by_id(self, lead_id: uuid.UUID) -> Lead | None:
        return self._db.query(Lead).filter(Lead.id == lead_id).first()

    def get_customer_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        return self._db.query(Customer).filter(Customer.id == customer_id).first()

    def get_follow_up_by_id(self, follow_up_id: uuid.UUID) -> FollowUp | None:
        return self._db.query(FollowUp).filter(FollowUp.id == follow_up_id).first()

    def get_follow_up_with_owner(self, follow_up_id: uuid.UUID) -> tuple[FollowUp, uuid.UUID] | None:
        row = (
            self._db.query(FollowUp, Lead.owner_user_id)
            .join(Lead, Lead.id == FollowUp.lead_id)
            .filter(FollowUp.id == follow_up_id)
            .first()
        )
        if row is None:
            return None
        follow_up, owner_user_id = row
        return follow_up, owner_user_id

    def list_follow_ups(self, filters: FollowUpListFilters) -> tuple[int, list[FollowUp]]:
        query = self._db.query(FollowUp)

        if filters.owner_user_id is not None:
            query = query.join(Lead, Lead.id == FollowUp.lead_id).filter(
                Lead.owner_user_id == filters.owner_user_id
            )
        if filters.lead_id is not None:
            query = query.filter(FollowUp.lead_id == filters.lead_id)
        if filters.customer_id is not None:
            query = query.filter(FollowUp.customer_id == filters.customer_id)
        if filters.created_by is not None:
            query = query.filter(FollowUp.created_by == filters.created_by)
        if filters.created_at_start is not None:
            query = query.filter(FollowUp.created_at >= filters.created_at_start)
        if filters.created_at_end is not None:
            query = query.filter(FollowUp.created_at <= filters.created_at_end)

        total = query.count()
        items = (
            query.order_by(FollowUp.created_at.desc())
            .offset(filters.offset)
            .limit(filters.limit)
            .all()
        )
        return total, items

    def create_follow_up(
        self,
        *,
        lead_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        content: str,
        next_action_at: dt.datetime | None,
        created_by: uuid.UUID,
        now: dt.datetime,
    ) -> FollowUp:
        follow_up = FollowUp(
            lead_id=lead_id,
            customer_id=customer_id,
            content=content,
            next_action_at=next_action_at,
            created_by=created_by,
            created_at=now,
        )
        self._db.add(follow_up)
        self._db.flush()
        return follow_up

    def update_follow_up(self, follow_up: FollowUp, **updates: object) -> FollowUp:
        for field, value in updates.items():
            setattr(follow_up, field, value)
        self._db.flush()
        return follow_up

    def delete_follow_up(self, follow_up: FollowUp) -> None:
        self._db.delete(follow_up)
        self._db.flush()

    def get_latest_follow_up_at(self, lead_id: uuid.UUID) -> dt.datetime | None:
        return (
            self._db.query(func.max(FollowUp.created_at))
            .filter(FollowUp.lead_id == lead_id)
            .scalar()
        )

    def update_lead_latest_follow_up_at(
        self,
        lead: Lead,
        *,
        latest_follow_up_at: dt.datetime | None,
        now: dt.datetime,
    ) -> Lead:
        lead.latest_follow_up_at = latest_follow_up_at
        lead.updated_at = now
        self._db.flush()
        return lead

    def get_opportunity_by_id(self, opportunity_id: uuid.UUID) -> Opportunity | None:
        return self._db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()

    def get_opportunity_with_owner(
        self, opportunity_id: uuid.UUID
    ) -> tuple[Opportunity, uuid.UUID] | None:
        row = (
            self._db.query(Opportunity, Opportunity.owner_user_id)
            .filter(Opportunity.id == opportunity_id)
            .first()
        )
        if row is None:
            return None
        opportunity, owner_user_id = row
        return opportunity, owner_user_id

    def list_opportunities(self, filters: OpportunityListFilters) -> tuple[int, list[Opportunity]]:
        query = self._db.query(Opportunity)
        query = self._apply_opportunity_filters(query, filters)
        total = query.count()
        items = (
            query.order_by(Opportunity.updated_at.desc())
            .offset(filters.offset)
            .limit(filters.limit)
            .all()
        )
        return total, items

    def create_opportunity(
        self,
        *,
        lead_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        stage: OpportunityStage,
        amount_estimate: float | None,
        owner_user_id: uuid.UUID,
        now: dt.datetime,
    ) -> Opportunity:
        opportunity = Opportunity(
            lead_id=lead_id,
            customer_id=customer_id,
            stage=stage,
            amount_estimate=amount_estimate,
            owner_user_id=owner_user_id,
            created_at=now,
            updated_at=now,
        )
        self._db.add(opportunity)
        self._db.flush()
        return opportunity

    def update_opportunity(
        self,
        opportunity: Opportunity,
        *,
        stage: OpportunityStage | None = None,
        amount_estimate: float | None = None,
        now: dt.datetime,
    ) -> Opportunity:
        if stage is not None:
            opportunity.stage = stage
        if amount_estimate is not None:
            opportunity.amount_estimate = amount_estimate
        opportunity.updated_at = now
        self._db.flush()
        return opportunity

    def get_deal_with_owner(self, deal_id: uuid.UUID) -> tuple[Deal, uuid.UUID] | None:
        row = (
            self._db.query(Deal, Opportunity.owner_user_id)
            .join(Opportunity, Opportunity.id == Deal.opportunity_id)
            .filter(Deal.id == deal_id)
            .first()
        )
        if row is None:
            return None
        deal, owner_user_id = row
        return deal, owner_user_id

    def get_deal_by_opportunity_id(self, opportunity_id: uuid.UUID) -> Deal | None:
        return self._db.query(Deal).filter(Deal.opportunity_id == opportunity_id).first()

    def list_deals(self, filters: DealListFilters) -> tuple[int, list[Deal]]:
        query = self._db.query(Deal).join(Opportunity, Opportunity.id == Deal.opportunity_id)
        if filters.opportunity_id is not None:
            query = query.filter(Deal.opportunity_id == filters.opportunity_id)
        if filters.owner_user_id is not None:
            query = query.filter(Opportunity.owner_user_id == filters.owner_user_id)
        if filters.deal_date_start is not None:
            query = query.filter(Deal.deal_date >= filters.deal_date_start)
        if filters.deal_date_end is not None:
            query = query.filter(Deal.deal_date <= filters.deal_date_end)

        total = query.count()
        items = (
            query.order_by(Deal.deal_date.desc(), Deal.created_at.desc())
            .offset(filters.offset)
            .limit(filters.limit)
            .all()
        )
        return total, items

    def create_deal(
        self,
        *,
        opportunity_id: uuid.UUID,
        deal_amount: float,
        deal_date: dt.date,
        created_by: uuid.UUID,
        now: dt.datetime,
    ) -> Deal:
        deal = Deal(
            opportunity_id=opportunity_id,
            deal_amount=deal_amount,
            deal_date=deal_date,
            created_by=created_by,
            created_at=now,
        )
        self._db.add(deal)
        self._db.flush()
        return deal

    def get_opportunity_stage_counts(self, filters: OpportunityListFilters) -> dict[OpportunityStage, int]:
        query = self._db.query(Opportunity.stage, func.count(Opportunity.id))
        query = self._apply_opportunity_filters(query, filters)
        query = query.group_by(Opportunity.stage)
        return {stage: count for stage, count in query.all()}

    def count_opportunities(self, filters: OpportunityListFilters) -> int:
        query = self._db.query(func.count(Opportunity.id))
        query = self._apply_opportunity_filters(query, filters)
        total = query.scalar()
        return int(total or 0)

    def count_deals_and_sum_amount_by_opportunity_filters(
        self,
        filters: OpportunityListFilters,
    ) -> tuple[int, float]:
        query = self._db.query(
            func.count(Deal.id),
            func.coalesce(func.sum(Deal.deal_amount), 0),
        ).select_from(Opportunity)
        query = self._apply_opportunity_filters(query, filters)
        query = query.join(Deal, Deal.opportunity_id == Opportunity.id)

        deal_count, amount_sum = query.one()
        if amount_sum is None:
            amount_sum = 0
        if isinstance(amount_sum, Decimal):
            amount_value = float(amount_sum)
        else:
            amount_value = float(amount_sum)
        return int(deal_count or 0), amount_value

    def create_audit_log(
        self,
        *,
        actor_user_id: uuid.UUID,
        action: str,
        target_type: str,
        target_id: str,
        before_data: dict[str, Any] | None,
        after_data: dict[str, Any] | None,
        ip_address: str,
        request_id: str,
        now: dt.datetime,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_data=before_data,
            after_data=after_data,
            ip_address=ip_address,
            request_id=request_id,
            created_at=now,
        )
        self._db.add(audit_log)
        self._db.flush()
        return audit_log

    def _apply_opportunity_filters(self, query: Any, filters: OpportunityListFilters) -> Any:
        if filters.lead_id is not None:
            query = query.filter(Opportunity.lead_id == filters.lead_id)
        if filters.customer_id is not None:
            query = query.filter(Opportunity.customer_id == filters.customer_id)
        if filters.stage is not None:
            query = query.filter(Opportunity.stage == filters.stage)
        if filters.owner_user_id is not None:
            query = query.filter(Opportunity.owner_user_id == filters.owner_user_id)
        if filters.updated_at_start is not None:
            query = query.filter(Opportunity.updated_at >= filters.updated_at_start)
        if filters.updated_at_end is not None:
            query = query.filter(Opportunity.updated_at <= filters.updated_at_end)
        return query
