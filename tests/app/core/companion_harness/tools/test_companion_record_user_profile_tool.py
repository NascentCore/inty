"""Tests for companion_record_user_profile tool dispatch."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    USER_MD_REL,
)
from app.core.companion_harness.memory.user_md_identity import (
    UserIdentityFieldLabel,
    load_user_md_template_text,
)
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call,
)
from app.db.session import AsyncSessionLocal
from app.models.user import Gender, User
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
async def test_companion_record_user_profile_dispatch_ok(tmp_path) -> None:
    async with AsyncSessionLocal() as db:
        user = await add_guest_user(
            db,
            GuestUserInput(
                nickname_prefix="tool",
                meta_data={"profile_collection_required": True},
            ),
        )
        await db.commit()
        user_id = user.id

    st = _store(tmp_path, user_id)
    st.write_document(USER_MD_REL, load_user_md_template_text())
    args = json.dumps(
        {
            "gender": "FEMALE",
            "age_group": "18-25",
            "location": "London",
            "note": "user confirmed",
        }
    )
    out = await execute_tool_call(
        st,
        "companion_record_user_profile",
        args,
        write_allowlist=frozenset({USER_MD_REL}),
    )
    assert out.startswith("OK recorded user profile")

    async with AsyncSessionLocal() as db:
        row = await db.execute(select(User).where(User.id == user_id))
        loaded = row.scalar_one()
        assert loaded.gender == Gender.FEMALE
        assert loaded.age_group == "18-25"
        assert loaded.meta_data["location"] == "London"
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()

    lines = st.read_document(USER_MD_REL).splitlines()
    assert f"- {UserIdentityFieldLabel.GENDER}：女" in lines
    assert f"- {UserIdentityFieldLabel.AGE}：18-25" in lines
    assert f"- {UserIdentityFieldLabel.LOCATION}：London" in lines


@pytest.mark.asyncio
async def test_companion_record_user_profile_requires_field(tmp_path) -> None:
    st = _store(tmp_path, "user-missing")
    out = await execute_tool_call(
        st,
        "companion_record_user_profile",
        json.dumps({"note": "empty"}),
    )
    assert out.startswith("ERROR:")
