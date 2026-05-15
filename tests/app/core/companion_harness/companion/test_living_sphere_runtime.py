from __future__ import annotations

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.companion.manager import CompanionConfig, CompanionManager
from app.core.companion_harness.companion.models import load_context_meta, load_prompt_bundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
)
from living_sphere.seeding import (
    LIVING_SPHERE_RELATIVE_PATH,
    ensure_living_sphere_seeded,
)
from tests.app.core.companion_harness.companion_memory_registry_dsn import (
    companion_memory_registry_dsn,
)


def test_companion_session_seeds_living_sphere_and_injects_prompt(
) -> None:
    manager = CompanionManager(
        CompanionConfig(
            llm=CompanionLLMConfig(api_key="test-key"),
            memory_pg_dsn=companion_memory_registry_dsn(),
        )
    )
    session = manager.get_or_create_session("user-ls", "companion-ls", "chat-ls")

    seeded = session.store.read_document(LIVING_SPHERE_RELATIVE_PATH)
    assert "世界：TechnoCore" in seeded
    assert "当前默认位置：" in seeded
    assert "不要冒充现实地理位置" in seeded

    ensure_living_sphere_seeded(session.store)
    assert session.store.read_document(LIVING_SPHERE_RELATIVE_PATH) == seeded

    context = load_context_meta(store=session.store)
    bundle = load_prompt_bundle(session.store, meta=context)
    system_text = "\n".join(
        str(m.get("content") or "")
        for m in build_system_messages(bundle, context)
        if m.get("role") == "system"
    )
    assert "世界：TechnoCore" in system_text
    assert "不要冒充现实地理位置" in system_text

    manager.shutdown_all()
