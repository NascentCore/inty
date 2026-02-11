import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.user import AuthType, User
from app.schemas.user import UserUpdate
from app.services.cache_service import cache_service
from app.services.selfie_persona_service import selfie_persona_service
from app.services.user_service import build_user_info_prompt_block, update_user


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        str(global_config_loaded_from_config_yaml.database.async_url),
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )
    async_session = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        cache_service.clear_all_caches()
        yield session
        cache_service.clear_all_caches()

    await engine.dispose()


async def _create_test_user(
    db_session: AsyncSession,
    *,
    user_photo: str | None = None,
    selfie_persona_summary: str | None = None,
) -> User:
    user = User(
        id=f"test-user-{uuid.uuid4().hex[:12]}",
        readable_id=str(uuid.uuid4().int)[:8],
        auth_type=AuthType.PHONE,
        nickname="Test User",
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        system_language="en",
        user_photo=user_photo,
        selfie_persona_summary=selfie_persona_summary,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
@patch(
    "app.services.selfie_persona_service.selfie_persona_service.enqueue_selfie_persona_inference"
)
async def test_update_user_triggers_selfie_persona_background_task(
    mock_enqueue_inference,
    db_session: AsyncSession,
):
    user = await _create_test_user(
        db_session,
        user_photo="gs://test-bucket/users/old-selfie.jpg",
        selfie_persona_summary="Old summary should be reset.",
    )

    updated_user = await update_user(
        db_session,
        user.id,
        UserUpdate(user_photo="gs://test-bucket/users/new-selfie.jpg"),
    )

    assert updated_user.selfie_persona_summary is None
    mock_enqueue_inference.assert_called_once_with(
        user_id=user.id,
        user_photo_url=updated_user.user_photo,
    )

    await db_session.delete(updated_user)
    await db_session.commit()


@pytest.mark.asyncio
@patch(
    "app.services.selfie_persona_service.selfie_persona_service.enqueue_selfie_persona_inference"
)
async def test_update_user_with_same_selfie_does_not_trigger_background_task(
    mock_enqueue_inference,
    db_session: AsyncSession,
):
    selfie_url = "gs://test-bucket/users/same-selfie.jpg"
    user = await _create_test_user(
        db_session,
        user_photo=selfie_url,
        selfie_persona_summary="Keep existing summary.",
    )

    updated_user = await update_user(
        db_session,
        user.id,
        UserUpdate(nickname="Updated Nickname", user_photo=selfie_url),
    )

    assert updated_user.nickname == "Updated Nickname"
    assert updated_user.selfie_persona_summary == "Keep existing summary."
    mock_enqueue_inference.assert_not_called()

    await db_session.delete(updated_user)
    await db_session.commit()


@pytest.mark.asyncio
@patch(
    "app.services.memory_service.get_user_memory_for_prompt_async",
    new_callable=AsyncMock,
    return_value="",
)
async def test_build_user_info_prompt_block_contains_selfie_persona(
    _mock_memory,
    db_session: AsyncSession,
):
    summary = "Calm and confident style with a friendly vibe."
    user = await _create_test_user(
        db_session,
        user_photo="gs://test-bucket/users/selfie.jpg",
        selfie_persona_summary=summary,
    )

    block = await build_user_info_prompt_block(db_session, user.id)

    assert "##User Information" in block
    assert f"Selfie Persona: {summary}" in block

    await db_session.delete(user)
    await db_session.commit()


def test_normalize_persona_summary_truncates_and_strips_prefix():
    raw = "Summary: " + ("confident and stylish " * 30)

    normalized = selfie_persona_service._normalize_persona_summary(raw)

    assert normalized is not None
    assert not normalized.lower().startswith("summary:")
    assert len(normalized) <= selfie_persona_service.MAX_SUMMARY_LENGTH + 3
