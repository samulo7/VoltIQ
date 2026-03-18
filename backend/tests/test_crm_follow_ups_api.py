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
from app.db.models import AuditLog, Customer, FollowUp, Lead, User
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


def _utc(year: int, month: int, day: int, hour: int, minute: int) -> dt.datetime:
    return dt.datetime(year, month, day, hour, minute, tzinfo=dt.timezone.utc)


def _as_naive_utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(dt.timezone.utc).replace(tzinfo=None)


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
    latest_follow_up_at: dt.datetime | None = None,
) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    db.add(
        Lead(
            id=lead_id,
            name=name,
            phone=phone,
            company_name=company_name,
            source_channel="ad",
            status=LeadStatus.NEW,
            owner_user_id=owner_user_id,
            latest_follow_up_at=latest_follow_up_at,
            created_at=now,
            updated_at=now,
        )
    )


def _seed_customer(
    db: Session,
    *,
    customer_id: uuid.UUID,
    lead_id: uuid.UUID,
    company_name: str = "ACME Corp",
    contact_name: str = "Alice",
    contact_phone: str = "13800001111",
) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    db.add(
        Customer(
            id=customer_id,
            lead_id=lead_id,
            company_name=company_name,
            contact_name=contact_name,
            contact_phone=contact_phone,
            created_at=now,
            updated_at=now,
        )
    )


def _seed_follow_up(
    db: Session,
    *,
    follow_up_id: uuid.UUID,
    lead_id: uuid.UUID,
    created_by: uuid.UUID,
    content: str,
    created_at: dt.datetime,
    customer_id: uuid.UUID | None = None,
    next_action_at: dt.datetime | None = None,
) -> None:
    db.add(
        FollowUp(
            id=follow_up_id,
            lead_id=lead_id,
            customer_id=customer_id,
            content=content,
            next_action_at=next_action_at,
            created_by=created_by,
            created_at=created_at,
        )
    )


def _auth_headers(role: UserRole, user_id: uuid.UUID) -> dict[str, str]:
    return {
        "X-Actor-Role": role.value,
        "X-Actor-User-Id": str(user_id),
        "X-Request-Id": "test-request-id",
    }


def test_create_follow_up_updates_lead_latest_follow_up_at(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    owner_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=owner_id, role=UserRole.SALES, username="sales1")
        _seed_lead(
            db,
            lead_id=lead_id,
            owner_user_id=owner_id,
            name="Lead A",
            phone="13800000001",
            company_name="Company A",
        )
        db.commit()

    response = client.post(
        "/api/v1/crm/follow-ups",
        headers=_auth_headers(UserRole.SALES, owner_id),
        json={
            "lead_id": str(lead_id),
            "content": "Initial follow-up",
            "next_action_at": "2026-03-19T01:00:00Z",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["lead_id"] == str(lead_id)
    assert payload["created_by"] == str(owner_id)

    created_at = dt.datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))
    with session_factory() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        assert lead is not None
        assert lead.latest_follow_up_at == _as_naive_utc(created_at)
        assert db.query(AuditLog).filter(AuditLog.action == "follow_up.created").count() == 1


def test_create_follow_up_rejects_customer_not_belong_to_lead(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    owner_id = uuid.uuid4()
    lead_a = uuid.uuid4()
    lead_b = uuid.uuid4()
    customer_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=owner_id, role=UserRole.SALES, username="sales1")
        _seed_lead(
            db,
            lead_id=lead_a,
            owner_user_id=owner_id,
            name="Lead A",
            phone="13800000002",
            company_name="Company A",
        )
        _seed_lead(
            db,
            lead_id=lead_b,
            owner_user_id=owner_id,
            name="Lead B",
            phone="13800000003",
            company_name="Company B",
        )
        _seed_customer(db, customer_id=customer_id, lead_id=lead_b)
        db.commit()

    response = client.post(
        "/api/v1/crm/follow-ups",
        headers=_auth_headers(UserRole.SALES, owner_id),
        json={
            "lead_id": str(lead_a),
            "customer_id": str(customer_id),
            "content": "Invalid relation",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Customer does not belong to lead."


def test_list_follow_ups_with_sales_owner_scope(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    sales_a = uuid.uuid4()
    sales_b = uuid.uuid4()
    manager = uuid.uuid4()
    writer = uuid.uuid4()
    lead_a = uuid.uuid4()
    lead_b = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=sales_a, role=UserRole.SALES, username="sales_a")
        _seed_user(db, user_id=sales_b, role=UserRole.SALES, username="sales_b")
        _seed_user(db, user_id=manager, role=UserRole.MANAGER, username="mgr1")
        _seed_user(db, user_id=writer, role=UserRole.SALES, username="writer")
        _seed_lead(
            db,
            lead_id=lead_a,
            owner_user_id=sales_a,
            name="Lead A",
            phone="13800000004",
            company_name="Company A",
        )
        _seed_lead(
            db,
            lead_id=lead_b,
            owner_user_id=sales_b,
            name="Lead B",
            phone="13800000005",
            company_name="Company B",
        )
        _seed_follow_up(
            db,
            follow_up_id=uuid.uuid4(),
            lead_id=lead_a,
            created_by=writer,
            content="A follow-up",
            created_at=_utc(2026, 3, 18, 8, 0),
        )
        _seed_follow_up(
            db,
            follow_up_id=uuid.uuid4(),
            lead_id=lead_b,
            created_by=writer,
            content="B follow-up",
            created_at=_utc(2026, 3, 18, 9, 0),
        )
        db.commit()

    sales_response = client.get(
        "/api/v1/crm/follow-ups",
        headers=_auth_headers(UserRole.SALES, sales_a),
    )
    assert sales_response.status_code == 200
    assert sales_response.json()["total"] == 1
    assert sales_response.json()["items"][0]["lead_id"] == str(lead_a)

    forbidden_response = client.get(
        f"/api/v1/crm/follow-ups?lead_id={lead_b}",
        headers=_auth_headers(UserRole.SALES, sales_a),
    )
    assert forbidden_response.status_code == 403

    manager_response = client.get(
        "/api/v1/crm/follow-ups",
        headers=_auth_headers(UserRole.MANAGER, manager),
    )
    assert manager_response.status_code == 200
    assert manager_response.json()["total"] == 2


def test_update_and_delete_follow_up_recomputes_lead_latest_follow_up_at(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    owner_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    follow_up_1 = uuid.uuid4()
    follow_up_2 = uuid.uuid4()
    ts1 = _utc(2026, 3, 17, 1, 0)
    ts2 = _utc(2026, 3, 18, 1, 0)
    with session_factory() as db:
        _seed_user(db, user_id=owner_id, role=UserRole.SALES, username="sales1")
        _seed_lead(
            db,
            lead_id=lead_id,
            owner_user_id=owner_id,
            name="Lead A",
            phone="13800000006",
            company_name="Company A",
            latest_follow_up_at=ts2,
        )
        _seed_follow_up(
            db,
            follow_up_id=follow_up_1,
            lead_id=lead_id,
            created_by=owner_id,
            content="Older follow-up",
            created_at=ts1,
        )
        _seed_follow_up(
            db,
            follow_up_id=follow_up_2,
            lead_id=lead_id,
            created_by=owner_id,
            content="Latest follow-up",
            created_at=ts2,
        )
        db.commit()

    update_response = client.patch(
        f"/api/v1/crm/follow-ups/{follow_up_1}",
        headers=_auth_headers(UserRole.SALES, owner_id),
        json={"content": "Older follow-up updated"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["content"] == "Older follow-up updated"

    delete_latest_response = client.delete(
        f"/api/v1/crm/follow-ups/{follow_up_2}",
        headers=_auth_headers(UserRole.SALES, owner_id),
    )
    assert delete_latest_response.status_code == 204

    with session_factory() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        assert lead is not None
        assert lead.latest_follow_up_at == _as_naive_utc(ts1)

    delete_last_response = client.delete(
        f"/api/v1/crm/follow-ups/{follow_up_1}",
        headers=_auth_headers(UserRole.SALES, owner_id),
    )
    assert delete_last_response.status_code == 204

    with session_factory() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        assert lead is not None
        assert lead.latest_follow_up_at is None
        actions = {row.action for row in db.query(AuditLog).all()}
        assert {"follow_up.updated", "follow_up.deleted"}.issubset(actions)


def test_manager_is_read_only_for_follow_ups(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    manager_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=manager_id, role=UserRole.MANAGER, username="mgr1")
        _seed_user(db, user_id=owner_id, role=UserRole.SALES, username="sales1")
        _seed_lead(
            db,
            lead_id=lead_id,
            owner_user_id=owner_id,
            name="Lead A",
            phone="13800000007",
            company_name="Company A",
        )
        db.commit()

    create_response = client.post(
        "/api/v1/crm/follow-ups",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
        json={"lead_id": str(lead_id), "content": "manager should fail"},
    )
    assert create_response.status_code == 403

    list_response = client.get(
        "/api/v1/crm/follow-ups",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
    )
    assert list_response.status_code == 200


def test_sales_cannot_create_follow_up_for_foreign_lead(
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
            name="Lead B",
            phone="13800000008",
            company_name="Company B",
        )
        db.commit()

    response = client.post(
        "/api/v1/crm/follow-ups",
        headers=_auth_headers(UserRole.SALES, sales_a),
        json={"lead_id": str(lead_id), "content": "forbidden"},
    )
    assert response.status_code == 403
