"""Unit tests for ``run_inty_repl_regression.py`` proactive DB verification helpers.

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


def test_summarize_proactive_rounds() -> None:
    mod = _load_regression_module()

    summary = mod._summarize_proactive_rounds(
        [
            {"text_preview": "hello", "silent": False},
            {
                "text_preview": "[SYSTEM PROACTIVE CHAT] idle",
                "silent": True,
            },
        ]
    )
    assert summary == {
        "total": 2,
        "visible": 1,
        "silent": 1,
        "silent_token_leaks": 0,
    }


def test_proactive_entry_has_silent_token() -> None:
    mod = _load_regression_module()

    assert mod._proactive_entry_has_silent_token({"text_preview": "[SILENT]"})
    assert not mod._proactive_entry_has_silent_token({"text_preview": "hello"})


def test_append_proactive_db_row_dedupes_chat_history_id() -> None:
    mod = _load_regression_module()

    report: dict = {"proactive": []}
    row = mod.ProactiveChatHistoryRow(
        chat_history_id="42",
        content_preview="[SYSTEM PROACTIVE CHAT] a",
        created_at="2026-06-18T00:00:00+00",
        has_assistant_reply=False,
    )
    mod._append_proactive_db_row(report, row)
    mod._append_proactive_db_row(report, row)
    assert len(report["proactive"]) == 1
    assert report["proactive"][0]["silent"] is True


def test_parse_proactive_chat_history_rows() -> None:
    mod = _load_regression_module()

    rows = mod._parse_proactive_chat_history_rows("""
{"chat_history_id":"1","content_preview":"[SYSTEM PROACTIVE CHAT] a|b","created_at":"2026-06-18 00:15:04+00","has_assistant_reply":false}
{"chat_history_id":"2","content_preview":"[SYSTEM PROACTIVE CHAT] c","created_at":"2026-06-18 00:16:04+00","has_assistant_reply":true}
""")

    assert len(rows) == 2
    assert rows[0].chat_history_id == "1"
    assert rows[0].content_preview.endswith("a|b")
    assert rows[0].has_assistant_reply is False
    assert rows[1].has_assistant_reply is True


def test_parse_input_queue_status_counts() -> None:
    mod = _load_regression_module()

    counts = mod._parse_input_queue_status_counts("claimed|1\ndelivered|6\n")
    assert counts == {"claimed": 1, "delivered": 6}


def test_input_queue_has_in_flight() -> None:
    mod = _load_regression_module()

    assert mod._input_queue_has_in_flight({"delivered": 3}) is False
    assert (
        mod._input_queue_has_in_flight({"pending": 1, "delivered": 2}) is True
    )
    assert (
        mod._input_queue_has_in_flight({"claimed": 1, "delivered": 2}) is True
    )


def test_downlink_user_msg_uuid() -> None:
    mod = _load_regression_module()

    assert mod._downlink_user_msg_uuid({"user_msg_uuid": "abc"}) == "abc"
    assert mod._downlink_user_msg_uuid({}) == ""


def test_parse_feedback_jsonl_rows() -> None:
    mod = _load_regression_module()

    rows = mod._parse_feedback_jsonl_rows("""
{"kind":"snapshot","feedback_id":"fb-1","correlation":{"user_msg_uuid":"u1"}}
{"kind":"github_issue_created","feedback_id":"fb-1","github_issue_url":"https://github.com/o/r/issues/9","github_issue_number":9}
""")
    assert len(rows) == 2
    assert rows[0]["kind"] == "snapshot"


def test_find_snapshot_for_user_msg_uuid() -> None:
    mod = _load_regression_module()

    rows = mod._parse_feedback_jsonl_rows("""
{"kind":"snapshot","feedback_id":"fb-1","correlation":{"user_msg_uuid":"u1"}}
{"kind":"snapshot","feedback_id":"fb-2","correlation":{"user_msg_uuid":"u2"}}
""")
    assert mod._find_snapshot_for_user_msg_uuid(rows, "u1") is True
    assert mod._find_snapshot_for_user_msg_uuid(rows, "missing") is False


def test_find_feedback_id_for_user_msg_uuid() -> None:
    mod = _load_regression_module()

    rows = mod._parse_feedback_jsonl_rows("""
{"kind":"snapshot","feedback_id":"fb-1","correlation":{"user_msg_uuid":"u1"}}
""")
    assert mod._find_feedback_id_for_user_msg_uuid(rows, "u1") == "fb-1"
    assert mod._find_feedback_id_for_user_msg_uuid(rows, "u2") == ""


def test_parse_feedback_github_issue_row() -> None:
    mod = _load_regression_module()

    rows = mod._parse_feedback_jsonl_rows("""
{"kind":"snapshot","feedback_id":"fb-1","correlation":{"user_msg_uuid":"u1"}}
{"kind":"github_issue_created","feedback_id":"fb-2","github_issue_url":"https://github.com/o/r/issues/8","github_issue_number":8}
{"kind":"github_issue_created","feedback_id":"fb-1","github_issue_url":"https://github.com/o/r/issues/9","github_issue_number":9}
""")
    row = mod._parse_feedback_github_issue_row(
        rows, user_msg_uuid="u1", feedback_id="fb-1"
    )
    assert row is not None
    assert row.issue_number == 9
    assert row.user_msg_uuid == "u1"
    assert (
        mod._parse_feedback_github_issue_row(
            rows, user_msg_uuid="u1", feedback_id="fb-missing"
        )
        is None
    )


def test_find_github_issue_skipped_reason() -> None:
    mod = _load_regression_module()

    rows = mod._parse_feedback_jsonl_rows("""
{"kind":"github_issue_skipped","feedback_id":"fb-1","github_issue_status":"skipped_no_token"}
""")
    assert (
        mod._find_github_issue_skipped_reason(rows, feedback_id="fb-1")
        == "skipped_no_token"
    )
    assert (
        mod._find_github_issue_skipped_reason(rows, feedback_id="fb-2") is None
    )


def test_assistant_reply_discloses_issue_url() -> None:
    mod = _load_regression_module()

    url = "https://github.com/NascentCore/inty/issues/3595"
    assert mod._assistant_reply_discloses_issue_url(
        f"Filed your feedback: {url}",
        url,
        3595,
    )
    assert mod._assistant_reply_discloses_issue_url(
        "Tracked as NascentCore/inty/issues/3595 for the team.",
        url,
        3595,
    )
    assert not mod._assistant_reply_discloses_issue_url(
        "Thanks, I recorded your feedback.",
        url,
        3595,
    )
    assert not mod._assistant_reply_discloses_issue_url("", url, 3595)


def test_load_app_debug_from_config(tmp_path) -> None:
    mod = _load_regression_module()

    cfg = tmp_path / "config.yaml"
    cfg.write_text("app:\n  debug: true\n", encoding="utf-8")
    assert mod._load_app_debug_from_config(cfg) is True
    cfg.write_text("app:\n  debug: false\n", encoding="utf-8")
    assert mod._load_app_debug_from_config(cfg) is False


def test_is_implicit_sign_on_greeting() -> None:
    mod = _load_regression_module()

    assert mod._is_implicit_sign_on_greeting({"source": "greeting"})
    assert not mod._is_implicit_sign_on_greeting({"source": "chat"})
    assert not mod._is_implicit_sign_on_greeting({})


def test_verify_implicit_sign_on_greeting() -> None:
    mod = _load_regression_module()

    ok = mod._verify_implicit_sign_on_greeting(
        [
            {
                "text_preview": "hello",
                "meta": {"source": "greeting", "langsmith_trace_id": "t1"},
            }
        ]
    )
    assert ok.present is True
    assert ok.source_greeting is True
    assert ok.langsmith_trace_id == "t1"

    missing = mod._verify_implicit_sign_on_greeting(
        [{"text_preview": "hello", "meta": {"source": "chat"}}]
    )
    assert missing.present is False


def test_agent_scope_chat_id() -> None:
    mod = _load_regression_module()

    assert (
        mod._agent_scope_chat_id("user-testing", "agent-1")
        == "agent-scope:user-testing:agent-1"
    )


def test_verify_bootstrap_memdocs_detects_customization(tmp_path) -> None:
    mod = _load_regression_module()
    repo_root = Path(__file__).parents[4]
    mod._ensure_import_path(repo_root)
    from app.core.companion_harness.memory.memory_store_scope import (
        load_template_seed_text,
    )

    soul_seed = load_template_seed_text("SOUL.md")
    memory_seed = load_template_seed_text("MEMORY.md")
    style_seed = load_template_seed_text("STYLE.md")

    def fake_psql(_repo_root, _config_path, query: str) -> str:
        if "document_kind = 'user'" in query:
            return "2|# user\n大雄\n"
        if "document_kind = 'identity'" in query:
            return "2|# id\n多啦\n"
        if "document_kind = 'style'" in query:
            return f"2|{style_seed}\n# customized\n"
        if "document_kind = 'soul'" in query:
            return f"1|{soul_seed}"
        if "document_kind = 'memory'" in query:
            return f"1|{memory_seed}"
        return ""

    original = mod._psql
    mod._psql = fake_psql
    try:
        result = mod._verify_bootstrap_memdocs(
            repo_root,
            tmp_path / "missing.yaml",
            user_id="user-testing",
            agent_id="agent-1",
        )
    finally:
        mod._psql = original

    assert result.user_customized is True
    assert result.identity_customized is True
    assert result.style_customized is True
    assert result.soul_unchanged is True
    assert result.memory_unchanged is True
    assert result.errors == ()
