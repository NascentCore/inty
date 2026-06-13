from __future__ import annotations

from app.core.companion_harness.companion.bootstrap import (
    build_bootstrap_tool_call_section,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    CompanionToolName,
)
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
    build_system_messages_for_bootstrap_track,
)
from app.core.companion_harness.companion.prompt_stack import (
    companion_system_messages_for_track,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.turn_routes import TurnRouteMode


def _system_contents(messages: list[dict[str, object]]) -> list[str]:
    return [
        str(message.get("content") or "")
        for message in messages
        if message.get("role") == "system"
    ]


def test_capability_group_injects_channels_before_tools() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
        channels_md="# Channels\nchannel contract",
        tools_md="# Tools\ntool contract",
    )
    contents = _system_contents(build_system_messages(bundle, ContextMeta()))
    assert contents.index("# Channels\nchannel contract") < contents.index(
        "# Tools\ntool contract"
    )


def test_bootstrap_track_injects_typed_tool_call_section() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
    )
    contents = _system_contents(
        build_system_messages_for_bootstrap_track(bundle, ContextMeta())
    )
    tool_section = build_bootstrap_tool_call_section()

    assert tool_section in contents
    bootstrap_spec_block = next(
        content
        for content in contents
        if content.startswith("# Agentic 初始化执行规范（内部）")
    )
    assert contents.index(bootstrap_spec_block) < contents.index(tool_section)
    for tool_name in (
        CompanionToolName.MEMORY_STORE_READ_DOCUMENT,
        CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT,
        CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE,
        CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE,
    ):
        assert tool_name.value in tool_section


def test_bootstrap_output_contract_names_memory_store_write_paths_only() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
    )
    joined = "\n".join(
        _system_contents(
            build_system_messages_for_bootstrap_track(bundle, ContextMeta())
        )
    )
    assert "memory_store_write_document" in joined
    assert "IDENTITY.md / STYLE.md / USER.md" in joined
    assert "SOUL.md" in joined and "MEMORY.md" in joined
    assert "companion_update_prompt_slice" not in joined
    assert "schedule_task" not in joined


def test_bootstrap_omits_capability_package_slices() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
        channels_md="# Channels\nchannel contract",
        tools_md="# Tools\ntool contract",
    )
    joined = "\n".join(
        _system_contents(
            build_system_messages_for_bootstrap_track(bundle, ContextMeta())
        )
    )
    assert "channel contract" not in joined
    assert "tool contract" not in joined


def test_system_messages_omit_weixin_clawbot_alias_for_unknown_channel() -> None:
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


def test_system_messages_include_weixin_clawbot_alias_for_weixin_channel() -> None:
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
            memory_bootstrap_type="none",
            track=CompanionTurnTrack.USER_CHAT,
            route_mode=TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL,
            runtime_context=TurnRuntimeContext(
                channel=CompanionRuntimeChannel.WECHAT_WEIXIN,
                implicit_signal_bundle=None,
            ),
        )
    )
    system_text = "\n".join(contents)

    assert "Weixin / ClawBot 联系人显示名" in system_text
    assert "Weixin 里看到的名称" in system_text
    assert "不要声称已替用户改名" in system_text
    assert contents[-1].startswith("Weixin / ClawBot")
