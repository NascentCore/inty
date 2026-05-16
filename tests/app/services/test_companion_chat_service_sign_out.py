"""Regression tests for companion scope reset on ``user_signed_out``."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services import chat_history_service, chat_service
from app.services import companion_chat_service
from app.utils.models_catalog import DEEPSEEK_V3_2


@pytest.mark.asyncio
async def test_conclude_companion_scope_on_user_signed_out_order_and_session_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``shutdown_session`` → delete memory rows → ``clear_session_async`` → append CHAT_LOGS."""
    calls: list[str] = []
    fake_mgr = MagicMock()

    def shutdown_session(user_id: str, companion_id: str, chat_id: str) -> None:
        calls.append(f"shutdown:{user_id}:{companion_id}:{chat_id}")

    fake_mgr.shutdown_session.side_effect = shutdown_session

    def get_or_create_session(user_id: str, companion_id: str, chat_id: str) -> MagicMock:
        calls.append(f"get_or_create:{user_id}:{companion_id}:{chat_id}")
        sess = MagicMock()
        sess.store = MagicMock()

        def append_line(path: str, line: str) -> None:
            calls.append(f"append_line:{path}:{line[:24]}")

        sess.store.append_line.side_effect = append_line
        return sess

    fake_mgr.get_or_create_session.side_effect = get_or_create_session

    monkeypatch.setattr(
        companion_chat_service,
        "_companion_manager_for_resolved_model",
        lambda _chat_id, _tool_id, _fp: fake_mgr,
    )

    async def fake_delete(**kwargs: object) -> int:
        calls.append(
            "delete_mem:"
            f"{kwargs['user_id']}:{kwargs['companion_id']}:{kwargs['chat_id']}"
        )
        return 2

    monkeypatch.setattr(
        companion_chat_service,
        "delete_companion_memory_document_versions_for_scope_async",
        fake_delete,
    )

    cleared: list[str] = []

    async def fake_clear(session_id: str) -> None:
        cleared.append(session_id)
        calls.append(f"clear_history:{session_id}")

    monkeypatch.setattr(chat_history_service, "clear_session_async", fake_clear)

    log_line = "- **user_signed_out** `utc_ts=test`"
    await companion_chat_service.conclude_companion_scope_on_user_signed_out(
        user_id="u1",
        agent_id="a1",
        chat_id=99,
        resolved_chat_model=DEEPSEEK_V3_2,
        log_line=log_line,
    )

    assert cleared == [chat_service.generate_session_id("99")]

    assert calls[0] == "shutdown:u1:a1:99"
    assert calls[1] == "delete_mem:u1:a1:99"
    assert calls[2] == f"clear_history:{cleared[0]}"
    assert calls[3] == "get_or_create:u1:a1:99"
    assert calls[4].startswith("append_line:CHAT_LOGS.md:")
