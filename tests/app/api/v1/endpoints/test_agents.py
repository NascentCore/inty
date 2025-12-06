import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.core.security import create_access_token
from app.core.uuid import get_new_user_id
from app.models.agent import Agent
from app.models.subscription import SubscriptionUsage
from app.models.user import AuthType, Gender, User
from app.services.user_service import generate_next_readable_id_sync
from tests.app.api.test_client import TestClient


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
    # 创建多个 agent，设置不同的 points 值
    agent_ids = []
    points_values = [100, 50, 200, 0, 150]  # 降序应该是: 200, 150, 100, 50, 0

    for i, points in enumerate(points_values):
        agent_id = integration_client.create_agent(
            name=f"Test Agent Points {points}",
            visibility="PUBLIC",
        )
        agent_ids.append(agent_id)

        # 直接更新数据库中的 points 值
        agent = db_session.query(Agent).filter(Agent.id == agent_id).first()
        assert agent is not None, f"Agent {agent_id} not found in database"
        agent.points = points
        db_session.commit()

    try:
        # 调用 recommend API，使用 energy_points 排序
        response = integration_client.client.get(
            f"{integration_client.base_url}/api/v1/ai/agents/recommend",
            params={
                "page": 1,
                "page_size": 10,
                "sort": "energy_points",
            },
        )

        # 验证响应
        assert response.status_code == 200, f"Request failed: {response.text}"
        response_data = response.json()
        assert response_data.get("code") == 200, f"API error: {response_data}"

        # 验证返回的数据结构
        data = response_data["data"]
        assert "list" in data, "Response should contain 'list' field"
        assert "total" in data, "Response should contain 'total' field"
        assert "page" in data, "Response should contain 'page' field"
        assert "page_size" in data, "Response should contain 'page_size' field"

        items = data["list"]
        assert isinstance(items, list), "List should be a list"

        # 查找我们创建的 agents（可能还有其他公开的 agents）
        our_agents = [
            item for item in items if item["id"] in agent_ids
        ]

        # 验证我们的 agents 按 points 降序排列
        # 由于 points 字段不在 API 响应中，我们需要从数据库查询 points 值
        if len(our_agents) >= 2:
            # 创建一个 agent_id 到 points 的映射
            agent_points_map = {}
            for agent_id in agent_ids:
                agent = db_session.query(Agent).filter(Agent.id == agent_id).first()
                if agent:
                    agent_points_map[agent_id] = agent.points

            # 验证排序：每个 agent 的 points 应该大于或等于下一个 agent 的 points
            for i in range(len(our_agents) - 1):
                current_agent_id = our_agents[i]["id"]
                next_agent_id = our_agents[i + 1]["id"]
                current_points = agent_points_map.get(current_agent_id, 0)
                next_points = agent_points_map.get(next_agent_id, 0)
                assert (
                    current_points >= next_points
                ), f"Agents should be sorted in descending order by points. "
                f"Agent {current_agent_id} (points={current_points}) should come before "
                f"Agent {next_agent_id} (points={next_points})"

        # 验证分页功能
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
        # 清理：删除创建的 agents
        for agent_id in agent_ids:
            integration_client.delete_agent(agent_id)
