"""Unit tests for ``run_inty_repl_regression.py`` strict-mode DB verification helpers.

The skill script lives under ``.cursor/skills/scripts/`` and is loaded by file path
(see ``_load_regression_module``) because it is a CLI utility, not an ``app/`` module.
Only the JSON-line parser is covered here; the full driver is exercised manually via
the ``inty-repl-regression`` skill.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_regression_module():
    """Load the skill script as a module for unit-testing private parse helpers."""
    module_path = (
        Path(__file__).parents[4]
        / ".cursor"
        / "skills"
        / "scripts"
        / "run_inty_repl_regression.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_inty_repl_regression", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_proactive_chat_history_rows() -> None:
    mod = _load_regression_module()

    rows = mod._parse_proactive_chat_history_rows(
        """
{"chat_history_id":"1","content_preview":"[SYSTEM PROACTIVE CHAT] a|b","created_at":"2026-06-18 00:15:04+00","has_assistant_reply":false}
{"chat_history_id":"2","content_preview":"[SYSTEM PROACTIVE CHAT] c","created_at":"2026-06-18 00:16:04+00","has_assistant_reply":true}
"""
    )

    assert len(rows) == 2
    assert rows[0].chat_history_id == "1"
    assert rows[0].content_preview.endswith("a|b")
    assert rows[0].has_assistant_reply is False
    assert rows[1].has_assistant_reply is True
