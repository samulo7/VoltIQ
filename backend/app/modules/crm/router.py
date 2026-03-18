from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/health")
def crm_health() -> dict[str, str]:
    return {"module": "crm", "status": "ok"}

