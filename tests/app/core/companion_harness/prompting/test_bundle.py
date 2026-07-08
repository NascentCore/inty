from __future__ import annotations

from app.core.companion_harness.prompting.bundle import PromptBundle


def test_prompt_bundle_defaults() -> None:
    b = PromptBundle(identity="i", soul="s", user_md="u", memory_md="m")
    assert b.style_md == ""
    assert b.channels_md == ""
    assert b.harness_md == ""
    assert b.about_md == ""
    assert b.tools_md == ""
    assert b.memory_daily_today_md == ""
