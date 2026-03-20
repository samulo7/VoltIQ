from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.enums import KbMessageRole
from app.db.models import AuditLog, KbMessage, KbSession


@dataclass(frozen=True)
class KbSessionListFilters:
    user_id: uuid.UUID
    limit: int = 20
    offset: int = 0


class KbRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_session_by_key(self, session_key: str) -> KbSession | None:
        return self._db.query(KbSession).filter(KbSession.session_key == session_key).first()

    def list_sessions(self, filters: KbSessionListFilters) -> tuple[int, list[KbSession]]:
        query = self._db.query(KbSession).filter(KbSession.user_id == filters.user_id)
        total = query.count()
        items = (
            query.order_by(KbSession.updated_at.desc())
            .offset(filters.offset)
            .limit(filters.limit)
            .all()
        )
        return total, items

    def create_session(
        self,
        *,
        user_id: uuid.UUID,
        session_key: str,
        now: dt.datetime,
    ) -> KbSession:
        session = KbSession(
            user_id=user_id,
            session_key=session_key,
            created_at=now,
            updated_at=now,
        )
        self._db.add(session)
        self._db.flush()
        return session

    def touch_session(self, session: KbSession, *, now: dt.datetime) -> KbSession:
        session.updated_at = now
        self._db.add(session)
        self._db.flush()
        return session

    def create_message(
        self,
        *,
        session_id: uuid.UUID,
        role: KbMessageRole,
        content: str,
        source_refs: dict[str, Any] | None,
        now: dt.datetime,
    ) -> KbMessage:
        message = KbMessage(
            session_id=session_id,
            role=role,
            content=content,
            source_refs=source_refs,
            created_at=now,
        )
        self._db.add(message)
        self._db.flush()
        return message

    def create_audit_log(
        self,
        *,
        actor_user_id: uuid.UUID,
        action: str,
        target_type: str,
        target_id: str,
        before_data: dict[str, Any] | None,
        after_data: dict[str, Any] | None,
        ip_address: str,
        request_id: str,
        now: dt.datetime,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_data=before_data,
            after_data=after_data,
            ip_address=ip_address,
            request_id=request_id,
            created_at=now,
        )
        self._db.add(audit_log)
        self._db.flush()
        return audit_log
