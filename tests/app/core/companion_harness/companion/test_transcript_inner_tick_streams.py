from __future__ import annotations

from app.core.companion_harness.companion.models import (
    ChatMessage,
    InnerTickMode,
    merge_transcripts_by_ts,
    transcript_relative_path_for_turn_persistence,
    transcript_rows_for_public_chat_llm,
)


def test_transcript_rows_for_public_chat_llm_drops_maintenance_inner_tick() -> None:
    uid_m = "maint-user-1"
    uid_real = "real-user-1"
    rows = [
        ChatMessage(
            role="user", content="hello", ts="2026-05-01T00:00:01Z", uuid=uid_real
        ),
        ChatMessage(
            role="assistant", content="hi", ts="2026-05-01T00:00:02Z", reply_to=uid_real
        ),
        ChatMessage(
            role="user",
            content="（内在节拍）",
            ts="2026-05-01T00:00:03Z",
            uuid=uid_m,
            inner_tick=True,
        ),
        ChatMessage(
            role="assistant",
            content="internal",
            ts="2026-05-01T00:00:04Z",
            reply_to=uid_m,
            source="inner_tick",
        ),
    ]
    pub = transcript_rows_for_public_chat_llm(rows)
    assert len(pub) == 2
    assert pub[0].uuid == uid_real
    assert pub[1].reply_to == uid_real


def test_transcript_rows_for_public_chat_llm_keeps_proactive_heartbeat_inner_tick() -> (
    None
):
    uid_h = "hb-user-1"
    rows = [
        ChatMessage(
            role="user",
            content="（陪伴心跳）",
            ts="2026-05-01T00:00:01Z",
            uuid=uid_h,
            inner_tick=True,
            heartbeat=True,
        ),
        ChatMessage(
            role="assistant",
            content="hey",
            ts="2026-05-01T00:00:02Z",
            reply_to=uid_h,
            source="inner_tick",
        ),
    ]
    pub = transcript_rows_for_public_chat_llm(rows)
    assert len(pub) == 2


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
            inner_tick_mode=InnerTickMode.MAINTENANCE,
        )
        == "transcript.jsonl"
    )
    assert (
        transcript_relative_path_for_turn_persistence(
            inner_tick_turn=True,
            inner_tick_mode=InnerTickMode.PROACTIVE_CHAT,
        )
        == "transcript.jsonl"
    )
    assert (
        transcript_relative_path_for_turn_persistence(
            inner_tick_turn=True,
            inner_tick_mode=InnerTickMode.MAINTENANCE,
        )
        == "transcript_inner_tick.jsonl"
    )
