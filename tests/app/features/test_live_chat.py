"""
实时语音通话端点测试

CREATED_BY_AGENT
"""

import os

import httpx
import pytest

from tests.app.api.test_client import TestClient

API_BASE_URL = os.getenv("INTY_API_BASE_URL", "http://localhost:8000")


@pytest.fixture
def integration_client():
    client = TestClient(API_BASE_URL)
    client.create_user()
    try:
        yield client
    finally:
        client.delete_user()
        client.close()


class TestLiveChatStatus:
    """测试实时语音通话状态接口"""

    def test_get_live_chat_status(self, integration_client: TestClient):
        """测试获取实时语音通话服务状态"""
        response = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/live-chat/status"
        )

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
        """测试未认证时获取状态"""
        with httpx.Client() as client:
            response = client.get(f"{API_BASE_URL}/api/v1/live-chat/status")
            assert response.status_code == 401


class TestLiveChatWebSocket:
    """测试实时语音通话 WebSocket 端点

    注意：完整的 WebSocket 测试需要实际的 Gemini Live API 连接，
    这里仅测试基本的连接验证逻辑。
    """

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
        import json

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
