from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.enums import ContentTaskStatus, ContentTaskType
from app.db.models import AuditLog, ContentTask


@dataclass(frozen=True)
class ContentTaskListFilters:
    task_type: ContentTaskType | None = None
    status: ContentTaskStatus | None = None
    created_by: uuid.UUID | None = None
    created_at_start: dt.datetime | None = None
    created_at_end: dt.datetime | None = None
    limit: int = 20
    offset: int = 0


class ContentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_task_by_id(self, task_id: uuid.UUID) -> ContentTask | None:
        return self._db.query(ContentTask).filter(ContentTask.id == task_id).first()

    def list_tasks(self, filters: ContentTaskListFilters) -> tuple[int, list[ContentTask]]:
        query = self._db.query(ContentTask)

        if filters.task_type is not None:
            query = query.filter(ContentTask.task_type == filters.task_type)
        if filters.status is not None:
            query = query.filter(ContentTask.status == filters.status)
        if filters.created_by is not None:
            query = query.filter(ContentTask.created_by == filters.created_by)
        if filters.created_at_start is not None:
            query = query.filter(ContentTask.created_at >= filters.created_at_start)
        if filters.created_at_end is not None:
            query = query.filter(ContentTask.created_at <= filters.created_at_end)

        total = query.count()
        items = (
            query.order_by(ContentTask.created_at.desc())
            .offset(filters.offset)
            .limit(filters.limit)
            .all()
        )
        return total, items

    def create_task(
        self,
        *,
        task_type: ContentTaskType,
        prompt: str,
        status: ContentTaskStatus,
        result_text: str | None,
        result_meta: dict[str, Any] | None,
        created_by: uuid.UUID,
        now: dt.datetime,
    ) -> ContentTask:
        task = ContentTask(
            task_type=task_type,
            prompt=prompt,
            status=status,
            result_text=result_text,
            result_meta=result_meta,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self._db.add(task)
        self._db.flush()
        return task

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
