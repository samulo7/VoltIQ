from __future__ import annotations

import uuid

from app.db.enums import UserRole
from app.rbac import (
    CRITICAL_ENDPOINT_KEYS,
    CRITICAL_MENU_KEYS,
    ENDPOINT_POLICY_REGISTRY,
    MENU_POLICY_REGISTRY,
    AccessRequest,
    EndpointAccessRequest,
    OwnershipScope,
    PermissionCode,
    authorize_endpoint,
    can_view_menu,
    has_permission,
    is_allowed,
)


def test_operator_role_matrix() -> None:
    assert has_permission(UserRole.OPERATOR, PermissionCode.LEAD_WRITE)
    assert has_permission(UserRole.OPERATOR, PermissionCode.CONTENT_TASK_WRITE)
    assert not has_permission(UserRole.OPERATOR, PermissionCode.DEAL_CREATE)
    assert not has_permission(UserRole.OPERATOR, PermissionCode.AUDIT_LOG_READ)


def test_sales_owner_scope_enforced() -> None:
    actor_id = uuid.uuid4()
    foreign_owner_id = uuid.uuid4()

    assert is_allowed(
        AccessRequest(
            role=UserRole.SALES,
            permission=PermissionCode.LEAD_READ,
            actor_user_id=actor_id,
            resource_owner_user_id=actor_id,
            ownership_scope=OwnershipScope.OWNER,
        )
    )
    assert not is_allowed(
        AccessRequest(
            role=UserRole.SALES,
            permission=PermissionCode.LEAD_READ,
            actor_user_id=actor_id,
            resource_owner_user_id=foreign_owner_id,
            ownership_scope=OwnershipScope.OWNER,
        )
    )
    assert not is_allowed(
        AccessRequest(
            role=UserRole.SALES,
            permission=PermissionCode.LEAD_READ,
            actor_user_id=actor_id,
            resource_owner_user_id=actor_id,
            ownership_scope=OwnershipScope.NONE,
        )
    )
    assert not is_allowed(
        AccessRequest(
            role=UserRole.SALES,
            permission=PermissionCode.LEAD_READ,
            actor_user_id=None,
            resource_owner_user_id=actor_id,
            ownership_scope=OwnershipScope.OWNER,
        )
    )


def test_manager_is_read_only_with_approval_overrides() -> None:
    assert has_permission(UserRole.MANAGER, PermissionCode.LEAD_READ)
    assert not has_permission(UserRole.MANAGER, PermissionCode.LEAD_WRITE)
    assert has_permission(UserRole.MANAGER, PermissionCode.OPPORTUNITY_ROLLBACK)
    assert has_permission(UserRole.MANAGER, PermissionCode.DEAL_CORRECT)


def test_endpoint_authorization_with_sales_scope() -> None:
    actor_id = uuid.uuid4()
    foreign_owner_id = uuid.uuid4()

    assert authorize_endpoint(
        EndpointAccessRequest(
            endpoint_key="crm.opportunities.update_stage",
            role=UserRole.SALES,
            actor_user_id=actor_id,
            resource_owner_user_id=actor_id,
        )
    )
    assert not authorize_endpoint(
        EndpointAccessRequest(
            endpoint_key="crm.opportunities.update_stage",
            role=UserRole.SALES,
            actor_user_id=actor_id,
            resource_owner_user_id=foreign_owner_id,
        )
    )
    assert not authorize_endpoint(
        EndpointAccessRequest(
            endpoint_key="approvals.opportunity.rollback",
            role=UserRole.SALES,
            actor_user_id=actor_id,
        )
    )


def test_manager_approval_endpoint_allowed() -> None:
    assert authorize_endpoint(
        EndpointAccessRequest(
            endpoint_key="approvals.opportunity.rollback",
            role=UserRole.MANAGER,
        )
    )
    assert authorize_endpoint(
        EndpointAccessRequest(
            endpoint_key="approvals.deal.correct",
            role=UserRole.MANAGER,
        )
    )


def test_policy_registries_cover_critical_keys() -> None:
    missing_endpoints = CRITICAL_ENDPOINT_KEYS.difference(ENDPOINT_POLICY_REGISTRY)
    missing_menus = CRITICAL_MENU_KEYS.difference(MENU_POLICY_REGISTRY)
    assert not missing_endpoints
    assert not missing_menus


def test_menu_visibility_by_role() -> None:
    assert can_view_menu(UserRole.OPERATOR, "menu.leads")
    assert can_view_menu(UserRole.SALES, "menu.crm_deals")
    assert not can_view_menu(UserRole.OPERATOR, "menu.crm_deals")
    assert can_view_menu(UserRole.MANAGER, "menu.audit_logs")
    assert can_view_menu(UserRole.MANAGER, "menu.approvals")
    assert not can_view_menu(UserRole.SALES, "menu.approvals")
