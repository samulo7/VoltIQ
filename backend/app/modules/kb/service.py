from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status

from app.db.enums import KbMessageRole
from app.db.models import KbSession
from app.integrations.dify import DifyClient, DifyRequestError
from app.modules.kb.deps import ActorContext, RequestMeta
from app.modules.kb.repository import KbRepository, KbSessionListFilters
from app.modules.kb.schemas import KbChatRequest, KbChatResponse, KbSessionListResult, KbSessionResponse, KbSourceRef


class KbService:
    def __init__(self, repo: KbRepository, dify_client: DifyClient | None = None) -> None:
        self._repo = repo
        self._dify_client = dify_client

    def list_sessions(self, filters: KbSessionListFilters) -> KbSessionListResult:
        total, items = self._repo.list_sessions(filters)
        return KbSessionListResult(
            total=total,
            items=[KbSessionResponse.model_validate(item) for item in items],
        )

    def chat(
        self,
        payload: KbChatRequest,
        *,
        actor: ActorContext,
        request_meta: RequestMeta,
    ) -> KbChatResponse:
        existing_session: KbSession | None = None
        if payload.session_key:
            existing_session = self._repo.get_session_by_key(payload.session_key)
            if existing_session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="KB session not found.",
                )
            if existing_session.user_id != actor.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied for the target session.",
                )

        try:
            if self._dify_client is None:
                raise RuntimeError("Dify client is not configured for KB chat.")
            dify_result = self._dify_client.send_chat_message(
                query=payload.query,
                user=str(actor.user_id),
                conversation_id=existing_session.session_key if existing_session else None,
            )
        except DifyRequestError as exc:
            status_code = status.HTTP_502_BAD_GATEWAY
            if exc.status_code == 504:
                status_code = status.HTTP_504_GATEWAY_TIMEOUT
            raise HTTPException(
                status_code=status_code,
                detail=f"Dify request failed: {exc}",
            ) from exc

        answer = dify_result.answer.strip()
        if not answer:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Dify returned an empty answer.",
            )
        if not dify_result.retriever_resources:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Dify returned no retriever resources.",
            )

        now = _utcnow()
        session = self._ensure_session(
            actor=actor,
            existing_session=existing_session,
            conversation_id=dify_result.conversation_id,
            now=now,
        )
        self._repo.touch_session(session, now=now)

        source_items = [KbSourceRef.from_retriever_resource(item) for item in dify_result.retriever_resources]
        source_refs_payload = {
            "retriever_resources": [item.model_dump() for item in source_items],
        }

        self._repo.create_message(
            session_id=session.id,
            role=KbMessageRole.USER,
            content=payload.query.strip(),
            source_refs=None,
            now=now,
        )
        self._repo.create_message(
            session_id=session.id,
            role=KbMessageRole.ASSISTANT,
            content=answer,
            source_refs=source_refs_payload,
            now=now,
        )
        self._repo.create_audit_log(
            actor_user_id=actor.user_id,
            action="kb.session.chatted",
            target_type="kb_session",
            target_id=str(session.id),
            before_data=None,
            after_data={
                "session_key": session.session_key,
                "message_id": dify_result.message_id,
                "sources_count": len(source_items),
                "query_preview": _preview_text(payload.query),
            },
            ip_address=request_meta.ip_address,
            request_id=request_meta.request_id,
            now=now,
        )

        return KbChatResponse(
            session_key=session.session_key,
            conversation_id=dify_result.conversation_id,
            message_id=dify_result.message_id,
            answer=answer,
            sources=source_items,
        )

    def _ensure_session(
        self,
        *,
        actor: ActorContext,
        existing_session: KbSession | None,
        conversation_id: str,
        now: dt.datetime,
    ) -> KbSession:
        if existing_session is not None:
            if conversation_id != existing_session.session_key:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Dify returned a mismatched conversation_id.",
                )
            return existing_session

        session = self._repo.get_session_by_key(conversation_id)
        if session is None:
            return self._repo.create_session(
                user_id=actor.user_id,
                session_key=conversation_id,
                now=now,
            )
        if session.user_id != actor.user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation key already belongs to another user.",
            )
        return session


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _preview_text(text: str, max_length: int = 120) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[:max_length]}..."
