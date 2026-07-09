"""Checkpoint and JSONL persistence for long-term sim runs."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from tools.inty_user_sim.types import GrillObjective, GrillPhase, SimRunCheckpoint, SimTurnRecord


class SimRunStore:
    """Append-only turn log plus atomic checkpoint writes."""

    def __init__(self, run_id: str, base_dir: Path) -> None:
        assert run_id != ""
        self._run_id = run_id
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._jsonl_path = self._base_dir / f"user-sim-turns-{run_id}.jsonl"
        self._checkpoint_path = self._base_dir / f"user-sim-checkpoint-{run_id}.json"

    @property
    def jsonl_path(self) -> Path:
        return self._jsonl_path

    @property
    def checkpoint_path(self) -> Path:
        return self._checkpoint_path

    def append(self, record: SimTurnRecord) -> None:
        line = json.dumps(asdict(record), ensure_ascii=False)
        with self._jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def load_turns(self) -> list[SimTurnRecord]:
        if not self._jsonl_path.is_file():
            return []
        records: list[SimTurnRecord] = []
        for line in self._jsonl_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            records.append(
                SimTurnRecord(
                    sim_day=int(raw["sim_day"]),
                    phase=GrillPhase(str(raw["phase"])),
                    objective=GrillObjective(str(raw["objective"])),
                    user_text=str(raw["user_text"]),
                    assistant_text=raw.get("assistant_text"),
                    user_msg_uuid=str(raw["user_msg_uuid"]),
                    langsmith_trace_id=raw.get("langsmith_trace_id"),
                    input_queue_status=str(raw.get("input_queue_status", "")),
                    memdoc_user_seq=raw.get("memdoc_user_seq"),
                )
            )
        return records

    def write_checkpoint(self, checkpoint: SimRunCheckpoint) -> None:
        self._checkpoint_path.write_text(
            checkpoint.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def load_checkpoint(self) -> SimRunCheckpoint | None:
        if not self._checkpoint_path.is_file():
            return None
        return SimRunCheckpoint.model_validate_json(
            self._checkpoint_path.read_text(encoding="utf-8")
        )
