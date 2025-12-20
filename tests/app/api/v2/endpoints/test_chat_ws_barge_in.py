from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app import schemas
from app.api import deps
from app.api.v2.endpoints import chat_ws
from app.models.user import AuthType
from app.core.agent.agent import agent_manager
from app.services.realtime_chat_service import realtime_chat_service


@dataclass
class _FakeChat:
    id: str
    agent_id: str


@pytest.fixture
def ws_app(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(chat_ws.router, prefix="/api/v2")

    async def override_current_active_user_ws():
        return schemas.User(
            id="user-1",
            readable_id="readable-user-1",
            auth_type=AuthType.GOOGLE.value,
            is_active=True,
            is_superuser=False,
            created_at=datetime.now(timezone.utc),
        )

    async def override_get_async_db():
        yield None

    app.dependency_overrides[deps.get_current_active_user_ws] = (
        override_current_active_user_ws
    )
    app.dependency_overrides[deps.get_async_db] = override_get_async_db

    # Reset singleton runtime between tests
    realtime_chat_service._sessions.clear()  # type: ignore[attr-defined]

    try:
        yield app
    finally:
        realtime_chat_service._sessions.clear()  # type: ignore[attr-defined]
        app.dependency_overrides.clear()


def test_chat_ws_supports_barge_in_and_next_turn_prompt_injection(
    ws_app: FastAPI, monkeypatch: pytest.MonkeyPatch
):
    # Patch DB-dependent services
    async def fake_get_or_create_chat_by_agent(db, user_id: str, agent_id: str):
        return _FakeChat(id="chat-1", agent_id=agent_id)

    async def fake_get_or_create_chat_settings(db, chat_id: str, user_id: str, agent_id: str):
        return object()

    async def fake_check_chat_limit(db, user):
        return True, 0, 999

    def fake_add_user_message(session_id: str, message: str):
        return None

    async def fake_add_ai_message(db, session_id: str, message: str, agent_id: str = None, meta_data=None, audio_duration=None):
        return 123

    async def fake_get_agent_for_chat(db, agent_id: str):
        return {"id": agent_id, "name": "Agent"}

    seen_interruption_prompts: list[str | None] = []

    class FakeAgent:
        async def chat_stream(self, **kwargs):
            seen_interruption_prompts.append(kwargs.get("interruption_prompt"))
            for ch in ["你", "好", "呀", "，", "我"]:
                await asyncio.sleep(0.03)
                yield AIMessage(content=ch), {}
            return

    async def fake_get_agent(agent_data: dict):
        return FakeAgent()

    monkeypatch.setattr(
        "app.services.chat_service.get_or_create_chat_by_agent",
        fake_get_or_create_chat_by_agent,
    )
    monkeypatch.setattr(
        "app.services.chat_service.get_or_create_chat_settings",
        fake_get_or_create_chat_settings,
    )
    monkeypatch.setattr(
        "app.services.global_services.subscription_service.check_chat_limit",
        fake_check_chat_limit,
    )
    monkeypatch.setattr(
        "app.services.chat_history_service.add_user_message",
        fake_add_user_message,
    )
    monkeypatch.setattr(
        "app.services.chat_history_service.add_ai_message",
        fake_add_ai_message,
    )
    monkeypatch.setattr(
        "app.services.agent_service.get_agent_for_chat",
        fake_get_agent_for_chat,
    )
    monkeypatch.setattr(agent_manager, "get_agent", fake_get_agent)

    with TestClient(ws_app) as client:
        with client.websocket_connect("/api/v2/chat/ws/agent-1") as ws:
            connected = ws.receive_json()
            assert connected["type"] == "connected"

            ws.send_json({"type": "user_message", "message": "hi"})
            msg = ws.receive_json()
            assert msg["type"] == "ack"
            assert msg["event"] == "user_message"

            # Receive at least one delta, then barge-in
            delta = ws.receive_json()
            assert delta["type"] == "assistant_delta"

            ws.send_json({"type": "barge_in"})
            interrupted = ws.receive_json()
            assert interrupted["type"] == "assistant_interrupted"

            ws.send_json({"type": "user_message", "message": "new topic"})
            msg2 = ws.receive_json()
            assert msg2["type"] == "ack"

            # Drain until assistant_end
            while True:
                e = ws.receive_json()
                if e["type"] == "assistant_end":
                    break

    # First turn has no interruption prompt, second turn should.
    assert seen_interruption_prompts[0] is None
    assert any(p is not None for p in seen_interruption_prompts[1:])

