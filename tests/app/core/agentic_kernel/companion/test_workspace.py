from __future__ import annotations

from pathlib import Path

from app.core.agentic_kernel.companion.workspace import (
    WorkspacePaths,
    is_workspace_initialized,
)


def test_workspace_paths_properties(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    p = WorkspacePaths(root=root)
    assert p.identity == root / "IDENTITY.md"
    assert p.soul == root / "SOUL.md"
    assert p.user_md == root / "USER.md"
    assert p.memory_md == root / "MEMORY.md"
    assert p.agents_md == root / "AGENTS.md"
    assert p.heartbeat_md == root / "HEARTBEAT.md"
    assert p.tools_md == root / "TOOLS.md"
    assert p.transcript == root / "transcript.jsonl"
    assert p.context_json == root / "context.json"
    assert p.memory_dir == root / "memory"
    assert p.memory_daily_dir == root / "memory" / "daily"
    assert p.memory_raw_diary("2026-04-05") == root / "memory" / "daily" / "2026-04-05.md"
    assert p.memory_day_summary("2026-04-05") == root / "memory" / "2026-04-05.md"
    assert p.memory_pipeline_state_json == root / ".companion_memory_pipeline.json"
    assert p.schedule_queue_json == root / ".companion_schedule_tasks.json"


def test_is_workspace_initialized_empty(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    assert is_workspace_initialized(d) is False


def test_is_workspace_initialized_complete(tmp_path: Path) -> None:
    d = tmp_path / "full"
    d.mkdir()
    for name in (
        "IDENTITY.md",
        "SOUL.md",
        "USER.md",
        "MEMORY.md",
        "transcript.jsonl",
    ):
        (d / name).write_text("x", encoding="utf-8")
    assert is_workspace_initialized(d) is True


def test_is_workspace_initialized_partial(tmp_path: Path) -> None:
    d = tmp_path / "partial"
    d.mkdir()
    for name in ("IDENTITY.md", "SOUL.md", "USER.md", "MEMORY.md"):
        (d / name).write_text("x", encoding="utf-8")
    assert is_workspace_initialized(d) is False
