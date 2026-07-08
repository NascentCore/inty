"""Unit tests for ``companion_harness_todo_audit.py`` (fake issue cache, no live gh)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]


def _load_todo_audit_module():
    module_path = (
        REPO_ROOT / ".cursor" / "skills" / "scripts" / "companion_harness_todo_audit.py"
    )
    spec = importlib.util.spec_from_file_location(
        "companion_harness_todo_audit", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_plan_todo_hygiene_retargets_closed_3463_to_3801(tmp_path: Path) -> None:
    mod = _load_todo_audit_module()
    cache_path = tmp_path / "issues.json"
    cache_path.write_text(
        json.dumps(
            [
                {"number": 3463, "state": "CLOSED"},
                {"number": 3801, "state": "OPEN"},
            ]
        ),
        encoding="utf-8",
    )
    issue_state = mod.load_issue_state_cache(str(cache_path))
    anchor = mod.TodoAnchor(
        path="app/core/companion_harness/companion/bootstrap.py",
        line=68,
        raw_line="# TODO(bootstrap): single-source — #3463",
        issue_number=3463,
        tag="bootstrap",
    )
    rows = mod.plan_todo_hygiene([anchor], issue_state)
    assert len(rows) == 1
    assert rows[0].action == mod.TodoActionKind.RETARGET
    assert rows[0].target_issue == 3801


def test_assert_no_closed_refs_passes_on_open_only(tmp_path: Path) -> None:
    mod = _load_todo_audit_module()
    cache_path = tmp_path / "issues.json"
    cache_path.write_text(
        json.dumps([{"number": 3801, "state": "OPEN"}]),
        encoding="utf-8",
    )
    issue_state = mod.load_issue_state_cache(str(cache_path))
    anchor = mod.TodoAnchor(
        path="app/core/companion_harness/companion/bootstrap.py",
        line=68,
        raw_line="# TODO(#3801): bootstrap single-source",
        issue_number=3801,
        tag=None,
    )
    mod.assert_no_closed_refs([anchor], issue_state)


@pytest.mark.skipif(
    not (REPO_ROOT / ".inty" / "issue_audit_all.json").is_file(),
    reason="issue cache not exported",
)
def test_full_tree_audit_passes_after_hygiene() -> None:
    mod = _load_todo_audit_module()
    cache_path = REPO_ROOT / ".inty" / "issue_audit_all.json"
    issue_state = mod.load_issue_state_cache(str(cache_path))
    anchors = mod.scan_companion_harness_todos(str(REPO_ROOT / "app/core/companion_harness"))
    mod.assert_no_closed_refs(anchors, issue_state)
