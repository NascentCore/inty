from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.core.config import global_config_loaded_from_config_yaml
from app.models.user import AuthType, User
from app.schemas.user import UserUpdate
from app.services.cache_service import cache_service
from app.services.selfie_persona_service import selfie_persona_service
from app.services.user_service import build_user_info_prompt_block, update_user


def _build_user(
    *,
    user_photo: str | None = None,
    selfie_persona_summary: str | None = None,
) -> User:
    return User(
        id="test-user-1",
        readable_id="12345678",
        auth_type=AuthType.PHONE,
        nickname="Test User",
        email="test@example.com",
        system_language="en",
        user_photo=user_photo,
        selfie_persona_summary=selfie_persona_summary,
    )


def _build_mock_db_for_user(user: User) -> AsyncMock:
    db = AsyncMock()

    execute_result = Mock()
    scalars_result = Mock()
    scalars_result.first.return_value = user
    execute_result.scalars.return_value = scalars_result

    db.execute.return_value = execute_result
    return db


@pytest.mark.asyncio
@patch(
    "app.services.selfie_persona_service.selfie_persona_service.enqueue_selfie_persona_inference"
)
async def test_update_user_triggers_selfie_persona_background_task(
    mock_enqueue_inference,
):
    user = _build_user(
        user_photo="gs://test-bucket/users/old-selfie.jpg",
        selfie_persona_summary="Old summary should be reset.",
    )
    db = _build_mock_db_for_user(user)

    with patch(
        "app.services.image_transform_service.image_transform_service.normalize_image_url_for_storage",
        side_effect=lambda x: x,
    ):
        updated_user = await update_user(
            db,
            user.id,
            UserUpdate(user_photo="gs://test-bucket/users/new-selfie.jpg"),
        )

    assert updated_user.selfie_persona_summary is None
    mock_enqueue_inference.assert_called_once_with(
        user_id=user.id,
        user_photo_url=updated_user.user_photo,
    )
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
@patch(
    "app.services.selfie_persona_service.selfie_persona_service.enqueue_selfie_persona_inference"
)
async def test_update_user_with_same_selfie_does_not_trigger_background_task(
    mock_enqueue_inference,
):
    selfie_url = "gs://test-bucket/users/same-selfie.jpg"
    user = _build_user(
        user_photo=selfie_url,
        selfie_persona_summary="Keep existing summary.",
    )
    db = _build_mock_db_for_user(user)

    with patch(
        "app.services.image_transform_service.image_transform_service.normalize_image_url_for_storage",
        side_effect=lambda x: x,
    ):
        updated_user = await update_user(
            db,
            user.id,
            UserUpdate(nickname="Updated Nickname", user_photo=selfie_url),
        )

    assert updated_user.nickname == "Updated Nickname"
    assert updated_user.selfie_persona_summary == "Keep existing summary."
    mock_enqueue_inference.assert_not_called()


@pytest.mark.asyncio
@patch(
    "app.services.selfie_persona_service.selfie_persona_service.enqueue_selfie_persona_inference"
)
async def test_update_user_feature_disabled_clears_summary_without_background_task(
    mock_enqueue_inference,
):
    user = _build_user(
        user_photo="gs://test-bucket/users/old-selfie.jpg",
        selfie_persona_summary="Old summary should be reset.",
    )
    db = _build_mock_db_for_user(user)

    with (
        patch.object(
            global_config_loaded_from_config_yaml.app.features,
            "enable_selfie_persona_summary",
            False,
        ),
        patch(
            "app.services.image_transform_service.image_transform_service.normalize_image_url_for_storage",
            side_effect=lambda x: x,
        ),
    ):
        updated_user = await update_user(
            db,
            user.id,
            UserUpdate(user_photo="gs://test-bucket/users/new-selfie.jpg"),
        )

    assert updated_user.selfie_persona_summary is None
    mock_enqueue_inference.assert_not_called()


@pytest.mark.asyncio
@patch(
    "app.services.memory_service.get_user_memory_for_prompt_async",
    new_callable=AsyncMock,
    return_value="",
)
async def test_build_user_info_prompt_block_contains_selfie_persona(
    _mock_memory,
):
    summary = "Calm and confident style with a friendly vibe."
    user = _build_user(
        user_photo="gs://test-bucket/users/selfie.jpg",
        selfie_persona_summary=summary,
    )
    db = _build_mock_db_for_user(user)

    cache_service.clear_all_caches()
    block = await build_user_info_prompt_block(db, user.id)

    assert "##User Information" in block
    assert f"Selfie Persona: {summary}" in block


@pytest.mark.asyncio
@patch(
    "app.services.memory_service.get_user_memory_for_prompt_async",
    new_callable=AsyncMock,
    return_value="",
)
async def test_build_user_info_prompt_block_hides_selfie_persona_when_disabled(
    _mock_memory,
):
    summary = "Calm and confident style with a friendly vibe."
    user = _build_user(
        user_photo="gs://test-bucket/users/selfie.jpg",
        selfie_persona_summary=summary,
    )
    db = _build_mock_db_for_user(user)

    cache_service.clear_all_caches()
    with patch.object(
        global_config_loaded_from_config_yaml.app.features,
        "enable_selfie_persona_summary",
        False,
    ):
        block = await build_user_info_prompt_block(db, user.id)

    assert "##User Information" in block
    assert "Selfie Persona:" not in block


def test_normalize_persona_summary_truncates_and_strips_prefix():
    raw = "Summary: " + ("confident and stylish " * 30)

    normalized = selfie_persona_service._normalize_persona_summary(raw)

    assert normalized is not None
    assert not normalized.lower().startswith("summary:")
    assert len(normalized) <= selfie_persona_service.MAX_SUMMARY_LENGTH + 3
