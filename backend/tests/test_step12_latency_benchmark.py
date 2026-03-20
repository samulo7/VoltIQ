from __future__ import annotations

from datetime import datetime

from scripts.benchmark_step12_dify_latency import (
    ModeSummary,
    SampleRecord,
    build_mode_summary,
    parse_modes,
    percentile,
    render_summary_markdown,
)


def _record(
    *,
    mode: str,
    phase: str,
    sequence_no: int,
    elapsed_seconds: float,
    ttft_seconds: float | None = None,
    passed: bool,
    error: str = "",
) -> SampleRecord:
    return SampleRecord(
        mode=mode,
        phase=phase,
        sequence_no=sequence_no,
        query=f"q-{sequence_no}",
        elapsed_seconds=elapsed_seconds,
        ttft_seconds=ttft_seconds,
        passed=passed,
        sources=1 if passed else 0,
        error=error,
        conversation_id="conv",
        message_id="msg",
    )


def test_parse_modes_deduplicates_and_validates() -> None:
    assert parse_modes("blocking, streaming,blocking") == ("blocking", "streaming")


def test_percentile_linear_interpolation() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert percentile(values, 0) == 1.0
    assert percentile(values, 50) == 2.5
    assert percentile(values, 95) == 3.8499999999999996
    assert percentile(values, 100) == 4.0
    assert percentile([], 50) is None


def test_build_mode_summary_uses_sample_phase_only() -> None:
    records = [
        _record(mode="blocking", phase="warmup", sequence_no=1, elapsed_seconds=9.0, passed=True),
        _record(mode="blocking", phase="sample", sequence_no=1, elapsed_seconds=1.2, passed=True),
        _record(mode="blocking", phase="sample", sequence_no=2, elapsed_seconds=2.7, passed=True),
        _record(
            mode="blocking",
            phase="sample",
            sequence_no=3,
            elapsed_seconds=0.8,
            passed=False,
            error="timeout",
        ),
    ]

    summary = build_mode_summary(mode="blocking", records=records, threshold_seconds=2.0)
    assert summary.sample_total == 3
    assert summary.sample_success == 2
    assert summary.sample_failed == 1
    assert round(summary.average_seconds or 0.0, 2) == 1.95
    assert round(summary.p50_seconds or 0.0, 2) == 1.95
    assert round(summary.p95_seconds or 0.0, 2) == 2.62
    assert summary.average_ttft_seconds is None
    assert summary.p50_ttft_seconds is None
    assert summary.p95_ttft_seconds is None
    assert summary.within_threshold_count == 1
    assert round(summary.within_threshold_rate, 4) == 0.3333
    assert round(summary.failure_rate, 4) == 0.3333
    assert summary.slowest_successes[0].elapsed_seconds == 2.7
    assert summary.error_distribution == (("timeout", 1),)


def test_build_mode_summary_streaming_ttft_aggregates() -> None:
    records = [
        _record(
            mode="streaming",
            phase="sample",
            sequence_no=1,
            elapsed_seconds=3.0,
            ttft_seconds=0.7,
            passed=True,
        ),
        _record(
            mode="streaming",
            phase="sample",
            sequence_no=2,
            elapsed_seconds=5.0,
            ttft_seconds=1.1,
            passed=True,
        ),
        _record(
            mode="streaming",
            phase="sample",
            sequence_no=3,
            elapsed_seconds=4.0,
            ttft_seconds=0.9,
            passed=True,
        ),
    ]

    summary = build_mode_summary(mode="streaming", records=records, threshold_seconds=2.0)
    assert round(summary.average_ttft_seconds or 0.0, 2) == 0.90
    assert round(summary.p50_ttft_seconds or 0.0, 2) == 0.90
    assert round(summary.p95_ttft_seconds or 0.0, 2) == 1.08


def test_render_summary_markdown_contains_key_fields() -> None:
    summary = ModeSummary(
        mode="blocking",
        sample_total=2,
        sample_success=2,
        sample_failed=0,
        average_seconds=1.3,
        p50_seconds=1.3,
        p95_seconds=1.5,
        average_ttft_seconds=None,
        p50_ttft_seconds=None,
        p95_ttft_seconds=None,
        threshold_seconds=2.0,
        within_threshold_count=2,
        within_threshold_rate=1.0,
        failure_rate=0.0,
        slowest_successes=(
            _record(mode="blocking", phase="sample", sequence_no=1, elapsed_seconds=1.5, passed=True),
        ),
        error_distribution=(),
    )
    markdown = render_summary_markdown(
        started_at=datetime.fromisoformat("2026-03-20T10:00:00+08:00"),
        finished_at=datetime.fromisoformat("2026-03-20T10:01:00+08:00"),
        threshold_seconds=2.0,
        summaries=(summary,),
    )
    assert "Step 12 Dify Latency Benchmark Summary" in markdown
    assert "| blocking | 2 | 2 | 0 | 1.300 | 1.300 | 1.500 | n/a | n/a | n/a | 2/2 (100.0%) | 0.0% |" in markdown
    assert "## blocking slowest successful samples" in markdown
