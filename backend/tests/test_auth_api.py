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
from app.db.enums import UserRole, UserStatus
from app.db.models import User
from app.main import create_app
from app.modules.auth.security import hash_password


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


def _seed_user(
    db: Session,
    *,
    username: str,
    password: str,
    role: UserRole = UserRole.OPERATOR,
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    now = dt.datetime.now(dt.timezone.utc)
    user = User(
        id=uuid.uuid4(),
        username=username,
        password_hash=hash_password(password),
        role=role,
        status=status,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.flush()
    return user


def test_login_and_me_success(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, session_factory = api_client
    with session_factory() as db:
        _seed_user(db, username="operator_demo", password="voltiq123", role=UserRole.OPERATOR)
        db.commit()

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "operator_demo", "password": "voltiq123"},
    )
    assert login_resp.status_code == 200
    payload = login_resp.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["username"] == "operator_demo"
    assert payload["user"]["role"] == "operator"
    assert payload["access_token"]
    assert payload["refresh_token"]

    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me_resp.status_code == 200
    me_payload = me_resp.json()
    assert me_payload["username"] == "operator_demo"
    assert me_payload["role"] == "operator"


def test_login_invalid_password_returns_401(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    with session_factory() as db:
        _seed_user(db, username="sales_demo", password="voltiq123", role=UserRole.SALES)
        db.commit()

    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "sales_demo", "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid username or password."


def test_login_disabled_user_returns_403(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, session_factory = api_client
    with session_factory() as db:
        _seed_user(
            db,
            username="disabled_demo",
            password="voltiq123",
            role=UserRole.MANAGER,
            status=UserStatus.DISABLED,
        )
        db.commit()

    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "disabled_demo", "password": "voltiq123"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "User is disabled."


def test_refresh_issues_new_token_pair(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, session_factory = api_client
    with session_factory() as db:
        _seed_user(db, username="manager_demo", password="voltiq123", role=UserRole.MANAGER)
        db.commit()

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "manager_demo", "password": "voltiq123"},
    )
    login_payload = login_resp.json()

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_payload["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    refresh_payload = refresh_resp.json()
    assert refresh_payload["token_type"] == "bearer"
    assert refresh_payload["access_token"]
    assert refresh_payload["refresh_token"]
    assert refresh_payload["access_token"] != login_payload["access_token"]


def test_me_requires_bearer_token(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api_client
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Missing Authorization header."

