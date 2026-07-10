from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    CHANNELS_MD_REL,
    LIFE_CURRENTS_MD_REL,
    USER_MD_REL,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call,
)


def _run_tool(
    store,
    name: str,
    args: str,
    *,
    write_allowlist: frozenset[str] | None = None,
) -> str:
    if write_allowlist is not None:
        return asyncio.run(
            execute_tool_call(
                store, name, args, write_allowlist=write_allowlist
            )
        )
    return asyncio.run(execute_tool_call(store, name, args))


def test_tool_memory_store_list_paths(tmp_path: Path) -> None:
    st = MemoryStore(
        scope=CompanionScope("tools", "a", tmp_path.name),
        repository=None,
    )
    st.write_document(USER_MD_REL, "u")
    st.write_document("memory/daily/2099-01-01.md", "d")
    out = _run_tool(
        st,
        "memory_store_list_paths",
        json.dumps({"relative_path": "."}),
    )
    assert USER_MD_REL in out
    assert "memory/" in out
    out_mem = _run_tool(
        st,
        "memory_store_list_paths",
        json.dumps({"relative_path": "memory"}),
    )
    assert "daily/" in out_mem


def test_tool_memory_store_read_write(tmp_path: Path) -> None:
    st = MemoryStore(
        scope=CompanionScope("tools", "a", f"{tmp_path.name}-rw"),
        repository=None,
    )
    w = _run_tool(
        st,
        "memory_store_write_document",
        json.dumps({"relative_path": USER_MD_REL, "content": "full text"}),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    )
    assert w.startswith("OK ")
    r = _run_tool(
        st,
        "memory_store_read_document",
        json.dumps({"relative_path": USER_MD_REL}),
    )
    assert r == "full text"


def test_tool_memory_store_write_user_rejected_under_autonomy_allowlist(
    tmp_path: Path,
) -> None:
    st = MemoryStore(
        scope=CompanionScope("tools", "a", f"{tmp_path.name}-autonomy-wl"),
        repository=None,
    )
    out = _run_tool(
        st,
        "memory_store_write_document",
        json.dumps({"relative_path": USER_MD_REL, "content": "nope"}),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
    )
    assert out.startswith("ERROR:")
    assert "only allows" in out
    life_out = _run_tool(
        st,
        "memory_store_write_document",
        json.dumps(
            {
                "relative_path": LIFE_CURRENTS_MD_REL,
                "content": "# 我最近在做的事\n",
            }
        ),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY,
    )
    assert life_out.startswith("OK ")


def test_tool_memory_store_write_not_in_allowlist(tmp_path: Path) -> None:
    st = MemoryStore(
        scope=CompanionScope("tools", "a", f"{tmp_path.name}-wl"),
        repository=None,
    )
    out = _run_tool(
        st,
        "memory_store_write_document",
        json.dumps({"relative_path": "secret.txt", "content": "nope"}),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    )
    assert out.startswith("ERROR:")
    assert "only allows" in out


def test_tool_memory_store_write_channels_not_mutable_during_chat(
    tmp_path: Path,
) -> None:
    st = MemoryStore(
        scope=CompanionScope("tools", "a", f"{tmp_path.name}-channels"),
        repository=None,
    )
    st.write_document(CHANNELS_MD_REL, "seed\n")
    out = _run_tool(
        st,
        "memory_store_write_document",
        json.dumps({"relative_path": CHANNELS_MD_REL, "content": "mutated"}),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    )
    assert out.startswith("ERROR:")
    assert st.read_document(CHANNELS_MD_REL) == "seed\n"


def test_tool_update_user_md_appends_custom_label(tmp_path: Path) -> None:
    st = MemoryStore(
        scope=CompanionScope("tools", "a", f"{tmp_path.name}-user-md"),
        repository=None,
    )
    st.write_document(USER_MD_REL, "# USER.md - 关于你的用户\n\n## 身份信息\n\n")
    out = _run_tool(
        st,
        "update_user_md",
        json.dumps(
            {"items": [{"label": "称呼偏好", "value": "叫我小宇"}]},
            ensure_ascii=False,
        ),
    )
    assert out == f"OK appended 1 line(s) in {USER_MD_REL}"
    user_md_lines = st.read_document(USER_MD_REL).split("\n")
    assert user_md_lines == [
        "# USER.md - 关于你的用户",
        "",
        "## 身份信息",
        "",
        f"- 称呼偏好：叫我小宇（记录日期 {date.today().isoformat()}）",
        "",
    ]


def test_tool_update_user_md_inline_fills_identity_template(
    tmp_path: Path,
) -> None:
    from app.core.companion_harness.memory.user_md_identity import (
        UserIdentityFieldLabel,
        load_user_md_template_text,
    )

    st = MemoryStore(
        scope=CompanionScope("tools", "a", f"{tmp_path.name}-inline"),
        repository=None,
    )
    st.write_document(USER_MD_REL, load_user_md_template_text())
    out = _run_tool(
        st,
        "update_user_md",
        json.dumps(
            {
                "items": [
                    {
                        "label": UserIdentityFieldLabel.GENDER,
                        "value": "男",
                    }
                ]
            },
            ensure_ascii=False,
        ),
    )
    assert out == f"OK filled 1 template slot(s) in {USER_MD_REL}"
    assert (
        f"- {UserIdentityFieldLabel.GENDER}：男"
        in st.read_document(USER_MD_REL).splitlines()
    )
