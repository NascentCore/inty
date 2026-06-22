"""Unit tests for ``telegram_screenshot_trace_match.py`` pure helpers."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


def _load_module():
    module_path = (
        Path(__file__).parents[4]
        / ".cursor"
        / "skills"
        / "scripts"
        / "telegram_screenshot_trace_match.py"
    )
    spec = importlib.util.spec_from_file_location(
        "telegram_screenshot_trace_match", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_local_clock_hh_mm() -> None:
    mod = _load_module()
    tz = ZoneInfo("Asia/Shanghai")
    parsed = mod._parse_local_clock(
        clock_text="21:24",
        calendar_date=date(2026, 6, 21),
        tz=tz,
    )
    assert parsed.hour == 21
    assert parsed.minute == 24
    assert parsed.tzinfo == tz


def test_build_search_window_converts_to_utc() -> None:
    mod = _load_module()
    window = mod._build_search_window(
        screenshot_clock="21:24",
        calendar_date=date(2026, 6, 21),
        tz_name="Asia/Shanghai",
        padding_minutes=15,
    )
    assert window.start_utc == datetime(2026, 6, 21, 13, 9, tzinfo=timezone.utc)
    assert window.end_utc == datetime(2026, 6, 21, 13, 39, tzinfo=timezone.utc)


def test_extract_last_user_snippet_skips_proactive() -> None:
    mod = _load_module()
    snippet = mod._extract_last_user_snippet(
        [
            {
                "role": "user",
                "content": "[2026-06-21 13:23:09 UTC] [SYSTEM PROACTIVE CHAT] tick",
            },
            {
                "role": "user",
                "content": "[2026-06-21 13:23:54 UTC] 那我就不能找你了？",
            },
        ]
    )
    assert snippet == "那我就不能找你了？"


def test_extract_reply_snippet_from_envelope_json() -> None:
    mod = _load_module()
    snippet = mod._extract_reply_snippet(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"user_facing_reply":"可以。\\n\\n那你先说，'
                            '找我是干嘛来了。"}'
                        )
                    }
                }
            ]
        }
    )
    assert "可以。" in snippet
    assert "找我是干嘛来了" in snippet


def test_keyword_hits_and_score() -> None:
    mod = _load_module()
    hits = mod._keyword_hits("batch 跑完 为什么来找我", ("batch", "missing"))
    assert hits == ("batch",)
    score = mod._score_match(
        keyword_hits=hits,
        runtime_channel="telegram",
        require_telegram=True,
    )
    assert score == 15


def test_parse_turn_name() -> None:
    mod = _load_module()
    user_id, agent_id = mod._parse_turn_name(
        "agentic_companion_user_turn user=user-01KV4TDNTATRQ2QG6W005KJ2NT "
        "agent=4d1dd1f1-532b-439d-b40c-a7169c5cfe0e"
    )
    assert user_id == "user-01KV4TDNTATRQ2QG6W005KJ2NT"
    assert agent_id == "4d1dd1f1-532b-439d-b40c-a7169c5cfe0e"


def test_resolve_runtime_channel_from_child() -> None:
    mod = _load_module()

    class _Run:
        def __init__(self, extra: dict[str, object]) -> None:
            self.extra = extra

    root = _Run({})
    child = _Run({"metadata": {"inty_runtime_channel": "telegram"}})
    assert mod._resolve_runtime_channel(root, [child]) == "telegram"
