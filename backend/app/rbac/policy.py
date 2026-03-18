from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.db.enums import UserRole
from app.rbac.types import AccessRequest, OwnershipScope, PermissionCode

ROLE_PERMISSION_MAP: dict[UserRole, frozenset[PermissionCode]] = {
    UserRole.OPERATOR: frozenset(
        {
            PermissionCode.LEAD_READ,
            PermissionCode.LEAD_WRITE,
            PermissionCode.LEAD_ASSIGN,
            PermissionCode.LEAD_MERGE,
            PermissionCode.CONTENT_TASK_READ,
            PermissionCode.CONTENT_TASK_WRITE,
            PermissionCode.KB_SESSION_READ,
        }
    ),
    UserRole.SALES: frozenset(
        {
            PermissionCode.LEAD_READ,
            PermissionCode.LEAD_WRITE,
            PermissionCode.FOLLOW_UP_READ,
            PermissionCode.FOLLOW_UP_WRITE,
            PermissionCode.OPPORTUNITY_READ,
            PermissionCode.OPPORTUNITY_WRITE,
            PermissionCode.DEAL_READ,
            PermissionCode.DEAL_CREATE,
            PermissionCode.METRICS_READ,
        }
    ),
    UserRole.MANAGER: frozenset(
        {
            PermissionCode.LEAD_READ,
            PermissionCode.FOLLOW_UP_READ,
            PermissionCode.OPPORTUNITY_READ,
            PermissionCode.DEAL_READ,
            PermissionCode.CONTENT_TASK_READ,
            PermissionCode.KB_SESSION_READ,
            PermissionCode.METRICS_READ,
            PermissionCode.AUDIT_LOG_READ,
            PermissionCode.OPPORTUNITY_ROLLBACK,
            PermissionCode.DEAL_CORRECT,
        }
    ),
}

SALES_OWNER_SCOPED_PERMISSIONS: frozenset[PermissionCode] = frozenset(
    {
        PermissionCode.LEAD_READ,
        PermissionCode.LEAD_WRITE,
        PermissionCode.FOLLOW_UP_READ,
        PermissionCode.FOLLOW_UP_WRITE,
        PermissionCode.OPPORTUNITY_READ,
        PermissionCode.OPPORTUNITY_WRITE,
        PermissionCode.DEAL_READ,
        PermissionCode.DEAL_CREATE,
    }
)


def has_permission(role: UserRole, permission: PermissionCode) -> bool:
    return permission in ROLE_PERMISSION_MAP.get(role, frozenset())


def is_allowed(request: AccessRequest) -> bool:
    if not has_permission(request.role, request.permission):
        return False

    if request.role is not UserRole.SALES:
        return True

    if request.permission not in SALES_OWNER_SCOPED_PERMISSIONS:
        return True

    if request.ownership_scope is not OwnershipScope.OWNER:
        return False

    if request.actor_user_id is None or request.resource_owner_user_id is None:
        return False

    return request.actor_user_id == request.resource_owner_user_id


@dataclass(frozen=True)
class EndpointPolicy:
    permission: PermissionCode
    sales_ownership_scope: OwnershipScope = OwnershipScope.NONE


@dataclass(frozen=True)
class EndpointAccessRequest:
    endpoint_key: str
    role: UserRole
    actor_user_id: uuid.UUID | None = None
    resource_owner_user_id: uuid.UUID | None = None


ENDPOINT_POLICY_REGISTRY: dict[str, EndpointPolicy] = {
    "leads.list": EndpointPolicy(PermissionCode.LEAD_READ, OwnershipScope.OWNER),
    "leads.detail": EndpointPolicy(PermissionCode.LEAD_READ, OwnershipScope.OWNER),
    "leads.create": EndpointPolicy(PermissionCode.LEAD_WRITE, OwnershipScope.OWNER),
    "leads.update": EndpointPolicy(PermissionCode.LEAD_WRITE, OwnershipScope.OWNER),
    "leads.assign": EndpointPolicy(PermissionCode.LEAD_ASSIGN),
    "leads.merge": EndpointPolicy(PermissionCode.LEAD_MERGE),
    "crm.follow_ups.list": EndpointPolicy(PermissionCode.FOLLOW_UP_READ, OwnershipScope.OWNER),
    "crm.follow_ups.create": EndpointPolicy(PermissionCode.FOLLOW_UP_WRITE, OwnershipScope.OWNER),
    "crm.follow_ups.update": EndpointPolicy(PermissionCode.FOLLOW_UP_WRITE, OwnershipScope.OWNER),
    "crm.follow_ups.delete": EndpointPolicy(PermissionCode.FOLLOW_UP_WRITE, OwnershipScope.OWNER),
    "crm.opportunities.list": EndpointPolicy(PermissionCode.OPPORTUNITY_READ, OwnershipScope.OWNER),
    "crm.opportunities.create": EndpointPolicy(PermissionCode.OPPORTUNITY_WRITE, OwnershipScope.OWNER),
    "crm.opportunities.update_stage": EndpointPolicy(
        PermissionCode.OPPORTUNITY_WRITE,
        OwnershipScope.OWNER,
    ),
    "crm.deals.list": EndpointPolicy(PermissionCode.DEAL_READ, OwnershipScope.OWNER),
    "crm.deals.create": EndpointPolicy(PermissionCode.DEAL_CREATE, OwnershipScope.OWNER),
    "content.tasks.list": EndpointPolicy(PermissionCode.CONTENT_TASK_READ),
    "content.tasks.create": EndpointPolicy(PermissionCode.CONTENT_TASK_WRITE),
    "kb.sessions.list": EndpointPolicy(PermissionCode.KB_SESSION_READ),
    "kb.sessions.chat": EndpointPolicy(PermissionCode.KB_SESSION_READ),
    "metrics.overview": EndpointPolicy(PermissionCode.METRICS_READ),
    "audit.logs.list": EndpointPolicy(PermissionCode.AUDIT_LOG_READ),
    "approvals.opportunity.rollback": EndpointPolicy(PermissionCode.OPPORTUNITY_ROLLBACK),
    "approvals.deal.correct": EndpointPolicy(PermissionCode.DEAL_CORRECT),
}

CRITICAL_ENDPOINT_KEYS: frozenset[str] = frozenset(
    {
        "leads.list",
        "leads.create",
        "leads.assign",
        "leads.merge",
        "crm.follow_ups.create",
        "crm.opportunities.update_stage",
        "crm.deals.create",
        "content.tasks.create",
        "kb.sessions.chat",
        "metrics.overview",
        "audit.logs.list",
        "approvals.opportunity.rollback",
        "approvals.deal.correct",
    }
)


def authorize_endpoint(request: EndpointAccessRequest) -> bool:
    policy = ENDPOINT_POLICY_REGISTRY.get(request.endpoint_key)
    if policy is None:
        return False

    return is_allowed(
        AccessRequest(
            role=request.role,
            permission=policy.permission,
            actor_user_id=request.actor_user_id,
            resource_owner_user_id=request.resource_owner_user_id,
            ownership_scope=policy.sales_ownership_scope,
        )
    )


@dataclass(frozen=True)
class MenuPolicy:
    required_permission: PermissionCode


MENU_POLICY_REGISTRY: dict[str, MenuPolicy] = {
    "menu.leads": MenuPolicy(PermissionCode.LEAD_READ),
    "menu.crm_follow_ups": MenuPolicy(PermissionCode.FOLLOW_UP_READ),
    "menu.crm_opportunities": MenuPolicy(PermissionCode.OPPORTUNITY_READ),
    "menu.crm_deals": MenuPolicy(PermissionCode.DEAL_READ),
    "menu.content_tasks": MenuPolicy(PermissionCode.CONTENT_TASK_READ),
    "menu.kb_sessions": MenuPolicy(PermissionCode.KB_SESSION_READ),
    "menu.metrics_dashboard": MenuPolicy(PermissionCode.METRICS_READ),
    "menu.audit_logs": MenuPolicy(PermissionCode.AUDIT_LOG_READ),
    "menu.approvals": MenuPolicy(PermissionCode.OPPORTUNITY_ROLLBACK),
}

CRITICAL_MENU_KEYS: frozenset[str] = frozenset(
    {
        "menu.leads",
        "menu.crm_follow_ups",
        "menu.crm_opportunities",
        "menu.crm_deals",
        "menu.content_tasks",
        "menu.kb_sessions",
        "menu.metrics_dashboard",
        "menu.audit_logs",
        "menu.approvals",
    }
)


def can_view_menu(role: UserRole, menu_key: str) -> bool:
    policy = MENU_POLICY_REGISTRY.get(menu_key)
    if policy is None:
        return False
    return has_permission(role, policy.required_permission)
