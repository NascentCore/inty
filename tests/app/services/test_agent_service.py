import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi import HTTPException
from google.cloud import storage
from loguru import logger
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.agent import Agent
from app.models.chat import Chat
from app.models.user import AuthType, Gender, User
from app.api.deps import get_async_db
from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal
from app.external_services.gcs import (
    download_from_gcs,
    get_bucket_and_path_from_gcs_url,
    get_gcs_client,
)
from app.models.agent import AgentVisibility
from app.schemas.agent import AgentSortOption, AgentUpdate, ModelConfig
from app.schemas.agent import AgentCreate
from app.schemas.user import User as UserSchema
from app.schemas.user import UserCreate
from app.services import agent_service
from app.services.agent_service import (
    _crop_avatar_from_background,
    _update_agent_in_db,
    get_balanced_score_based_agents,
    get_user_agents,
)

admin_user = None


class DummyUserWithGender:
    """Minimal user-like object with gender for recommend_agents_paginated tests."""

    def __init__(
        self, user_id: str, nickname: str, is_superuser: bool, gender=None
    ):
        self.id = user_id
        self.nickname = nickname
        self.is_superuser = is_superuser
        self.gender = gender


@pytest.fixture
async def db_session():
    """Provide a database session for testing with proper cleanup."""
    # Create a new engine for this test to avoid shared connection issues
    engine = create_async_engine(
        str(global_config_loaded_from_config_yaml.database.async_url),
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )

    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    # create default admin user (superuser for recommend API tests)
    global admin_user
    async with async_session() as session:
        user_id = str(uuid.uuid4())
        readable_id = str(uuid.uuid4().int)[:8]
        admin_user = User(
            id=user_id,
            readable_id=readable_id,
            auth_type=AuthType.PHONE,
            nickname="admin",
            email="admin@sxwl.ai",
            system_language="en",
            is_superuser=True,
        )
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

    async with async_session() as session:
        yield session

    # Properly dispose of the engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_crop_avatar_from_background():
    random_filename = f"frontal-{uuid.uuid4().hex}"
    expected_avatar_url = f"https://storage.googleapis.com/yx-test/{random_filename}-cropped-avatar.png"
    bucket_name, path = get_bucket_and_path_from_gcs_url(expected_avatar_url)
    gcs_client = get_gcs_client()
    bucket = gcs_client.bucket(bucket_name)

    assert not bucket.blob(path).exists()

    # 上传 tests/files/frontal.png
    with open("tests/files/frontal.png", "rb") as f:
        file_content = f.read()
    gcs_client.bucket("yx-test").blob(
        f"{random_filename}.png"
    ).upload_from_string(file_content)

    crop_avatar_result = await _crop_avatar_from_background(
        f"https://storage.cloud.google.com/yx-test/{random_filename}.png",
    )
    cropped_avatar_url = crop_avatar_result.avatar_url
    gcs_cfg = global_config_loaded_from_config_yaml.gcs
    if gcs_cfg.use_fake_gcs:
        expected_file_uri = (
            (
                Path(gcs_cfg.fake_gcs_base_dir).resolve()
                / "yx-test"
                / f"{random_filename}-cropped-avatar.png"
            )
            .resolve()
            .as_uri()
        )
        assert cropped_avatar_url == expected_file_uri
    else:
        assert cropped_avatar_url == expected_avatar_url
    logger.info(f"Cropped avatar URL: {cropped_avatar_url}")
    # 本地运行时，可以打开图片查看
    # jpe_data = download_from_gcs(cropped_avatar_url)
    # image = Image.open(io.BytesIO(jpe_data))
    # image.show()


def test_update_agent_in_db():
    """Test _update_agent_in_db function with llm_config update"""

    # Create a test user for this test
    test_user_id = str(uuid.uuid4())

    # Note: This test only validates in-memory object updates, not database constraints
    # The creator_id doesn't need to exist in the database since we're not saving
    agent_in_db = Agent(
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

    # Convert AgentUpdate to dict for the updated function signature
    update_data = agent_update.model_dump(exclude_unset=True)
    _update_agent_in_db(update_data, agent_in_db)

    # Verify agent attributes were updated
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

    # Convert AgentUpdate to dict for the updated function signature
    update_data = agent_update.model_dump(exclude_unset=True)
    _update_agent_in_db(update_data, agent_in_db)

    # Verify agent attributes were updated
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

    # Test with valid URLs
    agent_data = {
        "name": "Test Agent",
        "avatar": "https://storage.googleapis.com/test-bucket/avatar.jpg",
        "background": "https://storage.googleapis.com/test-bucket/background.jpg",
        "background_images": [
            "https://storage.googleapis.com/test-bucket/photo1.jpg",
            "https://storage.googleapis.com/test-bucket/photo2.jpg",
        ],
    }

    # Mock the is_valid_gcs_url function to return True for all URLs
    with patch("app.external_services.gcs.is_valid_gcs_url", return_value=True):
        result = process_agent_image_urls(agent_data)

        # Verify that all image URLs are collected in background_images
        assert result["background_images"] == [
            "https://storage.googleapis.com/test-bucket/avatar.jpg",
            "https://storage.googleapis.com/test-bucket/background.jpg",
            "https://storage.googleapis.com/test-bucket/photo1.jpg",
            "https://storage.googleapis.com/test-bucket/photo2.jpg",
        ]
        assert (
            result["avatar"]
            == "https://storage.googleapis.com/test-bucket/avatar.jpg"
        )
        assert (
            result["background"]
            == "https://storage.googleapis.com/test-bucket/background.jpg"
        )


@pytest.mark.asyncio
async def test_update_agent_increments_version(db_session, monkeypatch):
    """确保更新Agent时版本号自增"""

    agent = Agent(
        id=str(uuid.uuid4()),
        readable_id="verstest",
        name="Version Test Agent",
        gender=Gender.FEMALE,
        creator_id=admin_user.id,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    assert agent.version == 1

    class DummyCacheService:
        def __init__(self):
            self.invalidated = []

        def invalidate_agent_config(self, agent_id: str) -> bool:
            self.invalidated.append(agent_id)
            return True

    dummy_cache = DummyCacheService()
    dummy_agent_manager = type("DummyAgentManager", (), {})()
    dummy_agent_manager.reload_agent = AsyncMock(return_value=True)

    monkeypatch.setattr(agent_service, "cache_service", dummy_cache)
    monkeypatch.setattr(agent_service, "agent_manager", dummy_agent_manager)

    agent_update = AgentUpdate(name="Updated Name")
    updated_agent = await agent_service.update_agent(
        db_session, agent, agent_update
    )

    assert updated_agent.version == 2
    assert dummy_cache.invalidated == [agent.id]


# TODO: See how to test the ordering of the agents returned from get_balanced_score_based_agents.
# The ordering is deterministic but determined by random seed.
# Also the database can have values from other tests.


@pytest.mark.asyncio
async def test_get_balanced_score_based_agents_pagination(db_session):
    """
    Test that the agents returned from get_balanced_score_based_agents are paginated correctly.
    """
    test_id = str(uuid.uuid4())[:4]  # Use only 4 chars to leave room for index

    for i in range(10):
        db_session.add(
            Agent(
                id=f"test-agent-{test_id}-{i}",
                readable_id=f"{test_id}{i:04d}",  # 4 + 4 = 8 chars max
                name=f"Test Agent {i}",
                gender="FEMALE",
                meta_data={"score": i},
                creator_id=admin_user.id,
            )
        )
    await db_session.commit()

    # Get the agents with balanced score based on the score
    part1 = await get_balanced_score_based_agents(db_session, 1, 3)
    part2 = await get_balanced_score_based_agents(db_session, 2, 3)
    part3 = await get_balanced_score_based_agents(db_session, 3, 3)
    one_part = await get_balanced_score_based_agents(db_session, 1, 9)
    assert one_part == part1 + part2 + part3


@pytest.mark.asyncio
async def test_get_balanced_score_based_agents_stable_with_sort_seed(
    db_session,
):
    """
    Test that the agents returned from get_balanced_score_based_agents are stable with the same sort seed.
    """
    test_id = str(uuid.uuid4())[:4]  # Use only 4 chars to leave room for index

    for i in range(10):
        db_session.add(
            Agent(
                id=f"test-agent-seed-{test_id}-{i}",
                readable_id=f"{test_id}{i:04d}",  # 4 + 4 = 8 chars max
                name=f"Test Seed Agent {i}",
                gender="FEMALE",
                meta_data={"score": i},
                creator_id=admin_user.id,
            )
        )
    await db_session.commit()

    # Get the agents with balanced score based on the score
    agents = await get_balanced_score_based_agents(
        db_session, 1, 10, "test-seed"
    )
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


@pytest.mark.asyncio
async def test_get_balanced_score_based_agents_female_user_opposite_gender_first(
    db_session,
):
    """
    女性用户时，所有男性角色排在任意女性/OTHER 之前（确定性）。
    """
    test_id = str(uuid.uuid4())[:4]
    for i in range(4):
        db_session.add(
            Agent(
                id=f"test-male-{test_id}-{i}",
                readable_id=f"m{test_id}{i:02d}"[:8],
                name=f"Male Agent {i}",
                gender=Gender.MALE,
                meta_data={"score": 5},
                visibility=AgentVisibility.PUBLIC,
                creator_id=admin_user.id,
            )
        )
    for i in range(4):
        db_session.add(
            Agent(
                id=f"test-female-{test_id}-{i}",
                readable_id=f"f{test_id}{i:02d}"[:8],
                name=f"Female Agent {i}",
                gender=Gender.FEMALE,
                meta_data={"score": 5},
                visibility=AgentVisibility.PUBLIC,
                creator_id=admin_user.id,
            )
        )
    await db_session.commit()

    agents = await get_balanced_score_based_agents(
        db_session, 1, 20, "gender-seed", None, Gender.FEMALE
    )
    male_indices = [i for i, a in enumerate(agents) if a.gender == Gender.MALE]
    female_other_indices = [
        i for i, a in enumerate(agents) if a.gender != Gender.MALE
    ]
    if male_indices and female_other_indices:
        assert max(male_indices) < min(
            female_other_indices
        ), "All MALE agents must appear before any FEMALE/OTHER when user is FEMALE"


@pytest.mark.asyncio
async def test_get_recommended_agents_paginated_excludes_private_always(
    db_session,
):
    """推荐列表始终只返回公开角色，超级用户也不会看到私有角色。"""
    test_id = str(uuid.uuid4())[:6]

    public_agent = Agent(
        id=f"test-reco-public-{test_id}",
        readable_id=f"rp{test_id}"[:8],
        name=f"Reco Public {test_id}",
        gender=Gender.FEMALE,
        visibility=AgentVisibility.PUBLIC,
        creator_id=admin_user.id,
    )
    private_agent = Agent(
        id=f"test-reco-private-{test_id}",
        readable_id=f"rv{test_id}"[:8],
        name=f"Reco Private {test_id}",
        gender=Gender.FEMALE,
        visibility=AgentVisibility.PRIVATE,
        creator_id=admin_user.id,
    )
    db_session.add(public_agent)
    db_session.add(private_agent)
    await db_session.commit()

    class DummyUser:
        def __init__(self, user_id: str, nickname: str, is_superuser: bool):
            self.id = user_id
            self.nickname = nickname
            self.is_superuser = is_superuser

    normal_user = DummyUser("test-user-normal", "normal", False)
    super_user = DummyUser("test-user-super", "super", True)

    normal_page = await agent_service.get_recommended_agents_paginated(
        db_session,
        current_user=normal_user,  # type: ignore[arg-type]
        page=1,
        page_size=50,
        sort_by=AgentSortOption.CREATED_DESC,
    )
    normal_ids = {agent.id for agent in normal_page.list}
    assert public_agent.id in normal_ids
    assert private_agent.id not in normal_ids

    super_page = await agent_service.get_recommended_agents_paginated(
        db_session,
        current_user=super_user,  # type: ignore[arg-type]
        page=1,
        page_size=50,
        sort_by=AgentSortOption.CREATED_DESC,
    )
    super_ids = {agent.id for agent in super_page.list}
    assert public_agent.id in super_ids
    assert private_agent.id not in super_ids


@pytest.mark.asyncio
async def test_get_recommended_agents_paginated_created_desc_with_gender_filters_by_opposite(
    db_session,
):
    """CREATED_DESC_WITH_GENDER: MALE user gets only FEMALE agents; FEMALE user gets only MALE agents."""
    test_id = str(uuid.uuid4())[:6]
    agents = [
        Agent(
            id=f"test-gender-{test_id}-f{i}",
            readable_id=f"gf{i}{test_id}"[:8],
            name=f"Female {i} {test_id}",
            gender=Gender.FEMALE,
            visibility=AgentVisibility.PUBLIC,
            creator_id=admin_user.id,
        )
        for i in range(2)
    ] + [
        Agent(
            id=f"test-gender-{test_id}-m{i}",
            readable_id=f"gm{i}{test_id}"[:8],
            name=f"Male {i} {test_id}",
            gender=Gender.MALE,
            visibility=AgentVisibility.PUBLIC,
            creator_id=admin_user.id,
        )
        for i in range(2)
    ]
    for a in agents:
        db_session.add(a)
    await db_session.commit()

    male_user = DummyUserWithGender("u-male", "male", False, Gender.MALE)
    page_male = await agent_service.get_recommended_agents_paginated(
        db_session,
        current_user=male_user,  # type: ignore[arg-type]
        page=1,
        page_size=10,
        sort_by=AgentSortOption.CREATED_DESC_WITH_OPPOSITE_GENDER,
    )
    assert all(a.gender == Gender.FEMALE for a in page_male.list)

    female_user = DummyUserWithGender(
        "u-female", "female", False, Gender.FEMALE
    )
    page_female = await agent_service.get_recommended_agents_paginated(
        db_session,
        current_user=female_user,  # type: ignore[arg-type]
        page=1,
        page_size=10,
        sort_by=AgentSortOption.CREATED_DESC_WITH_OPPOSITE_GENDER,
    )
    assert all(a.gender == Gender.MALE for a in page_female.list)


@pytest.mark.asyncio
async def test_get_recommended_agents_paginated_created_desc_with_gender_other_no_filter(
    db_session,
):
    """CREATED_DESC_WITH_GENDER with user gender OTHER or None: no gender filter, same as created_desc."""
    test_id = str(uuid.uuid4())[:6]
    agent = Agent(
        id=f"test-gender-other-{test_id}",
        readable_id=f"go{test_id}"[:8],
        name=f"Agent Other {test_id}",
        gender=Gender.FEMALE,
        visibility=AgentVisibility.PUBLIC,
        creator_id=admin_user.id,
    )
    db_session.add(agent)
    await db_session.commit()

    desc_page = await agent_service.get_recommended_agents_paginated(
        db_session,
        current_user=DummyUserWithGender("u", "u", False, Gender.OTHER),  # type: ignore[arg-type]
        page=1,
        page_size=10,
        sort_by=AgentSortOption.CREATED_DESC,
    )
    with_gender_other_page = await agent_service.get_recommended_agents_paginated(
        db_session,
        current_user=DummyUserWithGender("u", "u", False, Gender.OTHER),  # type: ignore[arg-type]
        page=1,
        page_size=10,
        sort_by=AgentSortOption.CREATED_DESC_WITH_OPPOSITE_GENDER,
    )
    assert desc_page.total == with_gender_other_page.total
    assert {a.id for a in desc_page.list} == {
        a.id for a in with_gender_other_page.list
    }

    with_gender_none_page = await agent_service.get_recommended_agents_paginated(
        db_session,
        current_user=DummyUserWithGender("u", "u", False, None),  # type: ignore[arg-type]
        page=1,
        page_size=10,
        sort_by=AgentSortOption.CREATED_DESC_WITH_OPPOSITE_GENDER,
    )
    assert desc_page.total == with_gender_none_page.total


@pytest.mark.asyncio
async def test_get_user_agents_returns_created_agents_ordered_by_created_at(
    db_session,
):
    """
    单元测试 get_user_agents：使用本地数据库（config 见 devops/config.yaml.test），
    验证返回当前用户创建的、未删除的 agents，按 created_at 降序，并设置 agent.user。
    """
    test_id = str(uuid.uuid4())[:8]
    user_id = str(uuid.uuid4())
    readable_id = str(uuid.uuid4().int)[:8]

    db_user = User(
        id=user_id,
        readable_id=readable_id,
        auth_type=AuthType.PHONE,
        nickname="TestCreator",
        email="creator@test.local",
        system_language="en",
        is_superuser=False,
    )
    db_session.add(db_user)
    await db_session.flush()

    agent_a = Agent(
        id=f"test-ua-a-{test_id}",
        readable_id=f"uaa{test_id}"[:8],
        name=f"Agent A {test_id}",
        gender=Gender.FEMALE,
        visibility=AgentVisibility.PUBLIC,
        creator_id=db_user.id,
    )
    agent_b = Agent(
        id=f"test-ua-b-{test_id}",
        readable_id=f"uab{test_id}"[:8],
        name=f"Agent B {test_id}",
        gender=Gender.FEMALE,
        visibility=AgentVisibility.PUBLIC,
        creator_id=db_user.id,
    )
    db_session.add(agent_a)
    db_session.add(agent_b)
    await db_session.commit()
    await db_session.refresh(db_user)
    await db_session.refresh(agent_a)
    await db_session.refresh(agent_b)

    current_user = UserSchema.model_validate(db_user)

    agents = await get_user_agents(db_session, current_user, skip=0, limit=100)
    assert len(agents) == 2
    ids = [a.id for a in agents]
    assert agent_a.id in ids and agent_b.id in ids
    # 按 created_at 降序，后创建的在前（agent_b 后 add，通常后 commit 故 created_at 可能更晚）
    assert (
        ids[0] == agent_b.id
        and ids[1] == agent_a.id
        or ids[0] == agent_a.id
        and ids[1] == agent_b.id
    )
    for agent in agents:
        assert agent.user == "TestCreator"

    # 无 nickname 时应为 "you"
    db_user.nickname = None
    current_user_no_nick = UserSchema.model_validate(db_user)
    agents2 = await get_user_agents(
        db_session, current_user_no_nick, skip=0, limit=100
    )
    for agent in agents2:
        assert agent.user == "you"


@pytest.mark.asyncio
async def test_get_user_agents_empty_when_no_agents(db_session):
    """用户未创建任何 agent 时返回空列表。"""
    test_id = str(uuid.uuid4())[:8]
    user_id = str(uuid.uuid4())
    readable_id = str(uuid.uuid4().int)[:8]
    db_user = User(
        id=user_id,
        readable_id=readable_id,
        auth_type=AuthType.PHONE,
        nickname="NoAgents",
        email="noagents@test.local",
        system_language="en",
        is_superuser=False,
    )
    db_session.add(db_user)
    await db_session.commit()
    await db_session.refresh(db_user)
    current_user = UserSchema.model_validate(db_user)

    agents = await get_user_agents(db_session, current_user)
    assert agents == []


@pytest.mark.asyncio
async def test_get_user_agents_validation_skip_negative():
    """skip < 0 时抛出 HTTPException 400。"""
    mock_db = MagicMock()
    mock_user = UserSchema(
        id="u",
        readable_id="r",
        auth_type="PHONE",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        is_superuser=False,
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_user_agents(mock_db, mock_user, skip=-1)
    assert exc_info.value.status_code == 400
    assert "cannot be negative" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_user_agents_validation_limit_invalid():
    """limit <= 0 或 > 1000 时抛出 HTTPException 400。"""
    mock_db = MagicMock()
    mock_user = UserSchema(
        id="u",
        readable_id="r",
        auth_type="PHONE",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        is_superuser=False,
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_user_agents(mock_db, mock_user, skip=0, limit=0)
    assert exc_info.value.status_code == 400
    with pytest.raises(HTTPException) as exc_info2:
        await get_user_agents(mock_db, mock_user, skip=0, limit=1001)
    assert exc_info2.value.status_code == 400


@pytest.mark.asyncio
async def test_get_agent_follow_fields_are_defaults_without_follow_table(
    db_session,
):
    """get_agent 不再依赖 agent_followers，关注字段返回默认值。"""
    creator = User(
        id=str(uuid.uuid4()),
        readable_id=str(uuid.uuid4().int)[:8],
        auth_type=AuthType.PHONE,
        nickname="creator",
        email=f"creator-{uuid.uuid4().hex[:8]}@example.com",
        system_language="en",
        is_superuser=False,
    )
    viewer = User(
        id=str(uuid.uuid4()),
        readable_id=str(uuid.uuid4().int)[:8],
        auth_type=AuthType.PHONE,
        nickname="viewer",
        email=f"viewer-{uuid.uuid4().hex[:8]}@example.com",
        system_language="en",
        is_superuser=False,
    )
    db_session.add_all([creator, viewer])
    await db_session.flush()

    agent = Agent(
        id=str(uuid.uuid4()),
        readable_id=str(uuid.uuid4().int)[:8],
        name=f"agent-{uuid.uuid4().hex[:6]}",
        gender=Gender.FEMALE,
        visibility=AgentVisibility.PUBLIC,
        creator_id=creator.id,
    )
    db_session.add(agent)
    await db_session.flush()

    chat = Chat(
        id=str(uuid.uuid4()),
        user_id=viewer.id,
        agent_id=agent.id,
        is_active=True,
    )
    db_session.add(chat)
    await db_session.commit()

    loaded_agent = await agent_service.get_agent(
        db_session, agent_id=agent.id, current_user_id=viewer.id
    )
    assert loaded_agent is not None
    assert loaded_agent.follower_count == 0
    assert loaded_agent.is_followed is False
    assert loaded_agent.connector_count == 1


@pytest.mark.asyncio
async def test_follow_unfollow_agent_returns_410():
    """关注相关接口已下线，返回 410。"""
    for action in [agent_service.follow_agent, agent_service.unfollow_agent]:
        with pytest.raises(HTTPException) as exc_info:
            await action(db=None, agent_id="a", user_id="u")  # type: ignore[arg-type]
        assert exc_info.value.status_code == 410


@pytest.mark.asyncio
async def test_get_user_followed_agents_returns_410():
    """用户关注列表接口已下线，返回 410。"""
    with pytest.raises(HTTPException) as exc_info:
        await agent_service.get_user_followed_agents(  # type: ignore[arg-type]
            db=None,
            user_id="u",
            page=1,
            page_size=10,
        )
    assert exc_info.value.status_code == 410


@pytest.mark.asyncio
async def test_create_agent_enqueues_opening_voice_generation(
    db_session, monkeypatch
):
    """创建 Agent 时只投递后台任务，不在当前调用中等待语音生成。"""
    user = User(
        id=str(uuid.uuid4()),
        readable_id=str(uuid.uuid4().int)[:8],
        auth_type=AuthType.PHONE,
        nickname="creator",
        email=f"creator-{uuid.uuid4().hex[:8]}@example.com",
        system_language="en",
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    enqueue_calls = []

    def fake_enqueue(agent_id: str, expected_version: int) -> None:
        enqueue_calls.append((agent_id, expected_version))

    generate_mock = AsyncMock()
    monkeypatch.setattr(
        agent_service,
        "_enqueue_agent_opening_voice_generation",
        fake_enqueue,
    )
    monkeypatch.setattr(
        agent_service, "generate_agent_opening_voice", generate_mock
    )

    agent_in = AgentCreate(
        name="Create Async Voice Agent",
        gender="FEMALE",
        opening="Hello there.",
    )
    created_agent = await agent_service.create_agent(
        db_session,
        agent_in=agent_in,
        user_id=user.id,
    )

    assert enqueue_calls == [(created_agent.id, created_agent.version)]
    generate_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_agent_enqueues_opening_voice_generation(
    db_session, monkeypatch
):
    """更新 opening 时只投递后台任务，不在当前调用中等待语音生成。"""
    user = User(
        id=str(uuid.uuid4()),
        readable_id=str(uuid.uuid4().int)[:8],
        auth_type=AuthType.PHONE,
        nickname="creator",
        email=f"creator-{uuid.uuid4().hex[:8]}@example.com",
        system_language="en",
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()

    agent = Agent(
        id=str(uuid.uuid4()),
        readable_id=str(uuid.uuid4().int)[:8],
        name="Update Async Voice Agent",
        gender=Gender.FEMALE,
        opening="Old opening",
        creator_id=user.id,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    class DummyCacheService:
        def invalidate_agent_config(self, agent_id: str) -> bool:
            return bool(agent_id)

    dummy_agent_manager = type("DummyAgentManager", (), {})()
    dummy_agent_manager.reload_agent = AsyncMock(return_value=True)

    enqueue_calls = []

    def fake_enqueue(agent_id: str, expected_version: int) -> None:
        enqueue_calls.append((agent_id, expected_version))

    generate_mock = AsyncMock()
    monkeypatch.setattr(agent_service, "cache_service", DummyCacheService())
    monkeypatch.setattr(agent_service, "agent_manager", dummy_agent_manager)
    monkeypatch.setattr(
        agent_service,
        "_enqueue_agent_opening_voice_generation",
        fake_enqueue,
    )
    monkeypatch.setattr(
        agent_service, "generate_agent_opening_voice", generate_mock
    )

    updated_agent = await agent_service.update_agent(
        db_session,
        db_agent=agent,
        agent_in=AgentUpdate(opening="New opening"),
    )

    assert enqueue_calls == [(updated_agent.id, updated_agent.version)]
    generate_mock.assert_not_awaited()
