from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.integrations.dify.schemas import DifyRetrieverResource


class KbChatRequest(BaseModel):
    query: str = Field(min_length=1)
    session_key: str | None = Field(default=None, min_length=1, max_length=128)


class KbSourceRef(BaseModel):
    position: int | None
    dataset_id: str | None
    dataset_name: str | None
    document_id: str | None
    document_name: str | None
    segment_id: str | None
    score: float | None
    content: str | None

    @classmethod
    def from_retriever_resource(cls, resource: DifyRetrieverResource) -> "KbSourceRef":
        return cls(
            position=resource.position,
            dataset_id=resource.dataset_id,
            dataset_name=resource.dataset_name,
            document_id=resource.document_id,
            document_name=resource.document_name,
            segment_id=resource.segment_id,
            score=resource.score,
            content=resource.content,
        )


class KbChatResponse(BaseModel):
    session_key: str
    conversation_id: str
    message_id: str
    answer: str
    sources: list[KbSourceRef]


class KbSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    session_key: str
    created_at: dt.datetime
    updated_at: dt.datetime


class KbSessionListResult(BaseModel):
    total: int
    items: list[KbSessionResponse]
