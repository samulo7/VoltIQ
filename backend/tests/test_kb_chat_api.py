from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.db.base import Base
from app.db.enums import KbMessageRole, UserRole, UserStatus
from app.db.models import AuditLog, KbMessage, KbSession, User
from app.integrations.dify.exceptions import DifyRequestError
from app.integrations.dify.schemas import DifyChatResult, DifyRetrieverResource
from app.main import create_app
from app.modules.kb.deps import get_dify_client


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type: JSONB, _compiler: object, **_kw: object) -> str:
    return "JSON"


@compiles(PGUUID, "sqlite")
def _compile_uuid_sqlite(_type: PGUUID, _compiler: object, **_kw: object) -> str:
    return "TEXT"


class FakeDifyClient:
    def __init__(self, responses: list[DifyChatResult | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def send_chat_message(
        self,
        *,
        query: str,
        user: str,
        conversation_id: str | None = None,
        inputs: dict[str, object] | None = None,
    ) -> DifyChatResult:
        self.calls.append(
            {
                "query": query,
                "user": user,
                "conversation_id": conversation_id,
            }
        )
        if not self._responses:
            raise AssertionError("No fake Dify response queued.")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture()
def api_client() -> Generator[
    tuple[TestClient, sessionmaker[Session], Callable[[FakeDifyClient], None]],
    None,
    None,
]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    app = create_app()
    dify_client_holder = {"client": FakeDifyClient([])}

    def _override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    def _override_get_dify_client() -> FakeDifyClient:
        return dify_client_holder["client"]

    def _set_dify_client(client: FakeDifyClient) -> None:
        dify_client_holder["client"] = client

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_dify_client] = _override_get_dify_client
    client = TestClient(app)
    try:
        yield client, session_factory, _set_dify_client
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


def _seed_session(
    db: Session,
    *,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    session_key: str,
    created_at: dt.datetime,
    updated_at: dt.datetime,
) -> None:
    db.add(
        KbSession(
            id=session_id,
            user_id=user_id,
            session_key=session_key,
            created_at=created_at,
            updated_at=updated_at,
        )
    )


def _auth_headers(role: UserRole, user_id: uuid.UUID) -> dict[str, str]:
    return {
        "X-Actor-Role": role.value,
        "X-Actor-User-Id": str(user_id),
        "X-Request-Id": "test-request-id",
    }


def _make_chat_result(
    *,
    message_id: str,
    conversation_id: str,
    answer: str,
    source_count: int = 1,
) -> DifyChatResult:
    resources = tuple(
        DifyRetrieverResource(
            position=index + 1,
            dataset_id=f"dataset-{index + 1}",
            dataset_name=f"dataset-name-{index + 1}",
            document_id=f"doc-{index + 1}",
            document_name=f"doc-name-{index + 1}",
            segment_id=f"seg-{index + 1}",
            score=0.9 - index * 0.1,
            content=f"source-content-{index + 1}",
        )
        for index in range(source_count)
    )
    return DifyChatResult(
        message_id=message_id,
        conversation_id=conversation_id,
        answer=answer,
        retriever_resources=resources,
        raw_payload={"mocked": True},
    )


def test_chat_auto_creates_session_and_persists_messages(
    api_client: tuple[TestClient, sessionmaker[Session], Callable[[FakeDifyClient], None]],
) -> None:
    client, session_factory, set_dify_client = api_client
    operator_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="operator1")
        db.commit()

    fake_dify = FakeDifyClient(
        [
            _make_chat_result(
                message_id="msg-1",
                conversation_id="conv-1",
                answer="这是基于知识库的回答。",
            )
        ]
    )
    set_dify_client(fake_dify)

    response = client.post(
        "/api/v1/kb/sessions/chat",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
        json={"query": "请解释直接交易定义"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["session_key"] == "conv-1"
    assert payload["conversation_id"] == "conv-1"
    assert payload["message_id"] == "msg-1"
    assert payload["answer"]
    assert len(payload["sources"]) == 1

    with session_factory() as db:
        session = db.query(KbSession).filter(KbSession.session_key == "conv-1").first()
        assert session is not None
        assert session.user_id == operator_id

        user_messages = db.query(KbMessage).filter(KbMessage.role == KbMessageRole.USER).count()
        assistant_messages = (
            db.query(KbMessage).filter(KbMessage.role == KbMessageRole.ASSISTANT).count()
        )
        assert user_messages == 1
        assert assistant_messages == 1

        assistant_message = (
            db.query(KbMessage).filter(KbMessage.role == KbMessageRole.ASSISTANT).first()
        )
        assert assistant_message is not None
        assert assistant_message.source_refs is not None
        assert len(assistant_message.source_refs.get("retriever_resources", [])) == 1
        assert db.query(AuditLog).filter(AuditLog.action == "kb.session.chatted").count() == 1


def test_chat_with_existing_session_uses_conversation_id(
    api_client: tuple[TestClient, sessionmaker[Session], Callable[[FakeDifyClient], None]],
) -> None:
    client, session_factory, set_dify_client = api_client
    operator_id = uuid.uuid4()
    session_id = uuid.uuid4()
    base_time = dt.datetime(2026, 3, 20, 8, 0, tzinfo=dt.timezone.utc)
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="operator1")
        _seed_session(
            db,
            session_id=session_id,
            user_id=operator_id,
            session_key="conv-keep",
            created_at=base_time,
            updated_at=base_time,
        )
        db.commit()

    fake_dify = FakeDifyClient(
        [
            _make_chat_result(
                message_id="msg-2",
                conversation_id="conv-keep",
                answer="继续对话回答。",
            )
        ]
    )
    set_dify_client(fake_dify)

    response = client.post(
        "/api/v1/kb/sessions/chat",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
        json={"query": "继续说明", "session_key": "conv-keep"},
    )
    assert response.status_code == 200
    assert response.json()["session_key"] == "conv-keep"
    assert fake_dify.calls[0]["conversation_id"] == "conv-keep"

    with session_factory() as db:
        session = db.query(KbSession).filter(KbSession.id == session_id).first()
        assert session is not None
        baseline = base_time
        if session.updated_at.tzinfo is None:
            baseline = base_time.replace(tzinfo=None)
        assert session.updated_at > baseline
        assert db.query(KbMessage).filter(KbMessage.session_id == session_id).count() == 2


def test_chat_rejects_foreign_session_key(
    api_client: tuple[TestClient, sessionmaker[Session], Callable[[FakeDifyClient], None]],
) -> None:
    client, session_factory, set_dify_client = api_client
    operator_id = uuid.uuid4()
    manager_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="operator1")
        _seed_user(db, user_id=manager_id, role=UserRole.MANAGER, username="manager1")
        _seed_session(
            db,
            session_id=uuid.uuid4(),
            user_id=manager_id,
            session_key="conv-manager",
            created_at=dt.datetime.now(dt.timezone.utc),
            updated_at=dt.datetime.now(dt.timezone.utc),
        )
        db.commit()

    set_dify_client(
        FakeDifyClient(
            [
                _make_chat_result(
                    message_id="msg-unreachable",
                    conversation_id="conv-manager",
                    answer="should not happen",
                )
            ]
        )
    )

    response = client.post(
        "/api/v1/kb/sessions/chat",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
        json={"query": "越权会话", "session_key": "conv-manager"},
    )
    assert response.status_code == 403

    with session_factory() as db:
        assert db.query(KbMessage).count() == 0


def test_chat_fails_when_sources_missing_without_partial_writes(
    api_client: tuple[TestClient, sessionmaker[Session], Callable[[FakeDifyClient], None]],
) -> None:
    client, session_factory, set_dify_client = api_client
    operator_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="operator1")
        db.commit()

    set_dify_client(
        FakeDifyClient(
            [
                _make_chat_result(
                    message_id="msg-3",
                    conversation_id="conv-3",
                    answer="回答没有来源。",
                    source_count=0,
                )
            ]
        )
    )

    response = client.post(
        "/api/v1/kb/sessions/chat",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
        json={"query": "来源为空会失败"},
    )
    assert response.status_code == 502
    assert "retriever resources" in response.json()["detail"]

    with session_factory() as db:
        assert db.query(KbSession).count() == 0
        assert db.query(KbMessage).count() == 0


def test_chat_maps_dify_timeout_to_504(
    api_client: tuple[TestClient, sessionmaker[Session], Callable[[FakeDifyClient], None]],
) -> None:
    client, session_factory, set_dify_client = api_client
    operator_id = uuid.uuid4()
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="operator1")
        db.commit()

    set_dify_client(
        FakeDifyClient(
            [
                DifyRequestError("timeout", status_code=504),
            ]
        )
    )

    response = client.post(
        "/api/v1/kb/sessions/chat",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
        json={"query": "超时场景"},
    )
    assert response.status_code == 504


def test_kb_rbac_and_session_list_scope(
    api_client: tuple[TestClient, sessionmaker[Session], Callable[[FakeDifyClient], None]],
) -> None:
    client, session_factory, set_dify_client = api_client
    operator_id = uuid.uuid4()
    manager_id = uuid.uuid4()
    sales_id = uuid.uuid4()
    base_time = dt.datetime(2026, 3, 20, 0, 0, tzinfo=dt.timezone.utc)
    with session_factory() as db:
        _seed_user(db, user_id=operator_id, role=UserRole.OPERATOR, username="operator1")
        _seed_user(db, user_id=manager_id, role=UserRole.MANAGER, username="manager1")
        _seed_user(db, user_id=sales_id, role=UserRole.SALES, username="sales1")
        _seed_session(
            db,
            session_id=uuid.uuid4(),
            user_id=operator_id,
            session_key="conv-op-1",
            created_at=base_time,
            updated_at=base_time + dt.timedelta(minutes=1),
        )
        _seed_session(
            db,
            session_id=uuid.uuid4(),
            user_id=operator_id,
            session_key="conv-op-2",
            created_at=base_time,
            updated_at=base_time + dt.timedelta(minutes=2),
        )
        _seed_session(
            db,
            session_id=uuid.uuid4(),
            user_id=operator_id,
            session_key="conv-op-3",
            created_at=base_time,
            updated_at=base_time + dt.timedelta(minutes=3),
        )
        _seed_session(
            db,
            session_id=uuid.uuid4(),
            user_id=manager_id,
            session_key="conv-mgr-1",
            created_at=base_time,
            updated_at=base_time + dt.timedelta(minutes=4),
        )
        db.commit()

    set_dify_client(
        FakeDifyClient(
            [
                _make_chat_result(
                    message_id="msg-op",
                    conversation_id="conv-op-chat",
                    answer="operator answer",
                ),
                _make_chat_result(
                    message_id="msg-mgr",
                    conversation_id="conv-mgr-chat",
                    answer="manager answer",
                ),
            ]
        )
    )

    operator_list = client.get(
        "/api/v1/kb/sessions?limit=2&offset=1",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
    )
    assert operator_list.status_code == 200
    operator_payload = operator_list.json()
    assert operator_payload["total"] == 3
    assert len(operator_payload["items"]) == 2
    assert operator_payload["items"][0]["session_key"] == "conv-op-2"
    assert operator_payload["items"][1]["session_key"] == "conv-op-1"

    manager_list = client.get(
        "/api/v1/kb/sessions",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
    )
    assert manager_list.status_code == 200
    assert manager_list.json()["total"] == 1

    sales_list = client.get(
        "/api/v1/kb/sessions",
        headers=_auth_headers(UserRole.SALES, sales_id),
    )
    assert sales_list.status_code == 403

    operator_chat = client.post(
        "/api/v1/kb/sessions/chat",
        headers=_auth_headers(UserRole.OPERATOR, operator_id),
        json={"query": "operator chat"},
    )
    assert operator_chat.status_code == 200

    manager_chat = client.post(
        "/api/v1/kb/sessions/chat",
        headers=_auth_headers(UserRole.MANAGER, manager_id),
        json={"query": "manager chat"},
    )
    assert manager_chat.status_code == 200

    sales_chat = client.post(
        "/api/v1/kb/sessions/chat",
        headers=_auth_headers(UserRole.SALES, sales_id),
        json={"query": "sales chat"},
    )
    assert sales_chat.status_code == 403
