from __future__ import annotations

from app.core.companion_harness.runtime.models import (
    ChatMessage,
    InnerTickActivity,
    merge_transcripts_by_ts,
    transcript_relative_path_for_turn_persistence,
)


def test_merge_transcripts_by_ts_orders_then_stable_tiebreak() -> None:
    main = [
        ChatMessage(role="user", content="a", ts="2026-05-01T00:00:02Z"),
    ]
    inner = [
        ChatMessage(role="user", content="b", ts="2026-05-01T00:00:02Z"),
    ]
    merged = merge_transcripts_by_ts(main, inner)
    assert [m.content for m in merged] == ["a", "b"]


def test_transcript_relative_path_for_turn_persistence() -> None:
    assert (
        transcript_relative_path_for_turn_persistence(
            inner_tick_turn=False,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
        )
        == "transcript.jsonl"
    )
    assert (
        transcript_relative_path_for_turn_persistence(
            inner_tick_turn=True,
            inner_tick_activity=InnerTickActivity.PROACTIVE_CHAT,
        )
        == "transcript.jsonl"
    )
    assert (
        transcript_relative_path_for_turn_persistence(
            inner_tick_turn=True,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
        )
        == "transcript_inner_tick.jsonl"
    )
