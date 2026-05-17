from __future__ import annotations

from experimental.agentic_ai_companion.memory_compaction import (
    COMPACTION_SYSTEM_TAG,
    CompactionConfig,
    ConversationCompactor,
)


def _build_messages(turns: int, *, tail: str = "") -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "You are a caring AI companion."}
    ]
    for idx in range(turns):
        messages.append(
            {
                "role": "user",
                "content": f"Turn {idx}: I am feeling stressed and I like jazz. {tail}",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": f"Turn {idx}: I hear you and I will stay with you. {tail}",
            }
        )
    return messages


def test_memory_compaction_not_triggered_under_budget():
    compactor = ConversationCompactor(
        config=CompactionConfig(
            max_context_chars=2000,
            keep_recent_messages=6,
            max_messages_per_episode=4,
            max_episodic_entries=20,
            max_semantic_entries=20,
            summary_max_chars=600,
            retrieval_episode_count=4,
            retrieval_semantic_count=6,
            retrieval_open_loop_count=4,
        )
    )
    messages = _build_messages(2)
    outcome = compactor.maybe_compact(messages=messages, turn=3)

    assert outcome.did_compact is False
    assert outcome.reason == "under_budget"
    assert outcome.messages == messages


def test_memory_compaction_inserts_snapshot_and_keeps_recent_dialogue():
    compactor = ConversationCompactor(
        config=CompactionConfig(
            max_context_chars=420,
            keep_recent_messages=4,
            max_messages_per_episode=4,
            max_episodic_entries=20,
            max_semantic_entries=20,
            summary_max_chars=600,
            retrieval_episode_count=4,
            retrieval_semantic_count=6,
            retrieval_open_loop_count=4,
        )
    )
    messages = _build_messages(8, tail="Please help me process this tonight.")
    dialogue = [m for m in messages if m["role"] != "system"]
    recent_dialogue = dialogue[-4:]

    outcome = compactor.maybe_compact(messages=messages, turn=9)

    assert outcome.did_compact is True
    assert outcome.approx_chars_after < outcome.approx_chars_before
    memory_msgs = [
        m
        for m in outcome.messages
        if m["role"] == "system"
        and str(m.get("content", "")).startswith(COMPACTION_SYSTEM_TAG)
    ]
    assert len(memory_msgs) == 1
    assert outcome.messages[-4:] == recent_dialogue


def test_memory_compaction_extracts_semantic_facts_and_open_loops():
    compactor = ConversationCompactor(
        config=CompactionConfig(
            max_context_chars=240,
            keep_recent_messages=4,
            max_messages_per_episode=4,
            max_episodic_entries=20,
            max_semantic_entries=20,
            summary_max_chars=600,
            retrieval_episode_count=4,
            retrieval_semantic_count=6,
            retrieval_open_loop_count=4,
        )
    )
    messages = [
        {"role": "system", "content": "You are a companion."},
        {
            "role": "user",
            "content": "I am a product designer. I like jazz and hiking.",
        },
        {"role": "assistant", "content": "That is wonderful."},
        {
            "role": "user",
            "content": "Can you remind me to recharge after work?",
        },
        {"role": "assistant", "content": "Yes, I can help with that."},
        {"role": "user", "content": "I need deeper emotional support tonight."},
        {"role": "assistant", "content": "I will stay with you."},
        {"role": "user", "content": "Tell me a short grounding exercise."},
        {"role": "assistant", "content": "Breathe and relax your shoulders."},
    ]

    outcome = compactor.maybe_compact(messages=messages, turn=10)

    assert outcome.did_compact is True
    facts = [item.fact for item in outcome.state.semantic_memory]
    assert any("i am a product designer" in fact for fact in facts)
    assert any("i like jazz and hiking" in fact for fact in facts)
    assert any(
        "can you remind me to recharge after work" in loop.lower()
        for episode in outcome.state.episodic_memory
        for loop in episode.open_loops
    )
