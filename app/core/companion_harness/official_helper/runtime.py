"""Build official helper ``CompanionTurnResult`` values without companion kernel turns."""

from __future__ import annotations

import uuid

from app.core.companion_harness.companion.models import CompanionTurnResult

from .models import OfficialHelperReason, OfficialHelperRequest


def dreaming_user_visible_text(*, companion_display_name: str) -> str:
    """Deterministic sleeping copy for the first official-helper slice."""
    assert companion_display_name
    return f"{companion_display_name} is sleeping ~"


def build_official_helper_turn(request: OfficialHelperRequest) -> CompanionTurnResult:
    """Materialize one helper-owned assistant reply for API/WS persistence."""
    match request.reason:
        case OfficialHelperReason.DREAMING:
            assistant_text = dreaming_user_visible_text(
                companion_display_name=request.companion_display_name,
            )
        case OfficialHelperReason.APP_HELP | OfficialHelperReason.SYSTEM_MALFUNCTION:
            raise NotImplementedError(
                f"official helper reason not implemented yet: {request.reason.value}"
            )
    trace_id = str(uuid.uuid4())
    assistant_msg_uuid = str(uuid.uuid4())
    return CompanionTurnResult(
        assistant_text=assistant_text,
        user_msg_uuid=request.user_msg_uuid,
        assistant_msg_uuid=assistant_msg_uuid,
        trace_id=trace_id,
        assistant_source="official_helper",
        official_helper_reason=request.reason.value,
    )
