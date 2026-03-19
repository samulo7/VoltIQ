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
from app.db.enums import ContentTaskStatus, ContentTaskType, UserRole, UserStatus
from app.db.models import AuditLog, ContentTask, User
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


def _seed_content_task(
    db: Session,
    *,
    task_id: uuid.UUID,
    task_type: ContentTaskType,
    status: ContentTaskStatus,
    prompt: str,
    created_by: uuid.UUID,
    created_at: dt.datetime,
) -> None:
    db.add(
        ContentTask(
            id=task_id,
            task_type=task_type,
            prompt=prompt,
            status=status,
            result_text="seed-result",
            result_meta={"seed": True, "task_type": task_type.value},
            created_by=created_by,
            created_at=created_at,
            updated_at=created_at,
        )
    )


def _auth_headers(role: UserRole, user_id: uuid.UUID) -> dict[str, str]:
    return {
        "X-Actor-Role": role.value,
        "X-Actor-User-Id": str(user_id),
        "X-Request-Id": "test-request-id",
    }


def test_create_content_tasks_for_all_types_and_write_audit(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    operator_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="operator1")
        db.commit()

    for task_type in (
        ContentTaskType.COPYWRITING,
        ContentTaskType.IMAGE,
        ContentTaskType.VIDEO_SCRIPT,
    ):
        response = client.post(
            "/api/v1/content/tasks",
            headers=_auth_headers(UserRole.OPERATOR, operator_id),
            json={"task_type": task_type.value, "prompt": f"prompt for {task_type.value}"},
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["task_type"] == task_type.value
        assert payload["status"] == ContentTaskStatus.SUCCEEDED.value
        assert payload["result_text"]
        assert payload["result_meta"]["provider"] == "placeholder"
        assert payload["result_meta"]["task_type"] == task_type.value

    with session_factory() as db:
        assert db.query(ContentTask).count() == 3
        created_count = db.query(AuditLog).filter(AuditLog.action == "content_task.created").count()
        assert created_count == 3


def test_list_content_tasks_with_filters_and_pagination(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    operator_id = uuid.uuid4()
    manager_id = uuid.uuid4()
    created_at_1 = dt.datetime(2026, 3, 18, 1, 0, tzinfo=dt.timezone.utc)
    created_at_2 = dt.datetime(2026, 3, 18, 2, 0, tzinfo=dt.timezone.utc)
    created_at_3 = dt.datetime(2026, 3, 18, 3, 0, tzinfo=dt.timezone.utc)
    task_1 = uuid.uuid4()
    task_2 = uuid.uuid4()
    task_3 = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="operator1")
        _seed_user(db, user_id=manager_id, role=UserRole.MANAGER, username="manager1")
        _seed_content_task(
            db,
            task_id=task_1,
            task_type=ContentTaskType.COPYWRITING,
            status=ContentTaskStatus.SUCCEEDED,
            prompt="copywriting prompt",
            created_by=operator_id,
            created_at=created_at_1,
        )
        _seed_content_task(
            db,
            task_id=task_2,
            task_type=ContentTaskType.IMAGE,
            status=ContentTaskStatus.PENDING,
            prompt="image prompt pending",
            created_by=operator_id,
            created_at=created_at_2,
        )
        _seed_content_task(
            db,
            task_id=task_3,
            task_type=ContentTaskType.IMAGE,
            status=ContentTaskStatus.SUCCEEDED,
            prompt="image prompt succeeded",
            created_by=manager_id,
            created_at=created_at_3,
        )
        db.commit()

    filter_response = client.get(
        (
            "/api/v1/content/tasks?"
            f"task_type={ContentTaskType.IMAGE.value}&"
            f"status={ContentTaskStatus.SUCCEEDED.value}&"
            f"created_by={manager_id}"
        ),
        headers=_auth_headers(UserRole.MANAGER, manager_id),
    )
    assert filter_response.status_code == 200
    payload = filter_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == str(task_3)

    pagination_response = client.get(
        "/api/v1/content/tasks?limit=1&offset=1",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
    )
    assert pagination_response.status_code == 200
    pagination_payload = pagination_response.json()
    assert pagination_payload["total"] == 3
    assert len(pagination_payload["items"]) == 1


def test_get_content_task_detail_records_query_audit(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    operator_id = uuid.uuid4()
    task_id = uuid.uuid4()
    now = dt.datetime(2026, 3, 18, 1, 0, tzinfo=dt.timezone.utc)
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="operator1")
        _seed_content_task(
            db,
            task_id=task_id,
            task_type=ContentTaskType.VIDEO_SCRIPT,
            status=ContentTaskStatus.SUCCEEDED,
            prompt="video prompt",
            created_by=operator_id,
            created_at=now,
        )
        db.commit()

    detail_response = client.get(
        f"/api/v1/content/tasks/{task_id}",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == str(task_id)

    with session_factory() as db:
        logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "content_task.queried",
                AuditLog.target_id == str(task_id),
            )
            .all()
        )
        assert len(logs) == 1


def test_content_task_rbac_operator_manager_sales(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = api_client
    operator_id = uuid.uuid4()
    manager_id = uuid.uuid4()
    sales_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="operator1")
        _seed_user(db, user_id=manager_id, role=UserRole.MANAGER, username="manager1")
        _seed_user(db, user_id=sales_id, role=UserRole.SALES, username="sales1")
        db.commit()

    operator_create = client.post(
        "/api/v1/content/tasks",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
        json={"task_type": ContentTaskType.COPYWRITING.value, "prompt": "operator prompt"},
    )
    assert operator_create.status_code == 201
    task_id = operator_create.json()["id"]

    manager_create = client.post(
        "/api/v1/content/tasks",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
        json={"task_type": ContentTaskType.COPYWRITING.value, "prompt": "manager prompt"},
    )
    assert manager_create.status_code == 403

    manager_list = client.get(
        "/api/v1/content/tasks",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
    )
    assert manager_list.status_code == 200

    manager_detail = client.get(
        f"/api/v1/content/tasks/{task_id}",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
    )
    assert manager_detail.status_code == 200

    sales_list = client.get(
        "/api/v1/content/tasks",
        headers=_auth_headers(UserRole.SALES, sales_id),
    )
    assert sales_list.status_code == 403

    sales_create = client.post(
        "/api/v1/content/tasks",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={"task_type": ContentTaskType.IMAGE.value, "prompt": "sales prompt"},
    )
    assert sales_create.status_code == 403

    sales_detail = client.get(
        f"/api/v1/content/tasks/{task_id}",
        headers=_auth_headers(UserRole.SALES, sales_id),
    )
    assert sales_detail.status_code == 403
