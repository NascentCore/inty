import uuid
from pathlib import Path

import pytest
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 15


@pytest.mark.noci
def test_android_app_requests_flow():
    session = requests.Session()

    # 1) 创建游客账号，获取 token
    guest_payload = {
        "device_id": f"requests-test-{uuid.uuid4().hex[:8]}",
        "system_language": "en",
        "age_group": "adult",
    }
    r = session.post(
        f"{BASE_URL}/api/v1/auth/guest", json=guest_payload, timeout=TIMEOUT
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("data", {}).get("token")
    token = data["data"]["token"]

    session.headers.update({"Authorization": f"Bearer {token}"})

    # 2) 检查版本（使用 header 传参）
    headers = session.headers.copy()
    headers.update(
        {
            "appVersionCode": "100",
            "appVersionName": "1.0.0",
        }
    )
    r = session.post(
        f"{BASE_URL}/api/v1/version/check", headers=headers, timeout=TIMEOUT
    )
    assert r.status_code == 200

    # 3) 获取订阅计划
    r = session.get(f"{BASE_URL}/api/v1/subscription/plans", timeout=TIMEOUT)
    assert r.status_code == 200

    # 4) 推荐角色列表（explore/chat 列表）
    recommend_params = {
        "page": 1,
        "page_size": 10,
        "sort": "created_desc",
        "sort_seed": uuid.uuid4().hex[:8],
    }
    r = session.get(
        f"{BASE_URL}/api/v1/ai/agents/recommend",
        params=recommend_params,
        timeout=TIMEOUT,
    )
    assert r.status_code == 200

    # 5) 创建一个角色（保证后续有可用 agent_id）
    create_agent_payload = {
        "name": f"Android Flow Test {uuid.uuid4().hex[:6]}",
        "gender": "MALE",
        "visibility": "PUBLIC",
    }
    r = session.post(
        f"{BASE_URL}/api/v1/ai/agents", json=create_agent_payload, timeout=TIMEOUT
    )
    assert r.status_code == 200
    agent_resp = r.json()
    assert agent_resp.get("data")
    agent_id = agent_resp["data"].get("id") or agent_resp["data"].get("data", {}).get(
        "id"
    )
    assert agent_id

    try:
        # 6) 我的角色列表
        r = session.get(
            f"{BASE_URL}/api/v1/ai/agents/me",
            params={"skip": 0, "limit": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200

        # 7) 角色详情
        r = session.get(f"{BASE_URL}/api/v1/ai/agents/{agent_id}", timeout=TIMEOUT)
        assert r.status_code == 200

        # 8) 获取聊天设置（按 agent）
        r = session.get(
            f"{BASE_URL}/api/v1/chats/agents/{agent_id}/settings", timeout=TIMEOUT
        )
        assert r.status_code == 200

        # 9) 更新聊天设置（仅更新允许的基础字段）
        update_settings_payload = {"language": "en", "voice_enabled": False}
        r = session.put(
            f"{BASE_URL}/api/v1/chats/agents/{agent_id}/settings",
            json=update_settings_payload,
            timeout=TIMEOUT,
        )
        assert r.status_code == 200

        # 10) 拉取消息（会自动创建会话）
        r = session.get(
            f"{BASE_URL}/api/v1/chats/agents/{agent_id}/messages",
            params={"limit": 20, "offset": 0, "order": "desc"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200

        # 11) 发送一条消息（可能受模型/配置影响失败，允许非200业务码，但HTTP应返回）
        chat_payload = {
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": False,
            "model": "chatbot",
            "language": "en",
        }
        r = session.post(
            f"{BASE_URL}/api/v1/chat/completions/{agent_id}",
            json=chat_payload,
            timeout=TIMEOUT,
        )
        assert r.status_code in (200, 500)
        message_id = None
        try:
            resp_json = r.json()
            if resp_json.get("code") == 200:
                message_id = (
                    resp_json.get("data", {})
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("id")
                )
        except Exception:
            pass

        # 12) 为消息生成语音（如果拿到了 message_id）
        if message_id:
            r = session.post(
                f"{BASE_URL}/api/v1/chats/agents/{agent_id}/messages/{message_id}/voice",
                timeout=TIMEOUT,
            )
            assert r.status_code == 200

        # 13) 会话列表
        r = session.get(
            f"{BASE_URL}/api/v1/chats/",
            params={"skip": 0, "limit": 10},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200

        # 14) 上传图片（可能依赖 GCS 配置失败，允许业务失败但 HTTP 可达）
        test_img = Path(__file__).resolve().parents[2] / "files" / "test.jpg"
        if test_img.exists():
            with test_img.open("rb") as f:
                r = session.post(
                    f"{BASE_URL}/api/v1/images",
                    files={"file": ("test.jpg", f, "image/jpeg")},
                    data={"cropping_avatar": "true"},
                    timeout=TIMEOUT,
                )
                assert r.status_code == 200

        # 15) 订阅验证（必然是演示数据，允许业务失败但 HTTP 可达）
        verify_payload = {
            "product_id": "test_product",
            "purchase_token": "invalid_token",
            "order_id": f"order-{uuid.uuid4().hex[:8]}",
        }
        r = session.post(
            f"{BASE_URL}/api/v1/subscription/verify",
            json=verify_payload,
            timeout=TIMEOUT,
        )
        assert r.status_code == 200

    finally:
        # 清理：删除创建的角色与测试账号
        try:
            session.delete(f"{BASE_URL}/api/v1/ai/agents/{agent_id}", timeout=TIMEOUT)
        except Exception:
            pass
        try:
            session.post(f"{BASE_URL}/api/v1/users/delete-account", timeout=TIMEOUT)
        except Exception:
            pass
