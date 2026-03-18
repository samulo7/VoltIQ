from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum

from app.db.enums import UserRole


class PermissionCode(str, Enum):
    LEAD_READ = "lead.read"
    LEAD_WRITE = "lead.write"
    LEAD_ASSIGN = "lead.assign"
    LEAD_MERGE = "lead.merge"
    FOLLOW_UP_READ = "follow_up.read"
    FOLLOW_UP_WRITE = "follow_up.write"
    OPPORTUNITY_READ = "opportunity.read"
    OPPORTUNITY_WRITE = "opportunity.write"
    OPPORTUNITY_ROLLBACK = "opportunity.rollback"
    DEAL_READ = "deal.read"
    DEAL_CREATE = "deal.create"
    DEAL_CORRECT = "deal.correct"
    CONTENT_TASK_READ = "content_task.read"
    CONTENT_TASK_WRITE = "content_task.write"
    KB_SESSION_READ = "kb_session.read"
    METRICS_READ = "metrics.read"
    AUDIT_LOG_READ = "audit_log.read"


class OwnershipScope(str, Enum):
    NONE = "none"
    OWNER = "owner"


@dataclass(frozen=True)
class AccessRequest:
    role: UserRole
    permission: PermissionCode
    actor_user_id: uuid.UUID | None = None
    resource_owner_user_id: uuid.UUID | None = None
    ownership_scope: OwnershipScope = OwnershipScope.NONE
