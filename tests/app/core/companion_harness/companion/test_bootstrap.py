from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core.companion_harness.companion.bootstrap import (
    interactive_bootstrap_active,
    tool_companion_bootstrap_user_interactive_complete,
    tool_companion_set_experience_profile,
    tool_companion_update_prompt_slice,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.models import ContextMeta
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call,
    tool_memory_store_write_document,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.tools.companion_tools import build_companion_tools


def _store(root: Path):
    return MemoryStore(
        scope=CompanionScope("bootstrap", "agent", str(root.resolve())),
        repository=None,
    )


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


def test_build_companion_tools_interactive_excludes_memory_store_write(tmp_path: Path) -> None:
    names = [t["function"]["name"] for t in build_companion_tools(interactive_bootstrap_active=True)]
    assert "memory_store_write_document" not in names
    assert "companion_update_prompt_slice" in names
    assert "companion_bootstrap_user_interactive_complete" in names
    assert "companion_set_experience_profile" in names


def test_tool_companion_set_experience_profile_updates_context(tmp_path: Path) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(
        "context.json",
        json.dumps({"context_mode": "intimate", "user_id": "u"}, ensure_ascii=False) + "\n",
    )
    ok = tool_companion_set_experience_profile(
        st, " ROLEPLAY ", note="user asked"
    )
    assert ok.startswith("OK ")
    data = json.loads(st.read_document("context.json"))
    assert data["context_mode"] == "roleplay"
    assert data["experience_profile_change_note"] == "user asked"


def test_execute_tool_call_dispatch_set_experience_profile_missing_note(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(
        "context.json",
        json.dumps({"context_mode": "public"}, ensure_ascii=False) + "\n",
    )
    r = asyncio.run(
        execute_tool_call(
            st,
            "companion_set_experience_profile",
            json.dumps({"context_mode": "emotional_companion"}),
        )
    )
    assert r == "ERROR: note must be a string"
    assert json.loads(st.read_document("context.json"))["context_mode"] == "public"


def test_execute_tool_call_dispatch_set_experience_profile(tmp_path: Path) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(
        "context.json",
        json.dumps({"context_mode": "public"}, ensure_ascii=False) + "\n",
    )
    r = asyncio.run(
        execute_tool_call(
            st,
            "companion_set_experience_profile",
            json.dumps(
                {
                    "context_mode": "emotional_companion",
                    "note": "user asked for emotional companion",
                }
            ),
        )
    )
    assert r.startswith("OK ")
    assert json.loads(st.read_document("context.json"))["context_mode"] == "emotional_companion"


def test_tool_companion_update_prompt_slice_writes_user_md(tmp_path: Path) -> None:
    root = tmp_path
    st = _store(root)
    out = tool_companion_update_prompt_slice(st, "USER", "# user\n")
    assert out.startswith("OK ")
    assert st.read_document("USER.md") == "# user\n"


def test_tool_companion_bootstrap_user_interactive_complete_updates_context(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = _store(root)
    ctx = {
        "context_mode": "unspecific",
        "user_id": "u1",
        "companion_id": "a1",
        "chat_id": "c1",
        "workspace_bootstrap_user_interactive_completed": False,
    }
    st.write_document("context.json", json.dumps(ctx, ensure_ascii=False) + "\n")
    out = tool_companion_bootstrap_user_interactive_complete(st, "done")
    assert out.startswith("OK ")
    data = json.loads(st.read_document("context.json"))
    assert data["workspace_bootstrap_user_interactive_completed"] is True
    assert data["workspace_bootstrap_user_interactive_complete_note"] == "done"
    assert data["context_mode"] == "unspecific"


def test_tool_companion_bootstrap_user_interactive_complete_promotes_legacy_bootstrap_mode(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "bootstrap",
                "user_id": "u",
                "workspace_bootstrap_user_interactive_completed": False,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    tool_companion_bootstrap_user_interactive_complete(st, None)
    data = json.loads(st.read_document("context.json"))
    assert data["context_mode"] == "unspecific"


def test_tool_companion_bootstrap_user_interactive_complete_preserves_non_bootstrap_mode(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "roleplay",
                "user_id": "u",
                "workspace_bootstrap_user_interactive_completed": False,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    tool_companion_bootstrap_user_interactive_complete(st, None)
    data = json.loads(st.read_document("context.json"))
    assert data["context_mode"] == "roleplay"


def test_tool_companion_set_experience_profile_rejects_bootstrap(tmp_path: Path) -> None:
    root = tmp_path
    st = _store(root)
    st.write_document(
        "context.json",
        json.dumps({"context_mode": "intimate", "user_id": "u"}, ensure_ascii=False) + "\n",
    )
    err = tool_companion_set_experience_profile(
        st, "bootstrap", note="attempt bootstrap switch"
    )
    assert err.startswith("ERROR:")
    assert json.loads(st.read_document("context.json"))["context_mode"] == "intimate"


def test_execute_tool_call_dispatch_slice_and_complete(tmp_path: Path) -> None:
    root = tmp_path
    st = _store(root)
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
            st,
            "companion_update_prompt_slice",
            json.dumps({"slice": "SOUL", "content": "new soul"}),
        )
    )
    assert r1.startswith("OK ")
    assert st.read_document("SOUL.md") == "new soul"
    r2 = asyncio.run(
        execute_tool_call(
            st,
            "companion_bootstrap_user_interactive_complete",
            json.dumps({}),
        )
    )
    assert r2.startswith("OK ")
    assert json.loads(st.read_document("context.json"))[
        "workspace_bootstrap_user_interactive_completed"
    ] is True
    r3 = asyncio.run(
        execute_tool_call(
            st,
            "companion_update_prompt_slice",
            json.dumps({"slice": "SOUL", "content": "soul after complete"}),
        )
    )
    assert r3.startswith("OK ")
    assert st.read_document("SOUL.md") == "soul after complete"


def test_soul_slice_allowed_after_interactive_bootstrap_complete(tmp_path: Path) -> None:
    root = tmp_path
    st = _store(root)
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
    ok = tool_companion_update_prompt_slice(st, "SOUL", "updated soul\n")
    assert ok.startswith("OK ")
    assert st.read_document("SOUL.md") == "updated soul\n"


def test_memory_store_write_soul_allowed_after_interactive_bootstrap_complete(
    tmp_path: Path,
) -> None:
    root = tmp_path
    st = _store(root)
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
    ok = tool_memory_store_write_document(st, "SOUL.md", "updated via store")
    assert ok.startswith("OK ")
    assert st.read_document("SOUL.md") == "updated via store"
