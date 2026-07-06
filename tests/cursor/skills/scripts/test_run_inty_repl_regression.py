"""Unit tests for ``run_inty_repl_regression.py`` proactive DB verification helpers.

The skill script lives under ``.cursor/skills/scripts/`` and is loaded by file path
(see ``_load_regression_module``) because it is a CLI utility, not an ``app/`` module.
Parsers and one-shot dreaming verification helpers are covered here; the full driver
is exercised manually via the ``inty-repl-regression`` skill.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest


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
    assert mod._is_implicit_sign_on_greeting({"isOpening": True})
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


def test_queue_has_in_flight() -> None:
    mod = _load_regression_module()

    assert mod._queue_has_in_flight({"delivered": 3}) is False
    assert mod._queue_has_in_flight({"pending": 1, "delivered": 2}) is True
    assert mod._queue_has_in_flight({"claimed": 1}) is True


def test_delivery_queue_table() -> None:
    mod = _load_regression_module()

    assert (
        mod._delivery_queue_table(mod.DeliveryQueueKind.INPUT)
        == "agentic_companion_input_queue"
    )
    assert (
        mod._delivery_queue_table(mod.DeliveryQueueKind.OUTPUT)
        == "agentic_companion_output_queue"
    )


def test_phase_settle_spec_timeouts() -> None:
    mod = _load_regression_module()

    spec = mod.PhaseSettleSpec(
        label="x",
        ws_quiet_sec=1.0,
        ws_max_sec=2.0,
        wait_input_queue=True,
        wait_output_queue=True,
        queue_timeout_sec=100.0,
        input_queue_timeout_sec=50.0,
    )
    assert spec.input_timeout() == 50.0
    assert spec.output_timeout() == 100.0


def test_regression_pass_gate_passed() -> None:
    mod = _load_regression_module()

    gate = mod.RegressionPassGate(
        bootstrap_done=True,
        greeting_present=True,
        memdoc_errors=(),
        experience_profile_ok=True,
        dreaming_ok=True,
        settled_ok=True,
        has_report_errors=False,
        input_all_delivered=True,
        output_all_delivered=True,
        proactive_present=True,
        proactive_silent_ok=True,
        github_issue_ok=True,
        github_disclosure_ok=True,
        scope=mod.RegressionScope.FULL,
        skip_db_checks=False,
        proactive_min_rounds=1,
    )
    assert gate.passed() is True
    gate_fail = mod.RegressionPassGate(
        bootstrap_done=True,
        greeting_present=True,
        memdoc_errors=("memdoc",),
        experience_profile_ok=True,
        dreaming_ok=True,
        settled_ok=True,
        has_report_errors=False,
        input_all_delivered=True,
        output_all_delivered=True,
        proactive_present=True,
        proactive_silent_ok=True,
        github_issue_ok=True,
        github_disclosure_ok=True,
        scope=mod.RegressionScope.FULL,
        skip_db_checks=False,
        proactive_min_rounds=1,
    )
    assert gate_fail.passed() is False


def test_build_regression_summary_skips_disclosure_when_not_debug() -> None:
    mod = _load_regression_module()

    github = mod.GithubIssueE2eResult(
        "u1",
        "https://github.com/o/r/issues/1",
        1,
        True,
        True,
        False,
        False,
        None,
    )
    summary, gate = mod._build_regression_summary(
        bootstrap_done="true",
        context_mode="roleplay",
        greeting_result=mod.ImplicitSignOnGreetingResult(
            present=True,
            source_greeting=True,
            text_preview="hi",
            langsmith_trace_id="t",
        ),
        memdoc_result=mod.BootstrapMemDocResult(
            user_customized=True,
            identity_customized=True,
            style_customized=True,
            soul_unchanged=True,
            memory_unchanged=True,
            user_sequence_id=2,
            identity_sequence_id=2,
            style_sequence_id=2,
            memory_sequence_id=1,
            errors=(),
            warnings=(),
        ),
        experience_profile_ok=True,
        dreaming_result=mod.DreamingConsolidationResult(
            checkpoint_present=True,
            memory_updated=True,
            memory_sequence_before=1,
            memory_sequence_after=2,
            error=None,
        ),
        github_result=github,
        app_debug=False,
        settled_ok=True,
        report_errors=[],
        proactive_summary={
            "total": 1,
            "visible": 1,
            "silent": 0,
            "silent_token_leaks": 0,
        },
        proactive_target_met=False,
        proactive_present=True,
        proactive_silent_ok=True,
        in_q="delivered|1",
        out_q="delivered|1",
        in_all_delivered=True,
        out_all_delivered=True,
        companion_bond_state="ACTIVE",
        skip_db_checks=False,
        scope=mod.RegressionScope.FULL,
        proactive_min_rounds=1,
    )
    assert summary["github_issue_disclosed_in_chat"] == "pass"
    assert gate.github_disclosure_ok is True
    assert gate.passed() is True

    undisclosed = mod.GithubIssueE2eResult(
        "u1",
        "",
        0,
        False,
        False,
        False,
        False,
        "no snapshot",
    )
    summary_skip, gate_skip = mod._build_regression_summary(
        bootstrap_done="true",
        context_mode="roleplay",
        greeting_result=mod.ImplicitSignOnGreetingResult(
            present=True,
            source_greeting=True,
            text_preview="hi",
            langsmith_trace_id="t",
        ),
        memdoc_result=mod.BootstrapMemDocResult(
            user_customized=True,
            identity_customized=True,
            style_customized=True,
            soul_unchanged=True,
            memory_unchanged=True,
            user_sequence_id=2,
            identity_sequence_id=2,
            style_sequence_id=2,
            memory_sequence_id=1,
            errors=(),
            warnings=(),
        ),
        experience_profile_ok=True,
        dreaming_result=mod.DreamingConsolidationResult(
            checkpoint_present=True,
            memory_updated=True,
            memory_sequence_before=1,
            memory_sequence_after=2,
            error=None,
        ),
        github_result=undisclosed,
        app_debug=False,
        settled_ok=True,
        report_errors=[],
        proactive_summary={
            "total": 1,
            "visible": 1,
            "silent": 0,
            "silent_token_leaks": 0,
        },
        proactive_target_met=False,
        proactive_present=True,
        proactive_silent_ok=True,
        in_q="delivered|1",
        out_q="delivered|1",
        in_all_delivered=True,
        out_all_delivered=True,
        companion_bond_state="ACTIVE",
        skip_db_checks=False,
        scope=mod.RegressionScope.FULL,
        proactive_min_rounds=1,
    )
    assert summary_skip["github_issue_disclosed_in_chat"] == "skipped"
    assert gate_skip.github_disclosure_ok is True


def test_query_input_batch_id_for_client_message_id() -> None:
    mod = _load_regression_module()
    repo_root = Path(__file__).parents[4]
    config_path = repo_root / "devops" / "config.yaml.regression_tests"
    captured: list[str] = []

    def fake_psql(_repo_root, _config_path, query: str) -> str:
        captured.append(query)
        return " batch-abc \n"

    original = mod._psql
    mod._psql = fake_psql
    try:
        batch_id = mod._query_input_batch_id_for_client_message_id(
            repo_root,
            config_path,
            agent_id="agent-1",
            client_message_id="client-msg-1",
        )
    finally:
        mod._psql = original

    assert batch_id == "batch-abc"
    assert len(captured) == 1
    assert "COALESCE(batch_id" in captured[0]
    assert "client_message_id = 'client-msg-1'" in captured[0]


def test_append_github_issue_disclosure_output_persists_correlated_row() -> None:
    mod = _load_regression_module()
    repo_root = Path(__file__).parents[4]
    mod._ensure_import_path(repo_root)
    from unittest.mock import AsyncMock, patch

    from app.services.agentic_companion.downlink import DownlinkKind

    class _FakeRecord:
        def __init__(self, message_id: str, text: str, sequence: int) -> None:
            self.message_id = message_id
            self.text = text
            self.sequence = sequence

    issue_url = "https://github.com/NascentCore/inty/issues/3652"

    with patch(
        "app.core.companion_harness.agentic_companion.output_queue.AsyncSessionLocal"
    ) as session_cls:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_cls.return_value = session
        repo = AsyncMock()
        repo.append_agent_output = AsyncMock(
            return_value=_FakeRecord("msg-disclosure", issue_url, 3)
        )
        with patch(
            "app.core.companion_harness.agentic_companion.output_queue.PostgresOutputQueueRepository",
            return_value=repo,
        ):
            mod._append_github_issue_disclosure_output(
                repo_root,
                user_id="user-testing",
                agent_id="agent-1",
                batch_id="batch-1",
                user_msg_uuid="client-msg-1",
                issue_url=issue_url,
            )

    persisted = repo.append_agent_output.await_args.args[0]
    assert persisted.batch_id == "batch-1"
    assert persisted.message_ids == ("client-msg-1",)
    assert persisted.kind == DownlinkKind.TOOL_BACKGROUND
    assert issue_url in persisted.text


def _github_summary_fixture_kwargs(
    mod: object, *, github_result: object, app_debug: bool
) -> dict[str, object]:
    return {
        "bootstrap_done": "true",
        "context_mode": "roleplay",
        "greeting_result": mod.ImplicitSignOnGreetingResult(
            present=True,
            source_greeting=True,
            text_preview="hi",
            langsmith_trace_id="t",
        ),
        "memdoc_result": mod.BootstrapMemDocResult(
            user_customized=True,
            identity_customized=True,
            style_customized=True,
            soul_unchanged=True,
            memory_unchanged=True,
            user_sequence_id=2,
            identity_sequence_id=2,
            style_sequence_id=2,
            memory_sequence_id=1,
            errors=(),
            warnings=(),
        ),
        "experience_profile_ok": True,
        "dreaming_result": mod.DreamingConsolidationResult(
            checkpoint_present=True,
            memory_updated=True,
            memory_sequence_before=1,
            memory_sequence_after=2,
            error=None,
        ),
        "github_result": github_result,
        "app_debug": app_debug,
        "settled_ok": True,
        "report_errors": [],
        "proactive_summary": {
            "total": 1,
            "visible": 1,
            "silent": 0,
            "silent_token_leaks": 0,
        },
        "proactive_target_met": False,
        "proactive_present": True,
        "proactive_silent_ok": True,
        "in_q": "delivered|1",
        "out_q": "delivered|1",
        "in_all_delivered": True,
        "out_all_delivered": True,
        "companion_bond_state": "ACTIVE",
        "skip_db_checks": False,
        "scope": mod.RegressionScope.FULL,
        "proactive_min_rounds": 1,
    }


def test_build_regression_summary_debug_disclosure_fails_without_chat_url() -> None:
    mod = _load_regression_module()
    github = mod.GithubIssueE2eResult(
        "u1",
        "https://github.com/o/r/issues/1",
        1,
        True,
        True,
        False,
        True,
        None,
    )
    summary, gate = mod._build_regression_summary(
        **_github_summary_fixture_kwargs(
            mod, github_result=github, app_debug=True
        )
    )
    assert summary["github_issue_disclosed_in_chat"] == "fail"
    assert gate.github_disclosure_ok is False
    assert gate.passed() is False


def test_build_regression_summary_debug_disclosure_passes_when_disclosed() -> None:
    mod = _load_regression_module()
    github = mod.GithubIssueE2eResult(
        "u1",
        "https://github.com/o/r/issues/1",
        1,
        True,
        True,
        True,
        True,
        None,
    )
    summary, gate = mod._build_regression_summary(
        **_github_summary_fixture_kwargs(
            mod, github_result=github, app_debug=True
        )
    )
    assert summary["github_issue_disclosed_in_chat"] == "pass"
    assert gate.github_disclosure_ok is True
    assert gate.passed() is True


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
            skip_db_checks=False,
        )
    finally:
        mod._psql = original

    assert result.user_customized is True
    assert result.identity_customized is True
    assert result.style_customized is True
    assert result.soul_unchanged is True
    assert result.memory_unchanged is True
    assert result.errors == ()


def test_target_presets_local() -> None:
    mod = _load_regression_module()
    repo_root = Path(__file__).parents[4]
    preset = mod._target_presets(mod.RegressionTarget.LOCAL, repo_root)
    assert preset.api_base == mod._DEFAULT_API_BASE
    assert preset.config_path == mod._DEFAULT_CONFIG
    assert preset.skip_db_checks is False
    assert preset.scope == mod.RegressionScope.FULL
    assert (
        preset.proactive_min_rounds_default == mod._DEFAULT_PROACTIVE_MIN_ROUNDS
    )
    assert preset.db_checks_label == "Postgres verified"
    assert preset.turn_scope_label == "Full regression"


def test_target_presets_dev() -> None:
    mod = _load_regression_module()
    repo_root = Path(__file__).parents[4]
    preset = mod._target_presets(mod.RegressionTarget.DEV, repo_root)
    assert preset.api_base == mod._DEV_API_BASE
    assert preset.config_path == mod._DEV_CONFIG
    assert preset.skip_db_checks is True
    assert preset.scope == mod.RegressionScope.FULL
    assert preset.proactive_min_rounds_default == 0
    assert preset.db_checks_label == "WS + gh only (no direct Postgres)"
    assert preset.turn_scope_label == "Full regression"


def test_target_presets_prod() -> None:
    mod = _load_regression_module()
    repo_root = Path(__file__).parents[4]
    preset = mod._target_presets(mod.RegressionTarget.PROD, repo_root)
    assert preset.api_base == mod._PROD_API_BASE
    assert preset.config_path == mod._PROD_CONFIG
    assert preset.skip_db_checks is True
    assert preset.scope == mod.RegressionScope.SAFE_SUBSET
    assert preset.proactive_min_rounds_default == 0
    assert preset.db_checks_label == "WS only"
    assert preset.turn_scope_label == "Safe subset: greeting + one settled turn"


def test_extract_github_issue_url() -> None:
    mod = _load_regression_module()
    url = "https://github.com/NascentCore/inty/issues/3732"
    text = f"Filed your feedback: {url}"
    assert mod._extract_github_issue_url(text) == (url, 3732)
    assert mod._extract_github_issue_url("no issue here") == ("", 0)


def test_wait_input_delivered_skip_db_checks(tmp_path) -> None:
    mod = _load_regression_module()
    repo_root = Path(__file__).parents[4]
    ok = mod._wait_input_delivered(
        repo_root,
        tmp_path / "missing.yaml",
        agent_id="agent-1",
        client_message_id="msg-1",
        timeout_sec=1.0,
        label="test",
        stderr=io.StringIO(),
        skip_db_checks=True,
    )
    assert ok is True


def test_verify_bootstrap_memdocs_skip_db_checks(tmp_path) -> None:
    mod = _load_regression_module()
    repo_root = Path(__file__).parents[4]
    result = mod._verify_bootstrap_memdocs(
        repo_root,
        tmp_path / "missing.yaml",
        user_id="user-testing",
        agent_id="agent-1",
        skip_db_checks=True,
    )
    assert result.errors == ()
    assert result.warnings


def test_build_regression_summary_skip_db_checks() -> None:
    mod = _load_regression_module()
    github = mod.GithubIssueE2eResult(
        "u1",
        "https://github.com/o/r/issues/1",
        1,
        True,
        True,
        True,
        False,
        None,
    )
    summary, gate = mod._build_regression_summary(
        bootstrap_done="true",
        context_mode="roleplay",
        greeting_result=mod.ImplicitSignOnGreetingResult(
            present=True,
            source_greeting=True,
            text_preview="hi",
            langsmith_trace_id="t",
        ),
        memdoc_result=mod.BootstrapMemDocResult(
            user_customized=False,
            identity_customized=False,
            style_customized=False,
            soul_unchanged=False,
            memory_unchanged=False,
            user_sequence_id=0,
            identity_sequence_id=0,
            style_sequence_id=0,
            memory_sequence_id=0,
            errors=("would fail",),
            warnings=("skipped: no direct DB access to remote environment",),
        ),
        experience_profile_ok=True,
        dreaming_result=mod.DreamingConsolidationResult(
            checkpoint_present=False,
            memory_updated=False,
            memory_sequence_before=0,
            memory_sequence_after=0,
            error="would fail",
        ),
        github_result=github,
        app_debug=True,
        settled_ok=True,
        report_errors=[],
        proactive_summary={
            "total": 0,
            "visible": 0,
            "silent": 0,
            "silent_token_leaks": 0,
        },
        proactive_target_met=False,
        proactive_present=False,
        proactive_silent_ok=True,
        in_q="",
        out_q="",
        in_all_delivered=False,
        out_all_delivered=False,
        companion_bond_state="",
        skip_db_checks=True,
        scope=mod.RegressionScope.FULL,
        proactive_min_rounds=0,
    )
    assert (
        summary["bootstrap_memdocs"] == mod.RegressionCheckStatus.SKIPPED.value
    )
    assert (
        summary["dreaming_consolidation"]
        == mod.RegressionCheckStatus.SKIPPED.value
    )
    assert gate.passed() is True


_SAMPLE_DREAMING_LOG = """\
2026-07-02 19:44:04.195 | INFO | dreaming_consolidation.py | dreaming_consolidation start ws=user-testing:agent-a:agent-scope:user-testing:agent-a rows=25 chars=2942
2026-07-02 19:45:15.021 | INFO | dreaming_consolidation.py | dreaming_consolidation curated step=daily_gist_md:2026-07-02 ms=70826 ws=user-testing:agent-a:agent-scope:user-testing:agent-a
2026-07-02 19:45:45.100 | INFO | dreaming_consolidation.py | dreaming_consolidation curated step=dreaming_memory_md ms=30100 ws=user-testing:agent-a:agent-scope:user-testing:agent-a
2026-07-02 19:47:48.975 | INFO | dreaming_consolidation.py | dreaming_consolidation done total_ms=243780 ws=user-testing:agent-a:agent-scope:user-testing:agent-a curated=True
2026-07-02 19:50:01.000 | INFO | dreaming_consolidation.py | dreaming_consolidation start ws=user-testing:agent-b:agent-scope:user-testing:agent-b rows=3 chars=120
2026-07-02 19:50:30.000 | INFO | dreaming_consolidation.py | dreaming_consolidation curated step=dreaming_soul_md ms=99999 ws=user-testing:agent-b:agent-scope:user-testing:agent-b
"""


def test_parse_dreaming_curation_timings_from_log_text() -> None:
    mod = _load_regression_module()
    timing = mod._parse_dreaming_curation_timings_from_log_text(
        _SAMPLE_DREAMING_LOG,
        user_id="user-testing",
        agent_id="agent-a",
    )
    assert timing is not None
    assert timing.rows == 25
    assert timing.chars == 2942
    assert timing.total_curation_ms == 243780.0
    assert timing.step_timings == (
        mod.DreamingStepTiming("daily_gist_md:2026-07-02", 70826.0),
        mod.DreamingStepTiming("dreaming_memory_md", 30100.0),
    )
    summary = mod._summarize_dreaming_step_timings(timing.step_timings)
    assert summary["daily_gist_md:2026-07-02"] == 70826.0
    assert summary["dreaming_memory_md"] == 30100.0


def test_parse_dreaming_curation_timings_ignores_other_agent() -> None:
    mod = _load_regression_module()
    timing = mod._parse_dreaming_curation_timings_from_log_text(
        _SAMPLE_DREAMING_LOG,
        user_id="user-testing",
        agent_id="agent-b",
    )
    assert timing is not None
    assert timing.rows == 3
    assert timing.step_timings == (
        mod.DreamingStepTiming("dreaming_soul_md", 99999.0),
    )
    assert timing.total_curation_ms is None


_INTERLEAVED_DREAMING_LOG = """\
2026-07-02 19:44:04.195 | INFO | dreaming_consolidation start ws=user-testing:agent-a:agent-scope:user-testing:agent-a rows=25 chars=2942
2026-07-02 19:44:10.000 | INFO | dreaming_consolidation start ws=user-testing:agent-b:agent-scope:user-testing:agent-b rows=3 chars=120
2026-07-02 19:45:15.021 | INFO | dreaming_consolidation curated step=daily_gist_md:2026-07-02 ms=70826 ws=user-testing:agent-a:agent-scope:user-testing:agent-a
2026-07-02 19:47:48.975 | INFO | dreaming_consolidation done total_ms=243780 ws=user-testing:agent-a:agent-scope:user-testing:agent-a curated=True
"""


def test_parse_dreaming_curation_timings_survives_interleaved_agents() -> None:
    mod = _load_regression_module()
    timing = mod._parse_dreaming_curation_timings_from_log_text(
        _INTERLEAVED_DREAMING_LOG,
        user_id="user-testing",
        agent_id="agent-a",
    )
    assert timing is not None
    assert timing.total_curation_ms == 243780.0
    assert len(timing.step_timings) == 1
    assert timing.step_timings[0].step == "daily_gist_md:2026-07-02"


def test_dreaming_report_fields_includes_step_timings() -> None:
    mod = _load_regression_module()
    result = mod.DreamingConsolidationResult(
        checkpoint_present=True,
        memory_updated=True,
        memory_sequence_before=1,
        memory_sequence_after=2,
        error=None,
        log_timing=mod.DreamingLogTiming(
            step_timings=(
                mod.DreamingStepTiming("daily_gist_md:2026-07-02", 70826.0),
                mod.DreamingStepTiming("dreaming_memory_md", 30100.0),
            ),
            total_curation_ms=243780.0,
            rows=25,
            chars=2942,
            timing_source=".inty/inty.log",
        ),
    )
    fields = mod._dreaming_report_fields(result)
    assert fields["step_timings"] == [
        {"step": "daily_gist_md:2026-07-02", "ms": 70826.0},
        {"step": "dreaming_memory_md", "ms": 30100.0},
    ]
    assert fields["total_curation_ms"] == 243780.0
    assert fields["rows"] == 25
    assert fields["chars"] == 2942
    assert fields["timing_source"] == ".inty/inty.log"


def test_load_dreaming_curation_timings_prefers_inty_log(
    tmp_path: Path,
) -> None:
    mod = _load_regression_module()
    inty_dir = tmp_path / ".inty"
    inty_dir.mkdir()
    (inty_dir / "inty.log").write_text(_SAMPLE_DREAMING_LOG, encoding="utf-8")
    timing = mod._load_dreaming_curation_timings_from_logs(
        tmp_path,
        user_id="user-testing",
        agent_id="agent-a",
    )
    assert timing is not None
    assert timing.timing_source == ".inty/inty.log"
    assert timing.total_curation_ms == 243780.0


def test_load_dreaming_curation_timings_falls_back_to_inty_log_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_regression_module()
    inty_dir = tmp_path / ".inty"
    inty_dir.mkdir()
    (inty_dir / "inty.log").write_text("unrelated log line\n", encoding="utf-8")
    alt_log = tmp_path / "alt-inty.log"
    alt_log.write_text(_SAMPLE_DREAMING_LOG, encoding="utf-8")
    monkeypatch.setenv("INTY_LOG_FILE", str(alt_log))
    timing = mod._load_dreaming_curation_timings_from_logs(
        tmp_path,
        user_id="user-testing",
        agent_id="agent-a",
    )
    assert timing is not None
    assert timing.timing_source == "alt-inty.log"
    assert timing.total_curation_ms == 243780.0


_DREAMING_REQUIRED_PATHS = (
    "memory/daily/2026-07-06.md",
    "MEMORY.md",
    "USER.md",
    "STYLE.md",
    "SOUL.md",
    "COMPANIONSHIP.md",
)
_DREAMING_ONE_SHOT_TRACE_ID = "019f354e-736f-7502-9ec6-ac9431b2f893"


def _dreaming_one_shot_tool_call(
    relative_path: str,
    *,
    content_changed: bool | None,
    body: str = "updated",
) -> dict:
    payload: dict[str, object] = {
        "document_kind": "memory",
        "relative_path": relative_path,
        "body": body,
        "changed_reason": "test",
    }
    if content_changed is not None:
        payload["content_changed"] = content_changed
    return {
        "function": {
            "name": "update_dreaming_document",
            "arguments": json.dumps(payload),
        }
    }


def test_dreaming_curator_mode_from_config_yaml_defaults_to_one_shot(
    tmp_path: Path,
) -> None:
    mod = _load_regression_module()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("app:\n  name: inty-backend\n", encoding="utf-8")
    assert (
        mod._dreaming_curator_mode_from_config_yaml(config_path) == "one_shot"
    )


def test_dreaming_curator_mode_from_config_yaml_reads_sequential_rollback(
    tmp_path: Path,
) -> None:
    mod = _load_regression_module()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "agent:\n  companion_harness:\n    dreaming_curator_mode: sequential\n",
        encoding="utf-8",
    )
    assert (
        mod._dreaming_curator_mode_from_config_yaml(config_path) == "sequential"
    )


def test_required_paths_from_dreaming_llm_inputs_extracts_headers() -> None:
    mod = _load_regression_module()
    content = "\n".join(
        f"### Current `{path}`" for path in _DREAMING_REQUIRED_PATHS
    )
    inputs = {
        "messages": [
            {"role": "system", "content": "ignore"},
            {"role": "user", "content": content},
        ]
    }
    assert (
        mod._required_paths_from_dreaming_llm_inputs(inputs)
        == _DREAMING_REQUIRED_PATHS
    )


def test_required_paths_from_dreaming_llm_inputs_returns_empty_without_user_content() -> (
    None
):
    mod = _load_regression_module()
    assert mod._required_paths_from_dreaming_llm_inputs({}) == ()
    assert (
        mod._required_paths_from_dreaming_llm_inputs(
            {"messages": [{"role": "assistant", "content": "no headers"}]}
        )
        == ()
    )
    assert (
        mod._required_paths_from_dreaming_llm_inputs(
            {"messages": [{"role": "user", "content": 42}]}
        )
        == ()
    )


def test_evaluate_dreaming_one_shot_tool_calls_all_changed() -> None:
    mod = _load_regression_module()
    tool_calls = [
        _dreaming_one_shot_tool_call(path, content_changed=True)
        for path in _DREAMING_REQUIRED_PATHS
    ]
    result = mod._evaluate_dreaming_one_shot_tool_calls(
        tool_calls,
        _DREAMING_REQUIRED_PATHS,
        trace_id=_DREAMING_ONE_SHOT_TRACE_ID,
    )
    assert result.ok is True
    assert result.error is None
    assert result.changed_count == 6
    assert result.no_op_count == 0
    assert result.tool_call_count == 6


def test_evaluate_dreaming_one_shot_tool_calls_mixed_changed_and_no_op() -> (
    None
):
    mod = _load_regression_module()
    tool_calls = [
        _dreaming_one_shot_tool_call(
            "memory/daily/2026-07-06.md", content_changed=True
        ),
        _dreaming_one_shot_tool_call("MEMORY.md", content_changed=True),
        _dreaming_one_shot_tool_call("USER.md", content_changed=False),
        _dreaming_one_shot_tool_call("STYLE.md", content_changed=False),
        _dreaming_one_shot_tool_call("SOUL.md", content_changed=False),
        _dreaming_one_shot_tool_call("COMPANIONSHIP.md", content_changed=False),
    ]
    result = mod._evaluate_dreaming_one_shot_tool_calls(
        tool_calls,
        _DREAMING_REQUIRED_PATHS,
        trace_id=_DREAMING_ONE_SHOT_TRACE_ID,
    )
    assert result.ok is True
    assert result.changed_count == 2
    assert result.no_op_count == 4


def test_evaluate_dreaming_one_shot_tool_calls_missing_required_path() -> None:
    mod = _load_regression_module()
    tool_calls = [
        _dreaming_one_shot_tool_call(path, content_changed=True)
        for path in _DREAMING_REQUIRED_PATHS[:-1]
    ]
    result = mod._evaluate_dreaming_one_shot_tool_calls(
        tool_calls,
        _DREAMING_REQUIRED_PATHS,
        trace_id=_DREAMING_ONE_SHOT_TRACE_ID,
    )
    assert result.ok is False
    assert result.error is not None
    assert "missing dreaming tool calls" in result.error


def test_evaluate_dreaming_one_shot_tool_calls_extra_unexpected_path() -> None:
    mod = _load_regression_module()
    tool_calls = [
        _dreaming_one_shot_tool_call(path, content_changed=True)
        for path in _DREAMING_REQUIRED_PATHS
    ]
    tool_calls.append(
        _dreaming_one_shot_tool_call("IDENTITY.md", content_changed=False)
    )
    result = mod._evaluate_dreaming_one_shot_tool_calls(
        tool_calls,
        _DREAMING_REQUIRED_PATHS,
        trace_id=_DREAMING_ONE_SHOT_TRACE_ID,
    )
    assert result.ok is False
    assert result.error is not None
    assert "unexpected" in result.error


def test_evaluate_dreaming_one_shot_tool_calls_all_no_op_fails() -> None:
    mod = _load_regression_module()
    tool_calls = [
        _dreaming_one_shot_tool_call(path, content_changed=False)
        for path in _DREAMING_REQUIRED_PATHS
    ]
    result = mod._evaluate_dreaming_one_shot_tool_calls(
        tool_calls,
        _DREAMING_REQUIRED_PATHS,
        trace_id=_DREAMING_ONE_SHOT_TRACE_ID,
    )
    assert result.ok is False
    assert result.error == "no content_changed=true tool calls"
    assert result.changed_count == 0
    assert result.no_op_count == 6


def test_evaluate_dreaming_one_shot_tool_calls_duplicate_path_fails() -> None:
    mod = _load_regression_module()
    tool_calls = [
        _dreaming_one_shot_tool_call(path, content_changed=True)
        for path in _DREAMING_REQUIRED_PATHS
    ]
    tool_calls.append(
        _dreaming_one_shot_tool_call("MEMORY.md", content_changed=False)
    )
    result = mod._evaluate_dreaming_one_shot_tool_calls(
        tool_calls,
        _DREAMING_REQUIRED_PATHS,
        trace_id=_DREAMING_ONE_SHOT_TRACE_ID,
    )
    assert result.ok is False
    assert result.error is not None
    assert "duplicate" in result.error
    assert result.tool_call_count == 6
    assert result.tool_call_count == len(result.paths)


def test_evaluate_dreaming_one_shot_tool_calls_duplicate_path_ignores_unparsed_raw_calls() -> (
    None
):
    mod = _load_regression_module()
    tool_calls = [
        _dreaming_one_shot_tool_call(path, content_changed=True)
        for path in _DREAMING_REQUIRED_PATHS
    ]
    tool_calls.append(
        _dreaming_one_shot_tool_call("MEMORY.md", content_changed=False)
    )
    tool_calls.append({"function": {"name": "other_tool", "arguments": "{}"}})
    result = mod._evaluate_dreaming_one_shot_tool_calls(
        tool_calls,
        _DREAMING_REQUIRED_PATHS,
        trace_id=_DREAMING_ONE_SHOT_TRACE_ID,
    )
    assert result.ok is False
    assert result.tool_call_count == 6
    assert result.tool_call_count != len(tool_calls)


def test_evaluate_dreaming_one_shot_tool_calls_missing_content_changed_key() -> (
    None
):
    mod = _load_regression_module()
    tool_calls = [
        _dreaming_one_shot_tool_call(path, content_changed=True)
        for path in _DREAMING_REQUIRED_PATHS[:-1]
    ]
    tool_calls.append(
        _dreaming_one_shot_tool_call("COMPANIONSHIP.md", content_changed=None)
    )
    result = mod._evaluate_dreaming_one_shot_tool_calls(
        tool_calls,
        _DREAMING_REQUIRED_PATHS,
        trace_id=_DREAMING_ONE_SHOT_TRACE_ID,
    )
    assert result.ok is False
    assert result.error is not None
    assert "missing content_changed" in result.error
    assert result.tool_call_count == 5
    assert result.tool_call_count == len(result.paths)


def test_main_requires_target() -> None:
    mod = _load_regression_module()
    with pytest.raises(SystemExit) as exc:
        mod.main([])
    assert exc.value.code == 2


def test_format_target_preset_table_matches_target_presets() -> None:
    mod = _load_regression_module()
    repo_root = Path(__file__).parents[4]
    table = mod._format_target_preset_table(repo_root)
    row_by_target = {
        line.split()[0]: line
        for line in table.splitlines()
        if line.startswith(("local ", "dev ", "prod "))
    }
    for target in mod.RegressionTarget:
        preset = mod._target_presets(target, repo_root)
        row = row_by_target[target.value]
        assert preset.api_base in row
        assert preset.config_path in row
        assert preset.db_checks_label in row
        assert preset.turn_scope_label in row


def test_main_help_includes_target_preset_table(capsys) -> None:
    mod = _load_regression_module()
    with pytest.raises(SystemExit) as exc:
        mod.main(["--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert mod._DEV_API_BASE in captured.out
    assert mod._PROD_API_BASE in captured.out
    assert "Safe subset: greeting + one settled turn" in captured.out


def test_purge_regression_bootstrap_agents_deletes_prefix_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_regression_module()
    token_path = tmp_path / "token.txt"
    token_path.write_text("bearer-tok", encoding="utf-8")
    calls: list[tuple[str, str]] = []

    class _FakeResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def read(self) -> bytes:
            return json.dumps(self._payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(request, timeout=0.0):  # noqa: ANN001
        url = request.full_url
        method = request.method
        calls.append((method, url))
        if method == "GET":
            return _FakeResponse(
                {
                    "code": 200,
                    "data": [
                        {"id": "agent-bootstrap", "name": "bootstrap-test-abc"},
                        {"id": "agent-other", "name": "my-other-agent"},
                    ],
                }
            )
        if method == "DELETE" and url.endswith("/agent-bootstrap"):
            return _FakeResponse(
                {"code": 200, "data": {"id": "agent-bootstrap"}}
            )
        raise AssertionError(f"unexpected request: {method} {url}")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    deleted = mod._purge_regression_bootstrap_agents_via_api(
        api_base="https://dev.ops.inty.cc",
        token_path=str(token_path),
        http_timeout=30.0,
        stderr=io.StringIO(),
    )
    assert deleted == 1
    delete_calls = [url for method, url in calls if method == "DELETE"]
    assert len(delete_calls) == 1
    assert delete_calls[0].endswith("/api/v1/ai/agents/agent-bootstrap")


def test_purge_regression_bootstrap_agents_empty_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_regression_module()
    token_path = tmp_path / "token.txt"
    token_path.write_text("bearer-tok", encoding="utf-8")

    class _FakeResponse:
        def read(self) -> bytes:
            return b'{"code": 200, "data": []}'

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

    import urllib.request

    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *a, **k: _FakeResponse()
    )
    deleted = mod._purge_regression_bootstrap_agents_via_api(
        api_base="https://dev.ops.inty.cc",
        token_path=str(token_path),
        http_timeout=30.0,
        stderr=io.StringIO(),
    )
    assert deleted == 0


def test_purge_regression_bootstrap_agents_paginates_before_delete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_regression_module()
    token_path = tmp_path / "token.txt"
    token_path.write_text("bearer-tok", encoding="utf-8")
    calls: list[tuple[str, str]] = []
    first_page = [
        {"id": f"agent-other-{idx}", "name": f"other-{idx}"}
        for idx in range(99)
    ]
    first_page.append({"id": "agent-first", "name": "bootstrap-test-first"})
    second_page = [{"id": "agent-second", "name": "bootstrap-test-second"}]

    class _FakeResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def read(self) -> bytes:
            return json.dumps(self._payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(request, timeout=0.0):  # noqa: ANN001
        url = request.full_url
        calls.append((request.method, url))
        if request.method == "GET" and "skip=0" in url:
            return _FakeResponse({"code": 200, "data": first_page})
        if request.method == "GET" and "skip=100" in url:
            return _FakeResponse({"code": 200, "data": second_page})
        if request.method == "DELETE":
            return _FakeResponse({"code": 200, "data": {}})
        raise AssertionError(f"unexpected request: {request.method} {url}")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    deleted = mod._purge_regression_bootstrap_agents_via_api(
        api_base="https://dev.ops.inty.cc",
        token_path=str(token_path),
        http_timeout=30.0,
        stderr=io.StringIO(),
    )
    assert deleted == 2
    assert [method for method, _ in calls] == ["GET", "GET", "DELETE", "DELETE"]


def test_purge_regression_bootstrap_agents_delete_failure_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_regression_module()
    token_path = tmp_path / "token.txt"
    token_path.write_text("bearer-tok", encoding="utf-8")

    class _FakeResponse:
        def read(self) -> bytes:
            return json.dumps(
                {
                    "code": 200,
                    "data": [
                        {"id": "agent-bootstrap", "name": "bootstrap-test-x"}
                    ],
                }
            ).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

    import urllib.error
    import urllib.request

    def fake_urlopen(request, timeout=0.0):  # noqa: ANN001
        if request.method == "GET":
            return _FakeResponse()
        raise urllib.error.HTTPError(
            request.full_url,
            500,
            "server error",
            hdrs=None,
            fp=io.BytesIO(b"internal error"),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="delete agent"):
        mod._purge_regression_bootstrap_agents_via_api(
            api_base="https://dev.ops.inty.cc",
            token_path=str(token_path),
            http_timeout=30.0,
            stderr=io.StringIO(),
        )


def test_main_dev_create_agent_purges_before_create(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_regression_module()
    order: list[str] = []
    stderr_buf = io.StringIO()

    def fake_purge(**kwargs: object) -> int:
        order.append("purge")
        return 2

    def fake_create(**kwargs: object) -> str:
        order.append("create")
        return "new-agent-id"

    def fake_run_regression(**kwargs: object) -> int:
        order.append("run")
        return 0

    monkeypatch.setattr(
        mod,
        "_purge_regression_bootstrap_agents_via_api",
        fake_purge,
    )
    monkeypatch.setattr(mod, "_create_agent_id", fake_create)
    monkeypatch.setattr(mod, "run_regression", fake_run_regression)
    monkeypatch.setattr(
        sys,
        "stderr",
        stderr_buf,
    )
    rc = mod.main(
        [
            "--target",
            "dev",
            "--create-agent",
            "--report",
            str(tmp_path / "report.json"),
        ]
    )
    assert rc == 0
    assert order == ["purge", "create", "run"]
    assert "purged 2 bootstrap-test agent(s) via API" in stderr_buf.getvalue()
    assert (
        "deactivated prior ACTIVE companion bonds" not in stderr_buf.getvalue()
    )
