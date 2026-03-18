from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from fastapi import HTTPException, status

from app.db.models import FollowUp, Lead
from app.modules.crm.deps import ActorContext, RequestMeta
from app.modules.crm.repository import CrmRepository, FollowUpListFilters
from app.modules.crm.schemas import (
    FollowUpCreateRequest,
    FollowUpListResult,
    FollowUpResponse,
    FollowUpUpdateRequest,
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

    def list_follow_ups(self, filters: FollowUpListFilters) -> FollowUpListResult:
        total, items = self._repo.list_follow_ups(filters)
        return FollowUpListResult(
            total=total,
            items=[FollowUpResponse.model_validate(item) for item in items],
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
