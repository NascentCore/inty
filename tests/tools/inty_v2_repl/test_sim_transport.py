"""Unit tests for ``tools.inty_v2_repl.sim_transport`` pure helpers."""

from __future__ import annotations

from pathlib import Path

from tools.inty_v2_repl.sim_transport import (
    downlink_user_msg_uuid,
    find_repo_root,
    is_implicit_sign_on_greeting,
    parse_input_queue_status_counts,
    queue_has_in_flight,
    target_presets,
    RegressionTarget,
)


def test_parse_input_queue_status_counts() -> None:
    counts = parse_input_queue_status_counts("claimed|1\ndelivered|6\n")
    assert counts == {"claimed": 1, "delivered": 6}


def test_queue_has_in_flight() -> None:
    assert queue_has_in_flight({"delivered": 3}) is False
    assert queue_has_in_flight({"pending": 1, "delivered": 2}) is True
    assert queue_has_in_flight({"claimed": 1, "delivered": 2}) is True


def test_downlink_user_msg_uuid() -> None:
    assert downlink_user_msg_uuid({"user_msg_uuid": "abc"}) == "abc"
    assert downlink_user_msg_uuid({}) == ""


def test_is_implicit_sign_on_greeting() -> None:
    assert is_implicit_sign_on_greeting({"source": "greeting"})
    assert is_implicit_sign_on_greeting({"isOpening": True})
    assert not is_implicit_sign_on_greeting({"source": "chat"})


def test_target_presets_local() -> None:
    preset = target_presets(RegressionTarget.LOCAL, find_repo_root(Path(__file__)))
    assert preset.api_base == "http://127.0.0.1:8001"
    assert preset.skip_db_checks is False
