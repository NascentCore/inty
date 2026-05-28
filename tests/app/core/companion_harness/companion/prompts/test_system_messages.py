from __future__ import annotations

from app.core.companion_harness.companion.models import ContextMeta
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
)


def test_doctrine_system_prefix_excludes_subconscious_prompt() -> None:
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )
    messages = build_system_messages(bundle, ContextMeta())
    doctrine_lines = [
        str(messages[index]["content"]).split("\n")[0] for index in range(3)
    ]

    assert doctrine_lines == [
        "# Axiom - 你存在的根本法则",
        "# Inty - AI agents as human companions",
        "# Safety - 安全预防",
    ]
    assert all("SUBCONSCIOUS" not in str(message["content"]) for message in messages)
