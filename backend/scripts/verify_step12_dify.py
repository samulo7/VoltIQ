from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.integrations.dify import DifyClient, DifyRequestError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify Step 12 Dify connectivity and source attribution contract.",
    )
    parser.add_argument(
        "--query",
        default="Please explain direct power trading in an electricity retail contract and cite the basis.",
        help="Question sent to Dify chat app.",
    )
    parser.add_argument(
        "--user",
        default="step12-verify-user",
        help="Stable user id for Dify conversation context.",
    )
    parser.add_argument(
        "--conversation-id",
        default=None,
        help="Optional existing conversation id to continue chat.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help="Per-request timeout in seconds. Defaults to VOLTIQ_DIFY_REQUEST_TIMEOUT_SECONDS.",
    )
    parser.add_argument(
        "--response-mode",
        choices=["blocking", "streaming"],
        default=None,
        help="Dify response mode. Defaults to VOLTIQ_DIFY_RESPONSE_MODE.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=None,
        help="Retry count. Defaults to VOLTIQ_DIFY_REQUEST_MAX_RETRIES.",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=None,
        help="Exponential backoff base seconds. Defaults to VOLTIQ_DIFY_REQUEST_RETRY_BACKOFF_SECONDS.",
    )
    parser.add_argument(
        "--stream-output",
        action="store_true",
        help="Print streaming output chunks as they arrive.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()

    timeout_seconds = args.timeout_seconds if args.timeout_seconds is not None else settings.dify_request_timeout_seconds
    response_mode = args.response_mode if args.response_mode is not None else settings.dify_response_mode
    retries = args.retries if args.retries is not None else settings.dify_request_max_retries
    retry_backoff_seconds = (
        args.retry_backoff_seconds
        if args.retry_backoff_seconds is not None
        else settings.dify_request_retry_backoff_seconds
    )

    try:
        if args.stream_output:
            if response_mode != "streaming":
                response_mode = "streaming"
            result = _send_chat_message_streaming(
                base_url=settings.dify_base_url,
                api_key=settings.dify_api_key,
                timeout_seconds=timeout_seconds,
                response_mode=response_mode,
                max_retries=retries,
                retry_backoff_seconds=retry_backoff_seconds,
                query=args.query,
                user=args.user,
                conversation_id=args.conversation_id,
            )
        else:
            client = DifyClient(
                base_url=settings.dify_base_url,
                api_key=settings.dify_api_key,
                timeout_seconds=timeout_seconds,
                response_mode=response_mode,
                max_retries=retries,
                retry_backoff_seconds=retry_backoff_seconds,
            )
            result = client.send_chat_message(
                query=args.query,
                user=args.user,
                conversation_id=args.conversation_id,
            )
    except DifyRequestError as exc:
        print(f"[FAIL] Dify verification failed: {exc}")
        return 1

    if not result.answer.strip():
        print("[FAIL] Dify returned an empty answer.")
        return 2

    if not result.retriever_resources:
        print("[FAIL] Dify answer has no retriever_resources.")
        return 3

    print("[PASS] Step 12 Dify verification succeeded.")
    print(f"conversation_id={result.conversation_id}")
    print(f"message_id={result.message_id}")
    print(f"sources={len(result.retriever_resources)}")
    preview = result.answer.strip().replace("\n", " ")
    print(f"answer_preview={preview[:200]}")
    return 0


def _send_chat_message_streaming(
    *,
    base_url: str,
    api_key: str,
    timeout_seconds: float,
    response_mode: str,
    max_retries: int,
    retry_backoff_seconds: float,
    query: str,
    user: str,
    conversation_id: str | None,
) -> Any:
    if response_mode != "streaming":
        raise DifyRequestError("Streaming output requires response_mode=streaming.")

    url = _normalize_base_url(base_url)
    payload: dict[str, Any] = {
        "query": query,
        "inputs": {},
        "response_mode": response_mode,
        "user": user,
    }
    if conversation_id:
        payload["conversation_id"] = conversation_id

    attempts = max_retries + 1
    last_error: DifyRequestError | None = None
    for attempt in range(1, attempts + 1):
        try:
            return _stream_request(url, api_key, payload, timeout_seconds)
        except DifyRequestError as exc:
            last_error = exc
            if attempt >= attempts:
                break
            if retry_backoff_seconds > 0:
                time.sleep(retry_backoff_seconds * (2 ** (attempt - 1)))

    raise last_error or DifyRequestError("Dify request failed after retries.")


def _stream_request(url: str, api_key: str, payload: dict[str, Any], timeout_seconds: float) -> Any:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    answer_text = ""
    message_id: str | None = None
    conversation_id: str | None = None
    retriever_resources: list[dict[str, Any]] = []

    with httpx.stream(
        "POST",
        url,
        headers=headers,
        json=payload,
        timeout=timeout_seconds,
    ) as response:
        if response.status_code >= 400:
            raise _build_request_error(response)

        for event in _iter_sse_events(response):
            if message_id is None:
                message_id = _as_non_empty_str(event.get("message_id"))
            if conversation_id is None:
                conversation_id = _as_non_empty_str(event.get("conversation_id"))

            chunk = _extract_stream_answer_chunk(event)
            if chunk:
                answer_text = _merge_answer_chunk(answer_text, chunk)
                print(chunk, end="", flush=True)

            resources = _extract_resources_from_event(event)
            if resources:
                retriever_resources = resources

    print()

    if not message_id:
        raise DifyRequestError("Dify response missing required field: message_id.")
    if not conversation_id:
        raise DifyRequestError("Dify response missing required field: conversation_id.")
    if not answer_text.strip():
        raise DifyRequestError("Dify response missing required field: answer.")

    return _build_chat_result(message_id, conversation_id, answer_text, retriever_resources)


def _iter_sse_events(response: httpx.Response) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw_line in response.iter_lines():
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


def _merge_answer_chunk(current: str, incoming: str) -> str:
    if not current:
        return incoming
    if incoming.startswith(current):
        return incoming
    if current.endswith(incoming):
        return current
    return f"{current}{incoming}"


def _extract_resources_from_event(payload: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = payload.get("metadata")
    resources = metadata.get("retriever_resources") if isinstance(metadata, dict) else []
    if isinstance(resources, list):
        return resources
    return []


def _build_chat_result(
    message_id: str,
    conversation_id: str,
    answer: str,
    retriever_resources: list[dict[str, Any]],
) -> Any:
    from app.integrations.dify.schemas import DifyChatResult, DifyRetrieverResource

    parsed_resources = tuple(
        DifyRetrieverResource.from_payload(item)
        for item in retriever_resources
        if isinstance(item, dict)
    )
    return DifyChatResult(
        message_id=message_id,
        conversation_id=conversation_id,
        answer=answer,
        retriever_resources=parsed_resources,
        raw_payload={"streaming": True},
    )


def _build_request_error(response: httpx.Response) -> DifyRequestError:
    payload = {}
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        message = response.text.strip() or "Dify request returned an unknown error."

    error_code = payload.get("code") if isinstance(payload.get("code"), str) else None
    return DifyRequestError(message, status_code=response.status_code, error_code=error_code)


def _normalize_base_url(base_url: str) -> str:
    url = base_url.rstrip("/")
    if url.endswith("/v1"):
        return f"{url}/chat-messages"
    return f"{url}/v1/chat-messages"


def _as_non_empty_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


if __name__ == "__main__":
    sys.exit(main())
