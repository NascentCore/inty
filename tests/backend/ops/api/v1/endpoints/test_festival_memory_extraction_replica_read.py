from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.ops.schemas.festival_memory import FestivalMemoryExtractionRunRequest
from backend.ops.api.v1 import festival_memory as festival_memory_endpoint


@pytest.mark.asyncio
async def test_manual_festival_memory_extraction_uses_replica_read_path():
    body = FestivalMemoryExtractionRunRequest(
        festival_name="Valentine",
        festival_date=date(2026, 2, 14),
        prompt="Extract festival memories.",
        timezone="UTC",
        min_rounds_in_window=8,
    )
    db = AsyncMock()
    current_user = SimpleNamespace(is_superuser=True)
    mock_to_thread = AsyncMock(return_value=[("user-1", "agent-1"), ("user-2", "agent-2")])
    mock_extract = AsyncMock(side_effect=[True, False])

    with (
        patch.object(
            festival_memory_endpoint.festival_memory_service,
            "resolve_sync_read_db_url",
            return_value="postgresql://replica-host:5432/inty",
        ) as mock_resolve_read_url,
        patch.object(festival_memory_endpoint.asyncio, "to_thread", mock_to_thread),
        patch.object(
            festival_memory_endpoint.festival_memory_service,
            "extract_festival_and_save",
            mock_extract,
        ),
    ):
        resp = await festival_memory_endpoint.run_festival_memory_extraction(
            body=body,
            db=db,
            current_user=current_user,
        )

    mock_resolve_read_url.assert_called_once_with(prefer_replica_read=True)
    assert mock_to_thread.await_count == 1
    to_thread_args = mock_to_thread.await_args.args
    assert (
        to_thread_args[0]
        is festival_memory_endpoint.festival_memory_service.get_pairs_with_min_rounds_in_window_sync
    )
    assert to_thread_args[2] == "postgresql://replica-host:5432/inty"
    assert mock_extract.await_count == 2
    assert mock_extract.await_args_list[0].kwargs["prefer_replica_read"] is True
    assert mock_extract.await_args_list[1].kwargs["prefer_replica_read"] is True
    assert resp.data.total_pairs == 2
    assert resp.data.success_count == 1
    assert resp.data.failed_count == 1
