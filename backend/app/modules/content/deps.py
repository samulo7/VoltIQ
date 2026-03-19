from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.db.enums import UserRole, UserStatus
from app.db.models import User
from app.rbac import EndpointAccessRequest, authorize_endpoint


@dataclass(frozen=True)
class ActorContext:
    role: UserRole
    user_id: uuid.UUID


@dataclass(frozen=True)
class RequestMeta:
    request_id: str
    ip_address: str


def get_actor_context(
    actor_role: Annotated[str, Header(alias="X-Actor-Role")],
    actor_user_id: Annotated[str, Header(alias="X-Actor-User-Id")],
    db: Session = Depends(get_db),
) -> ActorContext:
    try:
        role = UserRole(actor_role.strip().lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Actor-Role header.",
        ) from exc

    try:
        user_id = uuid.UUID(actor_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Actor-User-Id header.",
        ) from exc

    user = (
        db.query(User)
        .filter(User.id == user_id, User.role == role, User.status == UserStatus.ACTIVE)
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Actor not found or inactive.",
        )

    return ActorContext(role=role, user_id=user_id)


def get_request_meta(
    request: Request,
    request_id_header: Annotated[str | None, Header(alias="X-Request-Id")] = None,
) -> RequestMeta:
    request_id = request_id_header or str(uuid.uuid4())
    client_host = request.client.host if request.client else "unknown"
    return RequestMeta(request_id=request_id, ip_address=client_host)


def authorize(
    endpoint_key: str,
    actor: ActorContext,
    resource_owner_user_id: uuid.UUID | None = None,
) -> None:
    allowed = authorize_endpoint(
        EndpointAccessRequest(
            endpoint_key=endpoint_key,
            role=actor.role,
            actor_user_id=actor.user_id,
            resource_owner_user_id=resource_owner_user_id,
        )
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied.",
        )
