from __future__ import annotations

from app.core.companion_harness.official_helper.models import OfficialHelperReason
from app.core.companion_harness.official_helper.prompts import (
    build_official_helper_system_messages,
)


def test_official_helper_prompt_states_system_role_not_companion() -> None:
    messages = build_official_helper_system_messages(
        reason=OfficialHelperReason.DREAMING,
        companion_display_name="Luna",
    )
    bodies = [str(m["content"]) for m in messages]
    joined = "\n".join(bodies)
    assert "Official helper" in joined
    assert "not" in joined.lower()
    assert "Luna" in joined
    assert "Do not impersonate the companion" in joined
    assert messages[0]["role"] == "system"
