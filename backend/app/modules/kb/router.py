from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/kb", tags=["kb"])


@router.get("/health")
def kb_health() -> dict[str, str]:
    return {"module": "kb", "status": "ok"}

