from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import Settings
from app.integrations.dify.exceptions import DifyRequestError
from app.integrations.dify.schemas import DifyChatResult, DifyRetrieverResource

_SUPPORTED_RESPONSE_MODES = frozenset({"blocking", "streaming"})
_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class DifyClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 30.0,
        response_mode: str = "blocking",
        max_retries: int = 2,
        retry_backoff_seconds: float = 1.0,
    ) -> None:
        self._base_url = _normalize_dify_base_url(base_url)
        self._api_key = api_key.strip()
        if not self._api_key or self._api_key == "replace_me":
            raise DifyRequestError("Dify API key is not configured.")

        if timeout_seconds <= 0:
            raise DifyRequestError("Dify timeout must be greater than 0.")
        self._timeout_seconds = timeout_seconds

        response_mode_normalized = response_mode.strip().lower()
        if response_mode_normalized not in _SUPPORTED_RESPONSE_MODES:
            raise DifyRequestError("Dify response mode must be either 'blocking' or 'streaming'.")
        self._response_mode = response_mode_normalized

        if max_retries < 0:
            raise DifyRequestError("Dify max retries must be greater than or equal to 0.")
        self._max_retries = max_retries

        if retry_backoff_seconds < 0:
            raise DifyRequestError("Dify retry backoff seconds must be greater than or equal to 0.")
        self._retry_backoff_seconds = retry_backoff_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> "DifyClient":
        return cls(
            base_url=settings.dify_base_url,
            api_key=settings.dify_api_key,
            timeout_seconds=settings.dify_request_timeout_seconds,
            response_mode=settings.dify_response_mode,
            max_retries=settings.dify_request_max_retries,
            retry_backoff_seconds=settings.dify_request_retry_backoff_seconds,
        )

    def send_chat_message(
        self,
        *,
        query: str,
        user: str,
        conversation_id: str | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> DifyChatResult:
        query_text = query.strip()
        if not query_text:
            raise DifyRequestError("Dify chat query must not be empty.")

        user_key = user.strip()
        if not user_key:
            raise DifyRequestError("Dify chat user must not be empty.")

        payload: dict[str, Any] = {
            "query": query_text,
            "inputs": inputs or {},
            "response_mode": self._response_mode,
            "user": user_key,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id

        url = f"{self._base_url}/chat-messages"
        response = self._post_with_retry(url=url, payload=payload)

        if self._response_mode == "streaming":
            return _parse_streaming_chat_response(response)
        return _parse_blocking_chat_response(response)

    def _post_with_retry(self, *, url: str, payload: dict[str, Any]) -> httpx.Response:
        max_attempts = self._max_retries + 1

        for attempt in range(1, max_attempts + 1):
            try:
                response = httpx.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self._timeout_seconds,
                )
            except httpx.TimeoutException as exc:
                if attempt < max_attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise DifyRequestError("Dify request timed out.", status_code=504) from exc
            except httpx.HTTPError as exc:
                if attempt < max_attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise DifyRequestError(f"Dify request failed: {exc}") from exc

            response_payload = _safe_json(response)
            if response.status_code >= 400:
                if response.status_code in _RETRYABLE_STATUS_CODES and attempt < max_attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise DifyRequestError(
                    _extract_error_message(response_payload, response.text),
                    status_code=response.status_code,
                    error_code=_extract_error_code(response_payload),
                )
            return response

        raise DifyRequestError("Dify request failed after retries.")

    def _sleep_before_retry(self, attempt: int) -> None:
        if self._retry_backoff_seconds <= 0:
            return
        backoff_seconds = self._retry_backoff_seconds * (2 ** (attempt - 1))
        time.sleep(backoff_seconds)


def _parse_blocking_chat_response(response: httpx.Response) -> DifyChatResult:
    response_payload = _safe_json(response)

    message_id = _expect_non_empty_str(response_payload.get("message_id"), "message_id")
    answer = _expect_non_empty_str(response_payload.get("answer"), "answer")
    returned_conversation_id = _expect_non_empty_str(
        response_payload.get("conversation_id"),
        "conversation_id",
    )

    retriever_resources = _extract_retriever_resources(response_payload)

    return DifyChatResult(
        message_id=message_id,
        conversation_id=returned_conversation_id,
        answer=_sanitize_answer(answer),
        retriever_resources=retriever_resources,
        raw_payload=response_payload,
    )


def _parse_streaming_chat_response(response: httpx.Response) -> DifyChatResult:
    stream_text = response.text
    stream_events = _parse_sse_events(stream_text)

    if not stream_events:
        # Some gateways can still return a plain JSON object even with streaming mode.
        return _parse_blocking_chat_response(response)

    message_id: str | None = None
    conversation_id: str | None = None
    answer_text = ""
    retriever_resources: tuple[DifyRetrieverResource, ...] = ()

    for event_payload in stream_events:
        if message_id is None:
            message_id = _as_non_empty_str(event_payload.get("message_id"))
        if conversation_id is None:
            conversation_id = _as_non_empty_str(event_payload.get("conversation_id"))

        answer_chunk = _extract_stream_answer_chunk(event_payload)
        if answer_chunk:
            answer_text = _merge_answer_chunk(answer_text, answer_chunk)

        event_resources = _extract_retriever_resources(event_payload)
        if event_resources:
            retriever_resources = event_resources

    if not message_id:
        raise DifyRequestError("Dify response missing required field: message_id.")
    if not conversation_id:
        raise DifyRequestError("Dify response missing required field: conversation_id.")

    answer = _sanitize_answer(answer_text.strip())
    if not answer:
        raise DifyRequestError("Dify response missing required field: answer.")

    return DifyChatResult(
        message_id=message_id,
        conversation_id=conversation_id,
        answer=answer,
        retriever_resources=retriever_resources,
        raw_payload={"stream_events": stream_events},
    )


def _parse_sse_events(stream_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw_line in stream_text.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("data:"):
            continue

        data_raw = line[len("data:") :].strip()
        if not data_raw or data_raw == "[DONE]":
            continue

        try:
            payload = json.loads(data_raw)
        except ValueError:
            continue

        if isinstance(payload, dict):
            events.append(payload)

    return events


def _extract_stream_answer_chunk(payload: dict[str, Any]) -> str:
    for key in ("answer", "text", "delta"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _sanitize_answer(answer: str) -> str:
    if not answer:
        return answer
    # First remove the entire <details> blocks (most models put reasoning there).
    cleaned = re.sub(r"<details\b[^>]*>.*?</details>", "", answer, flags=re.IGNORECASE | re.DOTALL).strip()
    if cleaned:
        return cleaned
    # If everything was inside <details>, try to extract the final answer from within.
    extracted = _extract_final_answer_from_details(answer)
    return extracted.strip()


def _extract_final_answer_from_details(answer: str) -> str:
    details_blocks = re.findall(r"<details\b[^>]*>(.*?)</details>", answer, flags=re.IGNORECASE | re.DOTALL)
    if not details_blocks:
        return ""

    markers = [
        r"Final Answer[:：]",
        r"Answer[:：]",
        r"最终答案[:：]",
        r"结论[:：]",
        r"答案[:：]",
        r"答复[:：]",
    ]

    for block in details_blocks:
        inner = re.sub(r"<summary\b[^>]*>.*?</summary>", "", block, flags=re.IGNORECASE | re.DOTALL).strip()
        if not inner:
            continue

        for pattern in markers:
            matches = list(re.finditer(pattern, inner, flags=re.IGNORECASE))
            if matches:
                last_match = matches[-1]
                candidate = inner[last_match.end() :].strip()
                if candidate:
                    return candidate

    return ""


def _merge_answer_chunk(current: str, incoming: str) -> str:
    if not current:
        return incoming
    if incoming.startswith(current):
        return incoming
    if current.endswith(incoming):
        return current
    return f"{current}{incoming}"


def _extract_retriever_resources(payload: dict[str, Any]) -> tuple[DifyRetrieverResource, ...]:
    metadata = payload.get("metadata")
    resources_payload = metadata.get("retriever_resources") if isinstance(metadata, dict) else []
    if not isinstance(resources_payload, list):
        resources_payload = []

    return tuple(
        DifyRetrieverResource.from_payload(item)
        for item in resources_payload
        if isinstance(item, dict)
    )


def _normalize_dify_base_url(base_url: str) -> str:
    url = base_url.strip()
    if not url:
        raise DifyRequestError("Dify base URL is not configured.")

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise DifyRequestError("Dify base URL must include scheme and host.")

    normalized = url.rstrip("/")
    if parsed.path in ("", "/"):
        normalized = f"{normalized}/v1"
    return normalized


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _extract_error_message(payload: dict[str, Any], fallback: str) -> str:
    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message
    if fallback.strip():
        return fallback
    return "Dify request returned an unknown error."


def _extract_error_code(payload: dict[str, Any]) -> str | None:
    code = payload.get("code")
    if isinstance(code, str) and code.strip():
        return code
    return None


def _as_non_empty_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _expect_non_empty_str(value: object, field_name: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    raise DifyRequestError(f"Dify response missing required field: {field_name}.")

