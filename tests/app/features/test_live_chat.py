"""
实时语音通话端点测试

CREATED_BY_AGENT
"""

import contextlib
import json
import os

import pytest
from fastapi.testclient import TestClient as FastAPITestClient
from starlette.websockets import WebSocketDisconnect

from app.api import deps
from app.db.session import get_async_db
from backend.inty.main import app
from tests.app.api.test_client import TestClient
from tests.app.api.v1.endpoints.conftest import _create_mock_db_session, _make_user

API_BASE_URL = os.getenv("INTY_API_BASE_URL", "http://localhost:8000")


@contextlib.contextmanager
def _live_chat_status_client_with_auth():
    async def override_get_current_user():
        return _make_user()

    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    try:
        with FastAPITestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(deps.get_current_user, None)


class TestLiveChatStatus:
    """测试实时语音通话状态接口（进程内 ASGI，不依赖已启动的 localhost:8000）"""

    def test_get_live_chat_status(self):
        with _live_chat_status_client_with_auth() as client:
            response = client.get("/api/v1/live-chat/status")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data

        status_data = data["data"]
        assert "enabled" in status_data
        assert "model" in status_data
        assert "default_voice" in status_data
        assert "send_sample_rate" in status_data
        assert "receive_sample_rate" in status_data
        assert "default_speech_language_code" in status_data
        assert "default_response_language_name" in status_data

    def test_get_live_chat_status_without_auth(self):
        with FastAPITestClient(app) as client:
            response = client.get("/api/v1/live-chat/status")
        assert response.status_code == 401


class TestLiveChatWebSocket:
    """测试实时语音通话 WebSocket 端点

    注意：完整的 WebSocket 测试需要实际的 Gemini Live API 连接，
    这里仅测试基本的连接验证逻辑。
    """

    def test_unauthorized_rejection_does_not_raise_asgi_mismatch(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Invalid token: reject during handshake (WebSocket close), not HTTP/WS ASGI state bug."""

        async def _mock_get_user_from_token(*_args, **_kwargs):
            return None

        monkeypatch.setattr(deps, "get_user_from_token", _mock_get_user_from_token)

        async def _override_get_async_db():
            db = _create_mock_db_session()
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_async_db] = _override_get_async_db
        try:
            with FastAPITestClient(app) as client:
                with pytest.raises(WebSocketDisconnect) as exc:
                    with client.websocket_connect(
                        "/api/v1/live-chat/test-agent?token=invalid"
                    ):
                        pass
        finally:
            app.dependency_overrides.pop(get_async_db, None)

        assert exc.value.code == 4001
        assert exc.value.reason == "Unauthorized"

    @pytest.mark.skip(reason="需要 websocket-client 包和运行中的服务器")
    def test_websocket_without_token(self):
        """测试无 token 时 WebSocket 连接被拒绝"""
        import websocket

        ws_url = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/api/v1/live-chat/test-agent-id"

        try:
            ws = websocket.create_connection(ws_url, timeout=5)
            ws.close()
            pytest.fail("Expected WebSocket connection to be rejected")
        except websocket.WebSocketBadStatusException as e:
            assert e.status_code == 4001
        except Exception:
            pass

    @pytest.mark.skip(reason="需要 websocket-client 包和运行中的服务器")
    def test_websocket_with_invalid_token(self):
        """测试无效 token 时 WebSocket 连接被拒绝"""
        import websocket

        ws_url = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/api/v1/live-chat/test-agent-id?token=invalid_token"

        try:
            ws = websocket.create_connection(ws_url, timeout=5)
            ws.close()
            pytest.fail("Expected WebSocket connection to be rejected")
        except websocket.WebSocketBadStatusException as e:
            assert e.status_code == 4001
        except Exception:
            pass

    @pytest.mark.skip(
        reason="需要有效的 Gemini Live API 配置才能运行完整 WebSocket 测试"
    )
    def test_websocket_connection_with_valid_token(
        self, integration_client: TestClient
    ):
        """测试有效 token 时 WebSocket 连接成功

        此测试需要：
        1. 有效的 Gemini Live API 配置
        2. 有效的 Agent ID
        3. gemini_live.enabled = true
        """
        import websocket

        ws_url = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")

        agents_response = integration_client.get("/api/v1/agents/")
        agents = agents_response.json().get("data", [])
        if not agents:
            pytest.skip("No agents available for testing")

        agent_id = agents[0]["id"]
        token = integration_client.token
        ws_url = f"{ws_url}/api/v1/live-chat/{agent_id}?token={token}"

        ws = websocket.create_connection(ws_url, timeout=10)

        try:
            message = ws.recv()
            data = json.loads(message)
            assert data["type"] in ["status", "error"]
        finally:
            ws.close()
