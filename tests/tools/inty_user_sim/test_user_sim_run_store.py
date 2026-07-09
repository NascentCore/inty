"""Unit tests for SimRunStore checkpoint roundtrip."""

from __future__ import annotations

from pathlib import Path

from tools.inty_user_sim.run_store import SimRunStore
from tools.inty_user_sim.types import (
    GrillObjective,
    GrillPhase,
    SimRunCheckpoint,
    SimTurnRecord,
)


def test_checkpoint_roundtrip(tmp_path: Path) -> None:
    store = SimRunStore("run-1", tmp_path)
    cp = SimRunCheckpoint(
        run_id="run-1",
        agent_id="agent-1",
        sim_day=3,
        phase=GrillPhase.DAILY_CHAT,
        director_cursor=2,
        director_seed=99,
        persona_hash="deadbeef",
        turn_count=5,
        rupture_sent=False,
        absence_done_days=[7],
    )
    store.write_checkpoint(cp)
    loaded = store.load_checkpoint()
    assert loaded is not None
    assert loaded.sim_day == 3
    assert loaded.absence_done_days == [7]


def test_append_turn_jsonl(tmp_path: Path) -> None:
    store = SimRunStore("run-2", tmp_path)
    store.append(
        SimTurnRecord(
            sim_day=0,
            phase=GrillPhase.BOOTSTRAP,
            objective=GrillObjective.BOOTSTRAP_IDENTITY,
            user_text="hello",
            assistant_text="hi",
            user_msg_uuid="uuid-1",
            langsmith_trace_id=None,
            input_queue_status="delivered",
            memdoc_user_seq=2,
        )
    )
    turns = store.load_turns()
    assert len(turns) == 1
    assert turns[0].user_text == "hello"
