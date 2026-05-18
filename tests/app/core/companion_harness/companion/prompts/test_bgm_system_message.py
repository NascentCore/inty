from __future__ import annotations

from app.core.companion_harness.companion.prompts.bgm_system import (
    build_bgm_system_message,
)


def test_build_bgm_system_message_contains_catalog() -> None:
    msg = build_bgm_system_message()
    assert msg["role"] == "system"
    content = msg["content"]
    assert "calm_evening_01" in content
    assert "set_bgm" in content
