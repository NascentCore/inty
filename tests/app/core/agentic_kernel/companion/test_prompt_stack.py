from __future__ import annotations

import json
from pathlib import Path

from app.utils.config import CompanionWorkspaceBootstrapType

from app.core.agentic_kernel.companion.bootstrap_user_interactive import (
    tool_companion_bootstrap_user_interactive_complete,
)
from app.core.agentic_kernel.companion.memory_registry import (
    get_memory_store,
    shutdown_memory_store,
)
from app.core.agentic_kernel.companion.models import (
    InnerTickMode,
    load_context_meta,
    load_prompt_bundle,
)
from app.core.agentic_kernel.companion.prompt_stack import (
    companion_turn_tools_and_system_messages,
    refresh_companion_turn_prompt_stack,
    replace_leading_system_messages_inplace,
)
from app.core.agentic_kernel.companion.prompts import build_system_messages
from app.core.agentic_kernel.companion.workspace import WorkspacePaths


def _seed_workspace_bootstrap_incomplete(root: Path) -> None:
    st = get_memory_store(root)
    for rel, body in (
        ("IDENTITY.md", "id\n"),
        ("SOUL.md", "soul\n"),
        ("USER.md", "user\n"),
        ("MEMORY.md", "mem\n"),
    ):
        st.write_document(rel, body)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "public",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
                "workspace_bootstrap_user_interactive_completed": False,
            },
            ensure_ascii=False,
        )
        + "\n",
    )


def _joined_leading_system_contents(messages: list[dict]) -> str:
    parts: list[str] = []
    for m in messages:
        if m.get("role") != "system":
            break
        parts.append(str(m.get("content") or ""))
    return "\n".join(parts)


def test_inner_tick_loads_ai_private_jsonl_into_system(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    st = get_memory_store(root)
    for rel, body in (
        ("IDENTITY.md", "id\n"),
        ("SOUL.md", "soul\n"),
        ("USER.md", "user\n"),
        ("MEMORY.md", "mem\n"),
    ):
        st.write_document(rel, body)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "public",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    st.write_document("ai_private.jsonl", '{"text": "jl seed line"}\n')
    paths = WorkspacePaths(root=root.resolve())
    context = load_context_meta(paths.context_json, store=st)
    bundle = load_prompt_bundle(paths, st, meta=context)
    _, systems, _ = companion_turn_tools_and_system_messages(
        workspace_root=root.resolve(),
        bundle=bundle,
        context=context,
        workspace_bootstrap_type=CompanionWorkspaceBootstrapType.NONE.value,
        inner_tick_turn=True,
        inner_tick_mode=InnerTickMode.MAINTENANCE,
        enable_async_tool_background=False,
        tool_side_compact_system_prompt=False,
    )
    joined = "\n".join(
        str(m.get("content") or "") for m in systems if m.get("role") == "system"
    )
    assert "jl seed line" in joined
    shutdown_memory_store(root.resolve())


def test_replace_leading_system_messages_inplace_keeps_tail() -> None:
    msgs = [
        {"role": "system", "content": "a"},
        {"role": "system", "content": "b"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "yo"},
    ]
    replace_leading_system_messages_inplace(
        msgs, [{"role": "system", "content": "fresh"}]
    )
    assert msgs == [
        {"role": "system", "content": "fresh"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "yo"},
    ]


def test_refresh_drops_interactive_bootstrap_after_complete(tmp_path: Path) -> None:
    root = tmp_path
    _seed_workspace_bootstrap_incomplete(root)
    st = get_memory_store(root)
    paths = WorkspacePaths(root=root.resolve())
    context = load_context_meta(paths.context_json, store=st)
    bundle = load_prompt_bundle(paths, st, meta=context)
    systems = build_system_messages(
        bundle,
        context,
        enable_tools=True,
        inner_tick_turn=False,
        interactive_bootstrap_active=True,
    )
    messages = [dict(m) for m in systems]
    messages.append({"role": "user", "content": "hello"})

    before = _joined_leading_system_contents(messages)
    assert "INTERACTIVE_BOOTSTRAP" in before

    out = tool_companion_bootstrap_user_interactive_complete(root, note=None)
    assert out.startswith("OK ")
    assert json.loads(st.read_document("context.json"))[
        "workspace_bootstrap_user_interactive_completed"
    ] is True

    new_tools = refresh_companion_turn_prompt_stack(
        workspace=root,
        store=st,
        workspace_bootstrap_type=CompanionWorkspaceBootstrapType.USER_INTERACTIVE.value,
        inner_tick_turn=False,
        inner_tick_mode=InnerTickMode.MAINTENANCE,
        enable_async_tool_background=True,
        messages=messages,
        tool_side_compact_system_prompt=False,
    )

    after = _joined_leading_system_contents(messages)
    assert "INTERACTIVE_BOOTSTRAP" not in after
    assert "BOOTSTRAP.md" not in after
    tool_names = [t["function"]["name"] for t in new_tools]
    assert "workspace_write_file" in tool_names
    assert "companion_bootstrap_user_interactive_complete" not in tool_names

    assert messages[-1] == {"role": "user", "content": "hello"}


def test_refresh_tool_side_compact_drops_bootstrap_after_complete(tmp_path: Path) -> None:
    root = tmp_path
    _seed_workspace_bootstrap_incomplete(root)
    st = get_memory_store(root)
    paths = WorkspacePaths(root=root.resolve())
    context = load_context_meta(paths.context_json, store=st)
    bundle = load_prompt_bundle(paths, st, meta=context)
    systems = build_system_messages(
        bundle,
        context,
        enable_tools=True,
        enable_user_profile_tool=False,
        inner_tick_turn=False,
        include_repl_image_generation_contract=True,
        tool_side_compact=True,
        interactive_bootstrap_active=True,
        include_significance_perception_slice=False,
    )
    messages = [dict(m) for m in systems]
    messages.append({"role": "user", "content": "x"})
    assert "INTERACTIVE_BOOTSTRAP" in _joined_leading_system_contents(messages)

    tool_companion_bootstrap_user_interactive_complete(root, note=None)
    refresh_companion_turn_prompt_stack(
        workspace=root,
        store=st,
        workspace_bootstrap_type=CompanionWorkspaceBootstrapType.USER_INTERACTIVE.value,
        inner_tick_turn=False,
        inner_tick_mode=InnerTickMode.MAINTENANCE,
        enable_async_tool_background=True,
        messages=messages,
        tool_side_compact_system_prompt=True,
    )
    assert "INTERACTIVE_BOOTSTRAP" not in _joined_leading_system_contents(messages)
