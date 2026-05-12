from __future__ import annotations

from pathlib import Path

from app.core.agentic_kernel.companion.llm_client import CompanionLLMConfig
from app.core.agentic_kernel.companion.manager import CompanionConfig, CompanionManager
from app.core.agentic_kernel.companion.memory_store_scope import MemoryStoreScopePaths
from app.core.agentic_kernel.companion.models import load_context_meta, load_prompt_bundle
from app.core.agentic_kernel.companion.prompts.system_messages import (
    build_system_messages,
)
from living_sphere.seeding import (
    LIVING_SPHERE_RELATIVE_PATH,
    ensure_living_sphere_seeded,
)


def test_companion_session_seeds_living_sphere_and_injects_prompt(
    tmp_path: Path,
) -> None:
    manager = CompanionManager(
        CompanionConfig(
            memory_store_scope_base_dir=str(tmp_path / "scopes"),
            llm=CompanionLLMConfig(api_key="test-key"),
        )
    )
    session = manager.get_or_create_session("user-ls", "companion-ls", "chat-ls")

    seeded = session.store.read_document(LIVING_SPHERE_RELATIVE_PATH)
    assert "世界：TechnoCore" in seeded
    assert "当前默认位置：" in seeded
    assert "不要冒充现实地理位置" in seeded

    ensure_living_sphere_seeded(session.store)
    assert session.store.read_document(LIVING_SPHERE_RELATIVE_PATH) == seeded

    paths = MemoryStoreScopePaths(root=session.workspace_path.resolve())
    context = load_context_meta(paths.context_json, store=session.store)
    bundle = load_prompt_bundle(paths, session.store, meta=context)
    system_text = "\n".join(
        str(m.get("content") or "")
        for m in build_system_messages(bundle, context)
        if m.get("role") == "system"
    )
    assert "## LIVING SPHERE" in system_text
    assert "世界：TechnoCore" in system_text
    assert "不要冒充现实地理位置" in system_text

    manager.shutdown_all()
