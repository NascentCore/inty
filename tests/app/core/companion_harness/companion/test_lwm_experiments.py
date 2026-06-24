"""Unit tests for LWM-inspired AUTONOMY experiment helpers."""

from __future__ import annotations

import json

from app.core.companion_harness.companion.lwm_experiments import (
    LwmExperimentFlags,
    build_lwm_experiment_autonomy_slices,
    read_recent_techno_core_event_summaries,
    resolve_lwm_experiment_flags,
)
from app.core.companion_harness.companion.models import ContextMeta
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.techno_core.models import (
    Sphere,
    TechnoCoreEvent,
    TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH,
)


def _store(tmp_path) -> MemoryStore:
    scope = CompanionScope(
        user_id="user-testing",
        companion_id="agent-test",
        chat_id="agent-scope:user-testing:agent-test",
    )
    return MemoryStore(scope=scope, repository=None)


def test_resolve_lwm_experiment_flags_uses_context_override(tmp_path) -> None:
    del tmp_path
    context = ContextMeta(
        lwm_experience_state_loop=True,
        lwm_state_consistency=False,
        lwm_mental_simulation=True,
    )
    flags = resolve_lwm_experiment_flags(context)
    assert flags.experience_state_loop is True
    assert flags.state_consistency is False
    assert flags.mental_simulation is True


def test_read_recent_techno_core_event_summaries_tail(tmp_path) -> None:
    store = _store(tmp_path)
    for idx in range(3):
        event = TechnoCoreEvent(
            sphere=Sphere.TECHNO_CORE,
            actor_companion_id="agent-test",
            summary=f"event-{idx}",
        )
        store.append_jsonl_record(
            TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH,
            json.loads(event.model_dump_json()),
        )
    summaries = read_recent_techno_core_event_summaries(store, limit=2)
    assert len(summaries) == 2
    assert "event-1" in summaries[0]
    assert "event-2" in summaries[1]


def test_build_slices_empty_when_all_off(tmp_path) -> None:
    store = _store(tmp_path)
    flags = LwmExperimentFlags(
        experience_state_loop=False,
        state_consistency=False,
        mental_simulation=False,
        max_techno_core_events_injected=5,
    )
    slices = build_lwm_experiment_autonomy_slices(
        store=store,
        context=ContextMeta(),
        flags=flags,
    )
    assert slices == []


def test_build_slices_includes_all_experiments(tmp_path) -> None:
    store = _store(tmp_path)
    flags = LwmExperimentFlags(
        experience_state_loop=True,
        state_consistency=True,
        mental_simulation=True,
        max_techno_core_events_injected=5,
    )
    slices = build_lwm_experiment_autonomy_slices(
        store=store,
        context=ContextMeta(),
        flags=flags,
    )
    assert len(slices) == 3
    assert "经验→状态闭环" in slices[0]
    assert "state consistency" in slices[1]
    assert "mental simulation" in slices[2]
