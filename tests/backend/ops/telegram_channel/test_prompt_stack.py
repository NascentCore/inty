"""Tests for TELEGRAM runtime channel prompt stack."""

from __future__ import annotations

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
    OUTPUT_FORMAT_IM_DM_MD,
)
from app.core.companion_harness.companion.prompt_stack import (
    companion_system_messages_for_track,
    output_format_prompt_slice_for_runtime_channel,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.memory.memory_store_scope import (
    load_template_seed_text,
)
from app.core.companion_harness.prompting.bundle import PromptBundle


def _bundle() -> PromptBundle:
    return PromptBundle(
        identity="identity",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="memory",
    )


def test_telegram_output_format_uses_im_dm_slice() -> None:
    im_body = load_template_seed_text(OUTPUT_FORMAT_IM_DM_MD)
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="memory",
        output_format_im_dm_md=im_body,
    )
    assert (
        output_format_prompt_slice_for_runtime_channel(
            bundle=bundle,
            runtime_channel=ChannelKind.TELEGRAM,
        )
        == im_body
    )


def test_telegram_system_messages_exclude_weixin_alias() -> None:
    bundle = _bundle()
    messages = companion_system_messages_for_track(
        store=None,  # type: ignore[arg-type]
        bundle=bundle,
        context=ContextMeta(),
        track=CompanionTurnTrack.USER_CHAT,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.TELEGRAM,
            implicit_signal_bundle=None,
        ),
    )
    system_text = "\n".join(
        str(m.get("content", "")) for m in messages if m.get("role") == "system"
    )
    assert "Weixin / ClawBot 联系人显示名" not in system_text
