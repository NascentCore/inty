from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core.agentic_kernel.companion.bootstrap_user_interactive import (
    interactive_bootstrap_active,
    soul_prompt_is_locked_after_interactive_bootstrap,
    tool_companion_bootstrap_user_interactive_complete,
    tool_companion_set_experience_profile,
    tool_companion_update_prompt_slice,
)
from app.core.agentic_kernel.companion.memory_registry import get_memory_store
from app.core.agentic_kernel.companion.models import ContextMeta
from app.core.agentic_kernel.companion.companion_tool_runtime import (
    execute_tool_call,
    tool_workspace_write_file,
)
from app.core.agentic_kernel.companion.tools import build_companion_tools


def test_interactive_bootstrap_active_requires_flag_and_incomplete_meta() -> None:
    assert not interactive_bootstrap_active(
        feature_enabled=False,
        meta=ContextMeta(workspace_bootstrap_user_interactive_completed=False),
    )
    assert not interactive_bootstrap_active(
        feature_enabled=True,
        meta=ContextMeta(workspace_bootstrap_user_interactive_completed=True),
    )
    assert interactive_bootstrap_active(
        feature_enabled=True,
        meta=ContextMeta(workspace_bootstrap_user_interactive_completed=False),
    )


def test_build_companion_tools_interactive_excludes_workspace_write(tmp_path: Path) -> None:
    names = [t["function"]["name"] for t in build_companion_tools(interactive_bootstrap_active=True)]
    assert "workspace_write_file" not in names
    assert "companion_update_prompt_slice" in names
    assert "companion_bootstrap_user_interactive_complete" in names
    assert "companion_set_experience_profile" in names


def test_tool_companion_set_experience_profile_requires_confirm(tmp_path: Path) -> None:
    root = tmp_path
    st = get_memory_store(root)
    st.write_document(
        "context.json",
        json.dumps({"context_mode": "intimate", "user_id": "u"}, ensure_ascii=False) + "\n",
    )
    err = tool_companion_set_experience_profile(
        root, "roleplay", user_confirmed=False
    )
    assert err.startswith("ERROR:")
    assert json.loads(st.read_document("context.json"))["context_mode"] == "intimate"


def test_tool_companion_set_experience_profile_updates_context(tmp_path: Path) -> None:
    root = tmp_path
    st = get_memory_store(root)
    st.write_document(
        "context.json",
        json.dumps({"context_mode": "intimate", "user_id": "u"}, ensure_ascii=False) + "\n",
    )
    ok = tool_companion_set_experience_profile(
        root, " ROLEPLAY ", user_confirmed=True, note="user asked"
    )
    assert ok.startswith("OK ")
    data = json.loads(st.read_document("context.json"))
    assert data["context_mode"] == "roleplay"
    assert data["experience_profile_change_note"] == "user asked"


def test_execute_tool_call_dispatch_set_experience_profile(tmp_path: Path) -> None:
    root = tmp_path
    st = get_memory_store(root)
    st.write_document(
        "context.json",
        json.dumps({"context_mode": "public"}, ensure_ascii=False) + "\n",
    )
    r = asyncio.run(
        execute_tool_call(
            root,
            "companion_set_experience_profile",
            json.dumps({"context_mode": "emotional_companion", "user_confirmed": True}),
        )
    )
    assert r.startswith("OK ")
    assert json.loads(st.read_document("context.json"))["context_mode"] == "emotional_companion"


def test_tool_companion_update_prompt_slice_writes_user_md(tmp_path: Path) -> None:
    root = tmp_path
    get_memory_store(root)
    out = tool_companion_update_prompt_slice(root, "USER", "# user\n")
    assert out.startswith("OK ")
    st = get_memory_store(root)
    assert st.read_document("USER.md") == "# user\n"


def test_tool_companion_bootstrap_user_interactive_complete_updates_context(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = get_memory_store(root)
    ctx = {
        "context_mode": "intimate",
        "user_id": "u1",
        "companion_id": "a1",
        "chat_id": "c1",
        "workspace_bootstrap_user_interactive_completed": False,
    }
    st.write_document("context.json", json.dumps(ctx, ensure_ascii=False) + "\n")
    out = tool_companion_bootstrap_user_interactive_complete(root, "done")
    assert out.startswith("OK ")
    data = json.loads(st.read_document("context.json"))
    assert data["workspace_bootstrap_user_interactive_completed"] is True
    assert data["workspace_bootstrap_user_interactive_complete_note"] == "done"


def test_execute_tool_call_dispatch_slice_and_complete(tmp_path: Path) -> None:
    root = tmp_path
    st = get_memory_store(root)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "intimate",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
                "workspace_bootstrap_user_interactive_completed": False,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    st.write_document("SOUL.md", "old")
    r1 = asyncio.run(
        execute_tool_call(
            root,
            "companion_update_prompt_slice",
            json.dumps({"slice": "SOUL", "content": "new soul"}),
        )
    )
    assert r1.startswith("OK ")
    assert st.read_document("SOUL.md") == "new soul"
    r2 = asyncio.run(
        execute_tool_call(
            root,
            "companion_bootstrap_user_interactive_complete",
            json.dumps({}),
        )
    )
    assert r2.startswith("OK ")
    assert json.loads(st.read_document("context.json"))[
        "workspace_bootstrap_user_interactive_completed"
    ] is True


def test_soul_lock_helper_requires_explicit_context_key(tmp_path: Path) -> None:
    st = get_memory_store(tmp_path)
    assert not soul_prompt_is_locked_after_interactive_bootstrap(store=st)
    st.write_document(
        "context.json",
        json.dumps({"user_id": "u"}, ensure_ascii=False) + "\n",
    )
    assert not soul_prompt_is_locked_after_interactive_bootstrap(store=st)
    st.write_document(
        "context.json",
        json.dumps(
            {"user_id": "u", "workspace_bootstrap_user_interactive_completed": False},
            ensure_ascii=False,
        )
        + "\n",
    )
    assert not soul_prompt_is_locked_after_interactive_bootstrap(store=st)
    st.write_document(
        "context.json",
        json.dumps(
            {"user_id": "u", "workspace_bootstrap_user_interactive_completed": True},
            ensure_ascii=False,
        )
        + "\n",
    )
    assert soul_prompt_is_locked_after_interactive_bootstrap(store=st)


def test_soul_slice_rejected_after_interactive_bootstrap_complete(tmp_path: Path) -> None:
    root = tmp_path
    st = get_memory_store(root)
    st.write_document("SOUL.md", "seed")
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "intimate",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
                "workspace_bootstrap_user_interactive_completed": True,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    err = tool_companion_update_prompt_slice(root, "SOUL", "nope")
    assert err.startswith("ERROR:")
    assert st.read_document("SOUL.md") == "seed"
    ok = tool_companion_update_prompt_slice(root, "USER", "# ok\n")
    assert ok.startswith("OK ")
    assert st.read_document("USER.md") == "# ok\n"


def test_workspace_write_soul_rejected_after_interactive_bootstrap_complete(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = get_memory_store(root)
    st.write_document("SOUL.md", "seed")
    st.write_document(
        "context.json",
        json.dumps(
            {
                "workspace_bootstrap_user_interactive_completed": True,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    err = tool_workspace_write_file(root, "SOUL.md", "hacked")
    assert err.startswith("ERROR:")
    assert st.read_document("SOUL.md") == "seed"
