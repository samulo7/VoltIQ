from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.enums import LeadStatus, UserStatus
from app.db.models import AuditLog, Lead, LeadMergeLog, User


@dataclass(frozen=True)
class LeadListFilters:
    status: LeadStatus | None = None
    owner_user_id: uuid.UUID | None = None
    source_channel: str | None = None
    keyword: str | None = None
    created_at_start: dt.datetime | None = None
    created_at_end: dt.datetime | None = None
    limit: int = 20
    offset: int = 0


class LeadRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, lead_id: uuid.UUID) -> Lead | None:
        return self._db.query(Lead).filter(Lead.id == lead_id).first()

    def get_by_phone(self, phone: str) -> Lead | None:
        return self._db.query(Lead).filter(Lead.phone == phone).first()

    def get_by_company_and_name(self, company_name: str, name: str) -> Lead | None:
        return (
            self._db.query(Lead)
            .filter(Lead.company_name == company_name, Lead.name == name)
            .first()
        )

    def user_exists_and_active(self, user_id: uuid.UUID) -> bool:
        count = (
            self._db.query(func.count(User.id))
            .filter(User.id == user_id, User.status == UserStatus.ACTIVE)
            .scalar()
        )
        return bool(count)

    def list_leads(self, filters: LeadListFilters) -> tuple[int, list[Lead]]:
        query = self._db.query(Lead)

        if filters.status is not None:
            query = query.filter(Lead.status == filters.status)
        if filters.owner_user_id is not None:
            query = query.filter(Lead.owner_user_id == filters.owner_user_id)
        if filters.source_channel is not None:
            query = query.filter(Lead.source_channel == filters.source_channel)
        if filters.keyword:
            keyword = f"%{filters.keyword}%"
            query = query.filter(
                or_(
                    Lead.name.ilike(keyword),
                    Lead.company_name.ilike(keyword),
                    Lead.phone.ilike(keyword),
                )
            )
        if filters.created_at_start is not None:
            query = query.filter(Lead.created_at >= filters.created_at_start)
        if filters.created_at_end is not None:
            query = query.filter(Lead.created_at <= filters.created_at_end)

        total = query.count()
        items = (
            query.order_by(Lead.created_at.desc())
            .offset(filters.offset)
            .limit(filters.limit)
            .all()
        )
        return total, items

    def create_lead(
        self,
        *,
        name: str,
        phone: str,
        company_name: str,
        source_channel: str,
        status: LeadStatus,
        owner_user_id: uuid.UUID,
        now: dt.datetime,
    ) -> Lead:
        lead = Lead(
            name=name,
            phone=phone,
            company_name=company_name,
            source_channel=source_channel,
            status=status,
            owner_user_id=owner_user_id,
            latest_follow_up_at=None,
            created_at=now,
            updated_at=now,
        )
        self._db.add(lead)
        self._db.flush()
        return lead

    def update_lead(self, lead: Lead, *, now: dt.datetime, **updates: object) -> Lead:
        for field, value in updates.items():
            setattr(lead, field, value)
        lead.updated_at = now
        self._db.flush()
        return lead

    def create_merge_log(
        self,
        *,
        target_lead_id: uuid.UUID,
        merged_payload: dict[str, object],
        merge_reason: str,
        operator_user_id: uuid.UUID,
        now: dt.datetime,
    ) -> LeadMergeLog:
        merge_log = LeadMergeLog(
            target_lead_id=target_lead_id,
            merged_payload=merged_payload,
            merge_reason=merge_reason,
            operator_user_id=operator_user_id,
            created_at=now,
        )
        self._db.add(merge_log)
        self._db.flush()
        return merge_log

    def create_audit_log(
        self,
        *,
        actor_user_id: uuid.UUID,
        action: str,
        target_type: str,
        target_id: str,
        before_data: dict[str, object] | None,
        after_data: dict[str, object] | None,
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
