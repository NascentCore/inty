"""Tests for iLink session-expired teardown scheduling in Weixin transport."""

from __future__ import annotations

import asyncio

import pytest

from backend.ops.weixin_channel.transport import (
    register_ilink_session_expired_handler,
    schedule_ilink_session_expired_teardown,
    unregister_ilink_session_expired_handler,
)


@pytest.mark.asyncio
async def test_schedule_ilink_session_expired_teardown_runs_once() -> None:
    call_count = 0
    done = asyncio.Event()

    async def handler() -> None:
        nonlocal call_count
        call_count += 1
        done.set()

    account_id = "wx-acct-teardown-once"
    register_ilink_session_expired_handler(account_id, handler)
    try:
        schedule_ilink_session_expired_teardown(account_id)
        schedule_ilink_session_expired_teardown(account_id)
        await asyncio.wait_for(done.wait(), timeout=2.0)
        await asyncio.sleep(0.05)
        assert call_count == 1
    finally:
        unregister_ilink_session_expired_handler(account_id)
