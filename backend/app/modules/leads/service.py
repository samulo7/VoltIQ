from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from app.db.enums import LeadStatus, UserRole
from app.db.models import Lead
from app.modules.leads.deps import ActorContext, RequestMeta
from app.modules.leads.repository import LeadListFilters, LeadRepository
from app.modules.leads.schemas import (
    LeadAssignRequest,
    LeadCreateRequest,
    LeadCreateResult,
    LeadListResult,
    LeadMergeRequest,
    LeadResponse,
    LeadUpdateRequest,
)


@dataclass(frozen=True)
class DuplicateLeadMatch:
    lead: Lead
    merge_reason: str


class LeadService:
    def __init__(self, repo: LeadRepository) -> None:
        self._repo = repo

    def list_leads(self, filters: LeadListFilters) -> LeadListResult:
        total, items = self._repo.list_leads(filters)
        return LeadListResult(total=total, items=[LeadResponse.model_validate(item) for item in items])

    def get_lead(self, lead_id: uuid.UUID) -> Lead:
        lead = self._repo.get_by_id(lead_id)
        if lead is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
        return lead

    def create_or_merge_lead(
        self,
        payload: LeadCreateRequest,
        *,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> LeadCreateResult:
        target_owner_user_id = payload.owner_user_id or actor.user_id
        if actor.role is UserRole.SALES and target_owner_user_id != actor.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sales can only create leads for self.",
            )
        if not self._repo.user_exists_and_active(target_owner_user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Owner user not found or inactive.",
            )

        duplicate = self._find_duplicate(payload)
        now = _utcnow()

        if duplicate is not None:
            if actor.role is UserRole.SALES and duplicate.lead.owner_user_id != actor.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sales can only merge into own leads.",
                )
            masked_payload = _mask_payload(payload.model_dump(mode="json"))
            self._repo.create_merge_log(
                target_lead_id=duplicate.lead.id,
                merged_payload=masked_payload,
                merge_reason=duplicate.merge_reason,
                operator_user_id=actor.user_id,
                now=now,
            )
            self._repo.create_audit_log(
                actor_user_id=actor.user_id,
                action="lead.merged",
                target_type="lead",
                target_id=str(duplicate.lead.id),
                before_data=None,
                after_data={
                    "merge_reason": duplicate.merge_reason,
                    "merged_payload": masked_payload,
                },
                ip_address=request_meta.ip_address,
                request_id=request_meta.request_id,
                now=now,
            )
            return LeadCreateResult(
                action="merged",
                merge_reason=duplicate.merge_reason,
                lead=LeadResponse.model_validate(duplicate.lead),
            )

        lead = self._repo.create_lead(
            name=payload.name,
            phone=payload.phone,
            company_name=payload.company_name,
            source_channel=payload.source_channel,
            status=payload.status,
            owner_user_id=target_owner_user_id,
            now=now,
        )
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="lead.created",
            target_type="lead",
            target_id=str(lead.id),
            before_data=None,
            after_data={
                "name": lead.name,
                "phone": _mask_phone(lead.phone),
                "company_name": lead.company_name,
                "owner_user_id": str(lead.owner_user_id),
                "status": lead.status.value,
            },
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=now,
        )
        return LeadCreateResult(
            action="created",
            lead=LeadResponse.model_validate(lead),
        )

    def update_lead(
        self,
        lead: Lead,
        payload: LeadUpdateRequest,
        *,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> LeadResponse:
        updates = payload.model_dump(exclude_none=True)
        if not updates:
            return LeadResponse.model_validate(lead)

        next_phone = updates.get("phone")
        if isinstance(next_phone, str) and next_phone != lead.phone:
            duplicated_by_phone = self._repo.get_by_phone(next_phone)
            if duplicated_by_phone is not None and duplicated_by_phone.id != lead.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Phone already exists on another lead.",
                )

        before_data = _lead_snapshot(lead)
        updated_lead = self._repo.update_lead(lead, now=_utcnow(), **updates)
        after_data = _lead_snapshot(updated_lead)

        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="lead.updated",
            target_type="lead",
            target_id=str(updated_lead.id),
            before_data=before_data,
            after_data=after_data,
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=_utcnow(),
        )
        return LeadResponse.model_validate(updated_lead)

    def assign_owner(
        self,
        lead: Lead,
        payload: LeadAssignRequest,
        *,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> LeadResponse:
        if not self._repo.user_exists_and_active(payload.owner_user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target owner user not found or inactive.",
            )

        before_owner_id = lead.owner_user_id
        updated = self._repo.update_lead(lead, owner_user_id=payload.owner_user_id, now=_utcnow())
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="lead.assign",
            target_type="lead",
            target_id=str(updated.id),
            before_data={"owner_user_id": str(before_owner_id)},
            after_data={"owner_user_id": str(updated.owner_user_id)},
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=_utcnow(),
        )
        return LeadResponse.model_validate(updated)

    def merge_lead(
        self,
        lead: Lead,
        payload: LeadMergeRequest,
        *,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> LeadCreateResult:
        now = _utcnow()
        masked_payload = _mask_payload(payload.merged_payload)
        self._repo.create_merge_log(
            target_lead_id=lead.id,
            merged_payload=masked_payload,
            merge_reason=payload.merge_reason,
            operator_user_id=actor.user_id,
            now=now,
        )
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="lead.merged",
            target_type="lead",
            target_id=str(lead.id),
            before_data=None,
            after_data={
                "merge_reason": payload.merge_reason,
                "merged_payload": masked_payload,
            },
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=now,
        )
        return LeadCreateResult(
            action="merged",
            merge_reason=payload.merge_reason,
            lead=LeadResponse.model_validate(lead),
        )

    def _find_duplicate(self, payload: LeadCreateRequest) -> DuplicateLeadMatch | None:
        by_phone = self._repo.get_by_phone(payload.phone)
        if by_phone is not None:
            return DuplicateLeadMatch(lead=by_phone, merge_reason="duplicate_phone")

        by_company_and_name = self._repo.get_by_company_and_name(payload.company_name, payload.name)
        if by_company_and_name is not None:
            return DuplicateLeadMatch(
                lead=by_company_and_name,
                merge_reason="duplicate_company_and_name",
            )

        return None


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _mask_phone(phone: str) -> str:
    if len(phone) <= 7:
        return "*" * len(phone)
    return f"{phone[:3]}****{phone[-4:]}"


def _mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    masked_payload = dict(payload)
    phone = masked_payload.get("phone")
    if isinstance(phone, str):
        masked_payload["phone"] = _mask_phone(phone)
    return masked_payload


def _lead_snapshot(lead: Lead) -> dict[str, Any]:
    return {
        "name": lead.name,
        "phone": _mask_phone(lead.phone),
        "company_name": lead.company_name,
        "source_channel": lead.source_channel,
        "status": lead.status.value,
        "owner_user_id": str(lead.owner_user_id),
    }
