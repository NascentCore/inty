"""Regression: Google Play RTDN background task must not reuse the request-scoped DB session."""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints import subscription as subscription_endpoint


@pytest.mark.asyncio
async def test_process_google_play_notification_uses_fresh_session():
    inner = {"subscriptionNotification": {"purchaseToken": "tok", "notificationType": 4}}
    payload = {"message": {"data": base64.b64encode(json.dumps(inner).encode()).decode()}}

    fake_session = MagicMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = fake_session
    session_cm.__aexit__.return_value = None

    with patch.object(
        subscription_endpoint,
        "AsyncSessionLocal",
        return_value=session_cm,
    ):
        with patch.object(
            subscription_endpoint.subscription_service,
            "handle_subscription_notification",
            new_callable=AsyncMock,
            return_value=True,
        ) as handle:
            await subscription_endpoint._process_google_play_notification(payload)

    session_cm.__aenter__.assert_awaited_once()
    handle.assert_awaited_once()
    assert handle.await_args[0][0] is fake_session
    assert handle.await_args[0][1] == inner
