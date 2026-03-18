from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/health")
def content_health() -> dict[str, str]:
    return {"module": "content", "status": "ok"}

