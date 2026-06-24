"""Tests for dual-write user profile persistence."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import delete, select

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.user_md_identity import (
    USER_MD_REL,
    UserIdentityFieldLabel,
    load_user_md_template_text,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.db.session import AsyncSessionLocal
from app.models.user import Gender, User
from app.schemas.user import UserAgeGroup, UserMetadata, UserProfileSnapshot
from app.services.agentic_channel.companion_guest_provision import (
    GuestUserInput,
    add_guest_user,
)
from app.services.user_profile_persistence import (
    persist_user_profile_snapshot,
    seed_profile_collection_required_in_context,
)


def _store(tmp_path) -> MemoryStore:
    return MemoryStore(
        scope=CompanionScope("u1", "a1", str(tmp_path.resolve())),
        repository=None,
    )


@pytest.mark.asyncio
async def test_persist_user_profile_snapshot_dual_write(tmp_path) -> None:
    st = _store(tmp_path)
    st.write_document(USER_MD_REL, load_user_md_template_text())

    async with AsyncSessionLocal() as db:
        user = await add_guest_user(
            db,
            GuestUserInput(
                nickname_prefix="profile",
                meta_data={"profile_collection_required": True},
            ),
        )
        await db.commit()
        user_id = user.id

    snapshot = UserProfileSnapshot(
        gender=Gender.MALE,
        age_group=UserAgeGroup.AGE_26_35,
        location="Berlin",
        iana_timezone="Europe/Berlin",
    )
    async with AsyncSessionLocal() as db:
        await persist_user_profile_snapshot(
            db,
            user_id=user_id,
            snapshot=snapshot,
            memory_store=st,
        )

    async with AsyncSessionLocal() as db:
        row = await db.execute(select(User).where(User.id == user_id))
        loaded = row.scalar_one()
        assert loaded.gender == Gender.MALE
        assert loaded.age_group == "26-35"
        meta = UserMetadata.model_validate(loaded.meta_data or {})
        assert meta.location == "Berlin"
        assert meta.iana_timezone == "Europe/Berlin"

    user_md = st.read_document(USER_MD_REL)
    lines = user_md.splitlines()
    assert f"- {UserIdentityFieldLabel.GENDER}：男" in lines
    assert f"- {UserIdentityFieldLabel.AGE}：26-35" in lines
    assert f"- {UserIdentityFieldLabel.LOCATION}：Berlin" in lines
    assert f"- {UserIdentityFieldLabel.TIMEZONE}：Europe/Berlin" in lines

    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


def test_seed_profile_collection_required_in_context(tmp_path) -> None:
    st = _store(tmp_path)
    st.write_document(
        "context.json",
        json.dumps({"context_mode": "unspecific"}, ensure_ascii=False) + "\n",
    )
    seed_profile_collection_required_in_context(st, required=True)
    data = json.loads(st.read_document("context.json"))
    assert data["profile_collection_required"] is True
