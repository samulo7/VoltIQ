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
from app.db.enums import LeadStatus, OpportunityStage, UserRole, UserStatus
from app.db.models import Deal, Lead, Opportunity, User
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
    status: LeadStatus,
    created_at: dt.datetime,
    phone: str,
) -> None:
    db.add(
        Lead(
            id=lead_id,
            name="Lead",
            phone=phone,
            company_name="ACME",
            source_channel="ad",
            status=status,
            owner_user_id=owner_user_id,
            latest_follow_up_at=None,
            created_at=created_at,
            updated_at=created_at,
        )
    )


def _seed_opportunity(
    db: Session,
    *,
    opportunity_id: uuid.UUID,
    lead_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    stage: OpportunityStage = OpportunityStage.WON,
) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    db.add(
        Opportunity(
            id=opportunity_id,
            lead_id=lead_id,
            customer_id=None,
            stage=stage,
            amount_estimate=1000,
            owner_user_id=owner_user_id,
            created_at=now,
            updated_at=now,
        )
    )


def _seed_deal(
    db: Session,
    *,
    deal_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    created_by: uuid.UUID,
    deal_date: dt.date,
) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    db.add(
        Deal(
            id=deal_id,
            opportunity_id=opportunity_id,
            deal_amount=1000,
            deal_date=deal_date,
            created_by=created_by,
            created_at=now,
        )
    )


def _auth_headers(role: UserRole, user_id: uuid.UUID) -> dict[str, str]:
    return {
        "X-Actor-Role": role.value,
        "X-Actor-User-Id": str(user_id),
        "X-Request-Id": "metrics-test-request-id",
    }


def test_metrics_overview_applies_sales_scope_and_shanghai_day_boundaries(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client

    sales_a = uuid.uuid4()
    sales_b = uuid.uuid4()
    manager = uuid.uuid4()
    lead_a1 = uuid.uuid4()
    lead_a2 = uuid.uuid4()
    lead_a3 = uuid.uuid4()
    lead_a_out = uuid.uuid4()
    lead_b1 = uuid.uuid4()
    lead_b2 = uuid.uuid4()
    opp_a1 = uuid.uuid4()
    opp_a2 = uuid.uuid4()
    opp_b1 = uuid.uuid4()

    with session_factory() as db:
        _seed_user(db, user_id=sales_a, role=UserRole.SALES, username="sales_a")
        _seed_user(db, user_id=sales_b, role=UserRole.SALES, username="sales_b")
        _seed_user(db, user_id=manager, role=UserRole.MANAGER, username="manager")

        _seed_lead(
            db,
            lead_id=lead_a_out,
            owner_user_id=sales_a,
            status=LeadStatus.CONTACTED,
            created_at=_utc(2026, 3, 19, 15, 59),  # Shanghai: 2026-03-19 23:59
            phone="13800000001",
        )
        _seed_lead(
            db,
            lead_id=lead_a1,
            owner_user_id=sales_a,
            status=LeadStatus.NEW,
            created_at=_utc(2026, 3, 19, 16, 30),  # Shanghai: 2026-03-20 00:30
            phone="13800000002",
        )
        _seed_lead(
            db,
            lead_id=lead_a2,
            owner_user_id=sales_a,
            status=LeadStatus.CONTACTED,
            created_at=_utc(2026, 3, 20, 10, 0),  # Shanghai: 2026-03-20 18:00
            phone="13800000003",
        )
        _seed_lead(
            db,
            lead_id=lead_a3,
            owner_user_id=sales_a,
            status=LeadStatus.CONVERTED,
            created_at=_utc(2026, 3, 20, 18, 0),  # Shanghai: 2026-03-21 02:00
            phone="13800000004",
        )
        _seed_lead(
            db,
            lead_id=lead_b1,
            owner_user_id=sales_b,
            status=LeadStatus.CONTACTED,
            created_at=_utc(2026, 3, 19, 18, 0),  # Shanghai: 2026-03-20 02:00
            phone="13800000005",
        )
        _seed_lead(
            db,
            lead_id=lead_b2,
            owner_user_id=sales_b,
            status=LeadStatus.INVALID,
            created_at=_utc(2026, 3, 20, 17, 0),  # Shanghai: 2026-03-21 01:00
            phone="13800000006",
        )

        _seed_opportunity(db, opportunity_id=opp_a1, lead_id=lead_a1, owner_user_id=sales_a)
        _seed_opportunity(db, opportunity_id=opp_a2, lead_id=lead_a2, owner_user_id=sales_a)
        _seed_opportunity(db, opportunity_id=opp_b1, lead_id=lead_b1, owner_user_id=sales_b)

        _seed_deal(
            db,
            deal_id=uuid.uuid4(),
            opportunity_id=opp_a1,
            created_by=sales_a,
            deal_date=dt.date(2026, 3, 20),
        )
        _seed_deal(
            db,
            deal_id=uuid.uuid4(),
            opportunity_id=opp_a2,
            created_by=sales_a,
            deal_date=dt.date(2026, 3, 21),
        )
        _seed_deal(
            db,
            deal_id=uuid.uuid4(),
            opportunity_id=opp_b1,
            created_by=sales_b,
            deal_date=dt.date(2026, 3, 20),
        )
        db.commit()

    sales_resp = client.get(
        "/api/v1/metrics/overview?start_date=2026-03-20&end_date=2026-03-21",
        headers=_auth_headers(UserRole.SALES, sales_a),
    )
    assert sales_resp.status_code == 200
    sales_payload = sales_resp.json()
    assert sales_payload["timezone"] == "Asia/Shanghai"
    assert sales_payload["start_date"] == "2026-03-20"
    assert sales_payload["end_date"] == "2026-03-21"
    assert sales_payload["summary"]["lead_count"] == 3
    assert sales_payload["summary"]["effective_lead_count"] == 2
    assert sales_payload["summary"]["deal_count"] == 2
    assert sales_payload["summary"]["conversion_rate"] == pytest.approx(1.0)
    assert sales_payload["daily"] == [
        {
            "date": "2026-03-20",
            "lead_count": 2,
            "deal_count": 1,
            "effective_lead_count": 1,
            "conversion_rate": 1.0,
        },
        {
            "date": "2026-03-21",
            "lead_count": 1,
            "deal_count": 1,
            "effective_lead_count": 1,
            "conversion_rate": 1.0,
        },
    ]

    manager_resp = client.get(
        "/api/v1/metrics/overview?start_date=2026-03-20&end_date=2026-03-21",
        headers=_auth_headers(UserRole.MANAGER, manager),
    )
    assert manager_resp.status_code == 200
    manager_payload = manager_resp.json()
    assert manager_payload["summary"]["lead_count"] == 5
    assert manager_payload["summary"]["effective_lead_count"] == 3
    assert manager_payload["summary"]["deal_count"] == 3
    assert manager_payload["summary"]["conversion_rate"] == pytest.approx(1.0)
    assert manager_payload["daily"] == [
        {
            "date": "2026-03-20",
            "lead_count": 3,
            "deal_count": 2,
            "effective_lead_count": 2,
            "conversion_rate": 1.0,
        },
        {
            "date": "2026-03-21",
            "lead_count": 2,
            "deal_count": 1,
            "effective_lead_count": 1,
            "conversion_rate": 1.0,
        },
    ]


def test_metrics_overview_forbidden_for_operator_and_invalid_date_range(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    manager = uuid.uuid4()
    operator = uuid.uuid4()

    with session_factory() as db:
        _seed_user(db, user_id=manager, role=UserRole.MANAGER, username="manager")
        _seed_user(db, user_id=operator, role=UserRole.OPERATOR, username="operator")
        db.commit()

    operator_resp = client.get(
        "/api/v1/metrics/overview?start_date=2026-03-20&end_date=2026-03-21",
        headers=_auth_headers(UserRole.OPERATOR, operator),
    )
    assert operator_resp.status_code == 403

    invalid_range_resp = client.get(
        "/api/v1/metrics/overview?start_date=2026-03-22&end_date=2026-03-21",
        headers=_auth_headers(UserRole.MANAGER, manager),
    )
    assert invalid_range_resp.status_code == 400
    assert invalid_range_resp.json()["detail"] == "start_date must be less than or equal to end_date."


def test_metrics_overview_defaults_today_and_returns_zero_conversion_when_denominator_is_zero(
    api_client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    manager = uuid.uuid4()
    sales = uuid.uuid4()
    lead_id = uuid.uuid4()

    monkeypatch.setattr("app.modules.metrics.service._today_in_shanghai", lambda: dt.date(2026, 3, 20))

    with session_factory() as db:
        _seed_user(db, user_id=manager, role=UserRole.MANAGER, username="manager")
        _seed_user(db, user_id=sales, role=UserRole.SALES, username="sales")
        _seed_lead(
            db,
            lead_id=lead_id,
            owner_user_id=sales,
            status=LeadStatus.NEW,
            created_at=_utc(2026, 3, 20, 2, 0),
            phone="13800000007",
        )
        db.commit()

    response = client.get(
        "/api/v1/metrics/overview",
        headers=_auth_headers(UserRole.MANAGER, manager),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["start_date"] == "2026-03-20"
    assert payload["end_date"] == "2026-03-20"
    assert payload["summary"]["lead_count"] == 1
    assert payload["summary"]["effective_lead_count"] == 0
    assert payload["summary"]["deal_count"] == 0
    assert payload["summary"]["conversion_rate"] == 0
    assert payload["daily"] == [
        {
            "date": "2026-03-20",
            "lead_count": 1,
            "deal_count": 0,
            "effective_lead_count": 0,
            "conversion_rate": 0.0,
        }
    ]
