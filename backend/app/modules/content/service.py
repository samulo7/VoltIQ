from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from fastapi import HTTPException, status

from app.db.enums import ContentTaskStatus, ContentTaskType
from app.db.models import ContentTask
from app.modules.content.deps import ActorContext, RequestMeta
from app.modules.content.repository import ContentRepository, ContentTaskListFilters
from app.modules.content.schemas import ContentTaskCreateRequest, ContentTaskListResult, ContentTaskResponse


class ContentService:
    def __init__(self, repo: ContentRepository) -> None:
        self._repo = repo

    def create_task(
        self,
        payload: ContentTaskCreateRequest,
        *,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> ContentTaskResponse:
        now = _utcnow()
        result_text, result_meta = _build_placeholder_result(payload.task_type, payload.prompt, now)
        task = self._repo.create_task(
            task_type=payload.task_type,
            prompt=payload.prompt,
            status=ContentTaskStatus.SUCCEEDED,
            result_text=result_text,
            result_meta=result_meta,
            created_by=actor.user_id,
            now=now,
        )
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="content_task.created",
            target_type="content_task",
            target_id=str(task.id),
            before_data=None,
            after_data=_task_snapshot(task),
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=now,
        )
        return ContentTaskResponse.model_validate(task)

    def list_tasks(self, filters: ContentTaskListFilters) -> ContentTaskListResult:
        total, items = self._repo.list_tasks(filters)
        return ContentTaskListResult(
            total=total,
            items=[ContentTaskResponse.model_validate(item) for item in items],
        )

    def get_task(self, task_id: uuid.UUID) -> ContentTask:
        task = self._repo.get_task_by_id(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content task not found.")
        return task

    def record_task_query(
        self,
        task: ContentTask,
        *,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> None:
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="content_task.queried",
            target_type="content_task",
            target_id=str(task.id),
            before_data=None,
            after_data={
                "task_type": task.task_type.value,
                "status": task.status.value,
            },
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=_utcnow(),
        )


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _prompt_preview(prompt: str, max_length: int = 120) -> str:
    if len(prompt) <= max_length:
        return prompt
    return f"{prompt[:max_length]}..."


def _build_placeholder_result(
    task_type: ContentTaskType,
    prompt: str,
    now: dt.datetime,
) -> tuple[str, dict[str, Any]]:
    base_meta: dict[str, Any] = {
        "provider": "placeholder",
        "generated_at": now.isoformat(),
        "task_type": task_type.value,
    }

    if task_type is ContentTaskType.COPYWRITING:
        return (
            f"[placeholder-copywriting] Generated copywriting from prompt: {_prompt_preview(prompt, 60)}",
            {**base_meta, "format": "text"},
        )

    if task_type is ContentTaskType.IMAGE:
        return (
            "[placeholder-image] Generated placeholder image result.",
            {
                **base_meta,
                "format": "image",
                "image_url": "https://example.com/placeholder-image.png",
            },
        )

    return (
        f"[placeholder-video-script] Generated video script from prompt: {_prompt_preview(prompt, 60)}",
        {**base_meta, "format": "text"},
    )


def _task_snapshot(task: ContentTask) -> dict[str, Any]:
    return {
        "task_type": task.task_type.value,
        "status": task.status.value,
        "prompt_preview": _prompt_preview(task.prompt),
        "result_text_preview": _prompt_preview(task.result_text or ""),
    }
