"""Fixed INTY.md system slice (after AXIOM, before security prefix)."""

from __future__ import annotations

from app.core.companion_harness.companion.models import ContextMeta, PromptBundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
)
from app.core.companion_harness.memory.memory_store_scope import (
    get_imate_axiom_system_text,
    get_inty_facts_system_text,
)


def test_get_inty_facts_system_text_loads_package_seed() -> None:
    text = get_inty_facts_system_text()
    assert "Intelligence Entity" in text
    assert "TechnoCore" in text


def test_build_system_messages_injects_inty_after_axiom() -> None:
    bundle = PromptBundle(
        identity="i",
        soul="s",
        user_md="u",
        memory_md="",
    )
    ctx = ContextMeta(context_mode="intimate")
    msgs = build_system_messages(bundle, ctx, enable_tools=False)
    system_contents = [m["content"] for m in msgs if m.get("role") == "system"]
    assert system_contents[0] == get_imate_axiom_system_text()
    assert system_contents[1] == get_inty_facts_system_text()
