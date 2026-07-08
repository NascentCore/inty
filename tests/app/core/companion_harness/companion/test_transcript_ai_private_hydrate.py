from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.companion.ai_private_prompt import (
    append_ai_private_thought,
)
from app.core.companion_harness.companion.models import (
    AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
    ChatMessage,
    CompanionTurnTrack,
    load_transcript_from_store,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.transcript_ai_private import (
    AiPrivateSplicePersistInput,
    AiPrivateSplicePlan,
    build_ai_private_splice_plan,
    expand_manifest_rows,
    persist_ai_private_splice_if_applicable,
    should_persist_ai_private_splice,
    transcript_window_to_llm_dialogue,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    TRANSCRIPT_JSONL_REL,
)


def test_expand_manifest_rows_hydrates_monolog(tmp_path: Path) -> None:
    store = MemoryStore(
        scope=CompanionScope("hydrate", "a", tmp_path.name),
        repository=None,
    )
    thought = append_ai_private_thought(
        store, text="inner line", after_user_msg_uuid=None
    )
    manifest = ChatMessage(
        role="system",
        content="[ai_private_splice]",
        ts="2026-01-02T10:00:00+00:00",
        uuid="manifest-1",
        source=AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
        ai_private_thought_uuids=[thought.uuid],
    )
    expanded = expand_manifest_rows(store, [manifest])
    assert len(expanded) == 1
    assert expanded[0].role == "assistant"
    assert expanded[0].content == "inner line"
    assert expanded[0].source == "ai_private"


def test_tail_splice_skips_surfaced_thoughts(tmp_path: Path) -> None:
    store = MemoryStore(
        scope=CompanionScope("splice", "a", tmp_path.name),
        repository=None,
    )
    thought = append_ai_private_thought(
        store, text="unsurfaced", after_user_msg_uuid=None
    )
    transcript = [
        ChatMessage(
            role="user",
            content="hi",
            ts="2026-01-02T09:00:00+00:00",
            uuid="user-1",
        ),
    ]
    selected = build_ai_private_splice_plan(store, transcript).thoughts
    assert [t.uuid for t in selected] == [thought.uuid]
    from app.core.companion_harness.companion.ai_private_prompt import (
        mark_ai_private_surfaced,
    )

    mark_ai_private_surfaced(store, [thought.uuid])
    assert build_ai_private_splice_plan(store, transcript).thoughts == ()


def test_transcript_window_to_llm_dialogue_appends_tail_splice(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dialogue", "a", tmp_path.name),
        repository=None,
    )
    append_ai_private_thought(
        store, text="tail thought", after_user_msg_uuid=None
    )
    transcript = [
        ChatMessage(
            role="user",
            content="hello",
            ts="2026-01-02T09:00:00+00:00",
            uuid="user-1",
        ),
    ]
    thoughts = list(build_ai_private_splice_plan(store, transcript).thoughts)
    dialogue = transcript_window_to_llm_dialogue(
        store, transcript, tail_splice_thoughts=thoughts
    )
    assert dialogue[-1]["role"] == "assistant"
    assert "tail thought" in dialogue[-1]["content"]


def test_persist_ai_private_splice_appends_manifest_and_marks_surfaced(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("persist", "a", tmp_path.name),
        repository=None,
    )
    thought = append_ai_private_thought(
        store, text="to surface", after_user_msg_uuid=None
    )
    persist_ai_private_splice_if_applicable(
        AiPrivateSplicePersistInput(
            store=store,
            transcript_relative_path=TRANSCRIPT_JSONL_REL,
            track=CompanionTurnTrack.USER_CHAT,
            splice_plan=AiPrivateSplicePlan(
                thoughts=(thought,),
                anchor_user_msg_uuid="user-1",
            ),
            user_msg_uuid="user-2",
            assistant_text="reply",
            skip_final_transcript_assistant_row=False,
        )
    )
    rows = load_transcript_from_store(store, TRANSCRIPT_JSONL_REL)
    assert len(rows) == 1
    assert rows[0].source == AI_PRIVATE_SPLICE_MANIFEST_SOURCE
    assert rows[0].ai_private_thought_uuids == [thought.uuid]
    assert (
        build_ai_private_splice_plan(
            store,
            [
                ChatMessage(
                    role="user",
                    content="hi",
                    ts="2026-01-02T09:00:00+00:00",
                    uuid="user-1",
                ),
            ],
        ).thoughts
        == ()
    )


def test_persist_ai_private_splice_skips_silent_reply(tmp_path: Path) -> None:
    store = MemoryStore(
        scope=CompanionScope("silent", "a", tmp_path.name),
        repository=None,
    )
    thought = append_ai_private_thought(
        store, text="unsurfaced", after_user_msg_uuid=None
    )
    persist_input = AiPrivateSplicePersistInput(
        store=store,
        transcript_relative_path=TRANSCRIPT_JSONL_REL,
        track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        splice_plan=AiPrivateSplicePlan(
            thoughts=(thought,),
            anchor_user_msg_uuid="user-1",
        ),
        user_msg_uuid="user-2",
        assistant_text="",
        skip_final_transcript_assistant_row=False,
    )
    assert not should_persist_ai_private_splice(persist_input)
    persist_ai_private_splice_if_applicable(persist_input)
    assert load_transcript_from_store(store, TRANSCRIPT_JSONL_REL) == []
    assert build_ai_private_splice_plan(
        store,
        [
            ChatMessage(
                role="user",
                content="hi",
                ts="2026-01-02T09:00:00+00:00",
                uuid="user-1",
            ),
        ],
    ).thoughts == (thought,)
