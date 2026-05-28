"""Implicit signal bundle from a WebSocket session ``client_context`` cache (``tc_box``)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from loguru import logger
from pydantic import ValidationError

from app.schemas.chat import UserTimeContext
from app.schemas.implicit_signals import HumanChannel, ImplicitSignalBundle


def implicit_signal_bundle_from_tc_box(
    tc_box: list[dict | None],
    human_channel: HumanChannel,
) -> Optional[ImplicitSignalBundle]:
    """Build companion ``ImplicitSignalBundle`` from ``tc_box[0]`` (last ``client_context``)."""
    assert human_channel is not None
    if not tc_box:
        if human_channel == HumanChannel.UNKNOWN:
            return None
        return ImplicitSignalBundle(
            human_channel=human_channel,
            user_signed_on=False,
            server_received_at_utc=datetime.now(timezone.utc),
        )
    raw = tc_box[0]
    if not raw:
        if human_channel == HumanChannel.UNKNOWN:
            return None
        return ImplicitSignalBundle(
            human_channel=human_channel,
            user_signed_on=False,
            server_received_at_utc=datetime.now(timezone.utc),
        )
    try:
        utc = UserTimeContext.model_validate(raw)
    except ValidationError as exc:
        logger.warning(
            "presence tc_box time_context invalid error={}",
            str(exc)[:500],
        )
        return None
    return ImplicitSignalBundle(
        client_time=utc,
        human_channel=human_channel,
        user_signed_on=False,
        server_received_at_utc=datetime.now(timezone.utc),
    )
