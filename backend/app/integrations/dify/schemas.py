from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DifyRetrieverResource:
    position: int | None
    dataset_id: str | None
    dataset_name: str | None
    document_id: str | None
    document_name: str | None
    segment_id: str | None
    score: float | None
    content: str | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DifyRetrieverResource":
        score_value = payload.get("score")
        try:
            score = float(score_value) if score_value is not None else None
        except (TypeError, ValueError):
            score = None

        position_value = payload.get("position")
        try:
            position = int(position_value) if position_value is not None else None
        except (TypeError, ValueError):
            position = None

        return cls(
            position=position,
            dataset_id=_as_optional_str(payload.get("dataset_id")),
            dataset_name=_as_optional_str(payload.get("dataset_name")),
            document_id=_as_optional_str(payload.get("document_id")),
            document_name=_as_optional_str(payload.get("document_name")),
            segment_id=_as_optional_str(payload.get("segment_id")),
            score=score,
            content=_as_optional_str(payload.get("content")),
        )


@dataclass(frozen=True)
class DifyChatResult:
    message_id: str
    conversation_id: str
    answer: str
    retriever_resources: tuple[DifyRetrieverResource, ...]
    raw_payload: dict[str, Any]


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)

