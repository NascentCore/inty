from __future__ import annotations

import datetime

import pytest

from app.core.agentic_kernel.companion.workspace_doc_mapping import (
    CompanionWorkspaceDocKind,
    parse_workspace_relative_path,
    relative_path_for_kind,
)


def test_parse_identity_and_daily() -> None:
    k, d = parse_workspace_relative_path("IDENTITY.md")
    assert k == CompanionWorkspaceDocKind.IDENTITY
    assert d is None
    k2, d2 = parse_workspace_relative_path("memory/daily/2026-03-01.md")
    assert k2 == CompanionWorkspaceDocKind.MEMORY_DAILY_RAW
    assert d2 == datetime.date(2026, 3, 1)
    k3, d3 = parse_workspace_relative_path("memory/2026-03-01.md")
    assert k3 == CompanionWorkspaceDocKind.MEMORY_DAY_SUMMARY
    assert d3 == datetime.date(2026, 3, 1)


def test_roundtrip_static_paths() -> None:
    for rel in (
        "SOUL.md",
        "transcript.jsonl",
        "tool_background.jsonl",
        ".companion_memory_pipeline.json",
        "generated_images/index.jsonl",
    ):
        kind, cal = parse_workspace_relative_path(rel)
        assert relative_path_for_kind(kind, cal) == rel


def test_invalid_path_raises() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        parse_workspace_relative_path("memory/not-a-date.md")
