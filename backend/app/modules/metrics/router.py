from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/health")
def metrics_health() -> dict[str, str]:
    return {"module": "metrics", "status": "ok"}

