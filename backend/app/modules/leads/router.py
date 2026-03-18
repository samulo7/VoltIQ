from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.db.enums import LeadStatus, UserRole
from app.modules.leads.deps import ActorContext, RequestMeta, authorize, get_actor_context, get_request_meta
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
from app.modules.leads.service import LeadService

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/health")
def leads_health() -> dict[str, str]:
    return {"module": "leads", "status": "ok"}


@router.post("", response_model=LeadCreateResult, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreateRequest,
    response: Response,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
    request_meta: RequestMeta = Depends(get_request_meta),
) -> LeadCreateResult:
    target_owner_user_id = payload.owner_user_id or actor.user_id
    authorize("leads.create", actor, resource_owner_user_id=target_owner_user_id)

    service = LeadService(LeadRepository(db))
    try:
        result = service.create_or_merge_lead(payload, actor=actor, request_meta=request_meta)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lead conflict detected.",
        ) from exc

    if result.action == "merged":
        # Step 8 requires create-and-merge behavior on dedup; return 200 for merged path.
        response.status_code = status.HTTP_200_OK
    return result


@router.get("", response_model=LeadListResult)
def list_leads(
    status_: Annotated[LeadStatus | None, Query(alias="status")] = None,
    owner_user_id: uuid.UUID | None = None,
    source_channel: str | None = None,
    keyword: str | None = None,
    created_at_start: dt.datetime | None = None,
    created_at_end: dt.datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
) -> LeadListResult:
    scoped_owner_user_id = owner_user_id
    if actor.role is UserRole.SALES:
        if owner_user_id is not None and owner_user_id != actor.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sales can only query own leads.",
            )
        scoped_owner_user_id = actor.user_id
        authorize("leads.list", actor, resource_owner_user_id=actor.user_id)
    else:
        authorize("leads.list", actor)

    filters = LeadListFilters(
        status=status_,
        owner_user_id=scoped_owner_user_id,
        source_channel=source_channel,
        keyword=keyword,
        created_at_start=created_at_start,
        created_at_end=created_at_end,
        limit=limit,
        offset=offset,
    )
    service = LeadService(LeadRepository(db))
    return service.list_leads(filters)


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead_detail(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
) -> LeadResponse:
    service = LeadService(LeadRepository(db))
    lead = service.get_lead(lead_id)
    authorize("leads.detail", actor, resource_owner_user_id=lead.owner_user_id)
    return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdateRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
    request_meta: RequestMeta = Depends(get_request_meta),
) -> LeadResponse:
    service = LeadService(LeadRepository(db))
    lead = service.get_lead(lead_id)
    authorize("leads.update", actor, resource_owner_user_id=lead.owner_user_id)

    try:
        result = service.update_lead(lead, payload, actor=actor, request_meta=request_meta)
        db.commit()
        return result
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lead conflict detected.",
        ) from exc


@router.post("/{lead_id}/assign", response_model=LeadResponse)
def assign_lead_owner(
    lead_id: uuid.UUID,
    payload: LeadAssignRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
    request_meta: RequestMeta = Depends(get_request_meta),
) -> LeadResponse:
    authorize("leads.assign", actor)
    service = LeadService(LeadRepository(db))
    lead = service.get_lead(lead_id)

    result = service.assign_owner(lead, payload, actor=actor, request_meta=request_meta)
    db.commit()
    return result


@router.post("/{lead_id}/merge", response_model=LeadCreateResult)
def merge_lead(
    lead_id: uuid.UUID,
    payload: LeadMergeRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
    request_meta: RequestMeta = Depends(get_request_meta),
) -> LeadCreateResult:
    authorize("leads.merge", actor)
    service = LeadService(LeadRepository(db))
    lead = service.get_lead(lead_id)

    result = service.merge_lead(lead, payload, actor=actor, request_meta=request_meta)
    db.commit()
    return result
