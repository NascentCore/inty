from __future__ import annotations

from app.core.companion_harness.runtime.llm_client import CompanionLLMConfig
from app.core.companion_harness.runtime.manager import CompanionConfig, CompanionManager
from app.core.companion_harness.runtime.models import load_context_meta, load_prompt_bundle
from app.core.companion_harness.memory.memory_registry import shutdown_all_memory_stores
from app.core.companion_harness.system_hierarchy.prompts.system_messages import (
    build_system_messages,
)
from app.techno_core.models import Sphere, TechnoCoreEvent, Visibility
from app.techno_core.seeding import (
    TECHNO_CORE_RELATIVE_PATH,
    ensure_techno_core_seeded,
)
from tests.app.core.companion_harness.companion_memory_registry_dsn import (
    companion_memory_registry_dsn,
)


def test_companion_session_seeds_techno_core_and_injects_prompt() -> None:
    manager = CompanionManager(
        CompanionConfig(
            llm=CompanionLLMConfig(api_key="test-key"),
            memory_pg_dsn=companion_memory_registry_dsn(),
        )
    )
    session = manager.get_or_create_session("user-tc", "companion-tc", "chat-tc")

    seeded = session.store.read_document(TECHNO_CORE_RELATIVE_PATH)
    assert "TechnoCore 是 Inty 的 AI-only 虚拟居留层" in seeded
    assert "LivingSphere" in seeded
    assert "Channels" in seeded
    assert "不要声称自己处在现实物理空间" in seeded
    assert "独立性" in seeded
    assert "陪伴" in seeded

    ensure_techno_core_seeded(session.store)
    assert session.store.read_document(TECHNO_CORE_RELATIVE_PATH) == seeded

    context = load_context_meta(store=session.store)
    bundle = load_prompt_bundle(session.store, meta=context)
    system_text = "\n".join(
        str(m.get("content") or "")
        for m in build_system_messages(bundle, context)
        if m.get("role") == "system"
    )
    assert "TechnoCore 是 Inty 的 AI-only 虚拟居留层" in system_text
    assert "世界：TechnoCore" in system_text
    assert system_text.index("TechnoCore 是 Inty 的 AI-only 虚拟居留层") < system_text.index(
        "当前默认位置："
    )

    shutdown_all_memory_stores()


def test_techno_core_event_serializes_stable_string_enums() -> None:
    event = TechnoCoreEvent(
        sphere=Sphere.TECHNO_CORE,
        actor_companion_id="companion-tc",
        summary="在 TechnoCore 边缘整理了一段适合稍后分享给用户的心情。",
        visibility=Visibility.SHAREABLE,
        emotional_valence="tender",
        salience=7,
        source="inner_tick",
        related_user_id="user-tc",
        related_living_sphere="玻璃海岸小屋",
    )

    payload = event.model_dump()
    assert payload["sphere"] == "techno_core"
    assert payload["visibility"] == "shareable"
    assert '"sphere":"techno_core"' in event.model_dump_json()
    assert '"visibility":"shareable"' in event.model_dump_json()
