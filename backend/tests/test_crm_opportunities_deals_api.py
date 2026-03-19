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
from app.db.models import AuditLog, Deal, Lead, Opportunity, User
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
    phone: str,
    name: str = "Lead",
    company_name: str = "ACME",
) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    db.add(
        Lead(
            id=lead_id,
            name=name,
            phone=phone,
            company_name=company_name,
            source_channel="ad",
            status=LeadStatus.CONTACTED,
            owner_user_id=owner_user_id,
            latest_follow_up_at=None,
            created_at=now,
            updated_at=now,
        )
    )


def _seed_opportunity(
    db: Session,
    *,
    opportunity_id: uuid.UUID,
    lead_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    stage: OpportunityStage,
    amount_estimate: float | None = None,
    customer_id: uuid.UUID | None = None,
    updated_at: dt.datetime | None = None,
) -> None:
    now = updated_at or dt.datetime.now(dt.timezone.utc)
    db.add(
        Opportunity(
            id=opportunity_id,
            lead_id=lead_id,
            customer_id=customer_id,
            stage=stage,
            amount_estimate=amount_estimate,
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
    deal_amount: float,
    deal_date: dt.date,
) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    db.add(
        Deal(
            id=deal_id,
            opportunity_id=opportunity_id,
            deal_amount=deal_amount,
            deal_date=deal_date,
            created_by=created_by,
            created_at=now,
        )
    )


def _auth_headers(role: UserRole, user_id: uuid.UUID) -> dict[str, str]:
    return {
        "X-Actor-Role": role.value,
        "X-Actor-User-Id": str(user_id),
        "X-Request-Id": "test-request-id",
    }


def test_create_and_list_opportunities_with_audit(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    sales_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=sales_id, role=UserRole.SALES, username="sales1")
        _seed_lead(db, lead_id=lead_id, owner_user_id=sales_id, phone="13810000001")
        db.commit()

    create_response = client.post(
        "/api/v1/crm/opportunities",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={"lead_id": str(lead_id), "amount_estimate": 56000.5},
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["lead_id"] == str(lead_id)
    assert payload["stage"] == OpportunityStage.INITIAL.value
    assert payload["owner_user_id"] == str(sales_id)
    opportunity_id = payload["id"]

    list_response = client.get(
        f"/api/v1/crm/opportunities?lead_id={lead_id}",
        headers=_auth_headers(UserRole.SALES, sales_id),
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["id"] == opportunity_id

    detail_response = client.get(
        f"/api/v1/crm/opportunities/{opportunity_id}",
        headers=_auth_headers(UserRole.SALES, sales_id),
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == opportunity_id

    with session_factory() as db:
        assert db.query(AuditLog).filter(AuditLog.action == "opportunity.created").count() == 1


def test_update_opportunity_stage_rules_and_audit(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    sales_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    opportunity_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=sales_id, role=UserRole.SALES, username="sales1")
        _seed_lead(db, lead_id=lead_id, owner_user_id=sales_id, phone="13810000002")
        _seed_opportunity(
            db,
            opportunity_id=opportunity_id,
            lead_id=lead_id,
            owner_user_id=sales_id,
            stage=OpportunityStage.INITIAL,
        )
        db.commit()

    to_proposal = client.patch(
        f"/api/v1/crm/opportunities/{opportunity_id}/stage",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={"stage": OpportunityStage.PROPOSAL.value},
    )
    assert to_proposal.status_code == 200
    assert to_proposal.json()["stage"] == OpportunityStage.PROPOSAL.value

    direct_won = client.patch(
        f"/api/v1/crm/opportunities/{opportunity_id}/stage",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={"stage": OpportunityStage.WON.value},
    )
    assert direct_won.status_code == 400

    lost_without_reason = client.patch(
        f"/api/v1/crm/opportunities/{opportunity_id}/stage",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={"stage": OpportunityStage.LOST.value},
    )
    assert lost_without_reason.status_code == 400

    lost_from_proposal = client.patch(
        f"/api/v1/crm/opportunities/{opportunity_id}/stage",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={
            "stage": OpportunityStage.LOST.value,
            "lost_reason": "budget insufficient",
        },
    )
    assert lost_from_proposal.status_code == 400

    to_negotiation = client.patch(
        f"/api/v1/crm/opportunities/{opportunity_id}/stage",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={"stage": OpportunityStage.NEGOTIATION.value},
    )
    assert to_negotiation.status_code == 200
    assert to_negotiation.json()["stage"] == OpportunityStage.NEGOTIATION.value

    to_lost = client.patch(
        f"/api/v1/crm/opportunities/{opportunity_id}/stage",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={"stage": OpportunityStage.LOST.value, "lost_reason": "client postponed"},
    )
    assert to_lost.status_code == 200
    assert to_lost.json()["stage"] == OpportunityStage.LOST.value

    with session_factory() as db:
        logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "opportunity.stage_changed",
                AuditLog.target_id == str(opportunity_id),
            )
            .order_by(AuditLog.created_at.asc())
            .all()
        )
        assert len(logs) == 3
        assert logs[-1].after_data is not None
        assert logs[-1].after_data.get("lost_reason") == "client postponed"


def test_create_deal_sets_opportunity_won_and_supports_list(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    sales_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    opportunity_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=sales_id, role=UserRole.SALES, username="sales1")
        _seed_lead(db, lead_id=lead_id, owner_user_id=sales_id, phone="13810000003")
        _seed_opportunity(
            db,
            opportunity_id=opportunity_id,
            lead_id=lead_id,
            owner_user_id=sales_id,
            stage=OpportunityStage.NEGOTIATION,
        )
        db.commit()

    create_response = client.post(
        "/api/v1/crm/deals",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={
            "opportunity_id": str(opportunity_id),
            "deal_amount": 128888.88,
            "deal_date": "2026-03-18",
        },
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["opportunity_id"] == str(opportunity_id)
    assert payload["deal_amount"] == 128888.88

    list_response = client.get(
        f"/api/v1/crm/deals?opportunity_id={opportunity_id}",
        headers=_auth_headers(UserRole.SALES, sales_id),
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    with session_factory() as db:
        opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        assert opportunity is not None
        assert opportunity.stage == OpportunityStage.WON
        actions = {row.action for row in db.query(AuditLog).all()}
        assert {"opportunity.stage_changed", "deal.created"}.issubset(actions)


def test_create_deal_requires_negotiation_and_prevents_duplicate(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    sales_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    proposal_opportunity_id = uuid.uuid4()
    duplicate_opportunity_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=sales_id, role=UserRole.SALES, username="sales1")
        _seed_lead(db, lead_id=lead_id, owner_user_id=sales_id, phone="13810000004")
        _seed_opportunity(
            db,
            opportunity_id=proposal_opportunity_id,
            lead_id=lead_id,
            owner_user_id=sales_id,
            stage=OpportunityStage.PROPOSAL,
        )
        _seed_opportunity(
            db,
            opportunity_id=duplicate_opportunity_id,
            lead_id=lead_id,
            owner_user_id=sales_id,
            stage=OpportunityStage.NEGOTIATION,
        )
        _seed_deal(
            db,
            deal_id=uuid.uuid4(),
            opportunity_id=duplicate_opportunity_id,
            created_by=sales_id,
            deal_amount=3000,
            deal_date=dt.date(2026, 3, 18),
        )
        db.commit()

    invalid_stage_response = client.post(
        "/api/v1/crm/deals",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={
            "opportunity_id": str(proposal_opportunity_id),
            "deal_amount": 4500,
            "deal_date": "2026-03-18",
        },
    )
    assert invalid_stage_response.status_code == 400

    duplicate_response = client.post(
        "/api/v1/crm/deals",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={
            "opportunity_id": str(duplicate_opportunity_id),
            "deal_amount": 4500,
            "deal_date": "2026-03-18",
        },
    )
    assert duplicate_response.status_code == 409


def test_sales_owner_scope_and_manager_read_only(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    sales_a = uuid.uuid4()
    sales_b = uuid.uuid4()
    manager_id = uuid.uuid4()
    lead_a = uuid.uuid4()
    lead_b = uuid.uuid4()
    opportunity_a = uuid.uuid4()
    opportunity_b = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=sales_a, role=UserRole.SALES, username="sales_a")
        _seed_user(db, user_id=sales_b, role=UserRole.SALES, username="sales_b")
        _seed_user(db, user_id=manager_id, role=UserRole.MANAGER, username="manager1")
        _seed_lead(db, lead_id=lead_a, owner_user_id=sales_a, phone="13810000005")
        _seed_lead(db, lead_id=lead_b, owner_user_id=sales_b, phone="13810000006")
        _seed_opportunity(
            db,
            opportunity_id=opportunity_a,
            lead_id=lead_a,
            owner_user_id=sales_a,
            stage=OpportunityStage.INITIAL,
        )
        _seed_opportunity(
            db,
            opportunity_id=opportunity_b,
            lead_id=lead_b,
            owner_user_id=sales_b,
            stage=OpportunityStage.NEGOTIATION,
        )
        db.commit()

    sales_list_response = client.get(
        "/api/v1/crm/opportunities",
        headers=_auth_headers(UserRole.SALES, sales_a),
    )
    assert sales_list_response.status_code == 200
    assert sales_list_response.json()["total"] == 1
    assert sales_list_response.json()["items"][0]["id"] == str(opportunity_a)

    forbidden_list_response = client.get(
        f"/api/v1/crm/opportunities?lead_id={lead_b}",
        headers=_auth_headers(UserRole.SALES, sales_a),
    )
    assert forbidden_list_response.status_code == 403

    forbidden_create_deal = client.post(
        "/api/v1/crm/deals",
        headers=_auth_headers(UserRole.SALES, sales_a),
        json={
            "opportunity_id": str(opportunity_b),
            "deal_amount": 8600,
            "deal_date": "2026-03-18",
        },
    )
    assert forbidden_create_deal.status_code == 403

    manager_update_response = client.patch(
        f"/api/v1/crm/opportunities/{opportunity_a}/stage",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
        json={"stage": OpportunityStage.PROPOSAL.value},
    )
    assert manager_update_response.status_code == 403

    manager_list_response = client.get(
        "/api/v1/crm/opportunities",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
    )
    assert manager_list_response.status_code == 200
    assert manager_list_response.json()["total"] == 2


def test_opportunity_stats_respects_owner_scope_and_amount_sum(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    sales_a = uuid.uuid4()
    sales_b = uuid.uuid4()
    manager_id = uuid.uuid4()
    lead_a = uuid.uuid4()
    lead_b = uuid.uuid4()
    opp_a_initial = uuid.uuid4()
    opp_a_negotiation = uuid.uuid4()
    opp_a_won = uuid.uuid4()
    opp_b_won = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=sales_a, role=UserRole.SALES, username="sales_a")
        _seed_user(db, user_id=sales_b, role=UserRole.SALES, username="sales_b")
        _seed_user(db, user_id=manager_id, role=UserRole.MANAGER, username="manager1")
        _seed_lead(db, lead_id=lead_a, owner_user_id=sales_a, phone="13810000007")
        _seed_lead(db, lead_id=lead_b, owner_user_id=sales_b, phone="13810000008")
        _seed_opportunity(
            db,
            opportunity_id=opp_a_initial,
            lead_id=lead_a,
            owner_user_id=sales_a,
            stage=OpportunityStage.INITIAL,
            updated_at=_utc(2026, 3, 18, 1, 0),
        )
        _seed_opportunity(
            db,
            opportunity_id=opp_a_negotiation,
            lead_id=lead_a,
            owner_user_id=sales_a,
            stage=OpportunityStage.NEGOTIATION,
            updated_at=_utc(2026, 3, 18, 2, 0),
        )
        _seed_opportunity(
            db,
            opportunity_id=opp_a_won,
            lead_id=lead_a,
            owner_user_id=sales_a,
            stage=OpportunityStage.WON,
            updated_at=_utc(2026, 3, 18, 3, 0),
        )
        _seed_opportunity(
            db,
            opportunity_id=opp_b_won,
            lead_id=lead_b,
            owner_user_id=sales_b,
            stage=OpportunityStage.WON,
            updated_at=_utc(2026, 3, 18, 4, 0),
        )
        _seed_deal(
            db,
            deal_id=uuid.uuid4(),
            opportunity_id=opp_a_won,
            created_by=sales_a,
            deal_amount=1000.5,
            deal_date=dt.date(2026, 3, 18),
        )
        _seed_deal(
            db,
            deal_id=uuid.uuid4(),
            opportunity_id=opp_b_won,
            created_by=sales_b,
            deal_amount=300.0,
            deal_date=dt.date(2026, 3, 18),
        )
        db.commit()

    sales_stats = client.get(
        "/api/v1/crm/opportunities/stats",
        headers=_auth_headers(UserRole.SALES, sales_a),
    )
    assert sales_stats.status_code == 200
    sales_payload = sales_stats.json()
    assert sales_payload["opportunity_total"] == 3
    assert sales_payload["stage_counts"]["initial"] == 1
    assert sales_payload["stage_counts"]["negotiation"] == 1
    assert sales_payload["stage_counts"]["won"] == 1
    assert sales_payload["deal_count"] == 1
    assert sales_payload["deal_amount_sum"] == pytest.approx(1000.5)

    manager_stats = client.get(
        "/api/v1/crm/opportunities/stats",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
    )
    assert manager_stats.status_code == 200
    manager_payload = manager_stats.json()
    assert manager_payload["opportunity_total"] == 4
    assert manager_payload["deal_count"] == 2
    assert manager_payload["deal_amount_sum"] == pytest.approx(1300.5)
