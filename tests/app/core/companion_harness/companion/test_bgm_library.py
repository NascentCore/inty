from __future__ import annotations

from app.core.companion_harness.companion.bgm_library import (
    SET_BGM_OK_PREFIX,
    format_bgm_catalog_for_system_message,
    get_bgm_track,
    load_bgm_library,
    parse_set_bgm_ok_tool_content,
    tool_set_bgm,
)


def test_load_bgm_library_has_sample_tracks() -> None:
    by_id = load_bgm_library()
    assert "calm_evening_01" in by_id
    assert "warm_chat_02" in by_id
    assert by_id["calm_evening_01"].duration_sec > 0.0


def test_format_bgm_catalog_for_system_message_lines() -> None:
    lines = format_bgm_catalog_for_system_message().split("\n")
    assert len(lines) >= 3
    assert lines[0].startswith("track_id=")


def test_tool_set_bgm_ok_and_unknown() -> None:
    ok = tool_set_bgm(None, "calm_evening_01", "mood shift")
    assert ok.startswith(SET_BGM_OK_PREFIX)
    payload = parse_set_bgm_ok_tool_content(ok)
    assert payload is not None
    assert payload.track_id == "calm_evening_01"
    assert payload.reason == "mood shift"
    err = tool_set_bgm(None, "no_such_track", "x")
    assert err.startswith("ERROR:")


def test_get_bgm_track_missing() -> None:
    assert get_bgm_track("definitely_missing_track_xyz") is None
