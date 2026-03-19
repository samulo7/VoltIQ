from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from app.integrations.dify.client import DifyClient
from app.integrations.dify.exceptions import DifyRequestError


def _build_response(url: str, status_code: int, payload: dict[str, object]) -> httpx.Response:
    request = httpx.Request("POST", url)
    return httpx.Response(status_code=status_code, json=payload, request=request)


def _build_stream_response(url: str, status_code: int, stream_text: str) -> httpx.Response:
    request = httpx.Request("POST", url)
    return httpx.Response(
        status_code=status_code,
        text=stream_text,
        headers={"Content-Type": "text/event-stream"},
        request=request,
    )


def test_send_chat_message_success_and_payload_contract() -> None:
    url = "http://localhost/v1/chat-messages"

    def _mock_post(*args: object, **kwargs: object) -> httpx.Response:
        assert args == (url,)
        headers = kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-key"
        assert kwargs["timeout"] == 12.5

        payload = kwargs["json"]
        assert payload["query"] == "What is direct trading?"
        assert payload["response_mode"] == "blocking"
        assert payload["user"] == "test-user"
        assert payload["conversation_id"] == "conv-1"
        return _build_response(
            url,
            200,
            {
                "message_id": "msg-1",
                "conversation_id": "conv-2",
                "answer": "Direct trading means ...",
                "metadata": {
                    "retriever_resources": [
                        {
                            "position": 1,
                            "dataset_id": "dataset-1",
                            "dataset_name": "policy",
                            "document_id": "doc-1",
                            "document_name": "policy-doc",
                            "segment_id": "seg-1",
                            "score": 0.99,
                            "content": "policy source",
                        }
                    ]
                },
            },
        )

    client = DifyClient(
        base_url="http://localhost",
        api_key="test-key",
        timeout_seconds=12.5,
        max_retries=0,
    )
    with patch("app.integrations.dify.client.httpx.post", side_effect=_mock_post):
        result = client.send_chat_message(
            query="What is direct trading?",
            user="test-user",
            conversation_id="conv-1",
        )

    assert result.message_id == "msg-1"
    assert result.conversation_id == "conv-2"
    assert "Direct trading" in result.answer
    assert len(result.retriever_resources) == 1
    assert result.retriever_resources[0].dataset_id == "dataset-1"


def test_send_chat_message_retry_timeout_then_success() -> None:
    url = "http://localhost/v1/chat-messages"

    responses = [
        httpx.TimeoutException("timeout"),
        _build_response(
            url,
            200,
            {
                "message_id": "msg-2",
                "conversation_id": "conv-2",
                "answer": "ok",
                "metadata": {"retriever_resources": [{"dataset_id": "dataset-2"}]},
            },
        ),
    ]

    client = DifyClient(
        base_url="http://localhost/v1",
        api_key="test-key",
        max_retries=1,
        retry_backoff_seconds=0,
    )

    with patch("app.integrations.dify.client.httpx.post", side_effect=responses) as mocked_post:
        result = client.send_chat_message(query="q", user="u")

    assert mocked_post.call_count == 2
    assert result.message_id == "msg-2"
    assert len(result.retriever_resources) == 1


def test_send_chat_message_streaming_success() -> None:
    stream_text = "\n".join(
        [
            'data: {"event":"message","message_id":"msg-s1","conversation_id":"conv-s1","answer":"Direct "}',
            'data: {"event":"message","answer":"trading means market-based transactions."}',
            (
                'data: {"event":"message_end","metadata":{"retriever_resources":'
                '[{"dataset_id":"dataset-stream","document_id":"doc-1"}]}}'
            ),
            "data: [DONE]",
        ]
    )

    client = DifyClient(
        base_url="http://localhost/v1",
        api_key="test-key",
        response_mode="streaming",
        max_retries=0,
    )

    with patch(
        "app.integrations.dify.client.httpx.post",
        return_value=_build_stream_response("http://localhost/v1/chat-messages", 200, stream_text),
    ):
        result = client.send_chat_message(query="q", user="u")

    assert result.message_id == "msg-s1"
    assert result.conversation_id == "conv-s1"
    assert result.answer.startswith("Direct trading means")
    assert len(result.retriever_resources) == 1
    assert result.retriever_resources[0].dataset_id == "dataset-stream"



def test_send_chat_message_streaming_cumulative_chunks() -> None:
    stream_text = "\n".join(
        [
            'data: {"event":"message","message_id":"msg-s2","conversation_id":"conv-s2","answer":"Direct"}',
            'data: {"event":"message","answer":"Direct trading"}',
            'data: {"event":"message_end","metadata":{"retriever_resources":[{"dataset_id":"dataset-stream-2"}]}}',
            "data: [DONE]",
        ]
    )

    client = DifyClient(
        base_url="http://localhost/v1",
        api_key="test-key",
        response_mode="streaming",
        max_retries=0,
    )

    with patch(
        "app.integrations.dify.client.httpx.post",
        return_value=_build_stream_response("http://localhost/v1/chat-messages", 200, stream_text),
    ):
        result = client.send_chat_message(query="q", user="u")

    assert result.answer == "Direct trading"
    assert result.retriever_resources[0].dataset_id == "dataset-stream-2"


def test_send_chat_message_strips_details_block() -> None:
    url = "http://localhost/v1/chat-messages"
    payload = {
        "message_id": "msg-d1",
        "conversation_id": "conv-d1",
        "answer": "<details><summary>Thinking...</summary>internal</details>Final answer.",
        "metadata": {"retriever_resources": [{"dataset_id": "dataset-3"}]},
    }

    client = DifyClient(base_url="http://localhost/v1", api_key="test-key", max_retries=0)
    with patch(
        "app.integrations.dify.client.httpx.post",
        return_value=_build_response(url, 200, payload),
    ):
        result = client.send_chat_message(query="q", user="u")

    assert result.answer == "Final answer."


def test_send_chat_message_extracts_final_answer_from_details() -> None:
    url = "http://localhost/v1/chat-messages"
    payload = {
        "message_id": "msg-d2",
        "conversation_id": "conv-d2",
        "answer": "<details><summary>Thinking...</summary>Thinking Process...\nFinal Answer: Market-based deal.</details>",
        "metadata": {"retriever_resources": [{"dataset_id": "dataset-4"}]},
    }

    client = DifyClient(base_url="http://localhost/v1", api_key="test-key", max_retries=0)
    with patch(
        "app.integrations.dify.client.httpx.post",
        return_value=_build_response(url, 200, payload),
    ):
        result = client.send_chat_message(query="q", user="u")

    assert result.answer == "Market-based deal."
def test_send_chat_message_http_error_maps_to_request_error() -> None:
    client = DifyClient(base_url="http://localhost/v1", api_key="test-key", max_retries=0)
    with patch(
        "app.integrations.dify.client.httpx.post",
        return_value=_build_response(
            "http://localhost/v1/chat-messages",
            401,
            {"code": "unauthorized", "message": "invalid api key"},
        ),
    ):
        with pytest.raises(DifyRequestError) as exc_info:
            client.send_chat_message(query="q", user="u")

    assert exc_info.value.status_code == 401
    assert exc_info.value.error_code == "unauthorized"
    assert "invalid api key" in str(exc_info.value)


def test_send_chat_message_timeout_maps_to_request_error() -> None:
    client = DifyClient(base_url="http://localhost/v1", api_key="test-key", max_retries=0)
    with patch("app.integrations.dify.client.httpx.post", side_effect=httpx.TimeoutException("timeout")):
        with pytest.raises(DifyRequestError) as exc_info:
            client.send_chat_message(query="q", user="u")

    assert exc_info.value.status_code == 504
    assert "timed out" in str(exc_info.value).lower()


def test_invalid_response_mode_rejected() -> None:
    with pytest.raises(DifyRequestError):
        DifyClient(base_url="http://localhost/v1", api_key="test-key", response_mode="invalid")


def test_invalid_retry_config_rejected() -> None:
    with pytest.raises(DifyRequestError):
        DifyClient(base_url="http://localhost/v1", api_key="test-key", max_retries=-1)

    with pytest.raises(DifyRequestError):
        DifyClient(base_url="http://localhost/v1", api_key="test-key", retry_backoff_seconds=-0.1)

