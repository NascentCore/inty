"""Dual-write user profile fields to users row and companion USER.md.

The user profile database fields (gender, age group, location, timezone) are used
for pending changes to user identity, and may support personalization or integration
flows, including advertising campaigns (such as Telegram ads) when configured.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.user_md_identity import (
    USER_MD_REL,
    fill_user_md_identity_fields,
    identity_field_values_for_snapshot,
)
from app.models.user import User, normalize_gender
from app.schemas.user import UserMetadata, UserProfileSnapshot


async def persist_user_profile_snapshot(
    db: AsyncSession,
    *,
    user_id: str,
    snapshot: UserProfileSnapshot,
    memory_store: MemoryStore,
) -> None:
    """Merge snapshot into users row, then inline-fill matching USER.md identity slots."""
    assert user_id != ""
    has_field = (
        snapshot.gender is not None
        or snapshot.age_group is not None
        or (snapshot.location is not None and snapshot.location != "")
        or (snapshot.iana_timezone is not None and snapshot.iana_timezone != "")
    )
    assert has_field

    row = await db.execute(select(User).where(User.id == user_id))
    user = row.scalar_one_or_none()
    if user is None:
        raise ValueError(f"user not found: {user_id}")

    meta = UserMetadata.model_validate(user.meta_data or {})
    if snapshot.gender is not None:
        user.gender = normalize_gender(snapshot.gender)
    if snapshot.age_group is not None:
        user.age_group = snapshot.age_group.value
    if snapshot.location is not None and snapshot.location != "":
        meta = meta.model_copy(update={"location": snapshot.location})
    if snapshot.iana_timezone is not None and snapshot.iana_timezone != "":
        meta = meta.model_copy(update={"iana_timezone": snapshot.iana_timezone})
    user.meta_data = meta.model_dump(mode="json", exclude_none=False)

    await db.flush()

    field_values = identity_field_values_for_snapshot(snapshot)
    if field_values:
        prev = memory_store.read_document_if_exists(USER_MD_REL)
        if prev is None:
            raise ValueError(f"missing {USER_MD_REL!r} in memory store")
        merged = fill_user_md_identity_fields(prev, field_values)
        memory_store.write_document(USER_MD_REL, merged)

    await db.commit()
    logger.info(
        "persist_user_profile_snapshot user_id={} fields={}",
        user_id,
        [
            name
            for name, val in (
                ("gender", snapshot.gender),
                ("age_group", snapshot.age_group),
                ("location", snapshot.location),
                ("iana_timezone", snapshot.iana_timezone),
            )
            if val is not None and val != ""
        ],
    )


def seed_profile_collection_required_in_context(
    store: MemoryStore,
    *,
    required: bool,
) -> None:
    """Persist profile-collection flag into session context after Telegram provision."""
    rel = "context.json"
    raw = store.read_document_if_exists(rel)
    if raw is None or not str(raw).strip():
        raise ValueError("ERROR: missing context.json")
    data: dict[str, Any] = json.loads(str(raw))
    if not isinstance(data, dict):
        raise ValueError("ERROR: context.json must be a JSON object")
    data["profile_collection_required"] = required
    store.write_document(
        rel,
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
    )
