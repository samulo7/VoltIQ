from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

import httpx

from app.core.config import get_settings
from app.integrations.dify import DifyClient, DifyRequestError

DEFAULT_QUESTIONS: tuple[str, ...] = (
    "What is direct power trading in electricity retail contracts?",
    "What is the difference between medium and long-term transactions and spot transactions?",
    "Which contract clauses usually define electricity settlement rules?",
    "What is a typical process from lead to signed electricity contract?",
    "What risks should customers watch in power purchase contracts?",
    "How is conversion rate defined for sales metrics in this project?",
    "What is the role of retriever_resources in knowledge-grounded answers?",
    "How should account roles differ between operator, sales, and manager?",
    "What evidence should be returned for an answer to be considered grounded?",
    "Why is Asia/Shanghai the default timezone for metrics in this system?",
)


@dataclass(frozen=True)
class SampleRecord:
    mode: str
    phase: str
    sequence_no: int
    query: str
    elapsed_seconds: float
    ttft_seconds: float | None
    passed: bool
    sources: int
    error: str
    conversation_id: str
    message_id: str


@dataclass(frozen=True)
class ModeSummary:
    mode: str
    sample_total: int
    sample_success: int
    sample_failed: int
    average_seconds: float | None
    p50_seconds: float | None
    p95_seconds: float | None
    average_ttft_seconds: float | None
    p50_ttft_seconds: float | None
    p95_ttft_seconds: float | None
    threshold_seconds: float
    within_threshold_count: int
    within_threshold_rate: float
    failure_rate: float
    slowest_successes: tuple[SampleRecord, ...]
    error_distribution: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class _StreamingRequestResult:
    elapsed_seconds: float
    ttft_seconds: float | None
    passed: bool
    sources: int
    error: str
    conversation_id: str
    message_id: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark Step 12 Dify Q&A latency with fixed question samples.",
    )
    parser.add_argument(
        "--modes",
        default="blocking,streaming",
        help="Comma-separated response modes. Supported: blocking,streaming.",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=10,
        help="Number of measured samples per mode.",
    )
    parser.add_argument(
        "--warmup-count",
        type=int,
        default=2,
        help="Number of warm-up requests per mode (excluded from summary).",
    )
    parser.add_argument(
        "--threshold-seconds",
        type=float,
        default=2.0,
        help="Target latency threshold in seconds.",
    )
    parser.add_argument(
        "--queries-file",
        default=None,
        help="Optional text file with one query per line. Defaults to built-in 10-query set.",
    )
    parser.add_argument(
        "--user-prefix",
        default="step12-benchmark-user",
        help="Prefix for Dify user id.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help="Per-request timeout. Defaults to VOLTIQ_DIFY_REQUEST_TIMEOUT_SECONDS.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=0,
        help="Retry count per request. Default 0 to reflect raw latency.",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=0.0,
        help="Retry backoff base seconds.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts",
        help="Directory for CSV and markdown benchmark outputs.",
    )
    parser.add_argument(
        "--print-each",
        action="store_true",
        help="Print one line for each request sample while running.",
    )
    return parser.parse_args()


def parse_modes(raw_modes: str) -> tuple[str, ...]:
    supported = {"blocking", "streaming"}
    items = [item.strip().lower() for item in raw_modes.split(",") if item.strip()]
    ordered: list[str] = []
    for item in items:
        if item not in supported:
            raise ValueError(f"Unsupported mode: {item}")
        if item not in ordered:
            ordered.append(item)
    if not ordered:
        raise ValueError("At least one response mode is required.")
    return tuple(ordered)


def load_queries(path: str | None) -> tuple[str, ...]:
    if not path:
        return DEFAULT_QUESTIONS
    file_path = Path(path)
    lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
    queries = tuple(line for line in lines if line)
    if not queries:
        raise ValueError("queries-file has no non-empty lines.")
    return queries


def pick_query(queries: tuple[str, ...], index: int) -> str:
    return queries[index % len(queries)]


def percentile(values: Iterable[float], percent: float) -> float | None:
    numbers = sorted(float(value) for value in values)
    if not numbers:
        return None
    if percent <= 0:
        return numbers[0]
    if percent >= 100:
        return numbers[-1]

    rank = (len(numbers) - 1) * (percent / 100.0)
    lower = int(rank)
    upper = lower + 1
    if upper >= len(numbers):
        return numbers[lower]
    fraction = rank - lower
    return numbers[lower] + (numbers[upper] - numbers[lower]) * fraction


def build_mode_summary(
    *,
    mode: str,
    records: list[SampleRecord],
    threshold_seconds: float,
) -> ModeSummary:
    sample_records = [record for record in records if record.phase == "sample"]
    successful = [record for record in sample_records if record.passed]
    failed = [record for record in sample_records if not record.passed]

    latencies = [record.elapsed_seconds for record in successful]
    average_seconds = (sum(latencies) / len(latencies)) if latencies else None
    p50_seconds = percentile(latencies, 50.0)
    p95_seconds = percentile(latencies, 95.0)

    ttft_latencies = [record.ttft_seconds for record in successful if record.ttft_seconds is not None]
    average_ttft_seconds = (sum(ttft_latencies) / len(ttft_latencies)) if ttft_latencies else None
    p50_ttft_seconds = percentile(ttft_latencies, 50.0)
    p95_ttft_seconds = percentile(ttft_latencies, 95.0)

    within_threshold_count = sum(1 for record in successful if record.elapsed_seconds <= threshold_seconds)
    sample_total = len(sample_records)
    within_threshold_rate = (within_threshold_count / sample_total) if sample_total else 0.0
    failure_rate = (len(failed) / sample_total) if sample_total else 0.0

    slowest_successes = tuple(sorted(successful, key=lambda record: record.elapsed_seconds, reverse=True)[:3])
    errors = Counter(record.error.strip() or "unknown_error" for record in failed)
    error_distribution = tuple(sorted(errors.items(), key=lambda item: (-item[1], item[0])))

    return ModeSummary(
        mode=mode,
        sample_total=sample_total,
        sample_success=len(successful),
        sample_failed=len(failed),
        average_seconds=average_seconds,
        p50_seconds=p50_seconds,
        p95_seconds=p95_seconds,
        average_ttft_seconds=average_ttft_seconds,
        p50_ttft_seconds=p50_ttft_seconds,
        p95_ttft_seconds=p95_ttft_seconds,
        threshold_seconds=threshold_seconds,
        within_threshold_count=within_threshold_count,
        within_threshold_rate=within_threshold_rate,
        failure_rate=failure_rate,
        slowest_successes=slowest_successes,
        error_distribution=error_distribution,
    )


def format_optional_seconds(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"


def write_csv(path: Path, records: list[SampleRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "mode",
                "phase",
                "sequence_no",
                "elapsed_seconds",
                "ttft_seconds",
                "passed",
                "sources",
                "error",
                "conversation_id",
                "message_id",
                "query",
            ]
        )
        for record in records:
            writer.writerow(
                [
                    record.mode,
                    record.phase,
                    record.sequence_no,
                    f"{record.elapsed_seconds:.6f}",
                    f"{record.ttft_seconds:.6f}" if record.ttft_seconds is not None else "",
                    "true" if record.passed else "false",
                    record.sources,
                    record.error,
                    record.conversation_id,
                    record.message_id,
                    record.query,
                ]
            )


def render_summary_markdown(
    *,
    started_at: datetime,
    finished_at: datetime,
    threshold_seconds: float,
    summaries: tuple[ModeSummary, ...],
) -> str:
    lines: list[str] = []
    lines.append("# Step 12 Dify Latency Benchmark Summary")
    lines.append("")
    lines.append(f"- Started at: {started_at.isoformat()}")
    lines.append(f"- Finished at: {finished_at.isoformat()}")
    lines.append(f"- Threshold: <= {threshold_seconds:.3f}s")
    lines.append("")
    lines.append(
        "| mode | samples | success | failed | avg(s) | p50(s) | p95(s) | avg_ttft(s) | p50_ttft(s) | p95_ttft(s) | <=threshold | failure_rate |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")

    for summary in summaries:
        lines.append(
            (
                "| {mode} | {samples} | {success} | {failed} | {avg} | {p50} | {p95} | {avg_ttft} | "
                "{p50_ttft} | {p95_ttft} | {within}/{samples} ({within_rate:.1%}) | {failure:.1%} |"
            ).format(
                mode=summary.mode,
                samples=summary.sample_total,
                success=summary.sample_success,
                failed=summary.sample_failed,
                avg=format_optional_seconds(summary.average_seconds),
                p50=format_optional_seconds(summary.p50_seconds),
                p95=format_optional_seconds(summary.p95_seconds),
                avg_ttft=format_optional_seconds(summary.average_ttft_seconds),
                p50_ttft=format_optional_seconds(summary.p50_ttft_seconds),
                p95_ttft=format_optional_seconds(summary.p95_ttft_seconds),
                within=summary.within_threshold_count,
                within_rate=summary.within_threshold_rate,
                failure=summary.failure_rate,
            )
        )

    lines.append("")
    for summary in summaries:
        lines.append(f"## {summary.mode} slowest successful samples")
        if not summary.slowest_successes:
            lines.append("- none")
        else:
            for record in summary.slowest_successes:
                preview = record.query.replace("|", "/")
                ttft_text = (
                    f", ttft={record.ttft_seconds:.3f}s"
                    if record.ttft_seconds is not None
                    else ""
                )
                lines.append(f"- #{record.sequence_no}: total={record.elapsed_seconds:.3f}s{ttft_text} | {preview}")
        lines.append("")
        lines.append(f"## {summary.mode} failure distribution")
        if not summary.error_distribution:
            lines.append("- none")
        else:
            for error, count in summary.error_distribution:
                lines.append(f"- {count}x {error}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def run_mode(
    *,
    mode: str,
    queries: tuple[str, ...],
    sample_count: int,
    warmup_count: int,
    user_prefix: str,
    timeout_seconds: float,
    max_retries: int,
    retry_backoff_seconds: float,
    print_each: bool,
    base_url: str,
    api_key: str,
) -> list[SampleRecord]:
    records: list[SampleRecord] = []
    total_requests = warmup_count + sample_count
    client: DifyClient | None = None
    if mode != "streaming":
        client = DifyClient(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            response_mode=mode,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )

    for index in range(total_requests):
        query = pick_query(queries, index)
        phase = "warmup" if index < warmup_count else "sample"
        sequence_no = (index + 1) if phase == "warmup" else (index - warmup_count + 1)

        passed = False
        sources = 0
        error = ""
        conversation_id = ""
        message_id = ""
        ttft_seconds: float | None = None

        if mode == "streaming":
            result = _send_streaming_request_with_metrics(
                base_url=base_url,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                retry_backoff_seconds=retry_backoff_seconds,
                query=query,
                user=f"{user_prefix}-{mode}",
            )
            elapsed_seconds = result.elapsed_seconds
            ttft_seconds = result.ttft_seconds
            passed = result.passed
            sources = result.sources
            error = result.error
            conversation_id = result.conversation_id
            message_id = result.message_id
        else:
            started_at = perf_counter()
            try:
                assert client is not None
                response = client.send_chat_message(
                    query=query,
                    user=f"{user_prefix}-{mode}",
                )
                passed = bool(response.answer.strip()) and bool(response.retriever_resources)
                if not response.answer.strip():
                    error = "empty_answer"
                elif not response.retriever_resources:
                    error = "empty_retriever_resources"
                sources = len(response.retriever_resources)
                conversation_id = response.conversation_id
                message_id = response.message_id
            except DifyRequestError as exc:
                error = str(exc).strip() or "dify_request_error"
            elapsed_seconds = perf_counter() - started_at

        record = SampleRecord(
            mode=mode,
            phase=phase,
            sequence_no=sequence_no,
            query=query,
            elapsed_seconds=elapsed_seconds,
            ttft_seconds=ttft_seconds,
            passed=passed,
            sources=sources,
            error=error,
            conversation_id=conversation_id,
            message_id=message_id,
        )
        records.append(record)

        if print_each:
            mark = "PASS" if record.passed else "FAIL"
            ttft_text = (
                f" ttft={record.ttft_seconds:.3f}s"
                if record.ttft_seconds is not None
                else ""
            )
            print(
                f"[{mode}/{phase}] #{record.sequence_no} {mark} "
                f"elapsed={record.elapsed_seconds:.3f}s{ttft_text} sources={record.sources} error={record.error}"
            )

    return records


def _send_streaming_request_with_metrics(
    *,
    base_url: str,
    api_key: str,
    timeout_seconds: float,
    max_retries: int,
    retry_backoff_seconds: float,
    query: str,
    user: str,
) -> _StreamingRequestResult:
    attempts = max_retries + 1
    last_error: DifyRequestError | None = None

    for attempt in range(1, attempts + 1):
        try:
            return _stream_once(
                base_url=base_url,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
                query=query,
                user=user,
            )
        except httpx.TimeoutException as exc:
            last_error = DifyRequestError("Dify request timed out.", status_code=504)
        except httpx.HTTPError as exc:
            last_error = DifyRequestError(f"Dify request failed: {exc}")
        except DifyRequestError as exc:
            last_error = exc

        if attempt < attempts:
            _sleep_before_retry(attempt=attempt, retry_backoff_seconds=retry_backoff_seconds)

    raise last_error or DifyRequestError("Dify request failed after retries.")


def _stream_once(
    *,
    base_url: str,
    api_key: str,
    timeout_seconds: float,
    query: str,
    user: str,
) -> _StreamingRequestResult:
    started_at = perf_counter()
    url = _normalize_base_url(base_url)
    payload: dict[str, Any] = {
        "query": query,
        "inputs": {},
        "response_mode": "streaming",
        "user": user,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    message_id = ""
    conversation_id = ""
    answer_text = ""
    retriever_resources: list[dict[str, Any]] = []
    ttft_seconds: float | None = None
    seen_event = False

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
            seen_event = True
            if not message_id:
                message_id = _as_non_empty_str(event.get("message_id")) or ""
            if not conversation_id:
                conversation_id = _as_non_empty_str(event.get("conversation_id")) or ""

            chunk = _extract_stream_answer_chunk(event)
            if chunk:
                if ttft_seconds is None:
                    ttft_seconds = perf_counter() - started_at
                answer_text = _merge_answer_chunk(answer_text, chunk)

            resources = _extract_resources_from_event(event)
            if resources:
                retriever_resources = resources

        # Some gateways can still return plain JSON even when streaming is requested.
        if not seen_event:
            fallback_payload = _read_json_payload(response)
            message_id = _as_non_empty_str(fallback_payload.get("message_id")) or ""
            conversation_id = _as_non_empty_str(fallback_payload.get("conversation_id")) or ""
            answer_text = _as_non_empty_str(fallback_payload.get("answer")) or ""
            retriever_resources = _extract_resources_from_event(fallback_payload)
            if answer_text and ttft_seconds is None:
                ttft_seconds = perf_counter() - started_at

    elapsed_seconds = perf_counter() - started_at
    passed = bool(answer_text.strip()) and bool(retriever_resources)
    error = ""
    if not answer_text.strip():
        error = "empty_answer"
    elif not retriever_resources:
        error = "empty_retriever_resources"

    return _StreamingRequestResult(
        elapsed_seconds=elapsed_seconds,
        ttft_seconds=ttft_seconds,
        passed=passed,
        sources=len(retriever_resources),
        error=error,
        conversation_id=conversation_id,
        message_id=message_id,
    )


def _sleep_before_retry(*, attempt: int, retry_backoff_seconds: float) -> None:
    if retry_backoff_seconds <= 0:
        return
    time.sleep(retry_backoff_seconds * (2 ** (attempt - 1)))


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/chat-messages"
    return f"{normalized}/v1/chat-messages"


def _iter_sse_events(response: httpx.Response) -> Iterable[dict[str, Any]]:
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
            yield payload


def _extract_stream_answer_chunk(payload: dict[str, Any]) -> str:
    for key in ("answer", "text", "delta"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _extract_resources_from_event(payload: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = payload.get("metadata")
    resources = metadata.get("retriever_resources") if isinstance(metadata, dict) else []
    if isinstance(resources, list):
        return [item for item in resources if isinstance(item, dict)]
    return []


def _merge_answer_chunk(current: str, incoming: str) -> str:
    if not current:
        return incoming
    if incoming.startswith(current):
        return incoming
    if current.endswith(incoming):
        return current
    return f"{current}{incoming}"


def _as_non_empty_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _read_json_payload(response: httpx.Response) -> dict[str, Any]:
    body = response.read()
    if not body:
        return {}
    try:
        payload = json.loads(body.decode("utf-8", errors="ignore"))
    except ValueError:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _build_request_error(response: httpx.Response) -> DifyRequestError:
    payload = _read_json_payload(response)
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        message = "Dify request returned an unknown error."
    error_code = payload.get("code") if isinstance(payload.get("code"), str) else None
    return DifyRequestError(message, status_code=response.status_code, error_code=error_code)


def main() -> int:
    args = parse_args()
    settings = get_settings()

    modes = parse_modes(args.modes)
    if args.sample_count <= 0:
        raise ValueError("sample-count must be greater than 0.")
    if args.warmup_count < 0:
        raise ValueError("warmup-count must be greater than or equal to 0.")
    if args.threshold_seconds <= 0:
        raise ValueError("threshold-seconds must be greater than 0.")
    if args.retries < 0:
        raise ValueError("retries must be greater than or equal to 0.")
    if args.retry_backoff_seconds < 0:
        raise ValueError("retry-backoff-seconds must be greater than or equal to 0.")
    if args.timeout_seconds is not None and args.timeout_seconds <= 0:
        raise ValueError("timeout-seconds must be greater than 0.")

    timeout_seconds = args.timeout_seconds if args.timeout_seconds is not None else settings.dify_request_timeout_seconds
    queries = load_queries(args.queries_file)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now().astimezone()
    summaries: list[ModeSummary] = []

    for mode in modes:
        try:
            records = run_mode(
                mode=mode,
                queries=queries,
                sample_count=args.sample_count,
                warmup_count=args.warmup_count,
                user_prefix=args.user_prefix,
                timeout_seconds=timeout_seconds,
                max_retries=args.retries,
                retry_backoff_seconds=args.retry_backoff_seconds,
                print_each=args.print_each,
                base_url=settings.dify_base_url,
                api_key=settings.dify_api_key,
            )
        except DifyRequestError as exc:
            print(f"[FAIL] mode={mode} {exc}")
            return 1

        csv_path = output_dir / f"step12-latency-{mode}.csv"
        write_csv(csv_path, records)

        summary = build_mode_summary(
            mode=mode,
            records=records,
            threshold_seconds=args.threshold_seconds,
        )
        summaries.append(summary)

        print(
            (
                "mode={mode} samples={samples} success={success} failed={failed} "
                "avg={avg}s p95={p95}s avg_ttft={avg_ttft}s p95_ttft={p95_ttft}s <=threshold={within}/{samples}"
            ).format(
                mode=summary.mode,
                samples=summary.sample_total,
                success=summary.sample_success,
                failed=summary.sample_failed,
                avg=format_optional_seconds(summary.average_seconds),
                p95=format_optional_seconds(summary.p95_seconds),
                avg_ttft=format_optional_seconds(summary.average_ttft_seconds),
                p95_ttft=format_optional_seconds(summary.p95_ttft_seconds),
                within=summary.within_threshold_count,
            )
        )
        print(f"csv={csv_path}")

    finished_at = datetime.now().astimezone()
    summary_path = output_dir / "step12-latency-summary.md"
    summary_markdown = render_summary_markdown(
        started_at=started_at,
        finished_at=finished_at,
        threshold_seconds=args.threshold_seconds,
        summaries=tuple(summaries),
    )
    summary_path.write_text(summary_markdown, encoding="utf-8")
    print(f"summary={summary_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DifyRequestError, FileNotFoundError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1)
