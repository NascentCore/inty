import uuid

import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps
from app.api.v1.endpoints import agents as agents_v1
from app.core.config import global_config_loaded_from_config_yaml
from app.core.security import create_access_token
from app.core.uuid import get_new_user_id
from app.models.agent import Agent
from app.models.resource import Resource, ResourceType
from app.models.subscription import SubscriptionUsage
from app.models.user import AuthType, Gender, User
from app.schemas.response import BusinessErrorCode
from app.services.user_service import generate_next_readable_id_sync
from app.services.global_services import subscription_service
from tests.app.api.test_client import TestClient
from tests.app.api.v1.endpoints.conftest import (
    _client_with_user,
    _create_mock_db_session,
    _make_user,
)


def test_chat_completions_endpoint(integration_client: TestClient):
    agent_id = integration_client.create_agent()

    response = integration_client.chat_completions(
        agent_id,
        messages=[
            {"role": "user", "content": "Tell me a fun fact about penguins."}
        ],
        language="en",
    )

    assert response["code"] == 200
    data = response["data"]
    assert data["model"] == "chatbot"
    assert isinstance(data["created"], int)

    choices = data["choices"]
    assert isinstance(choices, list) and choices

    message = choices[0]["message"]
    assert message["role"] == "assistant"
    assert isinstance(message["content"], str)
    assert message["content"].strip()

    usage = data["usage"]
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]


@pytest.fixture
def db_session():
    """提供数据库会话用于测试"""
    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def agents_business_error_app() -> FastAPI:
    app = FastAPI()
    app.include_router(agents_v1.router, prefix="/api/v1")

    async def override_db():
        mock_db = _create_mock_db_session()
        yield mock_db

    app.dependency_overrides[deps.get_async_db] = override_db

    yield app

    app.dependency_overrides.clear()


def test_create_agent_limit_returns_business_error(
    monkeypatch: pytest.MonkeyPatch, agents_business_error_app: FastAPI
):
    async def fake_check_agent_creation_limit(db, current_user):
        return False, 6, 6

    monkeypatch.setattr(
        subscription_service,
        "check_agent_creation_limit",
        fake_check_agent_creation_limit,
    )

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(agents_business_error_app, user) as client:
        response = client.post(
            "/api/v1/ai/agents",
            json={"name": "Test Agent", "gender": "FEMALE", "visibility": "PUBLIC"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.AGENT_CREATION_LIMIT_REACHED["code"]
    assert body["message"] == BusinessErrorCode.AGENT_CREATION_LIMIT_REACHED["message"]
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.AGENT_CREATION_LIMIT_REACHED["error_code"]
    )
    assert body["data"]["used_count"] == 6
    assert body["data"]["limit"] == 6
    assert body["data"]["feature"] == "agent_creation"


def test_text_to_image_limit_returns_business_error(
    monkeypatch: pytest.MonkeyPatch, agents_business_error_app: FastAPI
):
    async def fake_check_image_gen_limit(db, current_user):
        return False, 3, 3

    monkeypatch.setattr(
        subscription_service,
        "check_image_gen_limit",
        fake_check_image_gen_limit,
    )

    user = _make_user(auth_type=AuthType.GOOGLE)

    with _client_with_user(agents_business_error_app, user) as client:
        response = client.post(
            "/api/v1/ai/agents/text-to-image",
            json={"prompt": "generate image", "count": 1},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["code"] == BusinessErrorCode.IMAGE_GENERATION_LIMIT_REACHED["code"]
    assert (
        body["message"] == BusinessErrorCode.IMAGE_GENERATION_LIMIT_REACHED["message"]
    )
    assert (
        body["data"]["error_code"]
        == BusinessErrorCode.IMAGE_GENERATION_LIMIT_REACHED["error_code"]
    )
    assert body["data"]["used_count"] == 3
    assert body["data"]["limit"] == 3
    assert body["data"]["feature"] == "background_generation"


def test_text_to_image_endpoint(integration_client: TestClient, db_session):
    """测试图片生成功能，使用正式用户（非 guest）"""
    # 创建正式用户（EMAIL 类型）用于测试图片生成
    user_id = get_new_user_id()
    readable_id = generate_next_readable_id_sync(db_session)
    test_email = f"test-image-{uuid.uuid4().hex[:8]}@example.com"

    # 检查用户是否已存在
    existing_user = db_session.query(User).filter(User.email == test_email).first()
    if existing_user:
        # 如果用户已存在，使用现有用户
        user = existing_user
        is_new_user = False
    else:
        # 创建新用户
        user = User(
            id=user_id,
            gender=Gender.FEMALE,
            readable_id=readable_id,
            auth_type=AuthType.EMAIL,
            email=test_email,
            nickname=f"Test Image User {uuid.uuid4().hex[:6]}",
            system_language="en",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        is_new_user = True

    # 生成 token 并设置到 TestClient
    token = create_access_token(user.id)
    integration_client.token = token
    integration_client.client.headers.update({"Authorization": f"Bearer {token}"})

    try:
        image_urls = integration_client.text_to_image(
            "A warm portrait of a friendly companion, soft lighting, vivid colors",
            count=1,
        )

        assert image_urls
        assert all(url.startswith("http") for url in image_urls)
    finally:
        # 清理：删除测试用户（如果是我们创建的）
        if is_new_user:
            # 先删除用户创建的 agents
            agents = db_session.query(Agent).filter(Agent.creator_id == user.id).all()
            for agent in agents:
                db_session.delete(agent)

            # 删除用户的 subscription_usage 记录
            usage_records = (
                db_session.query(SubscriptionUsage)
                .filter(SubscriptionUsage.user_id == user.id)
                .all()
            )
            for usage in usage_records:
                db_session.delete(usage)

            db_session.commit()

            # 然后删除用户
            db_session.delete(user)
            db_session.commit()


@pytest.mark.parametrize("background", ["", None])
def test_create_agent_with_empty_background(
    integration_client: TestClient, background: str
):

    # 测试数据：background 为空字符串
    agent_data = {
        "name": "Test Agent Empty Background",
        "gender": "FEMALE",
        "visibility": "PRIVATE",
        "personality": "一个友好的测试角色",
        "scenario": "用于测试空背景字段的场景",
        "intro": "这是一个测试角色",
        "opening": "你好！我是用来测试空背景的角色。",
        "background": background,
    }

    # 发送创建请求
    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/ai/agents",
        json=agent_data,
        headers={"Authorization": f"Bearer {integration_client.token}"},
    )

    # 验证响应
    assert response.status_code == 200, f"Request failed: {response.text}"

    response_data = response.json()
    assert response_data.get("code") == 200, f"API error: {response_data}"

    # 验证创建的 agent 数据
    agent = response_data["data"]
    assert agent["name"] == agent_data["name"]
    assert agent["gender"] == agent_data["gender"]
    assert agent["visibility"] == agent_data["visibility"]
    assert agent["personality"] == agent_data["personality"]
    assert agent["scenario"] == agent_data["scenario"]

    # 关键验证：background 为空字符串时的实际行为
    # 由于 process_agent_image_urls 中的条件 `if processed_data.get("background"):`
    # 对空字符串返回 False，验证代码块被跳过，空字符串被保留
    assert (
        agent["background"] == background
    ), f"Expected background to be {background}, but got: {agent['background']}"

    # 验证 agent 有唯一 ID
    assert agent["id"]
    assert agent["readable_id"]

    # 清理：删除创建的 agent
    integration_client.delete_agent(agent["id"])


@pytest.fixture
def db_session():
    """提供数据库会话用于测试"""
    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_recommend_agents_energy_points_sorting(
    integration_client: TestClient, db_session
):
    """测试按 energy_points 排序推荐角色列表"""
    agent_ids = []
    points_values = [100, 50, 200, 0, 150]  # 降序应该是: 200, 150, 100, 50, 0

    for i, points in enumerate(points_values):
        agent_id = integration_client.create_agent(
            name=f"Test Agent Points {points}",
            visibility="PUBLIC",
        )
        agent_ids.append(agent_id)

        agent = db_session.query(Agent).filter(Agent.id == agent_id).first()
        assert agent is not None, f"Agent {agent_id} not found in database"
        agent.points = points
        db_session.commit()

    try:
        response = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/ai/agents/recommend",
            params={
                "page": 1,
                "page_size": 10,
                "sort": "energy_points",
            },
        )
        assert response.status_code == 200, f"Request failed: {response.text}"
        response_data = response.json()
        assert response_data.get("code") == 200, f"API error: {response_data}"

        data = response_data["data"]
        assert "list" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

        items = data["list"]
        assert isinstance(items, list)
        assert all("energy_points" in item for item in items)

        our_agents = [item for item in items if item["id"] in agent_ids]
        expected_points_map = dict(zip(agent_ids, points_values))

        for agent in our_agents:
            assert (
                agent["energy_points"] == expected_points_map[agent["id"]]
            ), "API energy_points should match database values"

        if len(our_agents) >= 2:
            energy_values = [agent["energy_points"] for agent in our_agents]
            assert energy_values == sorted(
                energy_values, reverse=True
            ), f"Agents should be sorted by energy_points desc, got {energy_values}"

        response_page2 = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/ai/agents/recommend",
            params={
                "page": 2,
                "page_size": 3,
                "sort": "energy_points",
            },
        )

        assert (
            response_page2.status_code == 200
        ), f"Page 2 request failed: {response_page2.text}"
        page2_data = response_page2.json()
        assert page2_data.get("code") == 200, f"Page 2 API error: {page2_data}"

        page2_items = page2_data["data"]["list"]
        assert (
            len(page2_items) <= 3
        ), f"Page 2 should have at most 3 items, got {len(page2_items)}"
        assert (
            page2_data["data"]["page"] == 2
        ), f"Page number should be 2, got {page2_data['data']['page']}"

    finally:
        for agent_id in agent_ids:
            integration_client.delete_agent(agent_id)


def test_recommend_agents_text_match_requires_match_description(
    integration_client: TestClient,
):
    """sort=text_match_image_description without match_description returns 400."""
    response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/ai/agents/recommend",
        params={
            "page": 1,
            "page_size": 10,
            "sort": "text_match_image_description",
        },
    )
    assert response.status_code == 400, response.text


def test_recommend_agents_text_match_ranks_exclusive_caption(
    integration_client: TestClient, db_session
):
    """Exclusive photo caption is matched; matched_image_items ordered by similarity."""
    me_resp = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/users/me",
    )
    assert me_resp.status_code == 200, me_resp.text
    user_id = me_resp.json()["data"]["id"]
    db_user = db_session.query(User).filter(User.id == user_id).first()
    assert db_user is not None
    was_super = db_user.is_superuser
    db_user.is_superuser = True
    db_session.commit()

    unique_caption = f"e2e_match_caption_{uuid.uuid4().hex[:12]}"
    agent_id = integration_client.create_agent(
        name=f"Text Match Agent {uuid.uuid4().hex[:6]}",
        visibility="PUBLIC",
    )
    try:
        agent = db_session.query(Agent).filter(Agent.id == agent_id).first()
        assert agent is not None
        agent.exclusive_photos = [
            {
                "image_url": "https://example.com/exclusive-placeholder.jpg",
                "caption": unique_caption,
                "credits_required": 0,
            }
        ]
        db_session.commit()

        response = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/ai/agents/recommend",
            params={
                "page": 1,
                "page_size": 10,
                "sort": "text_match_image_description",
                "match_description": unique_caption,
                "match_top_n": 20,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload.get("code") == 200, payload
        data = payload["data"]
        items = data.get("matched_image_items") or []
        assert items, "expected matched_image_items"
        first = items[0]
        assert first["agent_id"] == agent_id
        assert first["image_description"] == unique_caption
        assert first["similarity_score"] >= 99.0
        agent_list = data.get("list") or []
        assert any(a["id"] == agent_id for a in agent_list)
    finally:
        integration_client.delete_agent(agent_id)
        db_user.is_superuser = was_super
        db_session.commit()


def test_recommend_agents_text_match_finds_prompt_when_agent_url_differs_from_resource_pk(
    integration_client: TestClient, db_session
):
    """Resource row keyed by CDN url but metadata.gcs_url matches agent.background."""
    me_resp = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/users/me",
    )
    assert me_resp.status_code == 200, me_resp.text
    user_id = me_resp.json()["data"]["id"]
    db_user = db_session.query(User).filter(User.id == user_id).first()
    assert db_user is not None
    was_super = db_user.is_superuser
    db_user.is_superuser = True
    db_session.commit()

    suffix = uuid.uuid4().hex[:12]
    gcs_url = f"https://storage.googleapis.com/test-bucket/text-match-{suffix}/bg.jpg"
    cdn_url = f"https://cdn.example.invalid/test-bucket/text-match-{suffix}/bg.jpg"
    unique_prompt = f"e2e_gcs_align_prompt_{suffix}"

    agent_id = integration_client.create_agent(
        name=f"GCS Align Agent {suffix}",
        visibility="PUBLIC",
    )
    try:
        agent = db_session.query(Agent).filter(Agent.id == agent_id).first()
        assert agent is not None
        agent.background = gcs_url
        db_session.add(
            Resource(
                url=cdn_url,
                type=ResourceType.IMAGE,
                user_id=user_id,
                agent_id=agent_id,
                resource_metadata={
                    "gcs_url": gcs_url,
                    "generation_prompt": unique_prompt,
                    "creator": user_id,
                    "size": {"width": 1, "height": 1},
                    "content_type": "image/jpeg",
                    "byte_size": 1,
                    "compressed": False,
                    "cropped": False,
                },
            )
        )
        db_session.commit()

        response = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/ai/agents/recommend",
            params={
                "page": 1,
                "page_size": 10,
                "sort": "text_match_image_description",
                "match_description": unique_prompt,
                "match_top_n": 50,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload.get("code") == 200, payload
        items = payload["data"].get("matched_image_items") or []
        assert items, payload
        hit = next((x for x in items if x["agent_id"] == agent_id), None)
        assert hit is not None, items
        assert hit["image_description"] == unique_prompt
    finally:
        db_session.query(Resource).filter(Resource.url == cdn_url).delete()
        db_session.commit()
        integration_client.delete_agent(agent_id)
        db_user.is_superuser = was_super
        db_session.commit()


def test_recommend_agents_text_match_exclusive_empty_caption_falls_back_to_resource_prompt(
    integration_client: TestClient, db_session
):
    """exclusive_photos without caption still matches via resources.generation_prompt."""
    me_resp = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/users/me",
    )
    assert me_resp.status_code == 200, me_resp.text
    user_id = me_resp.json()["data"]["id"]
    db_user = db_session.query(User).filter(User.id == user_id).first()
    assert db_user is not None
    was_super = db_user.is_superuser
    db_user.is_superuser = True
    db_session.commit()

    suffix = uuid.uuid4().hex[:12]
    img_url = f"https://storage.googleapis.com/test-bucket/excl-{suffix}/p.jpg"
    unique_prompt = f"e2e_excl_fallback_{suffix}"

    agent_id = integration_client.create_agent(
        name=f"Excl Fallback {suffix}",
        visibility="PUBLIC",
    )
    try:
        agent = db_session.query(Agent).filter(Agent.id == agent_id).first()
        assert agent is not None
        agent.exclusive_photos = [
            {
                "image_url": img_url,
                "caption": "",
                "credits_required": 0,
            }
        ]
        db_session.add(
            Resource(
                url=img_url,
                type=ResourceType.IMAGE,
                user_id=user_id,
                agent_id=agent_id,
                resource_metadata={
                    "generation_prompt": unique_prompt,
                    "creator": user_id,
                    "size": {"width": 1, "height": 1},
                    "content_type": "image/jpeg",
                    "byte_size": 1,
                    "compressed": False,
                    "cropped": False,
                },
            )
        )
        db_session.commit()

        response = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/ai/agents/recommend",
            params={
                "page": 1,
                "page_size": 10,
                "sort": "text_match_image_description",
                "match_description": unique_prompt,
                "match_top_n": 50,
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload.get("code") == 200, payload
        items = payload["data"].get("matched_image_items") or []
        hit = next((x for x in items if x["agent_id"] == agent_id), None)
        assert hit is not None, items
        assert hit["image_description"] == unique_prompt
    finally:
        db_session.query(Resource).filter(Resource.url == img_url).delete()
        db_session.commit()
        integration_client.delete_agent(agent_id)
        db_user.is_superuser = was_super
        db_session.commit()


def test_recommend_agents_never_returns_private_even_for_superuser(
    integration_client: TestClient, db_session
):
    """验证 /recommend 对任何人（含 superuser）都不返回私有角色。"""
    private_agent_id = integration_client.create_agent(
        name=f"Private Agent {uuid.uuid4().hex[:6]}",
        visibility="PRIVATE",
    )
    public_agent_id = integration_client.create_agent(
        name=f"Public Agent {uuid.uuid4().hex[:6]}",
        visibility="PUBLIC",
    )

    try:
        guest_resp = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/ai/agents/recommend",
            params={"page": 1, "page_size": 50, "sort": "created_desc"},
        )
        assert guest_resp.status_code == 200, guest_resp.text
        guest_payload = guest_resp.json()
        assert guest_payload.get("code") == 200, guest_payload
        guest_ids = [item["id"] for item in guest_payload["data"]["list"]]
        assert private_agent_id not in guest_ids

        me_resp = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/users/me",
        )
        assert me_resp.status_code == 200, me_resp.text
        user_id = me_resp.json()["data"]["id"]
        db_user = db_session.query(User).filter(User.id == user_id).first()
        assert db_user is not None
        db_user.is_superuser = True
        db_session.commit()

        su_resp = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/ai/agents/recommend",
            params={"page": 1, "page_size": 50, "sort": "created_desc"},
        )
        assert su_resp.status_code == 200, su_resp.text
        su_payload = su_resp.json()
        assert su_payload.get("code") == 200, su_payload
        su_ids = [item["id"] for item in su_payload["data"]["list"]]
        assert private_agent_id not in su_ids
        assert public_agent_id in su_ids
    finally:
        # 恢复用户权限，避免影响后续测试
        try:
            me_resp = integration_client.client.get(
                f"{integration_client.base_url}/api/v1/users/me",
            )
            if me_resp.status_code == 200:
                user_id = me_resp.json()["data"]["id"]
                db_user = db_session.query(User).filter(User.id == user_id).first()
                if db_user is not None:
                    db_user.is_superuser = False
                    db_session.commit()
        finally:
            integration_client.delete_agent(private_agent_id)
            integration_client.delete_agent(public_agent_id)


def test_update_agent_adds_energy_points(
    integration_client: TestClient, db_session
):
    """验证用户可以通过更新接口为任意角色累计能量点数"""
    agent_id = integration_client.create_agent(
        name="Energy Points Test Agent", visibility="PUBLIC"
    )

    try:
        first_response = integration_client.client.put(
            f"{integration_client.base_url}/api/v1/ai/agents/{agent_id}",
            json={"energy_points": 25},
        )
        assert (
            first_response.status_code == 200
        ), f"Failed to add energy points: {first_response.text}"
        first_payload = first_response.json()
        assert (
            first_payload.get("energy_points") == 25
        ), f"API should report 25 energy points, got {first_payload}"

        db_session.expire_all()
        agent = db_session.query(Agent).filter(Agent.id == agent_id).first()
        assert agent is not None, "Agent should exist after energy update"
        assert agent.points == 25, f"Expected 25 points, got {agent.points}"

        second_response = integration_client.client.put(
            f"{integration_client.base_url}/api/v1/ai/agents/{agent_id}",
            json={"energy_points": 10},
        )
        assert (
            second_response.status_code == 200
        ), f"Failed to add more energy points: {second_response.text}"
        second_payload = second_response.json()
        assert (
            second_payload.get("energy_points") == 35
        ), f"API should report 35 energy points, got {second_payload}"

        db_session.expire_all()
        agent = db_session.query(Agent).filter(Agent.id == agent_id).first()
        assert agent.points == 35, f"Expected 35 points, got {agent.points}"

    finally:
        integration_client.delete_agent(agent_id)
