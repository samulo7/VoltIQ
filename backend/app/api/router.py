from __future__ import annotations

from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.content.router import router as content_router
from app.modules.crm.router import router as crm_router
from app.modules.kb.router import router as kb_router
from app.modules.leads.router import router as leads_router
from app.modules.metrics.router import router as metrics_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(leads_router)
api_router.include_router(crm_router)
api_router.include_router(content_router)
api_router.include_router(kb_router)
api_router.include_router(metrics_router)
api_router.include_router(audit_router)

