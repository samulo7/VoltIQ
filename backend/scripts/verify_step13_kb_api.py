from __future__ import annotations

import argparse
import sys
import uuid

import httpx

DEFAULT_QUESTIONS = (
    "请基于知识库说明：售电合同中直接交易的定义是什么？并给出依据。",
    "继续上一个问题，补充直接交易常见结算方式，并给出依据。",
    "如果客户担心偏差考核风险，应该如何解释？请给出依据。",
    "请总结上面内容，给一段可直接发送给客户的简短话术，并给出依据。",
    "最后再给出 3 条销售沟通注意事项，并标注依据来源。",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify Step 13 KB chat API with 5 sequential questions.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL.",
    )
    parser.add_argument(
        "--actor-role",
        choices=["operator", "manager"],
        default="operator",
        help="Role used for API verification.",
    )
    parser.add_argument(
        "--actor-user-id",
        required=True,
        help="Existing active user id in backend database.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120.0,
        help="Per-request timeout in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        actor_user_id = str(uuid.UUID(args.actor_user_id))
    except ValueError:
        print("[FAIL] --actor-user-id is not a valid UUID.")
        return 2

    base_url = args.base_url.rstrip("/")
    endpoint = f"{base_url}/api/v1/kb/sessions/chat"
    session_key: str | None = None

    with httpx.Client(timeout=args.timeout_seconds) as client:
        for index, query in enumerate(DEFAULT_QUESTIONS, start=1):
            payload = {"query": query}
            if session_key:
                payload["session_key"] = session_key

            try:
                response = client.post(
                    endpoint,
                    headers={
                        "X-Actor-Role": args.actor_role,
                        "X-Actor-User-Id": actor_user_id,
                        "X-Request-Id": f"step13-verify-{index}",
                    },
                    json=payload,
                )
            except httpx.HTTPError as exc:
                print(f"[FAIL] Q{index} request transport error: {exc}")
                return 1

            if response.status_code != 200:
                detail = _safe_detail(response)
                print(f"[FAIL] Q{index} request failed: status={response.status_code}, detail={detail}")
                return 1

            body = response.json()
            answer = str(body.get("answer", "")).strip()
            sources = body.get("sources") if isinstance(body.get("sources"), list) else []
            returned_session_key = str(body.get("session_key", "")).strip()

            if not answer:
                print(f"[FAIL] Q{index} returned empty answer.")
                return 1
            if not sources:
                print(f"[FAIL] Q{index} returned no sources.")
                return 1
            if not returned_session_key:
                print(f"[FAIL] Q{index} returned empty session_key.")
                return 1

            session_key = returned_session_key
            print(f"[PASS] Q{index} answer_ok sources={len(sources)} session_key={session_key}")

    print("[PASS] Step 13 KB API verification succeeded.")
    return 0


def _safe_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip()

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
    return str(payload)


if __name__ == "__main__":
    sys.exit(main())
