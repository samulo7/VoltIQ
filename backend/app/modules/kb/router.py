from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.integrations.dify import DifyClient
from app.modules.kb.deps import (
    ActorContext,
    RequestMeta,
    authorize,
    get_actor_context,
    get_dify_client,
    get_request_meta,
)
from app.modules.kb.repository import KbRepository, KbSessionListFilters
from app.modules.kb.schemas import KbChatRequest, KbChatResponse, KbSessionListResult
from app.modules.kb.service import KbService

router = APIRouter(prefix="/kb", tags=["kb"])


@router.get("/health")
def kb_health() -> dict[str, str]:
    return {"module": "kb", "status": "ok"}


@router.get("/sessions", response_model=KbSessionListResult)
def list_kb_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
) -> KbSessionListResult:
    authorize("kb.sessions.list", actor)
    service = KbService(KbRepository(db))
    filters = KbSessionListFilters(
        user_id=actor.user_id,
        limit=limit,
        offset=offset,
    )
    return service.list_sessions(filters)


@router.post("/sessions/chat", response_model=KbChatResponse)
def chat_with_kb(
    payload: KbChatRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
    request_meta: RequestMeta = Depends(get_request_meta),
    dify_client: DifyClient = Depends(get_dify_client),
) -> KbChatResponse:
    authorize("kb.sessions.chat", actor)
    service = KbService(KbRepository(db), dify_client=dify_client)
    response = service.chat(payload, actor=actor, request_meta=request_meta)
    db.commit()
    return response
