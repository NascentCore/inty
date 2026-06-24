"""Tests that bootstrap complete is not blocked on missing profile fields."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import delete

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.user_md_identity import USER_MD_REL
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call,
)
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.agentic_channel.companion_guest_provision import (
    GuestUserInput,
    add_guest_user,
)


def _store(tmp_path, user_id: str) -> MemoryStore:
    return MemoryStore(
        scope=CompanionScope(user_id, "agent-1", str(tmp_path.resolve())),
        repository=None,
    )


@pytest.mark.asyncio
async def test_bootstrap_complete_not_blocked_without_profile(tmp_path) -> None:
    async with AsyncSessionLocal() as db:
        user = await add_guest_user(
            db,
            GuestUserInput(
                nickname_prefix="ungated",
                meta_data={"profile_collection_required": True},
            ),
        )
        await db.commit()
        user_id = user.id

    st = _store(tmp_path, user_id)
    st.write_document(USER_MD_REL, "# 用户档案\n\n## 身份信息\n\n")
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "unspecific",
                "workspace_bootstrap_user_interactive_completed": False,
                "profile_collection_required": True,
            },
            ensure_ascii=False,
        )
        + "\n",
    )

    out = await execute_tool_call(
        st,
        "companion_bootstrap_user_interactive_complete",
        json.dumps({"note": "user impatient"}),
    )
    assert out.startswith("OK")
    ctx = json.loads(st.read_document("context.json"))
    assert ctx["workspace_bootstrap_user_interactive_completed"] is True

    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
