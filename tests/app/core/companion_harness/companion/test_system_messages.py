from __future__ import annotations

import pytest

from app.core.companion_harness.companion.bootstrap import (
    build_bootstrap_tool_call_section,
    load_bootstrap_spec_text,
    load_bootstrap_telegram_profile_slice_text,
)
from app.core.companion_harness.experience_profile.context_mode import (
    EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    CompanionToolName,
)
from app.core.companion_harness.prompt_builder import PromptBuilder
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
)
from app.core.companion_harness.companion.prompt_stack import (
    companion_system_messages_for_track,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)


def _system_contents(messages: list[dict[str, object]]) -> list[str]:
    return [
        str(message.get("content") or "")
        for message in messages
        if message.get("role") == "system"
    ]


def _bootstrap_system_contents(
    bundle: PromptBundle,
    context: ContextMeta,
    channel: ChannelKind,
) -> list[str]:
    return _system_contents(
        PromptBuilder(
            bundle=bundle,
            context=context,
            runtime_context=TurnRuntimeContext(
                channel=channel,
                implicit_signal_bundle=None,
            ),
        ).bootstrap_turn_system_dicts()
    )


def test_capability_group_injects_harness_channels_tools_in_order() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
        harness_md="# Harness\nharness contract",
        channels_md="# Channels\nchannel contract",
        tools_md="# Tools\ntool contract",
    )
    contents = _system_contents(build_system_messages(bundle, ContextMeta()))
    harness_i = contents.index("# Harness\nharness contract")
    channels_i = contents.index("# Channels\nchannel contract")
    tools_i = contents.index("# Tools\ntool contract")
    assert harness_i < channels_i < tools_i


def test_bootstrap_track_injects_typed_tool_call_section() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
    )
    contents = _bootstrap_system_contents(
        bundle,
        ContextMeta(workspace_bootstrap_user_interactive_completed=False),
        ChannelKind.APP_WS,
    )
    bootstrap_spec = load_bootstrap_spec_text()
    tool_section = build_bootstrap_tool_call_section()

    assert bootstrap_spec in contents
    assert tool_section in contents
    assert contents.index(bootstrap_spec) < contents.index(tool_section)
    for tool_name in (
        CompanionToolName.MEMORY_STORE_READ_DOCUMENT,
        CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT,
        CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE,
        CompanionToolName.COMPANION_RECORD_USER_PROFILE,
        CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE,
    ):
        assert tool_name.value in tool_section


def test_bootstrap_output_contract_names_memory_store_write_paths_only() -> (
    None
):
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
    )
    joined = "\n".join(
        _bootstrap_system_contents(bundle, ContextMeta(), ChannelKind.APP_WS)
    )
    assert "memory_store_write_document" in joined
    assert "COMPANIONSHIP.md / IDENTITY.md / STYLE.md / USER.md" in joined
    assert "SOUL.md" in joined and "MEMORY.md" in joined
    assert "companion_update_prompt_slice" not in joined
    assert "schedule_task" not in joined


def test_bootstrap_omits_experience_profile_context_mode_clause() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
    )
    joined = "\n".join(
        _bootstrap_system_contents(
            bundle,
            ContextMeta(context_mode="intimate"),
            ChannelKind.APP_WS,
        )
    )
    assert EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING not in joined


def test_bootstrap_omits_capability_package_slices() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
        harness_md="# Harness\nharness contract",
        channels_md="# Channels\nchannel contract",
        tools_md="# Tools\ntool contract",
    )
    joined = "\n".join(
        _bootstrap_system_contents(bundle, ContextMeta(), ChannelKind.APP_WS)
    )
    assert "harness contract" not in joined
    assert "channel contract" not in joined
    assert "tool contract" not in joined


def test_persona_injects_companionship_after_bootstrap() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="memory",
        companionship_md="# 我们的关系\n\n用户原话：朋友\n",
    )
    contents = _system_contents(
        build_system_messages(
            bundle,
            ContextMeta(workspace_bootstrap_user_interactive_completed=True),
        )
    )
    joined = "\n".join(contents)
    assert "COMPANIONSHIP — 陪伴关系 framing（COMPANIONSHIP.md）" in joined
    assert "用户原话：朋友" in joined
    style_idx = joined.index("style")
    companionship_idx = joined.index("用户原话：朋友")
    assert style_idx < companionship_idx


def test_persona_omits_companionship_during_bootstrap() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="",
        companionship_md="# 我们的关系\n\nseed\n",
    )
    joined = "\n".join(
        _bootstrap_system_contents(
            bundle,
            ContextMeta(workspace_bootstrap_user_interactive_completed=False),
            ChannelKind.APP_WS,
        )
    )
    assert "COMPANIONSHIP — 陪伴关系 framing（COMPANIONSHIP.md）" not in joined


def test_persona_injects_seed_companionship_after_bootstrap() -> None:
    from app.core.companion_harness.memory.memory_store_scope import (
        load_template_seed_text,
    )

    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="memory",
        companionship_md=load_template_seed_text("COMPANIONSHIP.md"),
    )
    joined = "\n".join(
        _system_contents(
            build_system_messages(
                bundle,
                ContextMeta(
                    workspace_bootstrap_user_interactive_completed=True
                ),
            )
        )
    )
    assert "COMPANIONSHIP — 陪伴关系 framing（COMPANIONSHIP.md）" in joined
    assert "我们的关系" in joined


def test_system_messages_omit_weixin_clawbot_alias_for_unknown_channel() -> (
    None
):
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="memory",
    )

    system_text = "\n".join(
        _system_contents(build_system_messages(bundle, ContextMeta()))
    )

    assert "Weixin / ClawBot 联系人显示名" not in system_text


def test_system_messages_include_weixin_clawbot_alias_for_weixin_channel() -> (
    None
):
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="memory",
    )

    context = ContextMeta()
    contents = _system_contents(
        companion_system_messages_for_track(
            store=None,  # type: ignore[arg-type]
            bundle=bundle,
            context=context,
            track=CompanionTurnTrack.USER_CHAT,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.WECHAT_WEIXIN,
                implicit_signal_bundle=None,
            ),
        )
    )
    system_text = "\n".join(contents)

    assert "Weixin / ClawBot 联系人显示名" in system_text
    assert "Weixin 里看到的名称" in system_text
    assert "不要声称已替用户改名" in system_text
    assert contents[-1].startswith("Weixin / ClawBot")


def test_telegram_bootstrap_injects_profile_collection_slice() -> None:
    from app.core.companion_harness.memory.user_md_identity import (
        load_user_md_template_text,
    )

    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md=load_user_md_template_text(),
        memory_md="",
    )
    contents = _bootstrap_system_contents(
        bundle,
        ContextMeta(
            workspace_bootstrap_user_interactive_completed=False,
            profile_collection_required=True,
        ),
        ChannelKind.TELEGRAM,
    )
    telegram_slice = load_bootstrap_telegram_profile_slice_text()
    assert telegram_slice in contents
    assert "仍待自然了解" in "\n".join(contents)


def test_telegram_bootstrap_omits_profile_slice_without_flag() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
    )
    contents = _bootstrap_system_contents(
        bundle,
        ContextMeta(workspace_bootstrap_user_interactive_completed=False),
        ChannelKind.TELEGRAM,
    )
    telegram_slice = load_bootstrap_telegram_profile_slice_text()
    assert telegram_slice not in contents


def test_app_ws_bootstrap_omits_telegram_profile_slice() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
    )
    contents = _bootstrap_system_contents(
        bundle,
        ContextMeta(workspace_bootstrap_user_interactive_completed=False),
        ChannelKind.APP_WS,
    )
    telegram_slice = load_bootstrap_telegram_profile_slice_text()
    assert telegram_slice not in contents


def test_implicit_sign_on_system_messages_include_fixed_reply_language_from_config(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.core.companion_harness.loop.runtime_system_clauses.resolved_companion_harness_reply_language",
        lambda: "English",
    )
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="memory",
    )
    system_text = "\n".join(
        _system_contents(
            PromptBuilder(
                bundle=bundle,
                context=ContextMeta(
                    workspace_bootstrap_user_interactive_completed=False,
                ),
                runtime_context=TurnRuntimeContext(
                    channel=ChannelKind.APP_WS,
                    implicit_signal_bundle=None,
                ),
            ).greeting_system_dicts()
        )
    )
    assert (
        "Use English for all user-facing reply text in this turn."
        in system_text
    )


def test_implicit_sign_on_system_messages_omit_reply_language_when_config_unset(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.core.companion_harness.loop.runtime_system_clauses.resolved_companion_harness_reply_language",
        lambda: None,
    )
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="memory",
    )
    system_text = "\n".join(
        _system_contents(
            PromptBuilder(
                bundle=bundle,
                context=ContextMeta(),
                runtime_context=TurnRuntimeContext(
                    channel=ChannelKind.APP_WS,
                    implicit_signal_bundle=None,
                ),
            ).greeting_system_dicts()
        )
    )
    assert (
        "Use English for all user-facing reply text in this turn."
        not in system_text
    )
    assert "Use the same language as the user's message(s)" not in system_text


def test_companion_system_messages_for_track_greeting_raises() -> None:
    with pytest.raises(RuntimeError, match="TrackPromptComposer"):
        companion_system_messages_for_track(
            store=None,  # type: ignore[arg-type]
            bundle=PromptBundle(
                identity="identity",
                soul="soul",
                user_md="user",
                memory_md="",
            ),
            context=ContextMeta(),
            track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            ),
        )
