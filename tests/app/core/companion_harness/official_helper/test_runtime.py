from __future__ import annotations

from app.core.companion_harness.official_helper.models import (
    OfficialHelperReason,
    OfficialHelperRequest,
)
from app.core.companion_harness.official_helper.runtime import (
    build_official_helper_turn,
    dreaming_user_visible_text,
)


def test_dreaming_user_visible_text() -> None:
    assert dreaming_user_visible_text(companion_display_name="Luna") == (
        "Luna is sleeping ~"
    )


def test_build_official_helper_turn_dreaming_sets_metadata() -> None:
    out = build_official_helper_turn(
        OfficialHelperRequest(
            reason=OfficialHelperReason.DREAMING,
            companion_display_name="Luna",
            user_msg_uuid="550e8400-e29b-41d4-a716-446655440000",
        )
    )
    assert out.assistant_text == "Luna is sleeping ~"
    assert out.assistant_source == "official_helper"
    assert out.official_helper_reason == "dreaming"
    assert out.user_msg_uuid == "550e8400-e29b-41d4-a716-446655440000"
    assert out.assistant_msg_uuid
    assert out.trace_id
