# Version code gating for festival memory system notification (FCM).
# Tests _user_satisfies_festival_memory_version_gate and its use in process_festival_memory_push_batch.

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.push_notification_service import (
    _user_satisfies_festival_memory_version_gate,
    process_festival_memory_push_batch,
)

# Min version used in "at min" / "below min" tests; matches config under patch.
MIN_VERSION_FOR_TESTS = 100


def _make_result_mock(scalar_value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_value
    return result


@pytest.mark.asyncio
async def test_user_satisfies_festival_memory_version_gate_null():
    """When user has no reported version (NULL), gate fails."""
    with patch(
        "app.services.push_notification_service.is_festival_memory_enabled"
    ) as mock_enabled:
        mock_enabled.return_value = False
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_make_result_mock(None))
        out = await _user_satisfies_festival_memory_version_gate(db, "user-1")
    assert out is False
    mock_enabled.assert_called_once_with(None)


@pytest.mark.asyncio
async def test_user_satisfies_festival_memory_version_gate_below_min():
    """When user version is below min_app_version_code_for_festival_memory, gate fails."""
    with patch(
        "app.services.push_notification_service.is_festival_memory_enabled"
    ) as mock_enabled:
        mock_enabled.return_value = False
        db = AsyncMock()
        db.execute = AsyncMock(
            return_value=_make_result_mock(MIN_VERSION_FOR_TESTS - 50)
        )
        out = await _user_satisfies_festival_memory_version_gate(db, "user-1")
    assert out is False
    mock_enabled.assert_called_once_with(MIN_VERSION_FOR_TESTS - 50)


@pytest.mark.asyncio
async def test_user_satisfies_festival_memory_version_gate_at_min():
    """When user version equals min, gate passes."""
    with patch(
        "app.services.push_notification_service.is_festival_memory_enabled"
    ) as mock_enabled:
        mock_enabled.return_value = True
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_make_result_mock(MIN_VERSION_FOR_TESTS))
        out = await _user_satisfies_festival_memory_version_gate(db, "user-1")
    assert out is True
    mock_enabled.assert_called_once_with(MIN_VERSION_FOR_TESTS)


@pytest.mark.asyncio
async def test_user_satisfies_festival_memory_version_gate_above_min():
    """When user version is above min, gate passes."""
    with patch(
        "app.services.push_notification_service.is_festival_memory_enabled"
    ) as mock_enabled:
        mock_enabled.return_value = True
        db = AsyncMock()
        db.execute = AsyncMock(
            return_value=_make_result_mock(MIN_VERSION_FOR_TESTS + 100)
        )
        out = await _user_satisfies_festival_memory_version_gate(db, "user-1")
    assert out is True
    mock_enabled.assert_called_once_with(MIN_VERSION_FOR_TESTS + 100)


@pytest.mark.asyncio
async def test_user_satisfies_festival_memory_version_gate_with_real_config():
    """Gate uses real is_festival_memory_enabled; only config min is patched."""
    fake_config = MagicMock()
    fake_config.app.min_app_version_code_for_festival_memory = MIN_VERSION_FOR_TESTS
    # Patch where the name is used (feature_gating), not the source (app.core.config),
    # so the already-imported reference in is_festival_memory_enabled gets the fake.
    with patch(
        "app.api.utils.feature_gating.global_config_loaded_from_config_yaml",
        fake_config,
    ):
        db = AsyncMock()
        db.execute = AsyncMock(
            return_value=_make_result_mock(MIN_VERSION_FOR_TESTS - 1)
        )
        out_below = await _user_satisfies_festival_memory_version_gate(db, "user-1")
        db.execute = AsyncMock(return_value=_make_result_mock(MIN_VERSION_FOR_TESTS))
        out_at = await _user_satisfies_festival_memory_version_gate(db, "user-1")
    assert out_below is False
    assert out_at is True


@pytest.mark.asyncio
async def test_process_festival_memory_push_batch_skips_when_version_gate_fails():
    """When version gate returns False, festival push is not sent for that user."""
    db = AsyncMock()
    pairs = [{"user_id": "u1", "agent_id": "a1", "festival_memory_id": 1}]

    with (
        patch(
            "app.services.push_notification_service.get_pairs_with_undelivered_festival_memories",
            new_callable=AsyncMock,
            return_value=pairs,
        ),
        patch(
            "app.services.push_notification_service._check_user_has_device_token",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.services.push_notification_service._user_satisfies_festival_memory_version_gate",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.services.push_notification_service.send_festival_memory_push",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        success_count, fail_count = await process_festival_memory_push_batch(
            db, batch_size=50
        )
    assert success_count == 0
    assert fail_count == 1
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_process_festival_memory_push_batch_proceeds_when_version_gate_passes():
    """When version gate returns True and other conditions met, festival push is sent."""
    db = AsyncMock()
    pairs = [{"user_id": "u1", "agent_id": "a1", "festival_memory_id": 1}]
    agent_data = {"name": "Agent", "avatar_url": "https://example.com/avatar.png"}

    with (
        patch(
            "app.services.push_notification_service.get_pairs_with_undelivered_festival_memories",
            new_callable=AsyncMock,
            return_value=pairs,
        ),
        patch(
            "app.services.push_notification_service._check_user_has_device_token",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.services.push_notification_service._user_satisfies_festival_memory_version_gate",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.services.push_notification_service.has_sent_festival_push_for_user_agent",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.services.push_notification_service.agent_service",
        ) as mock_agent_svc,
        patch(
            "app.services.push_notification_service._extract_agent_info",
            new_callable=AsyncMock,
            return_value=("Agent", "https://example.com/avatar.png"),
        ),
        patch(
            "app.services.push_notification_service.send_festival_memory_push",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send,
        patch(
            "app.services.push_notification_service.record_push_history",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.push_notification_service.mark_system_notification_sent_for_user_agent",
            new_callable=AsyncMock,
        ),
    ):
        mock_agent_svc.get_agent_for_chat = AsyncMock(return_value=agent_data)
        success_count, fail_count = await process_festival_memory_push_batch(
            db, batch_size=50
        )
    assert success_count == 1
    assert fail_count == 0
    mock_send.assert_called_once()
