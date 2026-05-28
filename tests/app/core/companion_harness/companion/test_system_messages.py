from __future__ import annotations

from app.core.companion_harness.companion.models import ContextMeta
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
    build_system_messages_for_bootstrap_track,
)


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


def test_system_messages_include_wechat_clawbot_contact_alias_boundary() -> None:
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

    assert "WeChat / ClawBot 联系人显示名" in system_text
    assert "微信联系人资料页" in system_text
    assert "不要声称已替用户改名" in system_text
