from __future__ import annotations

import datetime as dt

from fastapi import APIRouter
from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.db.enums import UserRole
from app.modules.metrics.deps import ActorContext, authorize, get_actor_context
from app.modules.metrics.repository import MetricsRepository
from app.modules.metrics.schemas import MetricsOverviewResponse
from app.modules.metrics.service import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/health")
def metrics_health() -> dict[str, str]:
    return {"module": "metrics", "status": "ok"}


@router.get("/overview", response_model=MetricsOverviewResponse)
def get_metrics_overview(
    start_date: dt.date | None = Query(default=None),
    end_date: dt.date | None = Query(default=None),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
) -> MetricsOverviewResponse:
    owner_user_id = None
    if actor.role is UserRole.SALES:
        authorize("metrics.overview", actor, resource_owner_user_id=actor.user_id)
        owner_user_id = actor.user_id
    else:
        authorize("metrics.overview", actor)

    service = MetricsService(MetricsRepository(db))
    return service.get_overview(
        start_date=start_date,
        end_date=end_date,
        owner_user_id=owner_user_id,
    )
