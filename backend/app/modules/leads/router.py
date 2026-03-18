from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/health")
def leads_health() -> dict[str, str]:
    return {"module": "leads", "status": "ok"}

