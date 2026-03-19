from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter
from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.db.enums import ContentTaskStatus, ContentTaskType
from app.modules.content.deps import (
    ActorContext,
    RequestMeta,
    authorize,
    get_actor_context,
    get_request_meta,
)
from app.modules.content.repository import ContentRepository, ContentTaskListFilters
from app.modules.content.schemas import ContentTaskCreateRequest, ContentTaskListResult, ContentTaskResponse
from app.modules.content.service import ContentService

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/health")
def content_health() -> dict[str, str]:
    return {"module": "content", "status": "ok"}


@router.post("/tasks", response_model=ContentTaskResponse, status_code=status.HTTP_201_CREATED)
def create_content_task(
    payload: ContentTaskCreateRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
    request_meta: RequestMeta = Depends(get_request_meta),
) -> ContentTaskResponse:
    authorize("content.tasks.create", actor)
    service = ContentService(ContentRepository(db))
    result = service.create_task(payload, actor=actor, request_meta=request_meta)
    db.commit()
    return result


@router.get("/tasks", response_model=ContentTaskListResult)
def list_content_tasks(
    task_type: ContentTaskType | None = None,
    status_: ContentTaskStatus | None = Query(default=None, alias="status"),
    created_by: uuid.UUID | None = None,
    created_at_start: dt.datetime | None = None,
    created_at_end: dt.datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
) -> ContentTaskListResult:
    authorize("content.tasks.list", actor)

    filters = ContentTaskListFilters(
        task_type=task_type,
        status=status_,
        created_by=created_by,
        created_at_start=created_at_start,
        created_at_end=created_at_end,
        limit=limit,
        offset=offset,
    )
    service = ContentService(ContentRepository(db))
    return service.list_tasks(filters)


@router.get("/tasks/{task_id}", response_model=ContentTaskResponse)
def get_content_task_detail(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
    request_meta: RequestMeta = Depends(get_request_meta),
) -> ContentTaskResponse:
    authorize("content.tasks.list", actor)

    service = ContentService(ContentRepository(db))
    task = service.get_task(task_id)
    service.record_task_query(task, actor=actor, request_meta=request_meta)
    db.commit()
    return ContentTaskResponse.model_validate(task)
