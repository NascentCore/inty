import io
import uuid
from unittest.mock import patch

import pytest
from google.cloud import storage
from loguru import logger
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.api.deps import get_async_db
from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal
from app.external_services.gcs import (
    download_from_gcs,
    get_bucket_and_path_from_gcs_url,
)
from app.schemas.agent import AgentUpdate, ModelConfig
from app.schemas.user import UserCreate
from app.services.agent_service import (
    _crop_avatar_from_background,
    _update_agent_in_db,
    get_balanced_score_based_agents,
)

admin_user = None

@pytest.fixture
async def db_session():
    """Provide a database session for testing with proper cleanup."""
#用于测试创建一个新引擎共享连接问题
    engine = create_async_engine(
        str(global_config_loaded_from_config_yaml.database.async_url),
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )

    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
#创建默认管理员用户
    global admin_user
    async with async_session() as session:
        user_id = str(uuid.uuid4())
        readable_id = str(uuid.uuid4().int)[:8]
        admin_user = models.User(
            id=user_id,
            readable_id=readable_id,
            auth_type=models.AuthType.PHONE,
            nickname="admin",
            email="admin@sxwl.ai",
            system_language="en",
            is_active=True,
        )
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

    async with async_session() as session:
        yield session
# Pr 排气发动机
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Do not have access to gcs")
async def test_crop_avatar_from_background():
    bucket_name, path = get_bucket_and_path_from_gcs_url(
        "https://storage.googleapis.com/yx-test/Screenshot_20250815_213911-cropped-avatar.png")
    bucket = storage.Client.from_service_account_json(
        global_config_loaded_from_config_yaml.app.gcp_service_account_key
    ).bucket(bucket_name)
    try:
        bucket.blob(path).delete()
    except Exception:
        pass

    assert not bucket.blob(path).exists()

    crop_avatar_result = await _crop_avatar_from_background(
        "https://storage.cloud.google.com/yx-test/Screenshot_20250815_213911.png",
    )
    cropped_avatar_url = crop_avatar_result.avatar_url
    assert cropped_avatar_url == "https://storage.googleapis.com/yx-test/Screenshot_20250815_213911-cropped-avatar.png"
    logger.info(f"Cropped avatar URL: {cropped_avatar_url}")
    jpe_data = download_from_gcs(cropped_avatar_url)
    image = Image.open(io.BytesIO(jpe_data))
    image.show()


def test_update_agent_in_db():
    """Test _update_agent_in_db function with llm_config update"""
# 用于创建一个测试用户
    test_user_id = str(uuid.uuid4())
#注意：此测试仅验证内存中对象更新，不受验证数据库约束
# Creator_id 需要存在于数据库中，因为我们不保存
    agent_in_db = models.Agent(
        name="Original Agent",
        personality="Original personality",
        settings={"existing_setting": "value"},
        creator_id=test_user_id,
    )

    agent_update = AgentUpdate(
        name="Updated Agent",
        personality="New personality",
        llm_config=ModelConfig(
            model="anthropic/claude-3.5-sonnet",
            temperature=0.7,
            max_tokens=2048,
        ),
        creator_id=test_user_id,
    )
# 将 AgentUpdate 转换为 dict 以获取更新的函数签名
    update_data = agent_update.model_dump(exclude_unset=True)
    _update_agent_in_db(update_data, agent_in_db)
# 验证代理属性是否已更新
    agent_in_db_dict = {
        k: v for k, v in agent_in_db.__dict__.items() if not k.startswith("_")
    }
    assert agent_in_db_dict == {
        "name": "Updated Agent",
        "personality": "New personality",
        "settings": {
            "existing_setting": "value",
            "llm_config": {
                "max_tokens": 2048,
                "model": "anthropic/claude-3.5-sonnet",
                "temperature": 0.7,
            },
        },
        "creator_id": test_user_id,
    }

    agent_update = AgentUpdate(llm_config=None)
# 将 AgentUpdate 转换为 dict 以获取更新的函数签名
    update_data = agent_update.model_dump(exclude_unset=True)
    _update_agent_in_db(update_data, agent_in_db)
# 验证代理属性是否已更新
    agent_in_db_dict = {
        k: v for k, v in agent_in_db.__dict__.items() if not k.startswith("_")
    }
    assert agent_in_db_dict == {
        "name": "Updated Agent",
        "personality": "New personality",
        "settings": {
            "existing_setting": "value",
        },
        "creator_id": test_user_id,
    }, "llm_config should be removed"


def test_process_agent_image_urls():
    """Test process_agent_image_urls function with valid URLs"""
    from app.services.agent_service import process_agent_image_urls
# 使用有效的 URL 进行测试
    agent_data = {
        "name": "Test Agent",
        "avatar": "https://storage.googleapis.com/test-bucket/avatar.jpg",
        "background": "https://storage.googleapis.com/test-bucket/background.jpg",
        "background_images": [
            "https://storage.googleapis.com/test-bucket/photo1.jpg",
            "https://storage.googleapis.com/test-bucket/photo2.jpg",
        ],
    }
# 模拟 is_valid_gcs_url 函数，为所有URL返回True
    with patch("app.external_services.gcs.is_valid_gcs_url", return_value=True):
        result = process_agent_image_urls(agent_data)
# 验证background_images中是否收集了所有图像URL
        assert result["background_images"] == [
            "https://storage.googleapis.com/test-bucket/avatar.jpg",
            "https://storage.googleapis.com/test-bucket/background.jpg",
            "https://storage.googleapis.com/test-bucket/photo1.jpg",
            "https://storage.googleapis.com/test-bucket/photo2.jpg",
        ]
        assert (
            result["avatar"] == "https://storage.googleapis.com/test-bucket/avatar.jpg"
        )
        assert (
            result["background"]
            == "https://storage.googleapis.com/test-bucket/background.jpg"
        )
# TODO：了解如何测试从 get_balanced_score_based_agents 返回的代理的排序。
# 排序是确定性的，但由随机种子决定。
# 数据库也可以有来自其他测试的值。


@pytest.mark.asyncio
async def test_get_balanced_score_based_agents_pagination(db_session):
    """
    Test that the agents returned from get_balanced_score_based_agents are paginated correctly.
    """
    test_id = str(uuid.uuid4())[:4]  # Use only 4 chars to leave room for index

    for i in range(10):
        db_session.add(
            models.Agent(
                id=f"test-agent-{test_id}-{i}",
                readable_id=f"{test_id}{i:04d}",  # 4 + 4 = 8 chars max
                name=f"Test Agent {i}",
                gender="FEMALE",
                meta_data={"score": i},
                creator_id=admin_user.id,
            )
        )
    await db_session.commit()
#根据获取分数平衡分数的智能体
    part1 = await get_balanced_score_based_agents(db_session, 1, 3)
    part2 = await get_balanced_score_based_agents(db_session, 2, 3)
    part3 = await get_balanced_score_based_agents(db_session, 3, 3)
    one_part = await get_balanced_score_based_agents(db_session, 1, 9)
    assert one_part == part1 + part2 + part3


@pytest.mark.asyncio
async def test_get_balanced_score_based_agents_stable_with_sort_seed(db_session):
    """
    Test that the agents returned from get_balanced_score_based_agents are stable with the same sort seed.
    """
    test_id = str(uuid.uuid4())[:4]  # Use only 4 chars to leave room for index

    for i in range(10):
        db_session.add(
            models.Agent(
                id=f"test-agent-seed-{test_id}-{i}",
                readable_id=f"{test_id}{i:04d}",  # 4 + 4 = 8 chars max
                name=f"Test Seed Agent {i}",
                gender="FEMALE",
                meta_data={"score": i},
                creator_id=admin_user.id,
            )
        )
    await db_session.commit()
#根据获取分数平衡分数的智能体
    agents = await get_balanced_score_based_agents(db_session, 1, 10, "test-seed")
    first_query_results = [agent.id for agent in agents]

    second_query_agents = await get_balanced_score_based_agents(
        db_session, 1, 10, "test-seed"
    )
    second_query_results = [agent.id for agent in second_query_agents]

    assert (
        first_query_results == second_query_results
    ), "The results of the two queries should be the same"

    third_query_agents = await get_balanced_score_based_agents(
        db_session, 1, 10, "test-seed"
    )
    third_query_results = [agent.id for agent in third_query_agents]

    assert (
        first_query_results == third_query_results
    ), "The results of the two queries should be the same"
