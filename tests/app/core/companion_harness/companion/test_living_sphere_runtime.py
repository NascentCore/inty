from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.core.companion_harness.companion.models import load_context_meta, load_prompt_bundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_pipeline import (
    MemoryPipelineConfig,
    memory_update_after_turn,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tools import (
    build_openai_repl_tools,
    build_openai_repl_tools_inner_tick,
)
from app.living_sphere.models import (
    LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME,
    LivingSphereUpdate,
)
from app.living_sphere.seeding import (
    LIVING_SPHERE_RELATIVE_PATH,
    ensure_living_sphere_seeded,
)
def test_living_sphere_seeded_and_injects_prompt(tmp_path: Path) -> None:
    root = tmp_path / "ls-seed"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("user-ls", "companion-ls", str(root.resolve())),
        repository=None,
    )
    for name, body in (
        ("IDENTITY.md", "id\n"),
        ("SOUL.md", "soul\n"),
        ("STYLE.md", "style\n"),
        ("USER.md", "user\n"),
        ("MEMORY.md", "mem\n"),
        ("context.json", '{"context_mode":"intimate"}\n'),
    ):
        store.write_document(name, body)
    ensure_living_sphere_seeded(store)
    seeded = store.read_document(LIVING_SPHERE_RELATIVE_PATH)
    assert "世界：TechnoCore" in seeded
    assert "当前默认位置：" in seeded
    assert "不要冒充现实地理位置" in seeded

    ensure_living_sphere_seeded(store)
    assert store.read_document(LIVING_SPHERE_RELATIVE_PATH) == seeded

    context = load_context_meta(store=store)
    bundle = load_prompt_bundle(store, meta=context)
    system_text = "\n".join(
        str(m.get("content") or "")
        for m in build_system_messages(bundle, context)
        if m.get("role") == "system"
    )
    assert "世界：TechnoCore" in system_text
    assert "不要冒充现实地理位置" in system_text


def test_inner_tick_tools_exclude_living_sphere_record_update() -> None:
    names = {t["function"]["name"] for t in build_openai_repl_tools_inner_tick()}
    assert LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME not in names


def test_repl_tools_include_living_sphere_record_update_after_bootstrap() -> None:
    names = {t["function"]["name"] for t in build_openai_repl_tools(interactive_bootstrap_active=False)}
    assert LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME in names


def test_prompt_reflects_compacted_living_sphere_md(tmp_path: Path) -> None:
    root = tmp_path / "ls-prompt"
    root.mkdir()
    store = MemoryStore(
        scope=CompanionScope("u", "c", str(root.resolve())),
        repository=None,
    )
    for name, body in (
        ("IDENTITY.md", "id\n"),
        ("SOUL.md", "soul\n"),
        ("STYLE.md", "style\n"),
        ("USER.md", "user\n"),
        ("MEMORY.md", "mem\n"),
        ("TECHNO_CORE.md", "tc\n"),
        ("context.json", '{"context_mode":"intimate"}\n'),
    ):
        store.write_document(name, body)
    ensure_living_sphere_seeded(store)
    update = LivingSphereUpdate(change_request="书架旁加落地灯")
    store.append_jsonl_record(
        "living_sphere_updates.jsonl",
        update.model_dump(mode="json"),
    )

    def fake_complete(msgs: list[dict[str, Any]], model_role: str) -> str:
        if model_role == "memory":
            body = store.read_document(LIVING_SPHERE_RELATIVE_PATH)
            return body.replace("氛围：", "氛围：落地灯旁更暖，")
        return "noop\n"

    idle = threading.Event()
    idle.set()
    memory_update_after_turn(
        store,
        "加灯",
        "好",
        fake_complete,
        MemoryPipelineConfig(memory_update_every_n_turns=999),
        tool_bg_idle_event=idle,
    )
    context = load_context_meta(store=store)
    bundle = load_prompt_bundle(store, meta=context)
    system_text = "\n".join(
        str(m.get("content") or "")
        for m in build_system_messages(bundle, context)
        if m.get("role") == "system"
    )
    assert "落地灯旁更暖" in system_text
    assert LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME in system_text
