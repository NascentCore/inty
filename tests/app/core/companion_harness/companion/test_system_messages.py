from __future__ import annotations

from app.core.companion_harness.companion.models import ContextMeta, PromptBundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
)


def test_system_messages_include_wechat_clawbot_contact_alias_boundary() -> None:
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        style_md="style",
        user_md="user",
        memory_md="memory",
    )
    context = ContextMeta()

    system_text = "\n".join(
        str(message.get("content") or "")
        for message in build_system_messages(bundle, context)
        if message.get("role") == "system"
    )

    assert "WeChat / ClawBot 联系人显示名" in system_text
    assert "微信联系人资料页" in system_text
    assert "不要声称已替用户改名" in system_text
