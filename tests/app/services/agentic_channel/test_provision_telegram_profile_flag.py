"""Tests for Telegram profile_collection_required guest provision."""

from __future__ import annotations

import pytest
from sqlalchemy import delete

from app.core.companion_harness.agent_channel.gateway import GatewayKind
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.agentic_channel.companion_guest_provision import (
    GuestUserInput,
    add_guest_user,
)
from app.services.agentic_channel.provision import _guest_meta_data_for_channel
from app.schemas.user import UserMetadata


def test_guest_meta_data_telegram_sets_profile_collection_required() -> None:
    meta = _guest_meta_data_for_channel(GatewayKind.TELEGRAM)
    assert meta["agent_channel"] is True
    assert meta["profile_collection_required"] is True


def test_guest_meta_data_weixin_unchanged() -> None:
    meta = _guest_meta_data_for_channel(GatewayKind.WECHAT_WEIXIN)
    assert meta == {"agent_channel": True}
    assert "profile_collection_required" not in meta


@pytest.mark.asyncio
async def test_telegram_guest_row_carries_profile_flag() -> None:
    async with AsyncSessionLocal() as db:
        user = await add_guest_user(
            db,
            GuestUserInput(
                nickname_prefix="tg",
                meta_data=_guest_meta_data_for_channel(GatewayKind.TELEGRAM),
            ),
        )
        await db.commit()
        parsed = UserMetadata.model_validate(user.meta_data or {})
        assert parsed.profile_collection_required is True
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()
