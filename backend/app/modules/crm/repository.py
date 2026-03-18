from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Customer, FollowUp, Lead


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
