from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.db.base import Base
from app.db.enums import LeadStatus, UserRole, UserStatus
from app.db.models import AuditLog, Lead, LeadMergeLog, User
from app.main import create_app


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type: JSONB, _compiler: object, **_kw: object) -> str:
    return "JSON"


@compiles(PGUUID, "sqlite")
def _compile_uuid_sqlite(_type: PGUUID, _compiler: object, **_kw: object) -> str:
    return "TEXT"


@pytest.fixture()
def api_client() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    app = create_app()

    def _override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    try:
        yield client, session_factory
    finally:
        app.dependency_overrides.clear()
        client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _seed_user(db: Session, *, user_id: uuid.UUID, role: UserRole, username: str) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    db.add(
        User(
            id=user_id,
            username=username,
            password_hash="not_used",
            role=role,
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )


def _seed_lead(
    db: Session,
    *,
    lead_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    name: str,
    phone: str,
    company_name: str,
    source_channel: str = "ad",
    status: LeadStatus = LeadStatus.NEW,
) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    db.add(
        Lead(
            id=lead_id,
            name=name,
            phone=phone,
            company_name=company_name,
            source_channel=source_channel,
            status=status,
            owner_user_id=owner_user_id,
            latest_follow_up_at=None,
            created_at=now,
            updated_at=now,
        )
    )


def _auth_headers(role: UserRole, user_id: uuid.UUID) -> dict[str, str]:
    return {
        "X-Actor-Role": role.value,
        "X-Actor-User-Id": str(user_id),
        "X-Request-Id": "test-request-id",
    }


def test_create_lead_success_and_get_detail(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, session_factory = api_client
    operator_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="op1")
        _seed_user(db, user_id=owner_id, role=UserRole.SALES, username="sales1")
        db.commit()

    create_resp = client.post(
        "/api/v1/leads",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
        json={
            "name": "张三",
            "phone": "13800001234",
            "company_name": "华能工厂",
            "source_channel": "wechat",
            "owner_user_id": str(owner_id),
        },
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["action"] == "created"
    assert body["lead"]["owner_user_id"] == str(owner_id)

    lead_id = body["lead"]["id"]
    detail_resp = client.get(
        f"/api/v1/leads/{lead_id}",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["company_name"] == "华能工厂"


def test_create_duplicate_by_phone_auto_merge_and_write_logs(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    operator_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    existing_lead_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="op1")
        _seed_user(db, user_id=owner_id, role=UserRole.SALES, username="sales1")
        _seed_lead(
            db,
            lead_id=existing_lead_id,
            owner_user_id=owner_id,
            name="李四",
            phone="13900001111",
            company_name="绿电科技",
            source_channel="douyin",
        )
        db.commit()

    resp = client.post(
        "/api/v1/leads",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
        json={
            "name": "李四",
            "phone": "13900001111",
            "company_name": "不同公司",
            "source_channel": "xiaohongshu",
            "owner_user_id": str(owner_id),
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["action"] == "merged"
    assert payload["merge_reason"] == "duplicate_phone"
    assert payload["lead"]["id"] == str(existing_lead_id)

    with session_factory() as db:
        assert db.query(Lead).count() == 1
        merge_logs = db.query(LeadMergeLog).all()
        assert len(merge_logs) == 1
        assert merge_logs[0].merge_reason == "duplicate_phone"
        assert db.query(AuditLog).filter(AuditLog.action == "lead.merged").count() == 1


def test_create_duplicate_by_company_and_name_auto_merge(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    operator_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    existing_lead_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="op1")
        _seed_user(db, user_id=owner_id, role=UserRole.SALES, username="sales1")
        _seed_lead(
            db,
            lead_id=existing_lead_id,
            owner_user_id=owner_id,
            name="王五",
            phone="13700001111",
            company_name="中能集团",
            source_channel="ad",
        )
        db.commit()

    resp = client.post(
        "/api/v1/leads",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
        json={
            "name": "王五",
            "phone": "13600002222",
            "company_name": "中能集团",
            "source_channel": "wechat",
            "owner_user_id": str(owner_id),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["merge_reason"] == "duplicate_company_and_name"


def test_list_filters_with_sales_owner_scope(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, session_factory = api_client
    sales_a = uuid.uuid4()
    sales_b = uuid.uuid4()
    operator = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=sales_a, role=UserRole.SALES, username="sales_a")
        _seed_user(db, user_id=sales_b, role=UserRole.SALES, username="sales_b")
        _seed_user(db, user_id=operator, role=UserRole.OPERATOR, username="op1")
        _seed_lead(
            db,
            lead_id=uuid.uuid4(),
            owner_user_id=sales_a,
            name="A1",
            phone="13600000001",
            company_name="A-Company",
            source_channel="wechat",
            status=LeadStatus.CONTACTED,
        )
        _seed_lead(
            db,
            lead_id=uuid.uuid4(),
            owner_user_id=sales_b,
            name="B1",
            phone="13600000002",
            company_name="B-Company",
            source_channel="douyin",
            status=LeadStatus.NEW,
        )
        db.commit()

    sales_resp = client.get(
        "/api/v1/leads?keyword=Company",
        headers=_auth_headers(UserRole.SALES, sales_a),
    )
    assert sales_resp.status_code == 200
    assert sales_resp.json()["total"] == 1
    assert sales_resp.json()["items"][0]["owner_user_id"] == str(sales_a)

    forbidden_resp = client.get(
        f"/api/v1/leads?owner_user_id={sales_b}",
        headers=_auth_headers(UserRole.SALES, sales_a),
    )
    assert forbidden_resp.status_code == 403

    operator_resp = client.get(
        "/api/v1/leads?status=contacted&source_channel=wechat",
        headers=_auth_headers(UserRole.OPERATOR, operator),
    )
    assert operator_resp.status_code == 200
    assert operator_resp.json()["total"] == 1


def test_update_assign_and_manual_merge_write_audit_logs(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    operator = uuid.uuid4()
    owner_old = uuid.uuid4()
    owner_new = uuid.uuid4()
    lead_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=operator, role=UserRole.OPERATOR, username="op1")
        _seed_user(db, user_id=owner_old, role=UserRole.SALES, username="sales_old")
        _seed_user(db, user_id=owner_new, role=UserRole.SALES, username="sales_new")
        _seed_lead(
            db,
            lead_id=lead_id,
            owner_user_id=owner_old,
            name="待更新",
            phone="13500003333",
            company_name="更新前",
            source_channel="ad",
        )
        db.commit()

    update_resp = client.patch(
        f"/api/v1/leads/{lead_id}",
        headers=_auth_headers(UserRole.OPERATOR, operator),
        json={"status": "contacted", "company_name": "更新后"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "contacted"
    assert update_resp.json()["company_name"] == "更新后"

    assign_resp = client.post(
        f"/api/v1/leads/{lead_id}/assign",
        headers=_auth_headers(UserRole.OPERATOR, operator),
        json={"owner_user_id": str(owner_new)},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["owner_user_id"] == str(owner_new)

    merge_resp = client.post(
        f"/api/v1/leads/{lead_id}/merge",
        headers=_auth_headers(UserRole.OPERATOR, operator),
        json={"merge_reason": "manual_merge", "merged_payload": {"phone": "13500003333"}},
    )
    assert merge_resp.status_code == 200
    assert merge_resp.json()["action"] == "merged"

    with session_factory() as db:
        actions = {row.action for row in db.query(AuditLog).all()}
        assert {"lead.updated", "lead.assign", "lead.merged"}.issubset(actions)


def test_rbac_restricts_manager_write_and_sales_cross_owner(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    manager_id = uuid.uuid4()
    sales_a = uuid.uuid4()
    sales_b = uuid.uuid4()
    lead_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=manager_id, role=UserRole.MANAGER, username="mgr1")
        _seed_user(db, user_id=sales_a, role=UserRole.SALES, username="sales_a")
        _seed_user(db, user_id=sales_b, role=UserRole.SALES, username="sales_b")
        _seed_lead(
            db,
            lead_id=lead_id,
            owner_user_id=sales_b,
            name="B owner",
            phone="13400004444",
            company_name="B-Lead",
        )
        db.commit()

    manager_write = client.patch(
        f"/api/v1/leads/{lead_id}",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
        json={"status": "invalid"},
    )
    assert manager_write.status_code == 403

    sales_cross_owner = client.patch(
        f"/api/v1/leads/{lead_id}",
        headers=_auth_headers(UserRole.SALES, sales_a),
        json={"status": "invalid"},
    )
    assert sales_cross_owner.status_code == 403


def test_sales_create_duplicate_of_foreign_owner_is_forbidden(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    sales_a = uuid.uuid4()
    sales_b = uuid.uuid4()
    lead_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=sales_a, role=UserRole.SALES, username="sales_a")
        _seed_user(db, user_id=sales_b, role=UserRole.SALES, username="sales_b")
        _seed_lead(
            db,
            lead_id=lead_id,
            owner_user_id=sales_b,
            name="外部线索",
            phone="13300005555",
            company_name="外部公司",
        )
        db.commit()

    resp = client.post(
        "/api/v1/leads",
        headers=_auth_headers(UserRole.SALES, sales_a),
        json={
            "name": "外部线索",
            "phone": "13300005555",
            "company_name": "外部公司",
            "source_channel": "wechat",
        },
    )
    assert resp.status_code == 403
