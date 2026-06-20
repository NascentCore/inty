import copy
import uuid

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.agent import Agent, AgentStatus, AgentVisibility
from app.models.user import AuthType, Gender, User


def test_agent_extensions_field():
    """测试 Agent 模型的 extensions 字段的读写操作"""

    # 数据库连接配置
    DATABASE_URL = global_config_loaded_from_config_yaml.database.url

    # 创建数据库引擎和会话
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # 创建会话
    db = SessionLocal()

    # 1. 首先创建一个测试用户
    user_id = f"test-user-{uuid.uuid4().hex[:8]}"
    user_readable_id = f"user{uuid.uuid4().hex[:4]}"

    test_user = User(
        id=user_id,
        readable_id=user_readable_id,
        auth_type=AuthType.PHONE,
        nickname="Test User",
        email="test@example.com",
        system_language="en",
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    # 2. 创建一个新的 Agent 记录，包含 extensions 数据
    agent_id = f"test-agent-{uuid.uuid4().hex[:8]}"
    readable_id = f"test{uuid.uuid4().hex[:4]}"

    # 初始 extensions 数据
    initial_extensions = {
        "custom_settings": {
            "data": "initial_data",
        },
    }

    # 创建 Agent 实例
    new_agent = Agent(
        id=agent_id,
        readable_id=readable_id,
        name="测试角色",
        gender=Gender.FEMALE,
        avatar="https://example.com/avatar.jpg",
        intro="这是一个测试角色",
        opening="你好！我是测试角色",
        visibility=AgentVisibility.PUBLIC,
        status=AgentStatus.APPROVED,
        extensions=initial_extensions,
        creator_id=test_user.id,  # Use the created user's ID
    )

    # 保存到数据库
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    # 2. 读取 extensions 数据
    retrieved_agent = db.query(Agent).filter(Agent.id == agent_id).first()

    assert retrieved_agent is not None, "Agent 应该存在"
    assert retrieved_agent.extensions is not None, "extensions 字段不应该为空"

    # 验证读取的数据
    assert retrieved_agent.extensions == initial_extensions

    updated_extensions = copy.deepcopy(initial_extensions)
    updated_extensions["new_section"] = {
        "data": "completely_new_data",
    }

    # 更新 extensions
    retrieved_agent.extensions = updated_extensions
    db.commit()
    db.refresh(retrieved_agent)

    # 4. 验证修改后的数据
    final_agent = db.query(Agent).filter(Agent.id == agent_id).first()

    assert (
        final_agent.extensions == updated_extensions
    ), "新增字段 new_section 应该在 JSON 字段内"

    # 5. 测试部分更新（只更新 extensions 中的特定字段）
    partial_update = copy.deepcopy(final_agent.extensions)
    partial_update["custom_settings"]["data"] = "updated_data"
    partial_update["new_section"]["data"] = "completely_new_data_2"

    final_agent.extensions = partial_update
    db.commit()
    db.refresh(final_agent)

    # 验证部分更新
    assert (
        final_agent.extensions == partial_update
    ), "部分更新后的字段值应该更新正确"

    # 6. 测试清空 extensions
    final_agent.extensions = None
    db.commit()
    db.refresh(final_agent)

    assert final_agent.extensions is None, "清空 extensions 后应该为 None"

    # 7. 测试空对象
    final_agent.extensions = {}
    db.commit()
    db.refresh(final_agent)

    assert final_agent.extensions == {}, "空对象应该为空对象"
    db.close()
