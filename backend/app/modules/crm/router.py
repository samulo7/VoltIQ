from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.db.enums import UserRole
from app.modules.crm.deps import ActorContext, RequestMeta, authorize, get_actor_context, get_request_meta
from app.modules.crm.repository import CrmRepository, FollowUpListFilters
from app.modules.crm.schemas import (
    FollowUpCreateRequest,
    FollowUpListResult,
    FollowUpResponse,
    FollowUpUpdateRequest,
)
from app.modules.crm.service import CrmService

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/health")
def crm_health() -> dict[str, str]:
    return {"module": "crm", "status": "ok"}


@router.post("/follow-ups", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
def create_follow_up(
    payload: FollowUpCreateRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
    request_meta: RequestMeta = Depends(get_request_meta),
) -> FollowUpResponse:
    service = CrmService(CrmRepository(db))
    lead = service.get_lead(payload.lead_id)
    authorize("crm.follow_ups.create", actor, resource_owner_user_id=lead.owner_user_id)

    result = service.create_follow_up(payload, lead=lead, actor=actor, request_meta=request_meta)
    db.commit()
    return result


@router.get("/follow-ups", response_model=FollowUpListResult)
def list_follow_ups(
    lead_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    created_by: uuid.UUID | None = None,
    created_at_start: dt.datetime | None = None,
    created_at_end: dt.datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
) -> FollowUpListResult:
    service = CrmService(CrmRepository(db))
    scoped_owner_user_id: uuid.UUID | None = None

    if actor.role is UserRole.SALES:
        if lead_id is not None:
            lead = service.get_lead(lead_id)
            authorize("crm.follow_ups.list", actor, resource_owner_user_id=lead.owner_user_id)
        else:
            authorize("crm.follow_ups.list", actor, resource_owner_user_id=actor.user_id)
        scoped_owner_user_id = actor.user_id
    else:
        authorize("crm.follow_ups.list", actor)

    filters = FollowUpListFilters(
        lead_id=lead_id,
        customer_id=customer_id,
        created_by=created_by,
        created_at_start=created_at_start,
        created_at_end=created_at_end,
        owner_user_id=scoped_owner_user_id,
        limit=limit,
        offset=offset,
    )
    return service.list_follow_ups(filters)


@router.get("/follow-ups/{follow_up_id}", response_model=FollowUpResponse)
def get_follow_up_detail(
    follow_up_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
) -> FollowUpResponse:
    service = CrmService(CrmRepository(db))
    follow_up, owner_user_id = service.get_follow_up_with_owner(follow_up_id)
    authorize("crm.follow_ups.list", actor, resource_owner_user_id=owner_user_id)
    return FollowUpResponse.model_validate(follow_up)


@router.patch("/follow-ups/{follow_up_id}", response_model=FollowUpResponse)
def update_follow_up(
    follow_up_id: uuid.UUID,
    payload: FollowUpUpdateRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
    request_meta: RequestMeta = Depends(get_request_meta),
) -> FollowUpResponse:
    service = CrmService(CrmRepository(db))
    follow_up, owner_user_id = service.get_follow_up_with_owner(follow_up_id)
    authorize("crm.follow_ups.update", actor, resource_owner_user_id=owner_user_id)

    result = service.update_follow_up(
        follow_up,
        payload,
        actor=actor,
        request_meta=request_meta,
    )
    db.commit()
    return result


@router.delete("/follow-ups/{follow_up_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_follow_up(
    follow_up_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
    request_meta: RequestMeta = Depends(get_request_meta),
) -> Response:
    service = CrmService(CrmRepository(db))
    follow_up, owner_user_id = service.get_follow_up_with_owner(follow_up_id)
    authorize("crm.follow_ups.delete", actor, resource_owner_user_id=owner_user_id)

    service.delete_follow_up(
        follow_up,
        actor=actor,
        request_meta=request_meta,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
