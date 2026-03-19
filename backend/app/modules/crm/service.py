from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from fastapi import HTTPException, status

from app.db.enums import OpportunityStage
from app.db.models import Deal, FollowUp, Lead, Opportunity
from app.modules.crm.deps import ActorContext, RequestMeta
from app.modules.crm.repository import (
    CrmRepository,
    DealListFilters,
    FollowUpListFilters,
    OpportunityListFilters,
)
from app.modules.crm.schemas import (
    DealCreateRequest,
    DealListResult,
    DealResponse,
    FollowUpCreateRequest,
    FollowUpListResult,
    FollowUpResponse,
    FollowUpUpdateRequest,
    OpportunityCreateRequest,
    OpportunityListResult,
    OpportunityResponse,
    OpportunityStageUpdateRequest,
    OpportunityStatsResponse,
)


class CrmService:
    def __init__(self, repo: CrmRepository) -> None:
        self._repo = repo

    def get_lead(self, lead_id: uuid.UUID) -> Lead:
        lead = self._repo.get_lead_by_id(lead_id)
        if lead is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
        return lead

    def get_follow_up_with_owner(self, follow_up_id: uuid.UUID) -> tuple[FollowUp, uuid.UUID]:
        row = self._repo.get_follow_up_with_owner(follow_up_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found.")
        return row

    def get_opportunity_with_owner(self, opportunity_id: uuid.UUID) -> tuple[Opportunity, uuid.UUID]:
        row = self._repo.get_opportunity_with_owner(opportunity_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found.")
        return row

    def list_follow_ups(self, filters: FollowUpListFilters) -> FollowUpListResult:
        total, items = self._repo.list_follow_ups(filters)
        return FollowUpListResult(
            total=total,
            items=[FollowUpResponse.model_validate(item) for item in items],
        )

    def list_opportunities(self, filters: OpportunityListFilters) -> OpportunityListResult:
        total, items = self._repo.list_opportunities(filters)
        return OpportunityListResult(
            total=total,
            items=[OpportunityResponse.model_validate(item) for item in items],
        )

    def list_deals(self, filters: DealListFilters) -> DealListResult:
        total, items = self._repo.list_deals(filters)
        return DealListResult(
            total=total,
            items=[DealResponse.model_validate(item) for item in items],
        )

    def create_follow_up(
        self,
        payload: FollowUpCreateRequest,
        *,
        lead: Lead,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> FollowUpResponse:
        if payload.customer_id is not None:
            customer = self._repo.get_customer_by_id(payload.customer_id)
            if customer is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customer does not exist.",
                )
            if customer.lead_id != lead.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customer does not belong to lead.",
                )

        now = _utcnow()
        follow_up = self._repo.create_follow_up(
            lead_id=lead.id,
            customer_id=payload.customer_id,
            content=payload.content,
            next_action_at=payload.next_action_at,
            created_by=actor.user_id,
            now=now,
        )
        self._repo.update_lead_latest_follow_up_at(
            lead,
            latest_follow_up_at=follow_up.created_at,
            now=now,
        )
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="follow_up.created",
            target_type="follow_up",
            target_id=str(follow_up.id),
            before_data=None,
            after_data=_follow_up_snapshot(follow_up),
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=now,
        )
        return FollowUpResponse.model_validate(follow_up)

    def create_opportunity(
        self,
        payload: OpportunityCreateRequest,
        *,
        lead: Lead,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> OpportunityResponse:
        if payload.customer_id is not None:
            customer = self._repo.get_customer_by_id(payload.customer_id)
            if customer is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customer does not exist.",
                )
            if customer.lead_id != lead.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customer does not belong to lead.",
                )

        now = _utcnow()
        opportunity = self._repo.create_opportunity(
            lead_id=lead.id,
            customer_id=payload.customer_id,
            stage=OpportunityStage.INITIAL,
            amount_estimate=payload.amount_estimate,
            owner_user_id=lead.owner_user_id,
            now=now,
        )
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="opportunity.created",
            target_type="opportunity",
            target_id=str(opportunity.id),
            before_data=None,
            after_data=_opportunity_snapshot(opportunity),
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=now,
        )
        return OpportunityResponse.model_validate(opportunity)

    def update_opportunity_stage(
        self,
        opportunity: Opportunity,
        payload: OpportunityStageUpdateRequest,
        *,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> OpportunityResponse:
        target_stage = payload.stage
        current_stage = opportunity.stage

        if target_stage is OpportunityStage.WON:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stage 'won' can only be set by creating a deal.",
            )
        if target_stage is OpportunityStage.LOST and not payload.lost_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="lost_reason is required when stage is 'lost'.",
            )
        if target_stage is not OpportunityStage.LOST and payload.lost_reason is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="lost_reason is only allowed when stage is 'lost'.",
            )

        if target_stage is current_stage:
            return OpportunityResponse.model_validate(opportunity)

        if not _is_valid_stage_transition(current_stage, target_stage):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stage transition: {current_stage.value} -> {target_stage.value}.",
            )

        now = _utcnow()
        updated = self._repo.update_opportunity(opportunity, stage=target_stage, now=now)
        before_data = {"stage": current_stage.value}
        after_data: dict[str, Any] = {"stage": target_stage.value}
        if target_stage is OpportunityStage.LOST:
            after_data["lost_reason"] = payload.lost_reason

        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="opportunity.stage_changed",
            target_type="opportunity",
            target_id=str(updated.id),
            before_data=before_data,
            after_data=after_data,
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=now,
        )
        return OpportunityResponse.model_validate(updated)

    def create_deal(
        self,
        payload: DealCreateRequest,
        *,
        opportunity: Opportunity,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> DealResponse:
        if opportunity.stage is not OpportunityStage.NEGOTIATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deal can only be created when opportunity stage is 'negotiation'.",
            )

        existing_deal = self._repo.get_deal_by_opportunity_id(opportunity.id)
        if existing_deal is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Deal already exists for this opportunity.",
            )

        now = _utcnow()
        deal = self._repo.create_deal(
            opportunity_id=opportunity.id,
            deal_amount=payload.deal_amount,
            deal_date=payload.deal_date,
            created_by=actor.user_id,
            now=now,
        )
        self._repo.update_opportunity(
            opportunity,
            stage=OpportunityStage.WON,
            now=now,
        )
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="opportunity.stage_changed",
            target_type="opportunity",
            target_id=str(opportunity.id),
            before_data={"stage": OpportunityStage.NEGOTIATION.value},
            after_data={"stage": OpportunityStage.WON.value, "trigger": "deal_created"},
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=now,
        )
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="deal.created",
            target_type="deal",
            target_id=str(deal.id),
            before_data=None,
            after_data=_deal_snapshot(deal),
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=now,
        )
        return DealResponse.model_validate(deal)

    def get_opportunity_stats(self, filters: OpportunityListFilters) -> OpportunityStatsResponse:
        opportunity_total = self._repo.count_opportunities(filters)
        raw_stage_counts = self._repo.get_opportunity_stage_counts(filters)
        stage_counts = {stage: raw_stage_counts.get(stage, 0) for stage in OpportunityStage}
        deal_count, deal_amount_sum = self._repo.count_deals_and_sum_amount_by_opportunity_filters(
            filters
        )
        return OpportunityStatsResponse(
            opportunity_total=opportunity_total,
            stage_counts=stage_counts,
            deal_count=deal_count,
            deal_amount_sum=deal_amount_sum,
        )

    def update_follow_up(
        self,
        follow_up: FollowUp,
        payload: FollowUpUpdateRequest,
        *,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> FollowUpResponse:
        updates = payload.model_dump(exclude_none=True)
        if not updates:
            return FollowUpResponse.model_validate(follow_up)

        before_data = _follow_up_snapshot(follow_up)
        updated = self._repo.update_follow_up(follow_up, **updates)
        now = _utcnow()
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="follow_up.updated",
            target_type="follow_up",
            target_id=str(updated.id),
            before_data=before_data,
            after_data=_follow_up_snapshot(updated),
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=now,
        )
        return FollowUpResponse.model_validate(updated)

    def delete_follow_up(
        self,
        follow_up: FollowUp,
        *,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> None:
        lead = self.get_lead(follow_up.lead_id)
        before_data = _follow_up_snapshot(follow_up)

        self._repo.delete_follow_up(follow_up)
        latest_follow_up_at = self._repo.get_latest_follow_up_at(lead.id)
        now = _utcnow()
        self._repo.update_lead_latest_follow_up_at(
            lead,
            latest_follow_up_at=latest_follow_up_at,
            now=now,
        )
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="follow_up.deleted",
            target_type="follow_up",
            target_id=before_data["id"],
            before_data=before_data,
            after_data=None,
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=now,
        )


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _datetime_to_iso(value: dt.datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _follow_up_snapshot(follow_up: FollowUp) -> dict[str, Any]:
    return {
        "id": str(follow_up.id),
        "lead_id": str(follow_up.lead_id),
        "customer_id": str(follow_up.customer_id) if follow_up.customer_id else None,
        "content": follow_up.content,
        "next_action_at": _datetime_to_iso(follow_up.next_action_at),
        "created_by": str(follow_up.created_by),
        "created_at": _datetime_to_iso(follow_up.created_at),
    }


def _opportunity_snapshot(opportunity: Opportunity) -> dict[str, Any]:
    return {
        "id": str(opportunity.id),
        "lead_id": str(opportunity.lead_id),
        "customer_id": str(opportunity.customer_id) if opportunity.customer_id else None,
        "stage": opportunity.stage.value,
        "amount_estimate": float(opportunity.amount_estimate)
        if opportunity.amount_estimate is not None
        else None,
        "owner_user_id": str(opportunity.owner_user_id),
        "created_at": _datetime_to_iso(opportunity.created_at),
        "updated_at": _datetime_to_iso(opportunity.updated_at),
    }


def _deal_snapshot(deal: Deal) -> dict[str, Any]:
    return {
        "id": str(deal.id),
        "opportunity_id": str(deal.opportunity_id),
        "deal_amount": float(deal.deal_amount),
        "deal_date": deal.deal_date.isoformat(),
        "created_by": str(deal.created_by),
        "created_at": _datetime_to_iso(deal.created_at),
    }


def _is_valid_stage_transition(from_stage: OpportunityStage, to_stage: OpportunityStage) -> bool:
    allowed_next_stages: dict[OpportunityStage, frozenset[OpportunityStage]] = {
        OpportunityStage.INITIAL: frozenset({OpportunityStage.PROPOSAL}),
        OpportunityStage.PROPOSAL: frozenset({OpportunityStage.NEGOTIATION}),
        OpportunityStage.NEGOTIATION: frozenset({OpportunityStage.LOST}),
        OpportunityStage.WON: frozenset(),
        OpportunityStage.LOST: frozenset(),
    }
    return to_stage in allowed_next_stages.get(from_stage, frozenset())
